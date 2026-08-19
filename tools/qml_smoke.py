"""Charge l'interface CliOS hors écran et produit des captures de référence."""

import argparse
import os
import sys

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle


class FakeBridge(QObject):
    dataChanged = Signal()
    statsChanged = Signal()
    configChanged = Signal()
    systemHealthChanged = Signal()
    storageStatusChanged = Signal()
    diagDataChanged = Signal()
    notificationEvent = Signal(str, str, int)

    def __init__(self):
        super().__init__()
        self._data = {
            "system_version": "GT-smoke", "speed": 82.0, "rpm": 3850, "gear": "4",
            "engine_temp": 92.0, "outside_temp": 23.5, "fuel_level": 31.5,
            "odometer": 128430.0, "session_state": "RUNNING", "accel_pos": 42.0,
            "accel_computed": 38.0, "driver_torque_request": 118.0, "clutch": False,
            "brake": False, "regulateur_mode": 2, "regulateur_statut": 4,
            "vitesse_regulateur": 90.0, "app_cpu_total_pct": 18.5, "app_ram_mb": 286.0,
            "cabin_noise_db": 68.0, "driver_unbelted": False, "door_fl_open": False,
            "door_fr_open": False, "door_rl_open": False, "door_rr_open": False,
            "trunk_open": False, "wheel_slip_fl": False, "wheel_slip_fr": False,
            "wheel_slip_rl": False, "wheel_slip_rr": False, "wheel_lock_fl": False,
            "wheel_lock_fr": False, "wheel_lock_rl": False, "wheel_lock_rr": False,
        }
        self._stats = {
            "is_active": True, "distance_km": 48.6, "session_fuel_l": 4.18,
            "session_cost": 7.52, "avg_rpm": 2740, "coasting_km": 8.4,
            "aggressivity_pct": 31.0, "shift_time_sec": 0.43, "trip_a": 382.4,
            "trip_b": 126.8, "inst_cons": 7.8, "avg_cons_b": 8.6,
            "avg_cons_session": 8.5, "autonomy": 412.0, "km_before_service": 7850.0,
            "service_warning": False, "g_force": 0.18,
        }
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
        self._health = {
            "CAN_Moteur": {"status": "OK", "message": "Bus CAN connecté"},
            "Diag": {"status": "OK", "message": "Diagnostic prêt"},
            "TripStats": {"status": "OK", "message": "Calcul actif"},
            "EngineSound": {"status": "DISABLED", "message": "Désactivé"},
        }
        self._storage = {"mode": "USB", "usb_connected": True, "free_space_mb": 24680.0}

    @Property("QVariant", notify=dataChanged)
    def data(self):
        return self._data

    @Property("QVariant", notify=statsChanged)
    def stats(self):
        return self._stats

    @Property("QVariant", notify=configChanged)
    def config(self):
        return self._config

    @Property("QVariant", notify=systemHealthChanged)
    def systemHealth(self):
        return self._health

    @Property("QVariant", notify=storageStatusChanged)
    def storageStatus(self):
        return self._storage

    @Property(bool, notify=diagDataChanged)
    def isScanning(self):
        return False

    @Property(bool, notify=diagDataChanged)
    def hasScanned(self):
        return True

    @Property("QVariantList", notify=diagDataChanged)
    def diagnosticCodes(self):
        return []

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

    @Slot(str, result=str)
    def getServiceParameters(self, _service):
        return "[]"

    @Slot(str, result=bool)
    def setActiveProfile(self, _profile):
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
        "gt_modern": ["drive", "trip", "performance", "diagnostic", "menu", "appearance", "vehicle", "services", "system", "developer"],
        "apex": ["drive", "perf", "menu"],
    }
    styles = ["gt_modern", "apex"]
    failures = []

    if args.output:
        os.makedirs(args.output, exist_ok=True)

    state = {"style": 0, "route": 0}
    base_data = bridge._data.copy()
    base_stats = bridge._stats.copy()

    def save_frame(name):
        if window.width() != 1920 or window.height() != 720:
            failures.append(f"taille inattendue: {window.width()}x{window.height()}")
        if args.output:
            image = window.grabWindow()
            target = os.path.join(args.output, name + ".png")
            if image.isNull() or not image.save(target):
                failures.append(f"capture impossible: {target}")

    specials = ["warnings", "paused", "missing-data", "confirmation", "legacy-dashboard"]
    special_index = {"value": 0}

    def run_special():
        idx = special_index["value"]
        if idx >= len(specials):
            app.quit()
            return
        name = specials[idx]
        bridge._data = base_data.copy()
        bridge._stats = base_stats.copy()
        bridge._storage = {"mode": "USB", "usb_connected": True, "free_space_mb": 24680.0}
        bridge._health["CAN_Moteur"] = {"status": "OK", "message": "Bus CAN connecté"}
        bridge.save_setting("ui.visual_style", "gt_modern")
        bridge.dataChanged.emit(); bridge.statsChanged.emit()
        bridge.storageStatusChanged.emit(); bridge.systemHealthChanged.emit()

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

        dashboard = window.findChild(QObject, "dashboardRoot")
        if dashboard is not None:
            dashboard.navigate("drive")
        banner = window.findChild(QObject, "attentionBanner")
        if banner:
            banner.setProperty("shown", False)

        if name == "warnings":
            bridge._data.update({
                "rpm": 6800, "engine_temp": 111, "fuel_level": 4.0,
                "driver_unbelted": True, "door_fl_open": True,
                "oil_warning": True, "battery_warning": True,
                "abs_warning": True, "esp_warning": True, "engine_warning": True,
            })
            bridge._storage = {"mode": "RAM", "usb_connected": False, "free_space_mb": 0.0}
            bridge._health["CAN_Moteur"] = {"status": "ERROR", "message": "Bus indisponible"}
            bridge.dataChanged.emit(); bridge.storageStatusChanged.emit(); bridge.systemHealthChanged.emit()
        elif name == "paused":
            bridge._data["session_state"] = "PAUSED"
            bridge._stats["is_active"] = False
            bridge.dataChanged.emit(); bridge.statsChanged.emit()
        elif name == "missing-data":
            bridge._data = {"system_version": "GT-smoke"}
            bridge._stats = {}
            bridge.dataChanged.emit(); bridge.statsChanged.emit()
        elif name == "confirmation":
            if dashboard is not None:
                dashboard.askConfirmation("shutdown")

        def finish_special():
            save_frame("state-" + name)
            special_index["value"] += 1
            QTimer.singleShot(100, run_special)

        QTimer.singleShot(180, finish_special)

    def advance():
        if state["style"] >= len(styles):
            QTimer.singleShot(100, run_special)
            return
        style = styles[state["style"]]
        routes = routes_by_style[style]
        route = routes[state["route"]]
        bridge.save_setting("ui.visual_style", style)

        def navigate_and_capture():
            object_name = "apexDashboardRoot" if style == "apex" else "dashboardRoot"
            active_dashboard = window.findChild(QObject, object_name)
            if active_dashboard is None:
                failures.append(f"dashboard introuvable: {style}")
            else:
                active_dashboard.navigate(route)

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
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    view_count = sum(len(routes_by_style[style]) for style in styles)
    print(f"QML OK: {view_count} vues et {len(specials)} états à 1920x720")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
