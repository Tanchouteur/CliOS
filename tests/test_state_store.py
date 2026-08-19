import unittest

from src.state_store import VehicleStateStore
from src.api import VehicleAPI


class MemoryStorage:
    def get(self, _key, default=None):
        return default


class VehicleStateStoreTest(unittest.TestCase):
    def test_classifies_domains_and_keeps_flat_compatibility(self):
        store = VehicleStateStore()
        store.update({"rpm": 1800, "speed": 72.0, "door_fl_open": True}, source="can")

        structured = store.domain_snapshot()
        self.assertEqual(structured["powertrain"]["rpm"], 1800)
        self.assertEqual(structured["motion"]["speed"], 72.0)
        self.assertTrue(structured["body"]["door_fl_open"])
        self.assertEqual(store.flat_snapshot()["rpm"], 1800)

    def test_tracks_source_unit_and_freshness(self):
        store = VehicleStateStore()
        store.update({"speed": 42.0}, source="can:0x5D7")

        metadata = store.metadata_snapshot()["speed"]
        self.assertEqual(metadata["source"], "can:0x5D7")
        self.assertEqual(metadata["unit"], "km/h")
        self.assertTrue(store.is_fresh("speed", 1.0))
        self.assertFalse(store.is_fresh("unknown", 1.0))

    def test_quality_becomes_stale_after_signal_ttl(self):
        store = VehicleStateStore()
        store.update({"rpm": 1200}, source="can", timestamp=0.0, ttl_s=0.1)
        self.assertEqual(store.metadata_snapshot()["rpm"]["quality"], "STALE")

    def test_startup_overlay_never_feeds_backend_services(self):
        api = VehicleAPI(MemoryStorage())
        api.update({"rpm": 850.0, "speed": 0.0}, source="can")
        with api.data_lock:
            api.is_starting_up = True
            api._startup_overlay = {"rpm": 7000.0, "speed": 200.0}

        self.assertEqual(api.get_display_data()["rpm"], 850.0)
        self.assertEqual(api.get_presentation_data()["rpm"], 7000.0)
