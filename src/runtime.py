import threading
import time

from src.logging_runtime import get_logger
from src.signal_catalog import definition_for
from src.state_store import StatePatch, VehicleStateStore


class VehicleRuntime:
    """Publication gateway around the strict runtime store."""

    def __init__(self, storage):
        self.logger = get_logger("VehicleRuntime")
        self.storage = storage
        last_odo = storage.get("vehicle.last_odometer", 0.0)
        if last_odo <= 0.0:
            last_odo = storage.get("last_odometer", 0.0)
        if last_odo <= 0.0:
            last_odo = max(
                storage.get("trips.a.marker", 0.0),
                storage.get("trips.b.marker", 0.0),
                storage.get("vehicle.last_revision_odo", 0.0),
            )

        self.store = VehicleStateStore()
        self.publish("powertrain", {"fuel_level": 100.0}, source="bootstrap")
        self.publish("motion", {"odometer": last_odo}, source="bootstrap")
        self.publish("alerts", {"engine_light": "OFF"}, source="bootstrap")

        self._presentation_lock = threading.RLock()
        self._startup_active = False
        self._startup_overrides = {}

    def publish(self, domain, values, *, source, ttl_s=None, units=None):
        return self.store.publish(StatePatch(
            domain=domain, values=values, source=source, ttl_s=ttl_s, units=units or {}
        ))

    def publish_many(self, patches):
        return self.store.publish_many(patches)

    def snapshot(self):
        return self.store.snapshot()

    def metadata_snapshot(self):
        return self.store.metadata_snapshot()

    def presentation_snapshot(self):
        with self._presentation_lock:
            return {
                "startup_active": self._startup_active,
                "domains": {
                    domain: values.copy() for domain, values in self._startup_overrides.items()
                },
            }

    def _set_startup_values(self, values):
        with self._presentation_lock:
            for key, value in values.items():
                try:
                    domain = definition_for(key).domain
                except KeyError:
                    domain = {
                        "gear": "motion", "engine_light": "alerts", "inst_cons": "trip",
                        "oil_warning": "alerts", "battery_warning": "alerts",
                        "abs_error": "alerts", "esp_active": "alerts",
                        "stop_warning": "alerts", "service_warning": "trip",
                    }.get(key)
                    if domain is None:
                        raise ValueError(f"Signal de présentation non catalogué: {key}")
                self._startup_overrides.setdefault(domain, {})[key] = value

    def run_startup_sequence(self, duration_sec=2.0):
        with self._presentation_lock:
            self._startup_active = True
            self._startup_overrides = {}

        def sequence():
            time.sleep(0.15)
            lamps = [
                "brake", "clutch", "comodo_down", "comodo_up", "door_fl_open",
                "door_fr_open", "door_rl_open", "door_rr_open", "doors_locked",
                "driver_unbelted", "fog_front", "fog_rear", "high_beam",
                "ignition_on", "key_acc", "key_run", "low_beam", "passenger_disabled",
                "pos_lights", "reverse_engaged", "trunk_locked", "trunk_open",
                "turn_left", "turn_right", "oil_warning", "battery_warning",
                "abs_error", "esp_active", "stop_warning", "service_warning",
            ]
            self._set_startup_values(dict.fromkeys(lamps, True))
            self._set_startup_values({"brightness": 100.0, "gear": "8", "engine_light": "RED"})
            steps = 50
            sleep_time = (duration_sec / 2.0) / steps
            for indexes in (range(steps + 1), range(steps, -1, -1)):
                for index in indexes:
                    fraction = index / steps
                    self._set_startup_values({
                        "rpm": fraction * 7000.0, "speed": fraction * 200.0,
                        "accel_pos": fraction * 100.0,
                        "engine_temp": -20.0 + fraction * 150.0,
                        "inst_cons": fraction * 30.0,
                    })
                    time.sleep(sleep_time)
                if index == steps:
                    time.sleep(0.3)
            with self._presentation_lock:
                self._startup_active = False
                self._startup_overrides = {}

        threading.Thread(target=sequence, daemon=True, name="StartupPresentation").start()
