import json
import tempfile
import unittest
from pathlib import Path

from src.update_safety import UpdateSafety


class UpdateSafetyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.status = self.root / "updater-status.json"
        self.mountinfo = self.root / "mountinfo"
        self.safety = UpdateSafety(str(self.status), str(self.mountinfo))

    def tearDown(self):
        self.temp.cleanup()

    def write_status(self, state):
        self.status.write_text(json.dumps({"state": state}), encoding="utf-8")

    def test_only_mutating_update_states_inhibit_power(self):
        for state in ("DOWNLOADING", "ACTIVATING"):
            self.write_status(state)
            self.assertTrue(self.safety.update_in_progress(), state)
        for state in ("IDLE", "CHECKING", "AVAILABLE", "STAGED", "ERROR"):
            self.write_status(state)
            self.assertFalse(self.safety.update_in_progress(), state)

    def test_invalid_or_missing_status_is_idle(self):
        self.assertFalse(self.safety.update_in_progress())
        self.status.write_text("not-json", encoding="utf-8")
        self.assertFalse(self.safety.update_in_progress())

    def test_longest_mount_decides_whether_install_is_volatile(self):
        self.mountinfo.write_text(
            "36 25 0:32 / / rw - overlay overlay rw\n"
            "40 36 8:2 / /opt/persistent rw - ext4 /dev/mmcblk0p2 rw\n",
            encoding="utf-8",
        )
        self.assertTrue(self.safety.path_is_overlay("/opt/clios"))
        self.assertFalse(self.safety.path_is_overlay("/opt/persistent/clios"))


if __name__ == "__main__":
    unittest.main()
