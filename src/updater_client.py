"""Client non privilégié du socket fermé clios-updater."""

from __future__ import annotations

import json
import socket


class UpdaterClientError(RuntimeError):
    def __init__(self, message: str, code: str = "UPDATER_CLIENT"):
        super().__init__(message)
        self.code = code


class UpdaterClient:
    def __init__(self, socket_path: str = "/run/clios/updater.sock", timeout: float = 5.0):
        self.socket_path = socket_path
        self.timeout = timeout

    def status(self) -> dict:
        return self._request({"operation": "status"})

    def stage(self, version: str, operation_id: str | None = None) -> dict:
        payload = {"operation": "stage", "version": version}
        if operation_id:
            payload["operation_id"] = operation_id
        return self._request(payload)

    def activate(self, version: str, operation_id: str | None = None) -> dict:
        payload = {"operation": "activate", "version": version}
        if operation_id:
            payload["operation_id"] = operation_id
        return self._request(payload)

    def rollback(self, stable_only: bool = False, operation_id: str | None = None) -> dict:
        payload = {"operation": "rollback", "stable_only": bool(stable_only)}
        if operation_id:
            payload["operation_id"] = operation_id
        return self._request(payload)

    def _request(self, payload: dict) -> dict:
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > 4096:
            raise UpdaterClientError("requête updater trop longue")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self.timeout)
                connection.connect(self.socket_path)
                connection.sendall(encoded)
                stream = connection.makefile("rb")
                raw = stream.readline(65537)
        except (OSError, TimeoutError) as exc:
            raise UpdaterClientError(f"helper privilégié indisponible: {exc}") from exc
        if not raw or len(raw) > 65536:
            raise UpdaterClientError("réponse updater absente ou trop longue")
        try:
            response = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise UpdaterClientError("réponse updater invalide") from exc
        if not isinstance(response, dict):
            raise UpdaterClientError("réponse updater invalide")
        if not response.get("ok"):
            error = response.get("error", {})
            raise UpdaterClientError(
                str(error.get("message", "erreur updater")),
                str(error.get("code", "UPDATE_ERROR")),
            )
        return response
