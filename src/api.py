import threading
import time

from src.logging_runtime import get_logger
from src.state_store import VEHICLE_DOMAINS, VehicleStateStore


class VehicleAPI:
    """Couche d'Abstraction Matérielle (HAL). Gère les données brutes du bus CAN."""

    def __init__(self, storage):
        self.logger = get_logger("VehicleAPI")
        self.storage = storage

        # Priorité à la clé actuelle, puis fallback legacy; évite les trips à 0 avec des saves anciens.
        last_odo = storage.get("vehicle.last_odometer", 0.0)
        if last_odo <= 0.0:
            legacy_odo = storage.get("last_odometer", 0.0)
            if legacy_odo > 0.0:
                last_odo = legacy_odo
            else:
                last_odo = max(
                    storage.get("trips.a.marker", 0.0),
                    storage.get("trips.b.marker", 0.0),
                    storage.get("vehicle.last_revision_odo", 0.0),
                )

        initial_state = {
            "fuel_level": 100.0,
            "engine_light": "OFF",
            "odometer": last_odo
        }
        self.state = VehicleStateStore(initial_state)

        # L'animation de démarrage est une surcouche de présentation. Elle ne
        # doit jamais devenir une entrée pour les services de calcul.
        self.data_lock = threading.RLock()
        self._startup_overlay = {}

        # Indicateurs d'état système
        self.is_starting_up = False
        self.critical_engine_error = False

    def get_display_data(self):
        """Vue plate de compatibilité contenant uniquement les vraies données."""
        return self.state.flat_snapshot()

    def get_presentation_data(self):
        """Vue historique destinée à l'UI, avec éventuel sweep de démarrage."""
        data = self.state.flat_snapshot()
        with self.data_lock:
            if self.is_starting_up:
                data.update(self._startup_overlay)
        return data

    def get_vehicle_state(self):
        """Contrat structuré stable pour les nouveaux consommateurs UI."""
        return self.state.domain_snapshot(VEHICLE_DOMAINS)

    def get_runtime_state(self):
        """Snapshot atomique de tous les domaines (debug et bridge)."""
        return self.state.domain_snapshot()

    def get_domain_state(self, *domains: str):
        return self.state.domain_snapshot(domains)

    def get_data_quality(self):
        return self.state.metadata_snapshot()

    def is_signal_fresh(self, key: str, max_age_s: float) -> bool:
        return self.state.is_fresh(key, max_age_s)

    def update(self, new_data: dict, *, domain=None, source="legacy", ttl_s=None):
        """Publie atomiquement des données, classées par domaine métier."""
        if not isinstance(new_data, dict):
            self.logger.warning("Payload API invalide ignore", extra={"error_code": "API_INVALID_PAYLOAD"})
            return

        self.state.update(new_data, source=source, domain=domain, ttl_s=ttl_s)

        # Compatibilité temporaire : l'état du voyant sera ensuite un calcul
        # dédié, mais sa publication reste ici atomique avec l'état moteur.
        current = self.state.flat_snapshot()
        rpm = current.get("rpm", 0)
        ignition = current.get("ignition_on", False) or current.get("key_run", False)
        if self.critical_engine_error:
            engine_light = "RED"
        elif ignition and rpm < 300:
            engine_light = "ORANGE"
        else:
            engine_light = "OFF"
        if current.get("engine_light") != engine_light:
            self.state.update(
                {"engine_light": engine_light}, domain="powertrain", source="engine-status"
            )

    def update_domain(self, domain: str, new_data: dict, *, source: str, ttl_s=None):
        self.update(new_data, domain=domain, source=source, ttl_s=ttl_s)

    # Séquence d'initialisation visuelle.

    def run_startup_sequence(self, duration_sec=2.0):
        """Exécute la routine de vérification matérielle visuelle (Sweep)."""
        self.is_starting_up = True

        with self.data_lock:
            self._startup_overlay = {}

        def sequence():
            time.sleep(1.0)
            voyants_booleens = [
                "brake", "clutch", "comodo_down", "comodo_up", "door_fl_open",
                "door_fr_open", "door_rl_open", "door_rr_open", "doors_locked",
                "driver_unbelted", "fog_front", "fog_rear", "high_beam",
                "ignition_on", "key_acc", "key_run", "low_beam", "passenger_disabled",
                "pos_lights", "reverse", "reverse_engaged", "trunk_locked",
                "trunk_open", "turn_left", "turn_right", "oil_warning",
                "battery_warning", "abs_error", "esp_active",
                "stop_warning", "service_warning"
            ]

            # Met à jour l'état UI de démarrage.
            with self.data_lock:
                self._startup_overlay.update(dict.fromkeys(voyants_booleens, True))
                self._startup_overlay.update({"brightness": 100.0, "gear": "8", "engine_light": "RED"})

            steps = 50
            sleep_time = (duration_sec / 2.0) / steps

            for i in range(steps + 1):
                fraction = i / steps
                with self.data_lock:
                    self._startup_overlay.update({
                        "rpm": fraction * 7000.0,
                        "speed": fraction * 200.0,
                        "accel_pos": fraction * 100.0,
                        "engine_temp": -20.0 + (fraction * 150.0),
                        "inst_cons": fraction * 30.0
                    })
                time.sleep(sleep_time)

            time.sleep(0.3)

            for i in range(steps, -1, -1):
                fraction = i / steps
                with self.data_lock:
                    self._startup_overlay.update({
                        "rpm": fraction * 7000.0,
                        "speed": fraction * 200.0,
                        "accel_pos": fraction * 100.0,
                        "engine_temp": -20.0 + (fraction * 150.0),
                        "inst_cons": fraction * 30.0
                    })
                time.sleep(sleep_time)

            with self.data_lock:
                self.is_starting_up = False
                self._startup_overlay = {}

        threading.Thread(target=sequence, daemon=True).start()
