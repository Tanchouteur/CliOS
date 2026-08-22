import unittest
from unittest.mock import MagicMock

from src.bridge.system_controller import SystemController


class FakeUpdateSafety:
    def update_in_progress(self):
        return True


class SystemControllerSafetyTest(unittest.TestCase):
    def setUp(self):
        self.target = MagicMock()
        self.controller = SystemController(self.target)
        self.controller.update_safety = FakeUpdateSafety()

    def test_poweroff_and_reboot_are_blocked_during_update(self):
        for action in ("poweroff", "reboot"):
            self.controller.request_exit(action)
        self.target.exitRequested.emit.assert_not_called()
        self.assertEqual(self.target.send_notification.call_count, 2)

    def test_overlay_toggle_is_blocked_during_update(self):
        self.controller.toggle_overlay()
        self.target.send_notification.assert_called_once()

    def test_quit_application_remains_available(self):
        self.controller.request_exit("quit")
        self.target.send_notification.assert_called_once()


if __name__ == "__main__":
    unittest.main()
