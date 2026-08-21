import os
import unittest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent

from tests.test_ui_structure import MockBridge


class UiSmoothingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.engine = QQmlEngine()
        cls.bridge = MockBridge()
        cls.engine.rootContext().setContextProperty("bridge", cls.bridge)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ui_state_path = os.path.join(base_dir, "frontend", "state", "UiState.qml")
        url = QUrl.fromLocalFile(ui_state_path)
        cls.comp = QQmlComponent(cls.engine, url)
        if cls.comp.isError():
            raise RuntimeError(f"UiState error: {[e.toString() for e in cls.comp.errors()]}")
        cls.ui_state = cls.comp.create()

    def test_temperature_smoothing(self):
        """Vérifie que la température extérieure transitionne de manière fluide via le bridge."""
        # Valeur initiale du mock : 20.0
        self.assertEqual(self.ui_state.property("outsideTemp"), 20.0)

        # Simulation d'un saut de température brute de 20°C à 40°C
        self.bridge._vehicle["environment"]["outside_temp"] = 40.0
        self.bridge.vehicleStateChanged.emit()
        self.app.processEvents()

        # rawOutsideTemp a changé instantanément, mais outsideTemp est en cours d'animation douce
        raw_val = self.ui_state.property("rawOutsideTemp")
        smooth_val = self.ui_state.property("outsideTemp")
        self.assertEqual(raw_val, 40.0)
        self.assertLess(smooth_val, 40.0)

    def test_fuel_level_smoothing(self):
        """Vérifie que le niveau de carburant s'amortit doucement (anti-clapotis)."""
        self.assertEqual(self.ui_state.property("fuelLevel"), 50.0)

        self.bridge._vehicle["powertrain"]["fuel_level"] = 25.0
        self.bridge.vehicleStateChanged.emit()
        self.app.processEvents()

        raw_val = self.ui_state.property("rawFuelLevel")
        smooth_val = self.ui_state.property("fuelLevel")
        self.assertEqual(raw_val, 25.0)
        self.assertGreater(smooth_val, 25.0)

    def test_speed_smoothing_and_instant_rpm(self):
        """Vérifie que la vitesse est lissée et que le RPM a une latence nulle (instantané)."""
        self.bridge._vehicle["motion"]["speed"] = 120.0
        self.bridge._vehicle["powertrain"]["rpm"] = 3500.0
        self.bridge.vehicleStateChanged.emit()
        self.app.processEvents()

        raw_speed = self.ui_state.property("rawSpeed")
        smooth_speed = self.ui_state.property("speed")
        self.assertEqual(raw_speed, 120.0)
        self.assertLess(smooth_speed, 120.0)

        # Le RPM ne doit subir aucun délai d'animation
        rpm_val = self.ui_state.property("rpm")
        self.assertEqual(rpm_val, 3500.0)


if __name__ == "__main__":
    unittest.main()
