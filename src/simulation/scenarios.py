"""Scénarios de conduite automatisés et séquences de test pour la simulation CliOS."""

import time
import threading
from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class ScenarioStep:
    """Étape individuelle au sein d'un scénario de conduite."""
    description: str
    duration_s: float
    throttle: float = 0.0
    brake: float = 0.0
    clutch: float = 0.0
    gear: int = 0
    steering: float = 0.0
    ignition: bool = True
    starter: bool = False
    handbrake: bool = False
    turn_left: bool = False
    turn_right: bool = False
    hazard: bool = False
    pos_lights: bool = False
    low_beam: bool = False
    high_beam: bool = False
    dtcs: list[str] | None = None
    force_temp: float | None = None
    force_fuel: float | None = None
    custom_action: Callable[[Any], None] | None = None


class Scenario:
    """Définition d'un scénario complet composé d'étapes ordonnées."""

    def __init__(self, name: str, description: str, steps: list[ScenarioStep]):
        self.name = name
        self.description = description
        self.steps = steps

    @property
    def total_duration_s(self) -> float:
        return sum(s.duration_s for s in self.steps)


class ScenarioRunner:
    """Orchestrateur de scénarios exécuté dans un thread dédié."""

    def __init__(self, mock_provider):
        self.provider = mock_provider
        self._thread = None
        self._stop_event = threading.Event()
        self._current_step_index = 0
        self._is_running = False
        self._progress_callback = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def set_progress_callback(self, callback: Callable[[int, int, str, float], None]):
        """Définit la fonction de rappel appelée à chaque progression d'étape."""
        self._progress_callback = callback

    def start_scenario(self, scenario: Scenario):
        """Lance l'exécution d'un scénario."""
        self.stop()
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(
            target=self._run,
            args=(scenario,),
            name=f"Scenario-{scenario.name}",
            daemon=True
        )
        self._thread.start()

    def stop(self):
        """Interrompt immédiatement le scénario en cours."""
        self._stop_event.set()
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None

    def _run(self, scenario: Scenario):
        total_steps = len(scenario.steps)
        total_time = scenario.total_duration_s
        elapsed_scenario = 0.0

        try:
            for idx, step in enumerate(scenario.steps):
                if self._stop_event.is_set():
                    break

                self._current_step_index = idx

                # Application des commandes physiques
                self.provider.engine.state.ignition_on = step.ignition
                self.provider.engine.state.key_run = step.ignition
                self.provider.engine.state.key_acc = step.ignition
                self.provider.engine.state.starter_active = step.starter
                self.provider.engine.state.selected_gear = step.gear
                self.provider.engine.state.clutch_pedal = step.clutch
                self.provider.engine.state.throttle_pedal = step.throttle
                self.provider.engine.state.brake_pedal = step.brake
                self.provider.engine.state.handbrake = step.handbrake
                self.provider.engine.state.steering_angle_deg = step.steering
                self.provider.engine.state.turn_left = step.turn_left
                self.provider.engine.state.turn_right = step.turn_right
                self.provider.engine.state.hazard = step.hazard
                self.provider.engine.state.pos_lights = step.pos_lights
                self.provider.engine.state.low_beam = step.low_beam
                self.provider.engine.state.high_beam = step.high_beam

                if step.dtcs is not None:
                    self.provider.engine.state.active_dtcs = list(step.dtcs)
                if step.force_temp is not None:
                    self.provider.engine.state.engine_temp_c = step.force_temp
                if step.force_fuel is not None:
                    self.provider.engine.state.fuel_level_l = step.force_fuel

                if step.custom_action:
                    step.custom_action(self.provider)

                # Émission de la notification de progression
                progress_pct = (elapsed_scenario / max(1.0, total_time)) * 100.0
                if self._progress_callback:
                    self._progress_callback(idx + 1, total_steps, step.description, progress_pct)

                # Attente fluide de la durée de l'étape
                step_elapsed = 0.0
                while step_elapsed < step.duration_s and not self._stop_event.is_set():
                    chunk = min(0.05, step.duration_s - step_elapsed)
                    time.sleep(chunk)
                    step_elapsed += chunk
                    elapsed_scenario += chunk

            if not self._stop_event.is_set() and self._progress_callback:
                self._progress_callback(total_steps, total_steps, "Scénario terminé avec succès", 100.0)

        finally:
            self._is_running = False


# =============================================================================
# SCÉNARIOS PRÉDÉFINIS
# =============================================================================

def get_builtin_scenarios() -> list[Scenario]:
    """Retourne la bibliothèque des scénarios de simulation disponibles."""

    # 1. Trajet Urbain
    city_steps = [
        ScenarioStep("1. Contact et allumage des feux de croisement", duration_s=1.0, ignition=True, low_beam=True),
        ScenarioStep("2. Action démarreur (Lancement moteur)", duration_s=1.2, ignition=True, starter=True, low_beam=True),
        ScenarioStep("3. Moteur au ralenti, débrayage et engagement de la 1ère", duration_s=1.0, clutch=100.0, gear=1, low_beam=True),
        ScenarioStep("4. Départ arrêté et accélération modérée", duration_s=3.0, clutch=0.0, throttle=40.0, gear=1, low_beam=True),
        ScenarioStep("5. Débrayage et passage en 2ème", duration_s=0.6, clutch=100.0, throttle=0.0, gear=2, low_beam=True),
        ScenarioStep("6. Accélération jusqu'à 50 km/h", duration_s=3.5, clutch=0.0, throttle=50.0, gear=2, low_beam=True),
        ScenarioStep("7. Débrayage et passage en 3ème", duration_s=0.6, clutch=100.0, throttle=0.0, gear=3, low_beam=True),
        ScenarioStep("8. Vitesse stabilisée 50 km/h en ville", duration_s=4.0, clutch=0.0, throttle=18.0, gear=3, low_beam=True),
        ScenarioStep("9. Clignotant gauche et léger virage", duration_s=2.5, throttle=15.0, gear=3, steering=-35.0, turn_left=True, low_beam=True),
        ScenarioStep("10. Ligne droite, arrêt clignotant", duration_s=2.0, throttle=18.0, gear=3, steering=0.0, turn_left=False, low_beam=True),
        ScenarioStep("11. Ralentissement, freinage et débrayage (Feu rouge)", duration_s=3.0, throttle=0.0, brake=45.0, clutch=100.0, gear=3, low_beam=True),
        ScenarioStep("12. Arrêt complet au point mort avec frein à main", duration_s=2.0, brake=0.0, clutch=0.0, gear=0, handbrake=True, low_beam=True),
        ScenarioStep("13. Coupure du contact", duration_s=1.0, ignition=False, low_beam=False, handbrake=True),
    ]
    city_scenario = Scenario("Trajet Urbain", "Simulation d'un trajet citadin complet avec arrêts, vitesses et feux.", city_steps)

    # 2. Autoroute & Régulateur
    highway_steps = [
        ScenarioStep("1. Démarrage moteur", duration_s=1.5, ignition=True, starter=True, clutch=100.0, gear=0),
        ScenarioStep("2. Insertion vive en 1ère", duration_s=2.5, clutch=0.0, throttle=75.0, gear=1),
        ScenarioStep("3. Passage 2ème", duration_s=0.5, clutch=100.0, throttle=0.0, gear=2),
        ScenarioStep("4. Pleine accélération 2ème", duration_s=3.0, clutch=0.0, throttle=85.0, gear=2),
        ScenarioStep("5. Passage 3ème", duration_s=0.5, clutch=100.0, throttle=0.0, gear=3),
        ScenarioStep("6. Montée en régime 3ème jusqu'à 90 km/h", duration_s=3.5, clutch=0.0, throttle=80.0, gear=3),
        ScenarioStep("7. Passage 4ème", duration_s=0.5, clutch=100.0, throttle=0.0, gear=4),
        ScenarioStep("8. Accélération 4ème jusqu'à 120 km/h", duration_s=4.0, clutch=0.0, throttle=75.0, gear=4),
        ScenarioStep("9. Passage 5ème", duration_s=0.5, clutch=100.0, throttle=0.0, gear=5),
        ScenarioStep("10. Vitesse de croisière 130 km/h (Régulateur actif)", duration_s=6.0, clutch=0.0, throttle=32.0, gear=5),
        ScenarioStep("11. Freinage d'approche de péage", duration_s=4.0, throttle=0.0, brake=60.0, clutch=100.0, gear=5),
        ScenarioStep("12. Arrêt complet au point mort", duration_s=2.0, brake=20.0, clutch=0.0, gear=0),
    ]
    highway_scenario = Scenario("Autoroute & Régulateur", "Accélération soutenue jusqu'à 130 km/h et régulation.", highway_steps)

    # 3. Circuit & Sport
    sport_steps = [
        ScenarioStep("1. Départ arrêté Launch Control (Haut régime en 1ère)", duration_s=1.5, ignition=True, clutch=100.0, throttle=95.0, gear=1),
        ScenarioStep("2. Lâcher d'embrayage brutal et patinage", duration_s=2.5, clutch=0.0, throttle=100.0, gear=1),
        ScenarioStep("3. Rupteur 1ère (Bounce) et passage éclair en 2ème", duration_s=0.4, clutch=100.0, throttle=100.0, gear=2),
        ScenarioStep("4. Pleine charge 2ème", duration_s=2.5, clutch=0.0, throttle=100.0, gear=2),
        ScenarioStep("5. Passage 3ème", duration_s=0.4, clutch=100.0, throttle=100.0, gear=3),
        ScenarioStep("6. Ligne droite des stands à 150 km/h", duration_s=4.0, clutch=0.0, throttle=100.0, gear=3),
        ScenarioStep("7. Gros freinage en bout de ligne droite (ABS actif)", duration_s=2.5, throttle=0.0, brake=95.0, clutch=100.0, gear=3),
        ScenarioStep("8. Virage serré à droite en 2ème avec accélération latérale", duration_s=3.0, clutch=0.0, throttle=65.0, gear=2, steering=85.0),
        ScenarioStep("9. Sortie de virage et remise des gaz", duration_s=3.0, clutch=0.0, throttle=90.0, gear=2, steering=0.0),
        ScenarioStep("10. Tour d'honneur et ralentissement", duration_s=3.0, throttle=0.0, brake=40.0, clutch=100.0, gear=0),
    ]
    sport_scenario = Scenario("Circuit & Performance", "Conduite sportive extrême : Launch control, rupteur et freinage ABS.", sport_steps)

    # 4. Surchauffe & Alertes
    stress_steps = [
        ScenarioStep("1. Moteur en fonctionnement normal", duration_s=2.0, ignition=True, throttle=20.0, gear=2, force_temp=85.0),
        ScenarioStep("2. Forte charge continue et montée thermique", duration_s=3.0, throttle=90.0, gear=3, force_temp=98.0),
        ScenarioStep("3. Alerte Surchauffe moteur (>105°C - Moto-ventilateur max)", duration_s=4.0, throttle=60.0, gear=3, force_temp=108.0),
        ScenarioStep("4. Alerte Carburant bas (Niveau de réserve < 15%)", duration_s=3.0, throttle=20.0, gear=3, force_temp=95.0, force_fuel=3.5),
        ScenarioStep("5. Débrayage et calage moteur involontaire", duration_s=2.5, throttle=0.0, clutch=0.0, brake=100.0, gear=3),
        ScenarioStep("6. Rétablissement des paramètres de base", duration_s=1.0, ignition=True, gear=0, force_temp=88.0, force_fuel=40.0),
    ]
    stress_scenario = Scenario("Stress & Alertes", "Déclenchement des alertes critiques : Surchauffe, Réserve carburant et Calage.", stress_steps)

    # 5. Injection Diagnostic OBD2
    diag_steps = [
        ScenarioStep("1. Véhicule avec contact mis", duration_s=1.5, ignition=True),
        ScenarioStep("2. Injection du code défaut P0300 (Raté d'allumage)", duration_s=2.0, ignition=True, dtcs=["P0300"]),
        ScenarioStep("3. Injection de codes défauts multiples (P0300, P0115, P0420)", duration_s=4.0, ignition=True, dtcs=["P0300", "P0115", "P0420"]),
        ScenarioStep("4. Prêt pour le scan OBD-II dans CliOS", duration_s=5.0, ignition=True, dtcs=["P0300", "P0115", "P0420"]),
    ]
    diag_scenario = Scenario("Diagnostic & Pannes OBD", "Injection de codes défauts DTC pour tester le service de diagnostic.", diag_steps)

    return [city_scenario, highway_scenario, sport_scenario, stress_scenario, diag_scenario]
