import json
import tempfile
import unittest
from pathlib import Path


def legacy_v200_state_reader(path: Path) -> dict:
    """Comportement de lecture v2.0.0 : clés connues, extras ignorés."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "channel": payload.get("channel", "stable"),
        "active": payload.get("active"),
        "previous": payload.get("previous"),
        "last_stable": payload.get("last_stable"),
        "pending_health": payload.get("pending_health"),
    }


class ReleaseNMinusOneTest(unittest.TestCase):
    def test_v200_reader_ignores_v201_additive_updater_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-state.json"
            path.write_text(json.dumps({
                "channel": "beta", "active": "2.0.1-rc.1", "previous": "2.0.0",
                "last_stable": "2.0.0", "pending_health": None,
                "updater_schema": 1, "last_manifest": {"schema_version": 1},
                "last_error": {"code": "NETWORK"},
            }), encoding="utf-8")
            state = legacy_v200_state_reader(path)
            self.assertEqual(state["previous"], "2.0.0")
            self.assertEqual(state["last_stable"], "2.0.0")
            self.assertNotIn("last_manifest", state)


if __name__ == "__main__":
    unittest.main()
