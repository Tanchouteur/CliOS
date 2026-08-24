"""Asynchronous NetworkManager facade used by the settings UI.

Only saved Wi-Fi profiles are exposed.  Scan results are deliberately used as
availability metadata and never become connectable networks on their own.
"""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable, Sequence


def split_terse(line: str) -> list[str]:
    """Split an nmcli ``--terse --escape yes`` line."""
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for character in line.rstrip("\n"):
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


def merge_saved_networks(saved_output: str, scan_output: str, active_output: str = "") -> list[dict]:
    """Merge saved Wi-Fi connections with visible access points by SSID."""
    visible: dict[str, int] = {}
    for line in scan_output.splitlines():
        fields = split_terse(line)
        if len(fields) < 2 or not fields[0]:
            continue
        try:
            signal = max(0, min(100, int(fields[1] or 0)))
        except ValueError:
            signal = 0
        visible[fields[0]] = max(signal, visible.get(fields[0], 0))

    active_uuids: set[str] = set()
    for line in active_output.splitlines():
        fields = split_terse(line)
        if fields and fields[0]:
            active_uuids.add(fields[0])

    networks: list[dict] = []
    for line in saved_output.splitlines():
        fields = split_terse(line)
        if len(fields) < 4:
            continue
        uuid, name, connection_type, ssid = fields[:4]
        if connection_type not in {"802-11-wireless", "wifi", "wireless"} or not uuid:
            continue
        ssid = ssid or name
        networks.append({
            "uuid": uuid,
            "name": name or ssid,
            "ssid": ssid,
            "available": ssid in visible,
            "signal": visible.get(ssid, 0),
            "active": uuid in active_uuids,
        })
    networks.sort(key=lambda item: (not item["active"], not item["available"], -item["signal"], item["name"].lower()))
    return networks


class NetworkController:
    """Serialize bounded nmcli operations away from the Qt/QML thread."""

    def __init__(
        self,
        on_change: Callable[[], None] | None = None,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        timeout: float = 8.0,
    ):
        self._on_change = on_change or (lambda: None)
        self._runner = runner
        self._timeout = timeout
        self._lock = threading.RLock()
        self._busy = False
        self._state = self._empty_state()

    @staticmethod
    def _empty_state() -> dict:
        return {
            "available": False,
            "wifi_enabled": False,
            "busy": False,
            "active_ssid": "",
            "ip_address": "",
            "error": "",
            "saved_networks": [],
        }

    @property
    def state(self) -> dict:
        with self._lock:
            return {**self._state, "saved_networks": [dict(item) for item in self._state["saved_networks"]]}

    def _publish(self, **changes) -> None:
        with self._lock:
            self._state.update(changes)
        self._on_change()

    def _run(self, args: Sequence[str], timeout: float | None = None) -> str:
        result = self._runner(
            list(args), capture_output=True, text=True,
            timeout=self._timeout if timeout is None else timeout, check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "commande refusée").strip()
            raise RuntimeError(detail[:240])
        return (result.stdout or "").strip()

    def _begin(self) -> bool:
        with self._lock:
            if self._busy:
                return False
            self._busy = True
            self._state["busy"] = True
            self._state["error"] = ""
        self._on_change()
        return True

    def _finish(self) -> None:
        with self._lock:
            self._busy = False
            self._state["busy"] = False
        self._on_change()

    def _start(self, operation: Callable[[], None]) -> bool:
        if not self._begin():
            return False

        def task() -> None:
            try:
                operation()
            except FileNotFoundError:
                self._publish(available=False, error="NetworkManager indisponible")
            except subprocess.TimeoutExpired:
                self._publish(error="Délai NetworkManager dépassé")
            except (OSError, RuntimeError) as exc:
                self._publish(error=str(exc) or "Erreur NetworkManager")
            finally:
                self._finish()

        threading.Thread(target=task, daemon=True, name="NetworkManagerUi").start()
        return True

    def _snapshot(self, rescan: bool) -> None:
        wifi = self._run(["nmcli", "-t", "-f", "WIFI", "general"])
        saved = self._run(["nmcli", "-t", "--escape", "yes", "-f", "UUID,NAME,TYPE,802-11-wireless.ssid", "connection", "show"])
        active = self._run(["nmcli", "-t", "--escape", "yes", "-f", "UUID,NAME,TYPE,DEVICE", "connection", "show", "--active"])
        scan = ""
        if wifi.lower() == "enabled":
            scan = self._run(["nmcli", "-t", "--escape", "yes", "-f", "SSID,SIGNAL", "device", "wifi", "list", "--rescan", "yes" if rescan else "auto"])
        networks = merge_saved_networks(saved, scan, active)
        active_network = next((item for item in networks if item["active"]), None)
        ip_address = ""
        if active_network:
            ip_lines = self._run(["nmcli", "-t", "-f", "IP4.ADDRESS", "connection", "show", "--active"])
            for line in ip_lines.splitlines():
                value = line.split(":", 1)[-1].split("/", 1)[0]
                if value:
                    ip_address = value
                    break
        self._publish(
            available=True,
            wifi_enabled=wifi.lower() == "enabled",
            active_ssid=active_network["ssid"] if active_network else "",
            ip_address=ip_address,
            saved_networks=networks,
            error="",
        )

    def refresh(self) -> bool:
        return self._start(lambda: self._snapshot(rescan=True))

    def connect(self, uuid: str) -> bool:
        allowed = {item["uuid"] for item in self.state["saved_networks"]}
        if not uuid or uuid not in allowed:
            self._publish(error="Profil Wi-Fi non autorisé")
            return False

        def operation() -> None:
            self._run(["nmcli", "connection", "up", "uuid", uuid], timeout=20)
            self._snapshot(rescan=False)
        return self._start(operation)

    def disconnect(self) -> bool:
        def operation() -> None:
            active = next((item for item in self.state["saved_networks"] if item["active"]), None)
            if active:
                self._run(["nmcli", "connection", "down", "uuid", active["uuid"]], timeout=15)
            self._snapshot(rescan=False)
        return self._start(operation)

    def set_wifi_enabled(self, enabled: bool) -> bool:
        def operation() -> None:
            self._run(["nmcli", "radio", "wifi", "on" if enabled else "off"])
            self._snapshot(rescan=False)
        return self._start(operation)
