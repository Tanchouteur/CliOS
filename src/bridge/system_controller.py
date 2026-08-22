"""System information, diagnostics and host commands for DashboardBridge."""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import threading
import time
import zipfile
from pathlib import Path

from src.diagnostic_bundle import create_diagnostic_bundle
from src.logging_runtime import get_recent_events
from src.update_safety import UpdateSafety


class SystemController:
    def __init__(self, target):
        self.target = target
        self.project_root = Path(__file__).parents[2]
        self.update_safety = UpdateSafety()

    def recent_logs(self, limit: int) -> str:
        return json.dumps(get_recent_events(limit=max(1, min(limit, 300))))

    def export_diagnostic_bundle(self) -> str:
        target = self.target
        try:
            if target._storage_manager:
                log_dir = target._storage_manager.resolve_path("logs")
                output_dir = target._storage_manager.resolve_path("diagnostics")
            else:
                data_dir = os.path.dirname(os.path.dirname(target._config_path))
                log_dir = os.path.join(data_dir, "logs")
                output_dir = os.path.join(data_dir, "diagnostics")
            bundle_path = create_diagnostic_bundle(
                output_dir=output_dir,
                log_dir=log_dir,
                config_path=target._config_path,
                system_health=target.orchestrator.get_system_health(),
                extra={"active_profile": target.getActiveProfile(), "updater": target._updater_state},
            )
            target.logger.info(
                "Bundle diagnostic exporte: %s", bundle_path,
                extra={"error_code": "DIAG_BUNDLE_EXPORTED"},
            )
            return bundle_path
        except (OSError, TypeError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
            target.logger.error(
                "Echec export bundle: %s", exc,
                extra={"error_code": "DIAG_BUNDLE_ERROR", "exception_type": type(exc).__name__},
            )
            return ""

    def _command_text(self, args: list[str], timeout: float = 1.0) -> str:
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=timeout, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.target.logger.debug(
                "Commande système indisponible %s: %s", args[0], exc,
                extra={"error_code": "SYSTEM_PROBE_UNAVAILABLE", "command": args[0]},
            )
            return ""
        if result.returncode != 0:
            self.target.logger.debug(
                "Sonde système %s terminée avec le code %s", args[0], result.returncode,
                extra={"error_code": "SYSTEM_PROBE_FAILED", "command": args[0], "returncode": result.returncode},
            )
            return ""
        return result.stdout.strip()

    def _local_ip(self) -> str:
        for destination in ("8.8.8.8", "1.1.1.1", "192.168.1.1", "10.0.0.1"):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                    probe.connect((destination, 80))
                    address = probe.getsockname()[0]
                if address and not address.startswith("127."):
                    return address
            except OSError as exc:
                self.target.logger.debug(
                    "Sonde IP locale impossible via %s: %s", destination, exc,
                    extra={"error_code": "NETWORK_IP_PROBE_FAILED", "destination": destination},
                )
        output = self._command_text(["hostname", "-I"])
        addresses = [ip for ip in output.split() if not ip.startswith(("127.", "169.254."))]
        if addresses:
            return addresses[0]
        output = self._command_text(["ifconfig"])
        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0] == "inet" and not parts[1].startswith(("127.", "169.254.")):
                return parts[1]
        return "Hors-ligne"

    def _wifi_ssid(self) -> str:
        output = self._command_text(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"])
        for line in output.splitlines():
            if ":" in line:
                name, connection_type = line.rsplit(":", 1)
                if any(kind in connection_type.lower() for kind in ("wireless", "wifi", "802-11")):
                    return name.strip()
        output = self._command_text(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"])
        for line in output.splitlines():
            if line.startswith("yes:"):
                return line.removeprefix("yes:").strip()
        for command in ("iwgetid", "/usr/sbin/iwgetid", "/sbin/iwgetid"):
            output = self._command_text([command, "-r"])
            if output:
                return output
        for device in ("wlan0", "wlan1"):
            output = self._command_text(["iw", "dev", device, "link"])
            for line in output.splitlines():
                if "SSID:" in line:
                    return line.split("SSID:", 1)[1].strip()
        output = self._command_text(["wpa_cli", "status"])
        for line in output.splitlines():
            if line.startswith("ssid="):
                return line.removeprefix("ssid=").strip()
        if platform.system() == "Darwin":
            output = self._command_text(["ipconfig", "getsummary", "en0"])
            for line in output.splitlines():
                if "SSID :" in line:
                    return line.split("SSID :", 1)[1].strip()
        return ""

    def maintenance_status(self) -> str:
        overlay_status = "READ_WRITE"
        try:
            mounts = Path("/proc/mounts").read_text(encoding="utf-8")
            if "overlay on / " in mounts or ("/dev/root" not in mounts and "overlay" in mounts):
                overlay_status = "READ_ONLY"
        except OSError as exc:
            self.target.logger.debug(
                "Lecture des montages impossible: %s", exc,
                extra={"error_code": "MOUNT_STATUS_UNAVAILABLE"},
            )

        branch = self._command_text(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=2)
        commit = self._command_text(["git", "rev-parse", "--short", "HEAD"], timeout=2)
        git_info = f"{branch} ({commit})" if branch and commit else "main"
        cpu_temp = ""
        try:
            cpu_temp = f"{float(Path('/sys/class/thermal/thermal_zone0/temp').read_text().strip()) / 1000.0:.1f}°C"
        except (OSError, ValueError) as exc:
            self.target.logger.debug(
                "Température CPU indisponible: %s", exc,
                extra={"error_code": "CPU_TEMP_UNAVAILABLE"},
            )
        version = self.target.runtime.snapshot().domain("system").get("system_version", "unknown")
        return json.dumps({
            "version": version,
            "ip_address": self._local_ip(),
            "wifi_ssid": self._wifi_ssid(),
            "overlay_status": overlay_status,
            "git_info": git_info,
            "cpu_temp": cpu_temp,
        })

    def toggle_overlay(self) -> None:
        target = self.target
        if self.update_safety.update_in_progress():
            target.send_notification("ERROR", "OverlayFS verrouillé pendant la mise à jour", 4500)
            return
        target.logger.info("Bascule protection SD demandée", extra={"error_code": "MAINT_SD_TOGGLE"})

        def task() -> None:
            overlay_script = self.project_root / "tools" / "toggle_overlayfs.sh"
            try:
                if overlay_script.is_file():
                    result = subprocess.run(
                        ["bash", str(overlay_script)], cwd=self.project_root,
                        capture_output=True, text=True, timeout=30, check=False,
                    )
                    if result.returncode == 0:
                        target.send_notification("WARNING", "Protection SD basculée ! Redémarrez le système.", 5000)
                    else:
                        target.logger.error(
                            "Bascule SD refusée (code %s): %s", result.returncode, result.stderr.strip(),
                            extra={"error_code": "SD_TOGGLE_FAILED", "returncode": result.returncode},
                        )
                        target.send_notification("ERROR", f"Erreur SD : {result.stderr.strip()[:50]}", 4000)
                    return
                check = subprocess.run(
                    ["sudo", "raspi-config", "nonint", "get_overlay_now"],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                if check.returncode != 0:
                    raise RuntimeError(f"raspi-config get_overlay_now: code {check.returncode}")
                action = "disable_overlayfs" if check.stdout.strip() == "0" else "enable_overlayfs"
                result = subprocess.run(
                    ["sudo", "raspi-config", "nonint", action],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"raspi-config {action}: code {result.returncode}")
                if action == "disable_overlayfs":
                    target.send_notification("WARNING", "Protection SD désactivée (Mode RW). Redémarrez pour valider.", 5000)
                else:
                    target.send_notification("SUCCESS", "Protection SD activée (Lecture Seule). Redémarrez pour valider.", 5000)
            except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
                target.logger.error(
                    "Erreur bascule SD: %s", exc,
                    extra={"error_code": "SD_TOGGLE_ERROR", "exception_type": type(exc).__name__},
                )
                target.send_notification("ERROR", f"Erreur SD: {str(exc)[:50]}", 4000)

        threading.Thread(target=task, daemon=True, name="SdToggleThread").start()

    def request_exit(self, action: str) -> None:
        target = self.target
        if action in {"poweroff", "reboot"} and self.update_safety.update_in_progress():
            target.logger.warning(
                "Action %s refusée pendant la mise à jour", action,
                extra={"error_code": "POWER_BLOCKED_BY_UPDATE", "action": action},
            )
            target.send_notification("ERROR", "Extinction bloquée : mise à jour en cours", 5000)
            return
        messages = {
            "poweroff": ("warning", "Extinction système demandée", "SYS_SHUTDOWN", "Extinction du système..."),
            "reboot": ("warning", "Redémarrage matériel demandé", "SYS_REBOOT", "Redémarrage du système..."),
            "quit": ("info", "Fermeture manuelle de l'application", "APP_QUIT", "Fermeture de l'application..."),
        }
        log_level, log_message, error_code, notice = messages[action]
        getattr(target.logger, log_level)(log_message, extra={"error_code": error_code})
        target.send_notification("INFO" if action == "quit" else "WARNING", notice, 2000 if action == "quit" else 3000)

        def task() -> None:
            time.sleep(1.0)
            target.requested_power_action = action
            target.exitRequested.emit()

        threading.Thread(target=task, daemon=True, name=f"SystemExit-{action}").start()
