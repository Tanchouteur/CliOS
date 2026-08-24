import os
import unittest

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from tools.qml_smoke import FakeBridge


class NavigationBridge(FakeBridge):
    openMaintenanceRequested = Signal()


class UnifiedSettingsNavigationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        self.engine = QQmlEngine()
        self.bridge = NavigationBridge()
        self.engine.rootContext().setContextProperty("bridge", self.bridge)
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "components", "AppShell.qml")
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(path))
        self.assertFalse(self.component.isError(), [error.toString() for error in self.component.errors()])
        self.shell = self.component.create()
        self.assertIsNotNone(self.shell)

    def tearDown(self):
        self.engine.deleteLater()

    def test_rail_is_permanent_and_routes_do_not_build_history(self):
        rail = self.shell.findChild(QObject, "settingsNavigationRail")
        self.assertIsNotNone(rail)
        self.assertEqual(rail.property("width"), 288.0)
        self.assertIsNone(self.shell.property("history"))

        for requested, canonical in (
            ("menu", "driving"), ("appearance", "appearance"),
            ("diagnostic", "vehicle"), ("services", "advanced"),
            ("maintenance", "system"),
        ):
            self.shell.openRoute(requested)
            self.assertEqual(self.shell.property("route"), canonical)

        self.shell.openRoute("home")
        self.assertEqual(self.shell.property("route"), "home")

    def test_legacy_maintenance_signal_opens_storage(self):
        self.bridge.openMaintenanceRequested.emit()
        self.app.processEvents()
        self.assertEqual(self.shell.property("route"), "system")
        self.assertEqual(self.shell.property("requestedRoute"), "maintenance")


if __name__ == "__main__":
    unittest.main()
