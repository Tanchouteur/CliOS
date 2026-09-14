import logging
import unittest

from src.bridge.ui_command_router import UiCommandRouter


class FakeNetworkController:
    def __init__(self):
        self.calls = []

    def add_network(self, ssid, password):
        self.calls.append((ssid, password))
        return True


class FakeTarget:
    session_manager = None

    def __init__(self, controller):
        self._network_controller = controller

    def __getattr__(self, _name):
        return lambda *args, **kwargs: False


class UiCommandRouterTest(unittest.TestCase):
    def test_wifi_credentials_are_decoded_but_redacted_from_logs(self):
        controller = FakeNetworkController()
        target = FakeTarget(controller)
        records = []

        class Handler(logging.Handler):
            def emit(self, record):
                records.append(record)

        logger = logging.getLogger("test-wifi-router")
        logger.handlers = [Handler()]
        logger.setLevel(logging.WARNING)
        router = UiCommandRouter(target, logger)

        self.assertTrue(router.execute("wifi_add:Maison%3A5G:mot%20de%20passe", 0))
        self.assertEqual(controller.calls, [("Maison:5G", "mot de passe")])
        rendered = "\n".join(record.getMessage() for record in records)
        self.assertNotIn("mot de passe", rendered)
        self.assertIn("wifi_add:<redacted>", rendered)


if __name__ == "__main__":
    unittest.main()
