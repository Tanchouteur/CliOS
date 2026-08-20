import time
import threading
import unittest
from unittest.mock import MagicMock
from src.runtime import VehicleRuntime
from src.services.diagnostic_service import DiagnosticService
from src.simulation.physique_mock import PhysicsMockProvider


class SimulationIsoTpObdTest(unittest.TestCase):
    def setUp(self):
        self.storage = MagicMock()
        self.storage.get.return_value = 0.0
        self.runtime = VehicleRuntime(storage=self.storage)
        self.provider = PhysicsMockProvider(self.runtime)
        self.provider.connect()
        self.diag_service = DiagnosticService(self.runtime, self.provider)
        self.provider.register_obd_callback(self.diag_service.receive_obd_frame)
        self.stop_event = threading.Event()

    def tearDown(self):
        self.diag_service.stop()
        self.provider.close()

    def test_obd_scan_with_zero_dtcs(self):
        self.provider.clear_dtcs()
        self.diag_service.start(self.stop_event)

        self.diag_service.request_scan()

        for _ in range(50):
            snap = self.runtime.snapshot().domain("diagnostics")
            if not snap.get("scanning", True) and snap.get("has_scanned", False):
                break
            time.sleep(0.05)

        snap = self.runtime.snapshot().domain("diagnostics")
        self.assertTrue(snap.get("has_scanned", False))
        self.assertEqual(snap.get("codes", []), [])

    def test_obd_scan_with_single_frame_dtcs(self):
        # 2 DTCs -> Single Frame ISO-TP
        self.provider.inject_dtcs(["P0300", "P0115"])
        self.diag_service.start(self.stop_event)

        self.diag_service.request_scan()

        for _ in range(50):
            snap = self.runtime.snapshot().domain("diagnostics")
            if not snap.get("scanning", True) and snap.get("has_scanned", False):
                break
            time.sleep(0.05)

        snap = self.runtime.snapshot().domain("diagnostics")
        self.assertTrue(snap.get("has_scanned", False))
        self.assertEqual(snap.get("codes", []), ["P0300", "P0115"])

    def test_obd_scan_with_multi_frame_dtcs(self):
        # 4 DTCs -> First Frame + Flow Control + Consecutive Frame ISO-TP
        self.provider.inject_dtcs(["P0300", "P0115", "P0420", "C0123"])
        self.diag_service.start(self.stop_event)

        self.diag_service.request_scan()

        for _ in range(50):
            snap = self.runtime.snapshot().domain("diagnostics")
            if not snap.get("scanning", True) and snap.get("has_scanned", False):
                break
            time.sleep(0.05)

        snap = self.runtime.snapshot().domain("diagnostics")
        self.assertTrue(snap.get("has_scanned", False))
        self.assertEqual(snap.get("codes", []), ["P0300", "P0115", "P0420", "C0123"])


if __name__ == "__main__":
    unittest.main()
