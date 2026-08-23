"""Helper root à protocole fermé pour les mises à jour atomiques CliOS."""

from __future__ import annotations

import argparse
import errno
import json
import os
import socket
import socketserver
import subprocess
import threading
import time
from pathlib import Path

from src.release_catalog import CatalogError, ReleaseCatalog
from src.release_contract import ReleaseContractError, SemVer
from src.release_manager import ReleaseError, ReleaseManager
from src.update_safety import ACTIVE_UPDATE_STATES, UpdateSafety


class UpdaterProtocolError(ValueError):
    pass


class UpdaterEngine:
    OPERATIONS = {
        "status": set(),
        "stage": {"version"},
        "activate": {"version"},
        "rollback": {"stable_only"},
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
            "error": {"code": "UPDATE_INTERRUPTED", "message": message},
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
            if operation == "stage":
                return self.stage(self._version(request.get("version")))
            if operation == "activate":
                return self.activate(self._version(request.get("version")))
            stable_only = request.get("stable_only", False)
            if not isinstance(stable_only, bool):
                raise UpdaterProtocolError("stable_only doit être booléen")
            return self.rollback(stable_only)
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

    def stage(self, version: str) -> dict:
        if self.update_safety.path_is_overlay(self.manager.install_root):
            raise ReleaseError(
                "protection SD active: désactivez OverlayFS et redémarrez avant la mise à jour"
            )
        self._write_status({
            "state": "DOWNLOADING", "operation": "stage", "version": version,
            "phase": "catalog", "progress": 1,
            "message": "Résolution de la release sur GitHub",
            "detail": "Lecture du catalogue et sélection des artefacts signés",
            "error": None,
        })
        try:
            manifest = self.catalog.find(version)
            self._write_status({
                "state": "DOWNLOADING", "operation": "stage", "version": version,
                "phase": "manifest", "progress": 4,
                "message": "Métadonnées GitHub vérifiées",
                "detail": "Le manifeste correspond à la version et à la plateforme",
                "last_manifest": manifest, "error": None,
            })
            target = self.manager.stage(manifest, strict=True)
            return {"state": "STAGED", "version": version, "path": str(target)}
        except Exception as exc:
            self._record_error(exc)
            raise

    def activate(self, version: str) -> dict:
        self._write_status({"state": "ACTIVATING", "operation": "activate", "version": version,
                            "phase": "activate", "progress": 100,
                            "message": "Activation atomique", "detail": "Bascule du lien current",
                            "error": None})
        try:
            target = self.manager.activate(version)
            marker = self.manager.state_root / f"health-{version}"
            marker.unlink(missing_ok=True)
            try:
                self.restart()
            except Exception:
                self.manager.rollback()
                raise
            threading.Thread(
                target=self._watch_first_boot,
                args=(version, marker),
                daemon=True,
                name=f"HealthWatch-{version}",
            ).start()
            return {"state": "ACTIVATING", "version": version, "path": str(target)}
        except Exception as exc:
            self._record_error(exc)
            raise

    def rollback(self, stable_only: bool) -> dict:
        self._write_status({"state": "ACTIVATING", "operation": "rollback", "progress": 100,
                            "phase": "rollback", "message": "Rollback",
                            "detail": "Restauration de la release précédente", "error": None})
        try:
            target = self.manager.rollback(stable_only=stable_only)
            self.restart()
            return {"state": "ACTIVATING", "version": target.name, "path": str(target)}
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

    def _progress(self, state: str, progress: int, message: str) -> None:
        current = self._read_status()
        lowered = message.lower()
        phase = "archive"
        if "manifeste" in lowered:
            phase = "manifest"
        elif "sign" in lowered or "sha-256" in lowered or "somme" in lowered:
            phase = "signature" if "sign" in lowered or "somme" in lowered else "hash"
        elif "extract" in lowered:
            phase = "extract"
        elif "environnement" in lowered or "wheelhouse" in lowered or "dépendance" in lowered:
            phase = "environment"
        elif "self-check" in lowered:
            phase = "self_check"
        elif "précompil" in lowered:
            phase = "precompile"
        elif state == "STAGED":
            phase = "complete"
        current.update({
            "state": state, "progress": progress, "message": message,
            "phase": phase, "detail": message, "error": None,
        })
        self._write_status(current)

    def _record_error(self, exc: Exception) -> None:
        code = self.error_code(exc)
        current = self._read_status()
        phase = str(current.get("phase", "operation"))
        raw_message = str(exc)
        message = f"Échec pendant {self._phase_label(phase)} : {raw_message}"
        current.update({
            "state": "ERROR", "message": message,
            "detail": self._error_hint(code, exc),
            "error": {"code": code, "message": raw_message, "phase": phase},
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
        if "sha-256" in message or "sha256" in message:
            return "SHA256"
        if getattr(exc, "errno", None) == errno.ENOSPC or "espace disque" in message or "no space" in message:
            return "DISK_SPACE"
        if "self-check" in message:
            return "SELF_CHECK"
        if "réseau" in message or "github inaccessible" in message or "timed out" in message:
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
        return f"Aucune release active n'a été remplacée. Détail système : {exc}"

    def _read_status(self) -> dict:
        try:
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {"state": "IDLE", "progress": 0, "message": ""}

    def _write_status(self, payload: dict) -> None:
        enriched = dict(payload)
        now = int(time.time())
        if str(enriched.get("state", "")) in ACTIVE_UPDATE_STATES:
            previous = self._read_status()
            new_operation = str(enriched.get("operation", ""))
            previous_operation = str(previous.get("operation", ""))
            previous_active = str(previous.get("state", "")) in ACTIVE_UPDATE_STATES
            if new_operation and (new_operation != previous_operation or not previous_active):
                enriched["started_at"] = now
            else:
                enriched.setdefault("started_at", int(previous.get("started_at", 0) or now))
        enriched["updated_at"] = now
        self.manager._write_json_atomic(self.status_path, enriched)

    def _restart_service(self) -> None:
        result = subprocess.run(["systemctl", "restart", self.service_name], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ReleaseError("redémarrage clios.service impossible: " + (result.stderr or result.stdout).strip())

    def _watch_first_boot(self, version: str, marker: Path) -> None:
        deadline = time.monotonic() + self.health_timeout
        while time.monotonic() < deadline:
            if marker.exists():
                with self._lock:
                    self.manager.mark_healthy(version)
                    self._write_status({"state": "IDLE", "version": version, "progress": 100,
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
                                    "message": f"{version} sans marqueur de santé; rollback automatique",
                                    "error": {"code": "HEALTH_TIMEOUT", "message": "premier démarrage non validé"}})
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
