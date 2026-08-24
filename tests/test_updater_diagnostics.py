import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.updater_diagnostics import collect_updater_diagnostics


class UpdaterDiagnosticsTest(unittest.TestCase):
    def test_collector_reports_permissions_disk_overlay_python_and_releases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install = root / "opt/clios"
            state = root / "var/lib/clios"
            release = install / "releases/2.0.0"
            release.mkdir(parents=True)
            state.mkdir(parents=True)
            (state / "release-state.json").write_text('{"active":"2.0.0"}', encoding="utf-8")
            (state / "updater-status.json").write_text('{"state":"IDLE"}', encoding="utf-8")
            (install / "current").symlink_to(release)
            command_result = {"command": ["test"], "returncode": 0, "stdout": "", "stderr": ""}
            with mock.patch("src.updater_diagnostics._command", return_value=command_result):
                report = collect_updater_diagnostics(str(install), str(state))

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["release_state"]["active"], "2.0.0")
        self.assertEqual(report["updater_status"]["state"], "IDLE")
        self.assertEqual(report["releases"], ["2.0.0"])
        self.assertGreater(report["disk_usage"]["free"], 0)
        self.assertTrue(any(item.get("symlink_target") for item in report["paths"]))
        json.dumps(report)


if __name__ == "__main__":
    unittest.main()
