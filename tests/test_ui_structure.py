import glob
import os
import unittest
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent


class MockBridge(QObject):
    storageStatusChanged = Signal()
    vehicleStateChanged = Signal()
    notificationEvent = Signal(str, str, int)

    def __init__(self):
        super().__init__()
        self._data = {
            "speed": 0.0, "rpm": 0.0, "gear": "N", "fuel_level": 50.0, "engine_temp": 90.0,
            "door_fl_open": False, "door_fr_open": False, "door_rl_open": False, "door_rr_open": False,
            "trunk_open": False, "driver_unbelted": False, "session_state": "RUNNING", "outside_temp": 20.0,
            "odometer": 100000.0, "system_version": "1.0.0",
        }
        self._stats = {"distance_km": 10.0, "session_fuel_l": 0.8, "session_cost": 1.5, "autonomy": 600.0, "trip_b": 50.0, "avg_cons_b": 6.2}
        self._config = {"theme": {"main": "#48B8FF"}, "ui": {"visual_style": "gt_modern"}}
        self._system_health = {"service1": {"status": "OK"}}
        self._storage_status = {"usb_connected": True, "free_space_mb": 15000.0}

    @Property("QVariantMap")
    def data(self): return self._data
    @Property("QVariantMap", notify=vehicleStateChanged)
    def vehicleState(self): return {}
    @Property("QVariantMap")
    def stats(self): return self._stats
    @Property("QVariantMap")
    def tripState(self): return self._stats
    @Property("QVariantMap")
    def config(self): return self._config
    @Property("QVariantMap")
    def systemHealth(self): return self._system_health
    @Property("QVariantMap", notify=storageStatusChanged)
    def storageStatus(self): return self._storage_status

    @Slot(result="QVariantList")
    def getAvailableUiStyles(self):
        return []

    @Slot(str, str)
    def save_setting(self, k, v): pass
    @Slot()
    def resetTripA(self): pass
    @Slot()
    def resetTripB(self): pass
    @Slot()
    def resetMaintenance(self): pass
    @Slot()
    def endTripSession(self): pass
    @Slot()
    def resumeTripSession(self): pass
    @Slot(str)
    def setSessionState(self, s): pass
    @Slot()
    def quitApplication(self): pass
    @Slot()
    def restartApplication(self): pass
    @Slot()
    def shutdownSystem(self): pass


class UiStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.engine = QQmlEngine()
        cls.bridge = MockBridge()
        cls.engine.rootContext().setContextProperty("bridge", cls.bridge)
        cls.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.frontend_dir = os.path.join(cls.base_dir, "frontend")

    def test_frontend_root_clean(self):
        """Vérifie que les anciens dossiers orphelins sont bien supprimés."""
        self.assertFalse(os.path.exists(os.path.join(self.frontend_dir, "views")), "frontend/views ne doit plus exister")
        self.assertFalse(os.path.exists(os.path.join(self.frontend_dir, "pages")), "frontend/pages ne doit plus exister")

        # Dans frontend/components, seul NotificationCenter.qml doit être présent
        components = [f for f in os.listdir(os.path.join(self.frontend_dir, "components")) if f.endswith(".qml")]
        self.assertEqual(components, ["NotificationCenter.qml"], "frontend/components ne doit contenir que NotificationCenter.qml")

    def test_dashboard_folders_structure(self):
        """Vérifie la présence et la structure des dashboards installés."""
        styles_dir = os.path.join(self.frontend_dir, "styles")

        expected_styles = {
            "gt_modern": ["Dashboard.qml", "components", "pages", "style.json"],
            "legacy_dashboard": ["Dashboard.qml", "components", "pages", "style.json"],
            "apex": ["Dashboard.qml", "components", "pages", "style.json"],
            "atelier_luxe": ["Dashboard.qml", "components", "style.json"],
            "_template": ["Dashboard.qml", "style.json"]
        }

        for style_name, items in expected_styles.items():
            style_path = os.path.join(styles_dir, style_name)
            self.assertTrue(os.path.isdir(style_path), f"Dossier {style_name} introuvable")
            for item in items:
                item_path = os.path.join(style_path, item)
                self.assertTrue(os.path.exists(item_path), f"Elément {item} manquant dans {style_name}")

    def test_all_qml_files_compile(self):
        """Compile tous les fichiers QML des styles pour vérifier l'absence d'erreurs d'import ou de syntaxe."""
        pattern = os.path.join(self.frontend_dir, "**", "*.qml")
        qml_files = sorted(glob.glob(pattern, recursive=True))

        self.assertGreater(len(qml_files), 50, "Nombre insuffisant de fichiers QML trouvés")

        failed_files = []
        for qml_path in qml_files:
            url = QUrl.fromLocalFile(qml_path)
            component = QQmlComponent(self.engine, url)
            if component.isError():
                errors = [e.toString() for e in component.errors()]
                failed_files.append((os.path.relpath(qml_path, self.base_dir), errors))

        if failed_files:
            error_report = "\n".join(f"{f}: {errs}" for f, errs in failed_files)
            self.fail(f"Erreurs de compilation QML détectées ({len(failed_files)} fichiers):\n{error_report}")


if __name__ == "__main__":
    unittest.main()
