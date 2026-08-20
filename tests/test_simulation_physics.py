"""Tests unitaires pour le moteur physique de simulation de véhicule."""

import unittest
from src.simulation.models import VehicleParameters, SimulatedVehicleState
from src.simulation.physics_engine import PhysicsEngine


class SimulationPhysicsTest(unittest.TestCase):
    def setUp(self):
        self.config = {
            "engine": {
                "label": "Test 2.0L",
                "max_torque_nm": 200,
                "performance_curve": [
                    {"rpm": 1000, "torque_nm": 100},
                    {"rpm": 3000, "torque_nm": 200},
                    {"rpm": 6000, "torque_nm": 180},
                ],
            },
            "tachometer": {
                "idle_rpm": 900,
                "redline_rpm": 6500,
                "max_rpm": 7000,
            },
            "fuel": {"max_liters": 50, "reserve_percentage": 0.15},
            "transmission": {
                "ratios": {"1": "3.7", "2": "2.0", "3": "1.4", "4": "1.0", "5": "0.8"}
            },
            "engine_temp": {"warning": 105},
        }
        self.params = VehicleParameters.from_config(self.config)
        self.engine = PhysicsEngine(self.params)

    def test_vehicle_parameters_from_config(self):
        self.assertEqual(self.params.label, "Test 2.0L")
        self.assertEqual(self.params.idle_rpm, 900.0)
        self.assertEqual(self.params.redline_rpm, 6500.0)
        self.assertEqual(self.params.fuel_capacity_l, 50.0)
        self.assertEqual(self.params.torque_at_rpm(1000), 100.0)
        self.assertEqual(self.params.torque_at_rpm(2000), 150.0)
        self.assertEqual(self.params.torque_at_rpm(3000), 200.0)

    def test_engine_starter_and_ignition_cycle(self):
        # Moteur éteint
        self.engine.state.engine_running = False
        self.engine.state.rpm = 0.0

        # Actionne le démarreur avec contact
        self.engine.state.starter_active = True
        self.engine.state.ignition_on = True
        self.engine.state.key_run = True

        for _ in range(15):
            self.engine.update(0.05)

        self.assertTrue(self.engine.state.engine_running)
        self.assertGreater(self.engine.state.rpm, 200.0)

        # Relâche le démarreur -> régime atteint le ralenti
        self.engine.state.starter_active = False
        for _ in range(40):
            self.engine.update(0.05)

        self.assertAlmostEqual(self.engine.state.rpm, self.params.idle_rpm, delta=100.0)

    def test_free_revving_in_neutral(self):
        self.engine.reset_state()
        self.engine.state.selected_gear = 0
        self.engine.state.throttle_pedal = 50.0

        for _ in range(30):
            self.engine.update(0.05)

        # Régime doit monter significativement au-dessus du ralenti
        self.assertGreater(self.engine.state.rpm, 2500.0)
        # La vitesse véhicule doit rester nulle au point mort
        self.assertEqual(self.engine.state.speed_kmh, 0.0)

    def test_acceleration_in_first_gear(self):
        self.engine.reset_state()
        self.engine.state.selected_gear = 1
        self.engine.state.clutch_pedal = 0.0
        self.engine.state.throttle_pedal = 60.0

        for _ in range(50):
            self.engine.update(0.05)

        # Le véhicule doit accélérer
        self.assertGreater(self.engine.state.speed_kmh, 10.0)
        self.assertGreater(self.engine.state.distance_trip_km, 0.0)
        self.assertGreater(self.engine.state.fuel_used_total_l, 0.0)

    def test_braking_deceleration(self):
        self.engine.reset_state()
        self.engine.state.speed_kmh = 60.0
        self.engine.state.selected_gear = 3
        self.engine.state.clutch_pedal = 100.0  # Débrayé
        self.engine.state.brake_pedal = 80.0

        for _ in range(30):
            self.engine.update(0.05)

        self.assertLess(self.engine.state.speed_kmh, 30.0)

    def test_rev_limiter_bounce(self):
        self.engine.reset_state()
        self.engine.state.selected_gear = 0
        self.engine.state.throttle_pedal = 100.0

        for _ in range(50):
            self.engine.update(0.05)

        self.assertTrue(self.engine.state.rev_limiter_active)
        self.assertLessEqual(self.engine.state.rpm, self.params.max_rpm + 50.0)

    def test_thermal_model_and_fan(self):
        self.engine.reset_state(temp_c=70.0)
        self.engine.state.selected_gear = 2
        self.engine.state.throttle_pedal = 80.0

        # Montée en température sous charge
        for _ in range(100):
            self.engine.update(0.1)

        self.assertGreater(self.engine.state.engine_temp_c, 70.0)

        # Forçage au-dessus de 96°C pour déclencher le ventilateur
        self.engine.state.engine_temp_c = 98.0
        self.engine.update(0.05)
        self.assertTrue(self.engine.state.radiator_fan_active)

    def test_turn_differential_wheels(self):
        self.engine.reset_state()
        self.engine.state.speed_kmh = 50.0
        self.engine.state.steering_angle_deg = 90.0  # Virage à droite

        self.engine.update(0.05)

        # Roue gauche (extérieure) plus rapide que roue droite (intérieure)
        self.assertGreater(self.engine.state.wheel_fl_speed, self.engine.state.wheel_fr_speed)


if __name__ == "__main__":
    unittest.main()
