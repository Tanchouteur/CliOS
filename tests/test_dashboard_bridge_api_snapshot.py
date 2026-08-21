import json
import pathlib
import unittest

from src.qt_bridge import DashboardBridge


ROOT = pathlib.Path(__file__).parents[1]


class DashboardBridgeApiSnapshotTest(unittest.TestCase):
    def test_qml_public_metaobject_matches_v1_snapshot(self):
        expected = json.loads((ROOT / "tests/fixtures/dashboard_bridge_api_v1.json").read_text(encoding="utf-8"))
        meta = DashboardBridge.staticMetaObject
        actual = {
            "properties": sorted(meta.property(index).name() for index in range(meta.propertyOffset(), meta.propertyCount())),
            "signals": sorted(
                bytes(meta.method(index).name()).decode("utf-8")
                for index in range(meta.methodOffset(), meta.methodCount())
                if meta.method(index).methodType().name == "Signal"
            ),
            "slots": sorted(
                bytes(meta.method(index).name()).decode("utf-8")
                for index in range(meta.methodOffset(), meta.methodCount())
                if meta.method(index).methodType().name == "Slot"
            ),
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
