import time
import unittest
from unittest import mock

from src.bridge.updater_controller import UpdaterController


class Target:
    def __init__(self, state):
        self._updater_state = dict(state)
        self._updater_poll_running = False
        self._updater_operation_started_at = 0.0
        self._last_updater_status_signature = None
        self._config = {"updates": {"channel": "stable"}}
        self.logger = mock.Mock()
        self.notifications = []

    def _set_updater_state(self, **changes):
        self._updater_state.update(changes)

    def send_notification(self, *args):
        self.notifications.append(args)


class Client:
    response = {}

    def __init__(self, timeout=0):
        self.timeout = timeout

    def status(self):
        return self.response


class UpdaterControllerTest(unittest.TestCase):
    @staticmethod
    def poll(target, response):
        Client.response = response
        with mock.patch("src.bridge.updater_controller.UpdaterClient", Client):
            UpdaterController(target).poll_status()
            deadline = time.monotonic() + 1
            while target._updater_poll_running and time.monotonic() < deadline:
                time.sleep(0.005)

    def test_stale_helper_error_does_not_hide_available_release(self):
        target = Target({"state": "AVAILABLE", "available_version": "2.1.0"})
        self.poll(target, {"result": {
            "state": "ERROR", "updated_at": 10,
            "message": "aucune release précédente",
            "error": {"code": "UPDATE_ERROR", "message": "aucune release précédente"},
            "previous": None, "last_stable": None,
        }})
        self.assertEqual(target._updater_state["state"], "AVAILABLE")
        self.assertEqual(target._updater_state["available_version"], "2.1.0")
        self.assertFalse(target._updater_state["can_rollback"])

    def test_rollback_capability_is_metadata_not_an_error(self):
        target = Target({"state": "IDLE", "available_version": ""})
        self.poll(target, {"result": {
            "state": "IDLE", "previous": "2.0.0", "last_stable": "2.0.0",
            "error": None,
        }})
        self.assertEqual(target._updater_state["state"], "IDLE")
        self.assertTrue(target._updater_state["can_rollback"])
        self.assertEqual(target._updater_state["rollback_target"], "2.0.0")

    def test_fresh_operation_error_is_published(self):
        target = Target({"state": "DOWNLOADING", "available_version": "2.1.0"})
        target._updater_operation_started_at = 100
        self.poll(target, {"result": {
            "state": "ERROR", "version": "2.1.0", "updated_at": 101,
            "message": "échec", "phase": "self_check",
            "error": {"code": "PRIVILEGE", "message": "EPERM"},
        }})
        self.assertEqual(target._updater_state["state"], "ERROR")
        self.assertEqual(target._updater_state["error"]["code"], "PRIVILEGE")


if __name__ == "__main__":
    unittest.main()
