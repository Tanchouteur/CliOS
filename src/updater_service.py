"""Helper root à protocole fermé pour les mises à jour atomiques CliOS."""

from __future__ import annotations

import argparse
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
                 service_name: str = "clios.service", restart=None, health_timeout: float = 45.0):
        self.manager = manager
        self.catalog = catalog
        self.status_path = Path(status_path)
        self.service_name = service_name
        self.restart = restart or self._restart_service
        self.health_timeout = health_timeout
        self._lock = threading.Lock()
        self.manager.progress_callback = self._progress

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
        self._write_status({"state": "DOWNLOADING", "version": version, "progress": 0, "message": "Résolution GitHub", "error": None})
        try:
            manifest = self.catalog.find(version)
            self._write_status({"state": "DOWNLOADING", "version": version, "progress": 0,
                                "message": "Release vérifiée", "last_manifest": manifest, "error": None})
            target = self.manager.stage(manifest, strict=True)
            return {"state": "STAGED", "version": version, "path": str(target)}
        except Exception as exc:
            self._record_error(exc)
            raise

    def activate(self, version: str) -> dict:
        self._write_status({"state": "ACTIVATING", "version": version, "progress": 100,
                            "message": "Activation atomique", "error": None})
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
        self._write_status({"state": "ACTIVATING", "progress": 100, "message": "Rollback", "error": None})
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
        current.update({"state": state, "progress": progress, "message": message, "error": None})
        self._write_status(current)

    def _record_error(self, exc: Exception) -> None:
        code = self.error_code(exc)
        current = self._read_status()
        current.update({"state": "ERROR", "message": str(exc), "error": {"code": code, "message": str(exc)}})
        self._write_status(current)

    @staticmethod
    def error_code(exc: Exception) -> str:
        explicit = getattr(exc, "code", None)
        if explicit:
            return str(explicit)
        message = str(exc).lower()
        if isinstance(exc, PermissionError) or "permission" in message or "privil" in message:
            return "PRIVILEGE"
        if "sha-256" in message or "sha256" in message:
            return "SHA256"
        if "espace disque" in message or "no space" in message:
            return "DISK_SPACE"
        if "self-check" in message:
            return "SELF_CHECK"
        if isinstance(exc, OSError) or "réseau" in message or "github inaccessible" in message:
            return "NETWORK"
        return "UPDATE_ERROR"

    def _read_status(self) -> dict:
        try:
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {"state": "IDLE", "progress": 0, "message": ""}

    def _write_status(self, payload: dict) -> None:
        self.manager._write_json_atomic(self.status_path, payload)

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
            time.sleep(0.25)
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
