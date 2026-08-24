import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main


class StartupHealthTest(unittest.TestCase):
    def test_health_marker_is_written_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "health-test"
            with mock.patch.dict(
                os.environ,
                {"CLIOS_HEALTH_MARKER": str(marker), "CLIOS_RELEASE_VERSION": "2.0.1-test"},
                clear=False,
            ):
                self.assertTrue(main.write_health_marker())
            self.assertEqual(marker.read_text(encoding="utf-8"), "2.0.1-test")
            self.assertFalse(marker.with_suffix(".tmp").exists())

    def test_health_marker_failure_is_visible(self):
        logger = mock.Mock()
        with mock.patch.dict(os.environ, {"CLIOS_HEALTH_MARKER": "/blocked/health"}, clear=False):
            with mock.patch.object(main, "_atomic_write", side_effect=PermissionError(13, "denied")):
                self.assertFalse(main.write_health_marker(logger))
        logger.error.assert_called_once()
        self.assertEqual(logger.error.call_args.kwargs["extra"]["error_code"], "APP_HEALTH_MARKER_WRITE")

    def test_startup_status_contains_phase_and_elapsed_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = Path(tmp) / "startup.json"
            with mock.patch.dict(os.environ, {"CLIOS_STARTUP_STATUS": str(status)}, clear=False):
                self.assertTrue(main.write_startup_status("qml_loaded"))
            payload = json.loads(status.read_text(encoding="utf-8"))
            self.assertEqual(payload["phase"], "qml_loaded")
            self.assertGreaterEqual(payload["elapsed_ms"], 0)

    def test_systemd_ready_datagram_contains_status(self):
        notifier = mock.MagicMock()
        notifier.__enter__.return_value = notifier
        with mock.patch.object(main.socket, "socket", return_value=notifier):
            with mock.patch.dict(os.environ, {"NOTIFY_SOCKET": "/run/notify.sock"}, clear=False):
                self.assertTrue(main.notify_systemd_ready("premier frame"))
        notifier.connect.assert_called_once_with("/run/notify.sock")
        notifier.sendall.assert_called_once_with(b"READY=1\nSTATUS=premier frame")


if __name__ == "__main__":
    unittest.main()
