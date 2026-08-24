"""Helper root à protocole fermé pour les mises à jour atomiques CliOS."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import errno
import json
import os
import re
import socket
import socketserver
import subprocess
import threading
import time
import uuid
from pathlib import Path

from src.release_catalog import CatalogError, ReleaseCatalog
from src.release_contract import ReleaseContractError, SemVer
from src.release_manager import (
    ReleaseCommandError,
    ReleaseDependencyError,
    ReleaseError,
    ReleaseManager,
)
from src.update_safety import ACTIVE_UPDATE_STATES, UpdateSafety


class UpdaterProtocolError(ValueError):
    pass


class UpdaterEngine:
    OPERATIONS = {
        "status": set(),
        "stage": {"version", "operation_id"},
        "activate": {"version", "operation_id"},
        "rollback": {"stable_only", "operation_id"},
    }

    def __init__(self, manager: ReleaseManager, catalog: ReleaseCatalog, status_path: str,
                 service_name: str = "clios.service", restart=None, health_timeout: float = 45.0,
                 update_safety: UpdateSafety | None = None):
        self.manager = manager
        self.catalog = catalog
        self.status_path = Path(status_path)
        self.service_name = service_name
        self.restart = restart or self._restart_service
        self.health_timeout = health_timeout
        self.update_safety = update_safety or UpdateSafety(status_path=status_path)
        self._lock = threading.Lock()
        self._status_lock = threading.RLock()
        self.trace_path = self.status_path.with_name("updater-operations.jsonl")
        self._active_operation_id = ""
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self.manager.progress_callback = self._progress
        self._recover_interrupted_operation()

    def _recover_interrupted_operation(self) -> None:
        previous = self._read_status()
        state = str(previous.get("state", "IDLE"))
        if state not in ACTIVE_UPDATE_STATES:
            return
        message = f"opération {state.lower()} interrompue au redémarrage du helper"
        previous.update({
            "state": "ERROR",
            "message": message,
            "error": {
                "code": "UPDATE_INTERRUPTED", "message": message,
                "phase": str(previous.get("phase", "operation")),
            },
        })
        self._write_status(previous)

    def handle(self, request: object) -> dict:
        if not isinstance(request, dict):
            raise UpdaterProtocolError("la requête doit être un objet JSON")
        operation = request.get("operation")
        if operation not in self.OPERATIONS:
            raise UpdaterProtocolError("opération inconnue")
        allowed = self.OPERATIONS[operation] | {"operation"}
        extra = set(request) - allowed
        if extra:
            raise UpdaterProtocolError("champs interdits: " + ", ".join(sorted(extra)))
        if operation == "status":
            return self.status()
        if not self._lock.acquire(blocking=False):
            raise ReleaseError("une opération updater est déjà en cours")
        try:
            operation_id = self._operation_id(request.get("operation_id"))
            if operation == "stage":
                return self.stage(self._version(request.get("version")), operation_id)
            if operation == "activate":
                return self.activate(self._version(request.get("version")), operation_id)
            stable_only = request.get("stable_only", False)
            if not isinstance(stable_only, bool):
                raise UpdaterProtocolError("stable_only doit être booléen")
            return self.rollback(stable_only, operation_id)
        finally:
            self._lock.release()

    def status(self) -> dict:
        state = self.manager._load_state()
        updater = self._read_status()
        updater.update({
            "active": state.get("active"),
            "previous": state.get("previous"),
            "last_stable": state.get("last_stable"),
            "pending_health": state.get("pending_health"),
            "channel": self.manager.get_channel(),
        })
        return updater

    def stage(self, version: str, operation_id: str | None = None) -> dict:
        operation_id = operation_id or uuid.uuid4().hex
        self._active_operation_id = operation_id
        self._write_status({
            "state": "DOWNLOADING", "operation": "stage", "version": version,
            "phase": "catalog", "progress": 1,
            "message": "Résolution de la release sur GitHub",
            "detail": "Lecture du catalogue et sélection des artefacts signés",
            "error": None, "operation_id": operation_id, "indeterminate": True,
        })
        self._start_heartbeat(operation_id)
        try:
            if self.update_safety.path_is_overlay(self.manager.install_root):
                error = ReleaseError(
                    "protection SD active: désactivez OverlayFS et redémarrez avant la mise à jour"
                )
                error.code = "OVERLAYFS"  # type: ignore[attr-defined]
                raise error
            manifest = self.catalog.find(version)
            self._write_status({
                "state": "DOWNLOADING", "operation": "stage", "version": version,
                "phase": "manifest", "progress": 4,
                "message": "Métadonnées GitHub vérifiées",
                "detail": "Le manifeste correspond à la version et à la plateforme",
                "last_manifest": manifest, "error": None,
                "operation_id": operation_id, "indeterminate": False,
            })
            target = self.manager.stage(manifest, strict=True)
            status = self._read_status()
            return {
                "state": "STAGED", "version": version, "path": str(target),
                "operation_id": operation_id, "sequence": status.get("sequence", 0),
            }
        except Exception as exc:
            self._record_error(exc)
            raise
        finally:
            self._stop_heartbeat()

    def activate(self, version: str, operation_id: str | None = None) -> dict:
        operation_id = operation_id or uuid.uuid4().hex
        self._active_operation_id = operation_id
        self._write_status({"state": "ACTIVATING", "operation": "activate", "version": version,
                            "phase": "activate", "progress": 99,
                            "message": "Activation atomique", "detail": "Bascule du lien current",
                            "error": None, "operation_id": operation_id, "indeterminate": True})
        try:
            marker = self.manager.state_root / f"health-{version}"
            marker.unlink(missing_ok=True)
            target = self.manager.activate(version)
            try:
                self.restart()
            except Exception:
                self.manager.rollback()
                raise
            threading.Thread(
                target=self._watch_first_boot,
                args=(version, marker, operation_id),
                daemon=True,
                name=f"HealthWatch-{version}",
            ).start()
            return {
                "state": "ACTIVATING", "version": version, "path": str(target),
                "operation_id": operation_id,
            }
        except Exception as exc:
            self._record_error(exc)
            raise

    def rollback(self, stable_only: bool, operation_id: str | None = None) -> dict:
        operation_id = operation_id or uuid.uuid4().hex
        self._active_operation_id = operation_id
        self._write_status({"state": "ACTIVATING", "operation": "rollback", "progress": 99,
                            "phase": "rollback", "message": "Rollback",
                            "detail": "Restauration de la release précédente", "error": None,
                            "operation_id": operation_id, "indeterminate": True})
        try:
            target = self.manager.rollback(stable_only=stable_only)
            try:
                self.restart()
            except Exception:
                self.manager.rollback()
                raise
            return {
                "state": "ACTIVATING", "version": target.name, "path": str(target),
                "operation_id": operation_id,
            }
        except Exception as exc:
            self._record_error(exc)
            raise

    @staticmethod
    def _version(value: object) -> str:
        if not isinstance(value, str):
            raise UpdaterProtocolError("version requise")
        try:
            return str(SemVer.parse(value))
        except ReleaseContractError as exc:
            raise UpdaterProtocolError(str(exc)) from exc

    @staticmethod
    def _operation_id(value: object) -> str:
        if value is None:
            return uuid.uuid4().hex
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,63}", value):
            raise UpdaterProtocolError("operation_id invalide")
        return value

    def _progress(self, state: str, progress: int, message: str, **details) -> None:
        current = self._read_status()
        phase = str(details.pop("phase", current.get("phase", "operation")))
        if str(current.get("operation_id", "")) == self._active_operation_id:
            progress = max(int(current.get("progress", 0) or 0), int(progress))
        current.update({
            "state": state, "progress": progress, "message": message,
            "phase": phase, "detail": message, "error": None,
            "operation_id": self._active_operation_id,
        })
        current.update(details)
        self._write_status(current)

    def _record_error(self, exc: Exception) -> None:
        code = self.error_code(exc)
        current = self._read_status()
        phase = str(current.get("phase", "operation"))
        raw_message = str(exc)
        message = f"Échec pendant {self._phase_label(phase)} : {raw_message}"
        diagnostic = self._exception_diagnostic(exc)
        current.update({
            "state": "ERROR", "message": message,
            "detail": self._error_hint(code, exc),
            "indeterminate": False,
            "error": {
                "code": code, "message": raw_message, "phase": phase,
                **diagnostic,
            },
        })
        self._write_status(current)

    @staticmethod
    def error_code(exc: Exception) -> str:
        explicit = getattr(exc, "code", None)
        if explicit:
            return str(explicit)
        message = str(exc).lower()
        if (
            isinstance(exc, PermissionError)
            or getattr(exc, "errno", None) in {errno.EPERM, errno.EACCES}
            or "permission" in message or "not permitted" in message or "privil" in message
        ):
            return "PRIVILEGE"
        if isinstance(exc, ReleaseDependencyError):
            return "DEPENDENCY_MISSING"
        if getattr(exc, "errno", None) == errno.ENOENT:
            return "NOT_FOUND"
        if isinstance(exc, subprocess.TimeoutExpired):
            return "SUBPROCESS_TIMEOUT"
        if isinstance(exc, subprocess.CalledProcessError):
            return "SUBPROCESS_FAILED"
        if "sha-256" in message or "sha256" in message:
            return "SHA256"
        if "signature" in message or "ed25519" in message:
            return "SIGNATURE"
        if getattr(exc, "errno", None) == errno.ENOSPC or "espace disque" in message or "no space" in message:
            return "DISK_SPACE"
        if "self-check" in message:
            return "SELF_CHECK"
        if (
            getattr(exc, "errno", None) in {errno.ENETDOWN, errno.ENETUNREACH, errno.ECONNRESET, errno.ETIMEDOUT}
            or "réseau" in message or "github inaccessible" in message or "timed out" in message
        ):
            return "NETWORK"
        return "UPDATE_ERROR"

    @staticmethod
    def _phase_label(phase: str) -> str:
        return {
            "catalog": "la résolution GitHub", "manifest": "la vérification du manifeste",
            "signature": "la vérification de signature", "archive": "le téléchargement de l'archive",
            "hash": "la vérification SHA-256", "extract": "l'extraction",
            "environment": "l'installation de l'environnement", "self_check": "le self-check",
            "precompile": "la précompilation", "activate": "l'activation",
            "rollback": "le rollback",
        }.get(phase, "la mise à jour")

    @staticmethod
    def _error_hint(code: str, exc: Exception) -> str:
        if code == "PRIVILEGE":
            return (
                "Le helper a été bloqué par une permission système. Consultez le journal "
                "clios-updater pour connaître l'appel refusé."
            )
        if code == "NETWORK":
            return "Vérifiez la connexion Internet ; aucun fichier actif n'a été remplacé."
        if code == "DISK_SPACE":
            return "Libérez de l'espace dans /opt/clios puis relancez le téléchargement."
        if code == "DEPENDENCY_MISSING":
            return "Installez la dépendance indiquée ou utilisez une release avec wheelhouse complet."
        if code == "NOT_FOUND":
            return "Un chemin requis est absent ; collectez le diagnostic updater avant de relancer."
        return f"Aucune release active n'a été remplacée. Détail système : {exc}"

    @staticmethod
    def _bounded(value: object, limit: int = 2048) -> str:
        text = str(value or "")
        return text if len(text) <= limit else text[:limit] + "…"

    def _exception_diagnostic(self, exc: Exception) -> dict:
        command = getattr(exc, "command", None) or getattr(exc, "cmd", None)
        stderr = getattr(exc, "stderr", "") or getattr(exc, "stdout", "")
        return {
            "exception_type": type(exc).__name__,
            "errno": getattr(exc, "errno", None),
            "returncode": getattr(exc, "returncode", None),
            "command": [str(part) for part in command] if isinstance(command, (list, tuple)) else str(command or ""),
            "stderr": self._bounded(stderr),
        }

    def _read_status(self) -> dict:
        with self._status_lock:
            try:
                payload = json.loads(self.status_path.read_text(encoding="utf-8"))
                return payload if isinstance(payload, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {"state": "IDLE", "progress": 0, "message": "", "sequence": 0}

    def _write_status(self, payload: dict) -> None:
        with self._status_lock:
            enriched = dict(payload)
            previous = self._read_status()
            now_ns = time.time_ns()
            now = now_ns // 1_000_000_000
            operation_id = str(enriched.get("operation_id", ""))
            previous_id = str(previous.get("operation_id", ""))
            if str(enriched.get("state", "")) in ACTIVE_UPDATE_STATES:
                if operation_id and operation_id != previous_id:
                    enriched["started_at"] = now
                    enriched["started_at_ns"] = now_ns
                else:
                    enriched.setdefault("started_at", int(previous.get("started_at", 0) or now))
                    enriched.setdefault("started_at_ns", int(previous.get("started_at_ns", 0) or now_ns))
            enriched["sequence"] = int(previous.get("sequence", 0) or 0) + 1
            enriched["updated_at"] = now
            enriched["updated_at_ns"] = now_ns
            enriched["updated_at_iso"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            enriched.setdefault("heartbeat_at_ns", now_ns)
            self.manager._write_json_atomic(self.status_path, enriched)
            self._append_trace(enriched)

    def _append_trace(self, status: dict) -> None:
        error = status.get("error") if isinstance(status.get("error"), dict) else {}
        event = {
            "operation_id": status.get("operation_id", ""),
            "sequence": status.get("sequence", 0),
            "updated_at": status.get("updated_at_iso", ""),
            "operation": status.get("operation", ""),
            "phase": status.get("phase", ""),
            "progress": status.get("progress", 0),
            "indeterminate": bool(status.get("indeterminate", False)),
            "bytes_received": status.get("bytes_received", 0),
            "bytes_total": status.get("bytes_total", 0),
            "command": error.get("command", status.get("command", "")),
            "exception_type": error.get("exception_type", ""),
            "errno": error.get("errno"),
            "returncode": error.get("returncode"),
            "stderr": self._bounded(error.get("stderr", "")),
        }
        try:
            self.trace_path.parent.mkdir(parents=True, exist_ok=True)
            if self.trace_path.exists() and self.trace_path.stat().st_size > 1024 * 1024:
                os.replace(self.trace_path, self.trace_path.with_suffix(".jsonl.1"))
            with self.trace_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError:
            # Le statut principal reste prioritaire, même si le journal détaillé est indisponible.
            pass

    def _start_heartbeat(self, operation_id: str) -> None:
        self._stop_heartbeat()
        self._heartbeat_stop.clear()

        def heartbeat() -> None:
            while not self._heartbeat_stop.wait(1.0):
                current = self._read_status()
                if current.get("operation_id") != operation_id or current.get("state") not in ACTIVE_UPDATE_STATES:
                    return
                if current.get("indeterminate"):
                    current["heartbeat_at_ns"] = time.time_ns()
                    self._write_status(current)

        self._heartbeat_thread = threading.Thread(
            target=heartbeat, daemon=True, name=f"UpdaterHeartbeat-{operation_id[:8]}",
        )
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        thread = self._heartbeat_thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=0.2)
        self._heartbeat_thread = None

    def _restart_service(self) -> None:
        command = ["systemctl", "restart", self.service_name]
        current = self._read_status()
        current["command"] = command
        current["indeterminate"] = True
        self._write_status(current)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        except FileNotFoundError as exc:
            raise ReleaseDependencyError("systemctl absent") from exc
        except subprocess.TimeoutExpired as exc:
            raise ReleaseCommandError(
                "redémarrage clios.service expiré", command,
                stderr=str(exc.stderr or exc.stdout or exc), code="SUBPROCESS_TIMEOUT",
            ) from exc
        if result.returncode:
            raise ReleaseCommandError(
                "redémarrage clios.service impossible", command,
                returncode=result.returncode, stderr=result.stderr or result.stdout,
            )

    def _watch_first_boot(self, version: str, marker: Path, operation_id: str) -> None:
        deadline = time.monotonic() + self.health_timeout
        while time.monotonic() < deadline:
            if marker.exists():
                with self._lock:
                    self.manager.mark_healthy(version)
                    self._write_status({"state": "IDLE", "version": version, "progress": 100,
                                        "phase": "complete", "indeterminate": False,
                                        "operation_id": operation_id,
                                        "message": "Premier démarrage validé", "error": None})
                return
            time.sleep(min(0.05, max(0.01, self.health_timeout)))
        with self._lock:
            state = self.manager._load_state()
            if state.get("pending_health") != version or state.get("active") != version:
                # Le lanceur a déjà demandé le rollback privilégié.
                return
            try:
                restored = self.manager.rollback()
                self._write_status({"state": "ERROR", "version": restored.name, "progress": 100,
                                    "phase": "first_boot", "indeterminate": False,
                                    "operation_id": operation_id,
                                    "message": f"{version} sans marqueur de santé; rollback automatique",
                                    "error": {"code": "HEALTH_TIMEOUT", "message": "premier démarrage non validé",
                                              "phase": "first_boot"}})
                self.restart()
            except Exception as exc:
                self._record_error(exc)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw = self.rfile.readline(4097)
        if not raw or len(raw) > 4096:
            self._reply_error("PROTOCOL", "requête absente ou trop longue")
            return
        try:
            request = json.loads(raw.decode("utf-8"))
            result = self.server.engine.handle(request)  # type: ignore[attr-defined]
            self._reply({"ok": True, "result": result, **result})
        except (json.JSONDecodeError, UnicodeDecodeError, UpdaterProtocolError) as exc:
            self._reply_error("PROTOCOL", str(exc))
        except (CatalogError, ReleaseError, OSError) as exc:
            self._reply_error(self.server.engine.error_code(exc), str(exc))  # type: ignore[attr-defined]
        except Exception:
            self._reply_error("INTERNAL", "erreur interne du helper")

    def _reply_error(self, code: str, message: str) -> None:
        self._reply({"ok": False, "error": {"code": code, "message": message}})

    def _reply(self, payload: dict) -> None:
        self.wfile.write((json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))


class UpdaterServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: str | None, engine: UpdaterEngine, inherited_fd: int | None = None):
        self.engine = engine
        if inherited_fd is None:
            super().__init__(address or "/run/clios/updater.sock", _Handler)
        else:
            socketserver.BaseServer.__init__(self, address or "systemd", _Handler)
            self.socket = socket.fromfd(inherited_fd, socket.AF_UNIX, socket.SOCK_STREAM)
            self.server_address = self.socket.getsockname()


def main() -> int:
    parser = argparse.ArgumentParser(description="Helper privilégié CliOS")
    parser.add_argument("--socket", default="/run/clios/updater.sock")
    parser.add_argument("--install-root", default="/opt/clios")
    parser.add_argument("--state-root", default="/var/lib/clios")
    parser.add_argument("--config", default="/etc/clios/updater.json")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("clios-updater doit être exécuté par root")
    manager = ReleaseManager(args.install_root, args.state_root, self_check_user="clios")
    catalog = ReleaseCatalog(args.config, str(Path(args.state_root) / "catalog-cache.json"))
    engine = UpdaterEngine(manager, catalog, str(Path(args.state_root) / "updater-status.json"))
    inherited = 3 if int(os.environ.get("LISTEN_FDS", "0")) == 1 else None
    with UpdaterServer(None if inherited else args.socket, engine, inherited) as server:
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
