import unittest

from src.runtime import VehicleRuntime
from src.state_store import StatePatch, VehicleStateStore


class MemoryStorage:
    def get(self, _key, default=None):
        return default


class VehicleStateStoreTest(unittest.TestCase):
    def test_requires_explicit_domains_and_returns_structured_snapshots(self):
        store = VehicleStateStore()
        revision = store.publish_many((
            StatePatch("powertrain", {"rpm": 1800}, "can", units={"rpm": "rpm"}),
            StatePatch("motion", {"speed": 72.0}, "can", units={"speed": "km/h"}),
            StatePatch("body", {"door_fl_open": True}, "can"),
        ))

        snapshot = store.snapshot()
        self.assertEqual(snapshot.domain("powertrain")["rpm"], 1800)
        self.assertEqual(snapshot.domain("motion")["speed"], 72.0)
        self.assertTrue(snapshot.domain("body")["door_fl_open"])
        self.assertEqual(snapshot.domain_revisions["powertrain"], revision)
        self.assertEqual(snapshot.domain_revisions["motion"], revision)
        self.assertEqual(snapshot.domain_revisions["body"], revision)
        self.assertFalse(hasattr(store, "flat_snapshot"))

    def test_rejects_unknown_domain(self):
        store = VehicleStateStore()
        with self.assertRaises(ValueError):
            store.publish(StatePatch("misc", {"speed": 42}, "test"))

    def test_tracks_metadata_per_domain(self):
        store = VehicleStateStore()
        store.publish(StatePatch(
            "motion", {"speed": 42.0}, "can:0x5D7", ttl_s=1.0,
            units={"speed": "km/h"},
        ))

        metadata = store.metadata_snapshot()["motion"]["speed"]
        self.assertEqual(metadata["source"], "can:0x5D7")
        self.assertEqual(metadata["unit"], "km/h")
        self.assertEqual(metadata["quality"], "VALID")

    def test_quality_becomes_stale_after_signal_ttl(self):
        store = VehicleStateStore()
        store.publish(StatePatch("powertrain", {"rpm": 1200}, "can", timestamp=0.0, ttl_s=0.1))
        self.assertEqual(store.metadata_snapshot()["powertrain"]["rpm"]["quality"], "STALE")

    def test_startup_overlay_never_mutates_runtime_domains(self):
        runtime = VehicleRuntime(MemoryStorage())
        runtime.publish("powertrain", {"rpm": 850.0}, source="can")
        runtime.publish("motion", {"speed": 0.0}, source="can")
        with runtime._presentation_lock:
            runtime._startup_active = True
        runtime._set_startup_values({"rpm": 7000.0, "speed": 200.0})

        snapshot = runtime.snapshot()
        presentation = runtime.presentation_snapshot()
        self.assertEqual(snapshot.domain("powertrain")["rpm"], 850.0)
        self.assertEqual(snapshot.domain("motion")["speed"], 0.0)
        self.assertEqual(presentation["domains"]["powertrain"]["rpm"], 7000.0)
        self.assertEqual(presentation["domains"]["motion"]["speed"], 200.0)

    def test_mutable_values_are_isolated_from_publishers_and_readers(self):
        store = VehicleStateStore()
        codes = ["P0100"]
        store.publish(StatePatch("diagnostics", {"codes": codes}, "test"))
        codes.append("P0200")
        snapshot = store.snapshot()
        snapshot.domain("diagnostics")["codes"].append("P0300")
        self.assertEqual(store.snapshot().domain("diagnostics")["codes"], ["P0100"])


if __name__ == "__main__":
    unittest.main()
