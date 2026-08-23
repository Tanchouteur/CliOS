"""Charge l'interface CliOS hors écran et produit des captures de référence."""

import argparse
import copy
import json
import os
import sys
import time

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle


class FakeBridge(QObject):
    vehicleStateChanged = Signal()
    tripStateChanged = Signal()
    diagnosticsStateChanged = Signal()
    systemStateChanged = Signal()
    sessionStateChanged = Signal()
    calibrationStateChanged = Signal()
    presentationStateChanged = Signal()
    dataQualityChanged = Signal()
    configChanged = Signal()
    notificationEvent = Signal(str, str, int)

    def __init__(self):
        super().__init__()
        self._vehicle_state = {
            "powertrain": {
                "rpm": 3850, "engine_temp": 92.0, "fuel_level": 31.5,
                "accel_pos": 42.0, "accel_computed": 38.0,
                "driver_torque_request": 58.0, "torque_available": 200.0,
                "engine_load_pct": 58.0, "estimated_torque_nm": 112.0,
                "estimated_power_kw": 45.1, "estimated_power_hp": 61.3,
                "key_run": True,
            },
            "motion": {
                "speed": 82.0, "gear": "4", "odometer": 128430.0,
                "clutch": False, "brake": False,
            },
            "wheels": {
                "wheel_slip_fl": False, "wheel_slip_fr": False,
                "wheel_slip_rl": False, "wheel_slip_rr": False,
                "wheel_lock_fl": False, "wheel_lock_fr": False,
                "wheel_lock_rl": False, "wheel_lock_rr": False,
            },
            "body": {
                "driver_unbelted": False, "door_fl_open": False,
                "door_fr_open": False, "door_rl_open": False,
                "door_rr_open": False, "trunk_open": False,
            },
            "assistance": {"regulateur_mode": 2, "regulateur_statut": 4, "vitesse_regulateur": 90.0},
            "dynamics": {},
            "environment": {"outside_temp": 23.5, "cabin_db_spl": 68.0, "cabin_freq_hz": 110},
            "controls": {},
            "alerts": {"engine_light": "OFF"},
        }
        self._trip_state = {
            "is_active": True, "distance_km": 48.6, "session_fuel_l": 4.18,
            "session_cost": 7.52, "avg_rpm": 2740, "deceleration_without_throttle_km": 8.4,
            "aggressivity_pct": 31.0, "shift_time_sec": 0.43, "trip_a": 382.4,
            "trip_b": 126.8, "trip_b_fuel": 10.9, "fuel_price": 1.80,
            "inst_cons": 7.8, "avg_cons_b": 8.6,
            "avg_cons_session": 8.5, "autonomy": 412.0, "km_before_service": 7850.0,
            "service_warning": False, "longitudinal_g": 0.18,
        }
        self._diagnostics_state = {"codes": [], "scanning": False, "has_scanned": True, "ignition_on": True}
        self._session_state = {"state": "RUNNING"}
        self._calibration_state = {"active": False, "ratio": 0.0, "count": 0, "gears_found": []}
        self._presentation_state = {"startup_active": False, "domains": {}}
        self._data_quality = {}
        self._config = {
            "theme": {"main": "#48B8FF"}, "ui": {"visual_style": "gt_modern"},
            "tachometer": {"max_rpm": 6000, "redline_rpm": 5100},
            "speedometer": {"max_speed": 200},
            "fuel": {"max_liters": 55},
            "engine_temp": {"warning": 105, "max_display": 120},
            "engine": {
                "label": "1.5 dCi 86", "max_power_kw": 63, "max_power_rpm": 3750,
                "max_torque_nm": 200, "max_torque_rpm": 1900,
                "performance_curve": [
                    {"rpm": 800, "torque_nm": 78}, {"rpm": 1250, "torque_nm": 145},
                    {"rpm": 1500, "torque_nm": 180}, {"rpm": 1900, "torque_nm": 200},
                    {"rpm": 2500, "torque_nm": 194}, {"rpm": 3000, "torque_nm": 184},
                    {"rpm": 3750, "torque_nm": 160}, {"rpm": 4000, "torque_nm": 143},
                    {"rpm": 4500, "torque_nm": 105}, {"rpm": 5000, "torque_nm": 65},
                ],
            },
        }
        health = {
            "CAN_Moteur": {"status": "OK", "message": "Bus CAN connecté"},
            "Diag": {"status": "OK", "message": "Diagnostic prêt"},
            "TripStats": {"status": "OK", "message": "Calcul actif"},
            "EngineSound": {"status": "DISABLED", "message": "Désactivé"},
        }
        storage = {"mode": "USB", "usb_connected": True, "free_space_mb": 24680.0}
        self._system_state = {
            "version": "GT-smoke",
            "telemetry": {"app_cpu_total_pct": 18.5, "app_ram_mb": 286.0},
            "health": health,
            "storage": storage,
            "updater": {"state": "IDLE", "installed_version": "2.0.0", "available_version": "", "progress": 0},
            "led_devices": [], "led_groups": [
                {"id": "all", "name": "Tout", "enabled": True, "brightness": 100,
                 "color_override": None, "device_count": 0},
            ],
            "led_max_devices": 4, "ble_scanning": False,
            "ble_scan_results": [], "ble_characteristics": [], "ble_test_state": {},
        }
        self.commands = []
        self._update_channel = "stable"

    @Property("QVariant", notify=vehicleStateChanged)
    def vehicleState(self):
        return self._vehicle_state

    @Property("QVariant", notify=tripStateChanged)
    def tripState(self):
        return self._trip_state

    @Property("QVariant", notify=diagnosticsStateChanged)
    def diagnosticsState(self): return self._diagnostics_state

    @Property("QVariant", notify=systemStateChanged)
    def systemState(self): return self._system_state

    @Property("QVariant", notify=sessionStateChanged)
    def sessionState(self): return self._session_state

    @Property("QVariant", notify=calibrationStateChanged)
    def calibrationState(self): return self._calibration_state

    @Property("QVariant", notify=presentationStateChanged)
    def presentationState(self): return self._presentation_state

    @Property("QVariant", notify=dataQualityChanged)
    def dataQuality(self): return self._data_quality

    @Property("QVariant", notify=configChanged)
    def config(self):
        return self._config

    @Slot(str, str)
    def save_setting(self, key, value):
        target = self._config
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
        self.configChanged.emit()

    @Slot(result="QVariantList")
    def getAvailableProfiles(self):
        return ["clio3diesel", "clio3_rs"]

    @Slot(result="QVariantList")
    def getAvailableUiStyles(self):
        return [
            {
                "id": "gt_modern", "label": "GT moderne",
                "description": "Graphite mat, blanc franc et détails lumineux",
                "order": 10, "dashboard": "styles/gt_modern/Dashboard.qml",
                "palette": {
                    "background": "#080B0F", "surface": "#11171D",
                    "surfaceRaised": "#182029", "surfaceSoft": "#202A34",
                    "text": "#F4F7FA", "textSecondary": "#CDD5DD",
                    "outline": "#34414D", "gaugeTrack": "#27323D",
                },
                "metrics": {"radiusSmall": 8, "radiusMedium": 14, "radiusLarge": 20, "borderWidth": 1},
            },
            {
                "id": "legacy_dashboard", "label": "Ancien dashboard",
                "description": "Votre ancien cockpit et ses compteurs circulaires",
                "order": 20, "dashboard": "styles/legacy_dashboard/Dashboard.qml",
                "palette": {
                    "background": "#000000", "surface": "#151515",
                    "surfaceRaised": "#202020", "surfaceSoft": "#2A2A2A",
                    "text": "#FFFFFF", "textSecondary": "#D5D5D5",
                    "outline": "#555555", "gaugeTrack": "#303030",
                },
                "metrics": {"radiusSmall": 8, "radiusMedium": 14, "radiusLarge": 20, "borderWidth": 1},
            },
            {
                "id": "apex", "label": "Apex",
                "description": "Cockpit panoramique haute lisibilite",
                "order": 1, "dashboard": "styles/apex/Dashboard.qml",
                "palette": {
                    "background": "#030509", "surface": "#090E15",
                    "surfaceRaised": "#101925", "surfaceSoft": "#162231",
                    "text": "#FFFFFF", "textSecondary": "#B9C6D4",
                    "outline": "#23354A", "gaugeTrack": "#142131",
                },
                "metrics": {"radiusSmall": 10, "radiusMedium": 18, "radiusLarge": 28, "borderWidth": 1},
            },
            {
                "id": "atelier_luxe", "label": "Atelier Luxe",
                "description": "Horlogerie et télémétrie de prestige",
                "order": 5, "dashboard": "styles/atelier_luxe/Dashboard.qml",
                "palette": {
                    "background": "#070A0F", "surface": "#0F1622",
                    "surfaceRaised": "#162030", "surfaceSoft": "#1E2C40",
                    "text": "#F5F8FC", "textSecondary": "#BAC8D9",
                    "outline": "#293A4E", "gaugeTrack": "#1B2533",
                },
                "metrics": {"radiusSmall": 10, "radiusMedium": 18, "radiusLarge": 26, "borderWidth": 1},
            },
            {
                "id": "jdm_mugen", "label": "Mugen Power JDM",
                "description": "Combiné d'instruments blanc sport Mugen Power avec triple compteur analogique",
                "order": 2, "dashboard": "styles/jdm_mugen/Dashboard.qml",
                "palette": {
                    "background": "#080B0F", "surface": "#101620",
                    "surfaceRaised": "#182230", "surfaceSoft": "#202E42",
                    "text": "#F5F8FA", "textSecondary": "#9EACB9",
                    "outline": "#2A394E", "gaugeTrack": "#E2E8F0",
                },
                "metrics": {"radiusSmall": 8, "radiusMedium": 14, "radiusLarge": 22, "borderWidth": 1.5},
            },
        ]

    @Slot(result="QVariantList")
    def getAvailableCanFiles(self):
        return ["can_moteur_clio3.json"]

    @Slot(result="QVariantList")
    def getAvailableConfigFiles(self):
        return ["config_clio3diesel.json", "clio3rs.json"]

    @Slot(result=str)
    def getActiveProfile(self):
        return "clio3diesel"

    @Slot(int, result=str)
    def getRecentLogs(self, _limit):
        return "[]"

    @Slot(result=str)
    def exportDiagnosticBundle(self):
        return "/tmp/clios-diagnostic.zip"

    @Slot(result=str)
    def getUpdateChannel(self):
        return self._update_channel

    @Slot(str, result=bool)
    def setUpdateChannel(self, channel):
        if channel not in {"stable", "beta"}:
            return False
        self._update_channel = channel
        return True

    @Slot()
    def checkForUpdates(self):
        pass

    @Slot(float)
    def stageUpdate(self, _speed):
        pass

    @Slot(float)
    def activateUpdate(self, _speed):
        pass

    @Slot(float, bool)
    def rollbackUpdate(self, _speed, _stable):
        pass

    @Slot(str, result=str)
    def getServiceParameters(self, service):
        if service != "CAN_Moteur":
            return "[]"
        return json.dumps([
            {"key": "enabled", "label": "Activer", "type": "toggle", "value": True},
            {"key": "rate", "label": "Fréquence", "type": "slider", "value": 25,
             "min_val": 1, "max_val": 100},
            {"key": "interface", "label": "Interface", "type": "list", "value": "can0",
             "options": ["can0", "vcan0"]},
            {"key": "address", "label": "Adresse", "type": "text", "value": "AA:BB:CC:DD:EE:FF"},
            {"key": "action", "label": "Action", "type": "button", "value": False},
        ])

    @Slot(result="QVariantList")
    def getBleProtocols(self):
        return [{
            "identifier": "LOTUS_9B", "label": "Lotus Lantern",
            "witness_color": "#FF0000", "witness_name": "ROUGE",
        }]

    @Slot(result="QVariantList")
    def getLedPredefinedNames(self):
        return ["Tableau de bord", "Plancher", "Console centrale", "Coffre"]

    @Slot(str, result=bool)
    def setActiveProfile(self, _profile):
        return True

    @Slot(str, float, result=bool)
    def executeUiCommand(self, _command, _speed):
        self.commands.append(_command)
        return True

    @Slot(str, str, str, str, str, result=bool)
    def createNewProfile(self, *_args):
        return True

    @Slot()
    @Slot(str)
    @Slot(str, bool)
    @Slot(str, str, "QVariant")
    def noop(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Répertoire des captures PNG")
    args = parser.parse_args()

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qml_messages = []

    def message_handler(_msg_type, context, message):
        source = getattr(context, "file", None) or ""
        lowered = message.lower()
        if source.endswith(".qml") or "qml" in lowered or "referenceerror" in lowered or "typeerror" in lowered:
            qml_messages.append(f"{source}: {message}")

    previous_handler = qInstallMessageHandler(message_handler)
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    bridge = FakeBridge()

    # Les actions existent toutes côté production; le smoke test ne les déclenche pas.
    for name in (
        "requestDiagnosticScan", "resetTripA", "resetTripB", "resetMaintenance",
        "resumeTripSession", "endTripSession", "quitApplication", "restartApplication",
        "shutdownSystem", "startGearCalibration", "stopGearCalibration", "setSessionState",
        "toggleService", "setServiceParameter",
    ):
        if not hasattr(FakeBridge, name):
            setattr(FakeBridge, name, FakeBridge.noop)

    engine.rootContext().setContextProperty("bridge", bridge)
    qml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "main.qml"))
    engine.load(qml_path)
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    window.setVisibility(QQuickWindow.Windowed)
    window.setWidth(1920)
    window.setHeight(720)
    routes_by_style = {
        style: ["home", "menu", "appearance", "vehicle", "services", "system", "diagnostic", "developer", "leds"]
        for style in ("apex", "atelier_luxe", "gt_modern", "jdm_mugen", "legacy_dashboard")
    }
    styles = ["apex", "atelier_luxe", "gt_modern", "jdm_mugen", "legacy_dashboard"]
    failures = []

    if args.output:
        os.makedirs(args.output, exist_ok=True)

    state = {"style": 0, "route": 0}
    base_vehicle = copy.deepcopy(bridge._vehicle_state)
    base_trip = copy.deepcopy(bridge._trip_state)
    base_session = copy.deepcopy(bridge._session_state)
    base_system = copy.deepcopy(bridge._system_state)

    def emit_runtime():
        bridge.vehicleStateChanged.emit()
        bridge.tripStateChanged.emit()
        bridge.sessionStateChanged.emit()
        bridge.systemStateChanged.emit()

    def save_frame(name):
        if window.width() != 1920 or window.height() != 720:
            failures.append(f"taille inattendue: {window.width()}x{window.height()}")
        if args.output:
            image = window.grabWindow()
            target = os.path.join(args.output, name + ".png")
            if image.isNull() or not image.save(target):
                failures.append(f"capture impossible: {target}")

    updater_states = ["IDLE", "CHECKING", "AVAILABLE", "DOWNLOADING", "STAGED", "ACTIVATING", "UP_TO_DATE", "ERROR"]
    specials = ["warnings", "paused", "missing-data", "confirmation", "legacy-dashboard", "jdm-motion"] + ["updater-" + value for value in updater_states]
    special_index = {"value": 0}

    def run_special():
        idx = special_index["value"]
        if idx >= len(specials):
            app.quit()
            return
        name = specials[idx]
        bridge._vehicle_state = copy.deepcopy(base_vehicle)
        bridge._trip_state = copy.deepcopy(base_trip)
        bridge._session_state = copy.deepcopy(base_session)
        bridge._system_state = copy.deepcopy(base_system)
        bridge.save_setting("ui.visual_style", "gt_modern")
        emit_runtime()

        if name == "legacy-dashboard":
            bridge.save_setting("ui.visual_style", "legacy_dashboard")

            def finish_legacy():
                legacy = window.findChild(QObject, "legacyDashboardRoot")
                if legacy is None:
                    failures.append("ancien dashboard non chargé")
                save_frame("state-legacy-dashboard")
                special_index["value"] += 1
                QTimer.singleShot(100, run_special)

            QTimer.singleShot(350, finish_legacy)
            return

        if name == "jdm-motion":
            bridge.save_setting("ui.visual_style", "jdm_mugen")
            shell = window.findChild(QObject, "appShell")
            if shell is not None:
                shell.openRoute("home")
            global_confirm = window.findChild(QObject, "globalConfirmDialog")
            if global_confirm is not None:
                global_confirm.setProperty("visible", False)
            bridge._vehicle_state["powertrain"]["rpm"] = 1200
            bridge._vehicle_state["motion"]["speed"] = 35.0
            emit_runtime()

            def sweep_needles():
                bridge._vehicle_state["powertrain"]["rpm"] = 5600
                bridge._vehicle_state["motion"]["speed"] = 155.0
                emit_runtime()
                QTimer.singleShot(24, finish_motion)

            def finish_motion():
                save_frame("state-jdm-motion")
                special_index["value"] += 1
                QTimer.singleShot(100, run_special)

            QTimer.singleShot(750, sweep_needles)
            return

        if name.startswith("updater-"):
            update_state = name.split("-", 1)[1]
            bridge._system_state["updater"] = {
                "state": update_state,
                "installed_version": "2.0.0",
                "available_version": "2.0.1-rc.1" if update_state in {"AVAILABLE", "DOWNLOADING", "STAGED", "ACTIVATING"} else "",
                "channel": "beta",
                "progress": 62 if update_state in {"DOWNLOADING", "ACTIVATING"} else 100 if update_state in {"STAGED", "UP_TO_DATE"} else 0,
                "message": "SHA-256 incorrect" if update_state == "ERROR" else "État updater de qualification",
                "detail": "Téléchargement de l'archive — 62%" if update_state == "DOWNLOADING" else "Détail de qualification updater",
                "phase": "archive" if update_state == "DOWNLOADING" else "complete",
                "started_at": int(time.time()) - 42 if update_state in {"CHECKING", "DOWNLOADING", "ACTIVATING"} else 0,
                "can_activate": update_state == "STAGED",
                "can_rollback": True, "rollback_target": "2.0.0",
                "error": {"code": "SHA256", "message": "SHA-256 incorrect", "phase": "hash"} if update_state == "ERROR" else {},
            }
            emit_runtime()
            shell = window.findChild(QObject, "appShell")
            if shell is not None:
                shell.openRoute("system")

            def finish_updater():
                save_frame("state-" + name.lower())
                special_index["value"] += 1
                QTimer.singleShot(100, run_special)

            QTimer.singleShot(220, finish_updater)
            return

        dashboard = window.findChild(QObject, "dashboardRoot")
        if dashboard is not None:
            dashboard.navigate("drive")
        banner = window.findChild(QObject, "attentionBanner")
        if banner:
            banner.setProperty("shown", False)

        if name == "warnings":
            bridge._vehicle_state["powertrain"].update({
                "rpm": 6800, "engine_temp": 111, "fuel_level": 4.0,
            })
            bridge._vehicle_state["body"].update({"driver_unbelted": True, "door_fl_open": True})
            bridge._vehicle_state["alerts"].update({
                "oil_warning": True, "battery_warning": True,
                "abs_warning": True, "esp_warning": True, "engine_warning": True,
            })
            bridge._system_state["storage"] = {"mode": "RAM", "usb_connected": False, "free_space_mb": 0.0}
            bridge._system_state["health"]["CAN_Moteur"] = {"status": "ERROR", "message": "Bus indisponible"}
            emit_runtime()
        elif name == "paused":
            bridge._session_state["state"] = "PAUSED"
            bridge._trip_state["is_active"] = False
            emit_runtime()
        elif name == "missing-data":
            bridge._vehicle_state = {}
            bridge._trip_state = {}
            emit_runtime()
        elif name == "confirmation":
            if dashboard is not None:
                dashboard.askConfirmation("shutdown")

        def finish_special():
            save_frame("state-" + name)
            special_index["value"] += 1
            QTimer.singleShot(100, run_special)

        QTimer.singleShot(180, finish_special)

    def advance():
        if not bridge.commands:
            shell = window.findChild(QObject, "appShell")
            if shell is not None:
                shell.requestCommand("resume_trip")
        if state["style"] >= len(styles):
            QTimer.singleShot(100, run_special)
            return
        style = styles[state["style"]]
        routes = routes_by_style[style]
        route = routes[state["route"]]
        bridge.save_setting("ui.visual_style", style)

        def navigate_and_capture():
            object_name = {
                "apex": "apexDashboardRoot",
                "atelier_luxe": "atelierLuxeDashboardRoot",
                "gt_modern": "dashboardRoot",
                "jdm_mugen": "mugenDashboardRoot",
                "legacy_dashboard": "legacyDashboardRoot",
            }[style]
            active_dashboard = window.findChild(QObject, object_name)
            if active_dashboard is None:
                failures.append(f"dashboard introuvable: {style}")
            shell = window.findChild(QObject, "appShell")
            if shell is None:
                failures.append("AppShell introuvable")
            elif route == "home":
                shell.openRoute("home")
            else:
                shell.openRoute(route)

            QTimer.singleShot(400, capture)

        def capture():
            save_frame(f"{style}-{route}")
            state["route"] += 1
            if state["route"] >= len(routes):
                state["route"] = 0
                state["style"] += 1
            QTimer.singleShot(80, advance)

        QTimer.singleShot(260, navigate_and_capture)

    QTimer.singleShot(200, advance)
    app.exec()
    qInstallMessageHandler(previous_handler)
    failures.extend(qml_messages)
    if "resume_trip" not in bridge.commands:
        failures.append("commande principale resume_trip non transmise par AppShell")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    view_count = sum(len(routes_by_style[style]) for style in styles)
    print(f"QML OK: {view_count} vues et {len(specials)} états à 1920x720")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
