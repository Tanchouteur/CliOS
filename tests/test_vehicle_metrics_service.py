import unittest

from src.services.vehicle_metrics_service import VehicleMetricsService


class VehicleMetricsServiceTest(unittest.TestCase):
    def setUp(self):
        config = {
            "engine": {
                "max_torque_nm": 200,
                "performance_curve": [
                    {"rpm": 1000, "torque_nm": 100},
                    {"rpm": 2000, "torque_nm": 200},
                    {"rpm": 4000, "torque_nm": 150},
                ],
            },
            "fuel": {"max_liters": 55, "reserve_percentage": 0.15},
            "engine_temp": {"warning": 105},
            "tachometer": {"redline_rpm": 5000},
        }
        self.service = VehicleMetricsService(runtime=None, config=config)

    def test_interpolates_profile_curve(self):
        self.assertEqual(self.service.torque_at_rpm(1500), 150.0)

    def test_calculates_load_torque_power_and_alerts(self):
        metrics, alerts = self.service.calculate({
            "rpm": 2000, "driver_torque_request": 50.0,
            "fuel_level": 5.0, "engine_temp": 110.0,
        })
        self.assertEqual(metrics["engine_load_pct"], 50.0)
        self.assertEqual(metrics["available_torque_nm"], 200.0)
        self.assertEqual(metrics["estimated_torque_nm"], 100.0)
        self.assertAlmostEqual(metrics["estimated_power_kw"], 20.9, places=1)
        self.assertTrue(alerts["low_fuel"])
        self.assertTrue(alerts["hot_engine"])

    def test_negative_torque_request_does_not_create_negative_power(self):
        metrics, _alerts = self.service.calculate({"rpm": 2000, "driver_torque_request": -20.0})
        self.assertEqual(metrics["engine_load_pct"], 0.0)
        self.assertEqual(metrics["estimated_power_kw"], 0.0)

    def test_previous_derived_load_never_masks_new_ecu_request(self):
        metrics, _alerts = self.service.calculate({
            "rpm": 2000, "engine_load_pct": 10.0, "driver_torque_request": 100.0,
        })
        self.assertEqual(metrics["engine_load_pct"], 100.0)
        self.assertEqual(metrics["estimated_torque_nm"], 200.0)


if __name__ == "__main__":
    unittest.main()
