"""Module de simulation physique et CAN pour CliOS."""

from src.simulation.models import VehicleParameters, SimulatedVehicleState
from src.simulation.physics_engine import PhysicsEngine
from src.simulation.can_encoder import CanFrameEncoder
from src.simulation.scenarios import Scenario, ScenarioStep, ScenarioRunner, get_builtin_scenarios
from src.simulation.physique_mock import PhysicsMockProvider

__all__ = [
    "VehicleParameters",
    "SimulatedVehicleState",
    "PhysicsEngine",
    "CanFrameEncoder",
    "Scenario",
    "ScenarioStep",
    "ScenarioRunner",
    "get_builtin_scenarios",
    "PhysicsMockProvider",
]
