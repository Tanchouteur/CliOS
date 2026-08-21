import pathlib
import unittest


class UpdaterQmlStatesTest(unittest.TestCase):
    def test_system_page_covers_every_public_state_and_safety_actions(self):
        source = (pathlib.Path(__file__).parents[1] / "frontend/shared_pages/SystemPage.qml").read_text(encoding="utf-8")
        for state in ("IDLE", "CHECKING", "AVAILABLE", "DOWNLOADING", "STAGED", "ACTIVATING", "UP_TO_DATE", "ERROR"):
            self.assertIn(f'"{state}"', source)
        self.assertIn("S.UiState.speed > 5", source)
        self.assertIn("ConfirmDialog", source)
        self.assertIn("bridge.stageUpdate", source)
        self.assertIn("bridge.activateUpdate", source)
        self.assertIn("bridge.rollbackUpdate", source)


if __name__ == "__main__":
    unittest.main()
