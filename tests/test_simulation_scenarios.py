import time
import unittest
from unittest.mock import MagicMock
from src.runtime import VehicleRuntime
from src.simulation.physique_mock import PhysicsMockProvider
from src.simulation.scenarios import Scenario, ScenarioStep, ScenarioRunner


class SimulationScenariosTest(unittest.TestCase):
    def setUp(self):
        self.storage = MagicMock()
        self.storage.get.return_value = 0.0
        self.runtime = VehicleRuntime(storage=self.storage)
        self.provider = PhysicsMockProvider(self.runtime)
        self.provider.connect()

    def tearDown(self):
        self.provider.close()

    def test_scenario_execution_and_callback(self):
        steps = [
            ScenarioStep("Étape 1 : Accélération", duration_s=0.1, throttle=50.0, gear=1),
            ScenarioStep("Étape 2 : Freinage", duration_s=0.1, throttle=0.0, brake=50.0, gear=0),
        ]
        scenario = Scenario("Test Scénario", "Scénario court de test", steps)

        progress_events = []
        def on_progress(cur, total, desc, pct):
            progress_events.append((cur, total, desc, pct))

        runner = ScenarioRunner(self.provider)
        runner.set_progress_callback(on_progress)
        runner.start_scenario(scenario)

        for _ in range(20):
            if not runner.is_running:
                break
            time.sleep(0.05)

        self.assertFalse(runner.is_running)
        self.assertGreaterEqual(len(progress_events), 2)
        self.assertEqual(progress_events[-1][0], 2)
        self.assertEqual(progress_events[-1][1], 2)

    def test_scenario_cancellation(self):
        steps = [
            ScenarioStep("Étape longue", duration_s=2.0, throttle=50.0, gear=1),
        ]
        scenario = Scenario("Test Long", "Scénario long annulé", steps)
        runner = ScenarioRunner(self.provider)
        runner.start_scenario(scenario)
        self.assertTrue(runner.is_running)

        runner.stop()
        self.assertFalse(runner.is_running)

    def test_direct_mock_fuel_signal_matches_the_wrapping_can_counter(self):
        self.provider.engine.state.fuel_used_total_l = 0.025
        time.sleep(0.05)
        fuel_used = self.runtime.snapshot().domain("powertrain").get("fuel_used")
        self.assertIsNotNone(fuel_used)
        self.assertGreaterEqual(fuel_used, 0.0)
        self.assertLess(fuel_used, 0.02048)


if __name__ == "__main__":
    unittest.main()
