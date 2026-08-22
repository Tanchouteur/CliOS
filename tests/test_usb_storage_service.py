import threading
import time
import unittest
from unittest.mock import MagicMock

from src.runtime import VehicleRuntime
from src.services.usb_storage_service import UsbStorageService


class UsbStorageServiceTest(unittest.TestCase):
    def test_ram_storage_is_nominal_in_development(self):
        storage = MagicMock()
        storage.get.return_value = 0.0
        runtime = VehicleRuntime(storage)
        manager = MagicMock()
        manager.get_status.return_value = {
            "mode": "RAM", "usb_connected": False, "free_space_mb": 1024.0,
            "mount_point": "", "usb_diagnostic": "Aucun montage sous /media/clios",
        }
        service = UsbStorageService(runtime, storage, manager, development_mode=True)
        stop_event = threading.Event()
        service.start(stop_event)
        deadline = time.monotonic() + 0.5
        while not service.get_health()["message"] and time.monotonic() < deadline:
            time.sleep(0.01)
        service.stop()

        health = service.get_health()
        self.assertEqual(health["status"], "OK")
        self.assertIn("développement", health["message"])


if __name__ == "__main__":
    unittest.main()
