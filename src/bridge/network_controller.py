"""Asynchronous NetworkManager facade used by the settings UI."""

from __future__ import annotations

import os
import subprocess
import threading
from collections.abc import Callable, Sequence

WIFI_TYPES = {"802-11-wireless", "wifi", "wireless"}


def split_terse(line: str) -> list[str]:
    """Split an nmcli ``--terse --escape yes`` line."""
    fields, current = [], []
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


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"yes", "true", "1"}


def _to_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def merge_saved_networks(saved_output: str, scan_output: str, active_output: str = "") -> list[dict]:
    """Merge UUID,NAME,TYPE,SSID,AUTOCONNECT,PRIORITY rows with scan data."""
    visible: dict[str, int] = {}
    for line in scan_output.splitlines():
        fields = split_terse(line)
        if len(fields) >= 2 and fields[0]:
            signal = max(0, min(100, _to_int(fields[1])))
            visible[fields[0]] = max(signal, visible.get(fields[0], 0))
    active_uuids = {fields[0] for line in active_output.splitlines() if (fields := split_terse(line)) and fields[0]}
    networks = []
    for line in saved_output.splitlines():
        fields = split_terse(line)
        if len(fields) < 3:
            continue
        uuid, name, connection_type = fields[:3]
        if connection_type not in WIFI_TYPES or not uuid:
            continue
        ssid = fields[3] if len(fields) > 3 and fields[3] else name
        networks.append(
            {
                "uuid": uuid,
                "name": name or ssid,
                "ssid": ssid,
                "available": ssid in visible,
                "signal": visible.get(ssid, 0),
                "active": uuid in active_uuids,
                "autoconnect": _to_bool(fields[4]) if len(fields) > 4 else True,
                "priority": _to_int(fields[5]) if len(fields) > 5 else 0,
            }
        )
    networks.sort(
        key=lambda item: (
            not item["active"],
            not item["available"],
            -item["priority"],
            -item["signal"],
            item["name"].lower(),
        )
    )
    return networks


def parse_visible_networks(scan_output: str, saved_networks: list[dict]) -> list[dict]:
    """Collapse access points by SSID and annotate already saved networks."""
    saved_by_ssid = {item["ssid"]: item for item in saved_networks}
    visible: dict[str, dict] = {}
    for line in scan_output.splitlines():
        fields = split_terse(line)
        if len(fields) < 2 or not fields[0]:
            continue
        ssid, signal = fields[0], max(0, min(100, _to_int(fields[1])))
        security = fields[2] if len(fields) > 2 else ""
        if ssid not in visible or signal > visible[ssid]["signal"]:
            saved = saved_by_ssid.get(ssid)
            visible[ssid] = {
                "ssid": ssid,
                "signal": signal,
                "security": security,
                "secured": bool(security and security not in {"--", "NONE"}),
                "supported": "802.1X" not in security,
                "saved": saved is not None,
                "uuid": saved["uuid"] if saved else "",
                "active": bool(saved and saved["active"]),
            }
    return sorted(
        visible.values(),
        key=lambda item: (
            not item["active"],
            -item["signal"],
            item["ssid"].lower(),
        ),
    )


class NetworkController:
    """Serialize bounded nmcli operations away from the Qt/QML thread."""

    def __init__(
        self,
        on_change: Callable[[], None] | None = None,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        timeout: float = 8.0,
    ):
        self._on_change = on_change or (lambda: None)
        self._runner, self._timeout = runner, timeout
        self._lock, self._busy = threading.RLock(), False
        self._state = self._empty_state()

    @staticmethod
    def _empty_state() -> dict:
        return {
            "available": False,
            "wifi_enabled": False,
            "busy": False,
            "active_ssid": "",
            "active_device": "",
            "ip_address": "",
            "connectivity": "unknown",
            "error": "",
            "saved_networks": [],
            "visible_networks": [],
        }

    @property
    def state(self) -> dict:
        with self._lock:
            return {
                **self._state,
                "saved_networks": [dict(item) for item in self._state["saved_networks"]],
                "visible_networks": [dict(item) for item in self._state["visible_networks"]],
            }

    def _publish(self, **changes) -> None:
        with self._lock:
            self._state.update(changes)
        self._on_change()

    def _run(
        self,
        args: Sequence[str],
        timeout: float | None = None,
        input_text: str | None = None,
    ) -> str:
        environment = os.environ.copy()
        environment.update({"LC_ALL": "C", "LANG": "C"})
        result = self._runner(
            list(args),
            capture_output=True,
            text=True,
            input=input_text,
            env=environment,
            timeout=self._timeout if timeout is None else timeout,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "commande refusée").strip()
            raise RuntimeError(self._friendly_error(detail[:240]))
        return (result.stdout or "").strip()

    @staticmethod
    def _friendly_error(detail: str) -> str:
        lowered = detail.lower()
        if "not authorized" in lowered or "permission denied" in lowered:
            return "Autorisation réseau refusée"
        if "secrets were required" in lowered or "no secrets" in lowered:
            return "Mot de passe Wi-Fi incorrect ou manquant"
        if "no network with ssid" in lowered or "not found" in lowered:
            return "Réseau Wi-Fi introuvable"
        if "activation failed" in lowered:
            return "Connexion Wi-Fi impossible"
        return detail or "Erreur NetworkManager"

    def _optional_run(self, args: Sequence[str], timeout: float | None = None) -> tuple[str, str]:
        try:
            return self._run(args, timeout), ""
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            return "", str(exc) or "Opération réseau incomplète"

    def _begin(self) -> bool:
        with self._lock:
            if self._busy:
                return False
            self._busy = self._state["busy"] = True
            self._state["error"] = ""
        self._on_change()
        return True

    def _finish(self) -> None:
        with self._lock:
            self._busy = self._state["busy"] = False
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
                self._publish(available=True, error="Délai NetworkManager dépassé")
            except (OSError, RuntimeError) as exc:
                message = str(exc) or "Erreur NetworkManager"
                unavailable = "NetworkManager is not running" in message or "Could not create NMClient" in message
                self._publish(available=not unavailable, error=message)
            finally:
                self._finish()

        threading.Thread(target=task, daemon=True, name="NetworkManagerUi").start()
        return True

    @staticmethod
    def _escape_field(value: str) -> str:
        return value.replace("\\", "\\\\").replace(":", "\\:")

    def _saved_profiles(self) -> str:
        output = self._run(
            [
                "nmcli",
                "-t",
                "--escape",
                "yes",
                "-f",
                "UUID,NAME,TYPE,AUTOCONNECT,AUTOCONNECT-PRIORITY",
                "connection",
                "show",
            ]
        )
        rows = []
        for line in output.splitlines():
            fields = split_terse(line)
            if len(fields) < 3 or fields[2] not in WIFI_TYPES:
                continue
            ssid, _ = self._optional_run(
                [
                    "nmcli",
                    "-g",
                    "802-11-wireless.ssid",
                    "connection",
                    "show",
                    "uuid",
                    fields[0],
                ]
            )
            values = [*fields[:3], ssid, *(fields[3:5])]
            rows.append(":".join(self._escape_field(value) for value in values))
        return "\n".join(rows)

    def _snapshot(self, rescan: bool) -> None:
        wifi = self._run(["nmcli", "-t", "-f", "WIFI", "general"])
        saved = self._saved_profiles()
        active = self._run(
            [
                "nmcli",
                "-t",
                "--escape",
                "yes",
                "-f",
                "UUID,TYPE,DEVICE",
                "connection",
                "show",
                "--active",
            ]
        )
        scan, warning = "", ""
        if wifi.lower() == "enabled":
            scan, warning = self._optional_run(
                [
                    "nmcli",
                    "-t",
                    "--escape",
                    "yes",
                    "-f",
                    "SSID,SIGNAL,SECURITY",
                    "device",
                    "wifi",
                    "list",
                    "--rescan",
                    "yes" if rescan else "auto",
                ],
                timeout=15 if rescan else None,
            )
        networks = merge_saved_networks(saved, scan, active)
        active_network = next((item for item in networks if item["active"]), None)
        active_device, active_uuid = "", active_network["uuid"] if active_network else ""
        fallback_device = ""
        for line in active.splitlines():
            fields = split_terse(line)
            if len(fields) >= 3 and fields[2] and fields[1] != "loopback" and not fallback_device:
                fallback_device = fields[2]
            if len(fields) >= 3 and fields[0] == active_uuid:
                active_device = fields[2]
                break
        active_device = active_device or fallback_device
        ip_address = ""
        if active_device:
            addresses, address_warning = self._optional_run(
                [
                    "nmcli",
                    "-g",
                    "IP4.ADDRESS",
                    "device",
                    "show",
                    active_device,
                ]
            )
            warning = warning or address_warning
            for line in addresses.splitlines():
                value = line.split("/", 1)[0].strip()
                if value:
                    ip_address = value
                    break
        connectivity, connectivity_warning = self._optional_run(
            [
                "nmcli",
                "-t",
                "-f",
                "CONNECTIVITY",
                "general",
            ]
        )
        warning = warning or connectivity_warning
        self._publish(
            available=True,
            wifi_enabled=wifi.lower() == "enabled",
            active_ssid=active_network["ssid"] if active_network else "",
            active_device=active_device,
            ip_address=ip_address,
            connectivity=connectivity.lower() or "unknown",
            saved_networks=networks,
            visible_networks=parse_visible_networks(scan, networks),
            error=warning,
        )

    def refresh(self) -> bool:
        return self._start(lambda: self._snapshot(rescan=True))

    def poll(self) -> bool:
        """Refresh state without requesting a new radio scan."""
        return self._start(lambda: self._snapshot(rescan=False))

    def _known_uuid(self, uuid: str) -> bool:
        return bool(uuid and uuid in {item["uuid"] for item in self.state["saved_networks"]})

    def connect(self, uuid: str) -> bool:
        if not self._known_uuid(uuid):
            self._publish(error="Profil Wi-Fi non autorisé")
            return False

        def operation() -> None:
            self._run(["nmcli", "connection", "up", "uuid", uuid], timeout=30)
            self._snapshot(rescan=False)

        return self._start(operation)

    def add_network(self, ssid: str, password: str = "") -> bool:
        ssid = ssid.strip()
        visible = {item["ssid"]: item for item in self.state["visible_networks"]}
        if not ssid or ssid not in visible:
            self._publish(error="Réseau Wi-Fi non autorisé")
            return False
        if not visible[ssid]["supported"]:
            self._publish(error="Les réseaux Wi-Fi Entreprise 802.1X ne sont pas encore pris en charge")
            return False
        if visible[ssid]["secured"] and len(password) < 8:
            self._publish(error="Le mot de passe Wi-Fi doit contenir au moins 8 caractères")
            return False

        def operation() -> None:
            args = ["nmcli", "device", "wifi", "connect", ssid]
            if password:
                args.insert(1, "--ask")
            self._run(args, timeout=40, input_text=f"{password}\n" if password else None)
            self._snapshot(rescan=False)

        return self._start(operation)

    def forget(self, uuid: str) -> bool:
        if not self._known_uuid(uuid):
            self._publish(error="Profil Wi-Fi non autorisé")
            return False

        def operation() -> None:
            self._run(["nmcli", "connection", "delete", "uuid", uuid])
            self._snapshot(rescan=False)

        return self._start(operation)

    def set_autoconnect(self, uuid: str, enabled: bool) -> bool:
        if not self._known_uuid(uuid):
            self._publish(error="Profil Wi-Fi non autorisé")
            return False

        def operation() -> None:
            self._run(
                ["nmcli", "connection", "modify", "uuid", uuid, "connection.autoconnect", "yes" if enabled else "no"]
            )
            self._snapshot(rescan=False)

        return self._start(operation)

    def set_preferred(self, uuid: str) -> bool:
        if not self._known_uuid(uuid):
            self._publish(error="Profil Wi-Fi non autorisé")
            return False

        def operation() -> None:
            for item in self.state["saved_networks"]:
                self._run(
                    [
                        "nmcli",
                        "connection",
                        "modify",
                        "uuid",
                        item["uuid"],
                        "connection.autoconnect-priority",
                        "100" if item["uuid"] == uuid else "0",
                    ]
                )
            self._run(["nmcli", "connection", "modify", "uuid", uuid, "connection.autoconnect", "yes"])
            self._snapshot(rescan=False)

        return self._start(operation)

    def disconnect(self) -> bool:
        def operation() -> None:
            active_device = self.state["active_device"]
            if active_device:
                self._run(["nmcli", "device", "disconnect", active_device], timeout=15)
            self._snapshot(rescan=False)

        return self._start(operation)

    def set_wifi_enabled(self, enabled: bool) -> bool:
        def operation() -> None:
            self._run(["nmcli", "radio", "wifi", "on" if enabled else "off"])
            self._snapshot(rescan=False)

        return self._start(operation)
