"""Routing of AppShell commands without exposing controller details to QML."""

from __future__ import annotations

from collections.abc import Callable


class UiCommandRouter:
    def __init__(self, target, logger):
        self.target = target
        self.logger = logger

    def execute(self, command: str, speed_kmh: float) -> bool:
        self.logger.warning(
            "Commande UI '%s' à %.1f km/h", command, speed_kmh,
            extra={"error_code": "UI_COMMAND", "speed_kmh": speed_kmh, "command": command},
        )
        actions: dict[str, Callable[[], object]] = {
            "reset_a": self.target.resetTripA,
            "reset_b": self.target.resetTripB,
            "reset_maintenance": self.target.resetMaintenance,
            "end_trip": self.target.endTripSession,
            "resume_trip": self.target.resumeTripSession,
            "new_trip": lambda: self.target.session_manager.start_new_trip()
            if self.target.session_manager else False,
            "pause_trip": lambda: self.target.setSessionState("PAUSED"),
            "quit": self.target.quitApplication,
            "restart": self.target.restartApplication,
            "reboot": self.target.rebootSystem,
            "shutdown": self.target.shutdownSystem,
            "diagnostic_scan": self.target.requestDiagnosticScan,
            "gear_calibration_start": self.target.startGearCalibration,
            "gear_calibration_stop": self.target.stopGearCalibration,
            "toggle_overlayfs": self.target.toggleOverlayFs,
            "update_activate": lambda: self.target.activateUpdate(speed_kmh),
            "update_rollback": lambda: self.target.rollbackUpdate(speed_kmh, self.target.getUpdateChannel() == "beta"),
        }
        action = actions.get(command)
        if action is not None:
            action()
            return True
        if command == "wifi_refresh":
            return self.target._network_controller.refresh()
        if command == "wifi_disconnect":
            return self.target._network_controller.disconnect()
        if command.startswith("wifi_connect:"):
            return self.target._network_controller.connect(command.removeprefix("wifi_connect:"))
        if command.startswith("wifi_radio:"):
            value = command.removeprefix("wifi_radio:")
            if value in {"on", "off"}:
                return self.target._network_controller.set_wifi_enabled(value == "on")
            return False
        for prefix, setter in {
            "set_fuel_price:": self.target.updateFuelPrice,
            "set_trip_b_fuel:": self.target.updateTripBFuel,
            "set_trip_b_distance:": self.target.updateTripBDistance,
        }.items():
            if command.startswith(prefix):
                try:
                    setter(float(command[len(prefix):]))
                    return True
                except ValueError:
                    break
        self.logger.error("Commande UI inconnue: %s", command, extra={"error_code": "UI_COMMAND_UNKNOWN"})
        return False
