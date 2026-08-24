import os
import unittest

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

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
        self.shell.setProperty("width", 1920)
        self.shell.setProperty("height", 720)
        self.app.processEvents()

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

    def test_alias_within_same_section_switches_the_visible_tab(self):
        self.shell.openRoute("appearance")
        self.app.processEvents()
        appearance = self.shell.findChild(QObject, "appearanceSettingsPage")
        self.assertIsNotNone(appearance)
        self.assertEqual(appearance.property("tab"), 0)

        self.shell.openRoute("accent")
        self.app.processEvents()
        self.assertEqual(appearance.property("tab"), 1)

        self.shell.openRoute("system")
        self.app.processEvents()
        system = self.shell.findChild(QObject, "systemSettingsPage")
        self.assertIsNotNone(system)
        self.shell.openRoute("updates")
        self.app.processEvents()
        self.assertEqual(system.property("tab"), 1)

    def test_services_tab_reuses_expandable_parameter_rows(self):
        self.shell.openRoute("services")
        self.app.processEvents()
        QTest.qWait(50)
        page = self.shell.findChild(QObject, "servicesSettingsPage")
        self.assertIsNotNone(page)
        self.assertTrue(page.property("embedded"))

        self.assertFalse(page.serviceExpanded("CAN_Moteur"))
        self.assertTrue(page.toggleServiceDetails("CAN_Moteur"))
        self.app.processEvents()
        self.assertTrue(page.serviceExpanded("CAN_Moteur"))


if __name__ == "__main__":
    unittest.main()
