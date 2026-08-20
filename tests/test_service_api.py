import threading
import unittest

from src.services.base_service import BaseService


class ServiceApiTest(unittest.TestCase):
    def test_v1_metadata_and_lifecycle(self):
        service = BaseService("Test", service_id="community.test", description="Test")
        event = threading.Event()
        BaseService.start(service, event, implemented=True)
        self.assertEqual(service.get_metadata()["api_version"], 1)
        self.assertEqual(service.get_health()["lifecycle"], "RUNNING")
        service.stop()
        self.assertEqual(service.get_health()["lifecycle"], "STOPPED")

    def test_invalid_service_id_is_rejected(self):
        with self.assertRaises(ValueError):
            BaseService("Test", service_id="bad id")


if __name__ == "__main__":
    unittest.main()
