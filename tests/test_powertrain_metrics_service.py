import unittest

from src.services.powertrain_metrics_service import PowertrainMetricsService


class PowertrainMetricsServiceTest(unittest.TestCase):
    def setUp(self):
        config = {
            "engine": {
                "max_torque_nm": 200,
                "performance_curve": [
                    {"rpm": 1000, "torque_nm": 100},
                    {"rpm": 2000, "torque_nm": 200},
                    {"rpm": 4000, "torque_nm": 150},
                ],
            }
        }
        self.service = PowertrainMetricsService(api=None, config=config)

    def test_interpolates_profile_curve(self):
        self.assertEqual(self.service.torque_at_rpm(1500), 150.0)

    def test_calculates_load_torque_and_power_in_backend(self):
        metrics = self.service.calculate({"rpm": 2000, "driver_torque_request": 50.0})
        self.assertEqual(metrics["engine_load_pct"], 50.0)
        self.assertEqual(metrics["estimated_torque_nm"], 100.0)
        self.assertAlmostEqual(metrics["estimated_power_kw"], 20.9, places=1)

    def test_negative_torque_request_does_not_create_negative_power(self):
        metrics = self.service.calculate({"rpm": 2000, "driver_torque_request": -20.0})
        self.assertEqual(metrics["engine_load_pct"], 0.0)
        self.assertEqual(metrics["estimated_power_kw"], 0.0)

