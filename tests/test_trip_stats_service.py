import time
import unittest
from unittest.mock import MagicMock

from src.runtime import VehicleRuntime
from src.services.trip_stats_service import TripStatsService


class TripStatsServiceTest(unittest.TestCase):
    def setUp(self):
        self.storage = MagicMock()
        self.storage.get.return_value = 0.0
        self.runtime = VehicleRuntime(self.storage)
        self.runtime.publish("motion", {"odometer": 10000.0, "speed": 0.0}, source="test")
        self.runtime.publish("session", {"state": "RUNNING"}, source="test")
        self.runtime.publish("powertrain", {
            "driver_torque_request": 0.0, "fuel_used": 0.0, "rpm": 1500,
        }, source="test")
        self.config = {"maintenance": {"revision": {"interval_km": 20000, "warning_threshold_km": 2000}}}
        self.service = TripStatsService(self.runtime, self.config, self.storage)
        self.service._stats["is_active"] = True

    def test_deceleration_without_throttle_accumulates_when_torque_request_negative(self):
        """Le couple négatif mesure le frein moteur, pas une roue libre mécanique."""
        data = {
            "driver_torque_request": -15.0,
            "rpm": 2000,
            "accel_computed": 0.0,
            "brake": False,
            "clutch": False,
        }
        dt = 1.0  # 1 seconde
        current_speed = 72.0  # 72 km/h = 20 m/s = 0.02 km en 1 sec
        current_time = time.time()

        self.service._calc_fast_telemetry(data, dt, current_time, current_speed, perfect_fuel=None)

        expected_km = 72.0 * (1.0 / 3600.0)
        self.assertAlmostEqual(self.service._deceleration_without_throttle_dist, expected_km, places=5)
        self.assertAlmostEqual(self.service._session_distance_km, expected_km, places=5)

    def test_no_deceleration_without_throttle_when_torque_request_positive(self):
        """La distance dédiée ne s'incrémente pas sous couple moteur positif."""
        data = {
            "driver_torque_request": 25.0,  # Accélération / maintien de vitesse
            "rpm": 2500,
            "accel_computed": 0.5,
            "brake": False,
            "clutch": False,
        }
        dt = 1.0
        current_speed = 90.0
        current_time = time.time()

        self.service._calc_fast_telemetry(data, dt, current_time, current_speed, perfect_fuel=None)

        self.assertEqual(self.service._deceleration_without_throttle_dist, 0.0)
        self.assertGreater(self.service._session_distance_km, 0.0)

    def test_no_deceleration_without_throttle_when_torque_request_zero(self):
        """Le couple nul ne déclenche pas la métrique."""
        data = {
            "driver_torque_request": 0.0,
            "rpm": 1000,
            "accel_computed": 0.0,
            "brake": False,
            "clutch": False,
        }
        dt = 1.0
        current_speed = 50.0
        current_time = time.time()

        self.service._calc_fast_telemetry(data, dt, current_time, current_speed, perfect_fuel=None)

        self.assertEqual(self.service._deceleration_without_throttle_dist, 0.0)

    def test_no_deceleration_without_throttle_when_speed_below_threshold(self):
        """La décélération à très basse vitesse n'est pas accumulée."""
        data = {
            "driver_torque_request": -30.0,
            "rpm": 800,
            "accel_computed": -1.0,
            "brake": False,
            "clutch": False,
        }
        dt = 1.0
        current_speed = 4.0  # Vitesse faible
        current_time = time.time()

        self.service._calc_fast_telemetry(data, dt, current_time, current_speed, perfect_fuel=None)

        self.assertEqual(self.service._deceleration_without_throttle_dist, 0.0)

    def test_deceleration_fallback_when_torque_signal_missing(self):
        """Vérifie le repli sur accel_pos quand driver_torque_request n'est pas dans la trame."""
        # Cas 1 : Pédale relâchée (accel_pos = 0)
        data_coasting = {
            "accel_pos": 0.0,
            "rpm": 2000,
            "accel_computed": 0.0,
            "brake": False,
            "clutch": False,
        }
        self.service._calc_fast_telemetry(data_coasting, 1.0, time.time(), 50.0, perfect_fuel=None)
        expected_dist = 50.0 * (1.0 / 3600.0)
        self.assertAlmostEqual(self.service._deceleration_without_throttle_dist, expected_dist, places=5)

        # Cas 2 : Pédale appuyée (accel_pos = 15%)
        self.service._deceleration_without_throttle_dist = 0.0
        data_driving = {
            "accel_pos": 15.0,
            "rpm": 2500,
            "accel_computed": 0.5,
            "brake": False,
            "clutch": False,
        }
        self.service._calc_fast_telemetry(data_driving, 1.0, time.time(), 50.0, perfect_fuel=None)
        self.assertEqual(self.service._deceleration_without_throttle_dist, 0.0)

    def test_slow_telemetry_updates_named_deceleration_metric(self):
        self.service._deceleration_without_throttle_dist = 3.456
        self.service._calc_slow_telemetry(current_odo=10010.0, perfect_fuel=1.5, current_time=time.time())

        stats = self.service._stats_snapshot()
        self.assertEqual(stats["deceleration_without_throttle_km"], 3.5)
        self.assertNotIn("coasting_km", stats)

    def test_reset_session_resets_all_session_accumulators_and_windows(self):
        self.service._session_distance_km = 12.0
        self.service._deceleration_without_throttle_dist = 3.0
        self.service._absolute_fuel_session = 1.2
        self.service.inst_window.append((time.monotonic(), 0.1, 1.0))
        self.service._stats["longitudinal_g"] = 0.4

        self.service.reset_session(10020.0)

        self.assertEqual(self.service._session_distance_km, 0.0)
        self.assertEqual(self.service._deceleration_without_throttle_dist, 0.0)
        self.assertEqual(self.service._absolute_fuel_session, 0.0)
        self.assertEqual(len(self.service.inst_window), 0)
        self.assertEqual(self.runtime.snapshot().domain("trip")["longitudinal_g"], 0.0)

    def test_slow_loop_contract_is_at_least_20_hz(self):
        self.assertLessEqual(self.service.RATE_SLOW_TELEMETRY, 1.0 / 20.0)

    def test_finish_session_closes_accumulator_before_reset_is_published(self):
        self.service._stats["is_active"] = True
        self.service._stats["distance_km"] = 12.3
        self.service._accept_running = True

        final = self.service.finish_session(10012.3)

        self.assertEqual(final["distance_km"], 12.3)
        self.assertFalse(self.service._accept_running)
        published = self.runtime.snapshot().domain("trip")
        self.assertFalse(published["is_active"])
        self.assertEqual(published["distance_km"], 0.0)

    def test_checkpoint_restore_preserves_totals_and_rebases_live_inputs(self):
        self.service._session_distance_km = 12.3
        self.service._absolute_fuel_session = 0.8
        self.service._rpm_integral = 21000.0
        self.service._engine_time = 10.0
        self.service._stats.update({
            "distance_km": 12.3,
            "session_fuel_l": 0.8,
            "session_cost": 1.36,
            "inst_cons": 7.2,
        })
        checkpoint = self.service.export_session_checkpoint()
        self.service.reset_session(10012.3)

        self.service.restore_session_checkpoint(checkpoint)

        self.assertEqual(self.service._session_distance_km, 12.3)
        self.assertEqual(self.service._absolute_fuel_session, 0.8)
        self.assertEqual(self.service._rpm_integral, 21000.0)
        self.assertEqual(self.service._last_raw_fuel, None)
        self.assertTrue(self.service._accept_running)
        published = self.runtime.snapshot().domain("trip")
        self.assertEqual(published["distance_km"], 12.3)
        self.assertEqual(published["session_cost"], 1.36)
        self.assertEqual(published["inst_cons"], 0.0)


if __name__ == "__main__":
    unittest.main()
