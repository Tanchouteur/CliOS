import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.bridge.system_controller import SystemController


class NoUpdate:
    def update_in_progress(self):
        return False


class OverlayFsStateTest(unittest.TestCase):
    def setUp(self):
        self.target = MagicMock()
        self.controller = SystemController(self.target)
        self.controller.update_safety = NoUpdate()

    def wait_toggle(self):
        deadline = time.time() + 1
        while self.controller.maintenance_state()["overlay_busy"] and time.time() < deadline:
            time.sleep(0.005)

    def test_success_distinguishes_current_configured_and_requires_reboot(self):
        self.controller._maintenance.update(overlay_current=False, overlay_configured=False)
        completed = subprocess.CompletedProcess([], 0, "ok", "")
        with patch.object(Path, "is_file", return_value=True), patch("src.bridge.system_controller.subprocess.run", return_value=completed):
            self.assertTrue(self.controller.toggle_overlay())
            self.wait_toggle()
        state = self.controller.maintenance_state()
        self.assertFalse(state["overlay_current"])
        self.assertTrue(state["overlay_configured"])
        self.assertTrue(state["restart_required"])

    def test_second_toggle_is_blocked_until_reboot(self):
        self.controller._maintenance.update(overlay_current=False, overlay_configured=True, restart_required=True)
        self.assertFalse(self.controller.toggle_overlay())
        self.target.send_notification.assert_called_once()

    def test_toggle_is_locked_while_operation_runs(self):
        self.controller._maintenance.update(overlay_current=False, overlay_configured=False)

        def slow_run(*args, **kwargs):
            time.sleep(0.08)
            return subprocess.CompletedProcess([], 0, "ok", "")

        with patch.object(Path, "is_file", return_value=True), patch("src.bridge.system_controller.subprocess.run", side_effect=slow_run):
            self.assertTrue(self.controller.toggle_overlay())
            self.assertFalse(self.controller.toggle_overlay())
            self.wait_toggle()


if __name__ == "__main__":
    unittest.main()
