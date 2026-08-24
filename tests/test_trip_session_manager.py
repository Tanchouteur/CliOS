import json
import os
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock

from src.runtime import VehicleRuntime
from src.services.trip_session_manager import TripSessionManager


class FakeTripStats:
    def __init__(self):
        self.begin_calls = []
        self.restored = None
        self.state = {
            "stats": {
                "distance_km": 12.3,
                "session_fuel_l": 0.8,
                "session_cost": 1.52,
                "avg_rpm": 2100,
                "aggressivity_pct": 4.0,
                "deceleration_without_throttle_km": 1.2,
                "longitudinal_g": 0.1,
            },
            "start_odo": 1000.0,
            "session_distance_km": 12.3,
            "absolute_fuel_session": 0.8,
            "rpm_integral": 21000.0,
            "engine_time": 10.0,
            "aggressive_time": 1.0,
            "motion_time": 10.0,
            "deceleration_without_throttle_dist": 1.2,
            "shift_time_sum": 2.0,
            "shift_count": 4,
        }

    def begin_session(self, odometer):
        self.begin_calls.append(odometer)

    def export_session_checkpoint(self):
        return json.loads(json.dumps(self.state))

    def restore_session_checkpoint(self, checkpoint):
        self.restored = checkpoint

    def finish_session(self, _odometer):
        return self.state["stats"].copy()


class TripSessionManagerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.storage = MagicMock()
        self.storage.get.side_effect = lambda _key, default=0.0: default
        self.runtime = VehicleRuntime(self.storage)
        self.runtime.publish("motion", {"odometer": 1012.3, "speed": 0.0}, source="test")
        self.runtime.publish("powertrain", {"key_run": True}, source="test")
        self.stats = FakeTripStats()

    def manager(self):
        return TripSessionManager(
            self.runtime, self.storage, self.stats, self.temporary.name
        )

    def make_suspended_checkpoint(self):
        manager = self.manager()
        manager.trip_start_time = time.time() - 120
        manager.trip_start_odo = 1000.0
        manager.trip_trace = [{"ts": 1, "spd": 50.0, "cons": 6.0}]
        manager._publish_session("RUNNING")
        self.assertTrue(manager._suspend_trip(self.runtime.snapshot()))
        return manager

    def test_contact_off_suspends_and_writes_atomic_checkpoint(self):
        self.runtime.publish("powertrain", {"key_run": False}, source="test")
        manager = self.make_suspended_checkpoint()
        session = self.runtime.snapshot().domain("session")
        self.assertEqual(session["state"], "SUSPENDED")
        checkpoint_path = os.path.join(self.temporary.name, manager.CHECKPOINT_FILENAME)
        self.assertTrue(os.path.isfile(checkpoint_path))
        with open(checkpoint_path, encoding="utf-8") as stream:
            checkpoint = json.load(stream)
        self.assertEqual(checkpoint["stats_state"]["stats"]["session_cost"], 1.52)

    def test_restart_offers_and_restores_previous_trip(self):
        original = self.make_suspended_checkpoint()
        recovered = self.manager()
        session = self.runtime.snapshot().domain("session")
        self.assertEqual(session["state"], "RECOVERY_PENDING")
        self.assertEqual(session["resume_trip"]["distance_km"], 12.3)

        self.assertTrue(recovered.resume_trip())
        self.assertEqual(self.runtime.snapshot().domain("session")["state"], "RUNNING")
        self.assertEqual(self.stats.restored["absolute_fuel_session"], 0.8)
        self.assertEqual(recovered.trip_trace, original.trip_trace)

    def test_new_trip_archives_previous_trip_before_starting(self):
        self.make_suspended_checkpoint()
        recovered = self.manager()

        self.assertTrue(recovered.start_new_trip())

        summaries = [
            name for name in os.listdir(self.temporary.name)
            if name.startswith("trip_") and name.endswith(".json")
        ]
        self.assertEqual(len(summaries), 1)
        self.assertEqual(self.stats.begin_calls, [1012.3])
        self.assertEqual(self.runtime.snapshot().domain("session")["state"], "RUNNING")

    def test_timeout_starts_new_trip(self):
        self.make_suspended_checkpoint()
        recovered = self.manager()
        recovered.RECOVERY_TIMEOUT_S = 0.05
        stop_event = threading.Event()
        recovered.start(stop_event)
        deadline = time.monotonic() + 2.0
        while not self.stats.begin_calls and time.monotonic() < deadline:
            time.sleep(0.02)
        stop_event.set()
        recovered._thread.join(timeout=1.0)

        self.assertEqual(self.stats.begin_calls, [1012.3])
        self.assertEqual(self.runtime.snapshot().domain("session")["state"], "RUNNING")

    def test_invalid_checkpoint_is_quarantined(self):
        checkpoint = os.path.join(
            self.temporary.name, TripSessionManager.CHECKPOINT_FILENAME
        )
        with open(checkpoint, "w", encoding="utf-8") as stream:
            stream.write("not-json")

        manager = self.manager()

        self.assertIsNone(manager._recovery_checkpoint)
        self.assertEqual(self.runtime.snapshot().domain("session")["state"], "IDLE")
        self.assertTrue(any(".invalid." in name for name in os.listdir(self.temporary.name)))


if __name__ == "__main__":
    unittest.main()
