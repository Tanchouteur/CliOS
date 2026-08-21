import threading
import unittest

from templates.service.example_service import ExampleService


class ExampleServiceContractTest(unittest.TestCase):
    def test_metadata_parameters_and_lifecycle(self):
        service = ExampleService(runtime=object())
        event = threading.Event()
        service.start(event)
        self.assertEqual(service.get_metadata()["api_version"], 1)
        self.assertEqual(service.get_health()["lifecycle"], "RUNNING")
        self.assertEqual(service.get_params_schema()[0]["type"], "toggle")
        service.stop()
        self.assertEqual(service.get_health()["lifecycle"], "STOPPED")


if __name__ == "__main__":
    unittest.main()
