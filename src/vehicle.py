import threading
import time

from src.storage import PersistentStorage


class VehicleAPI:
    """Couche d'Abstraction Matérielle (HAL). Gère uniquement les données brutes et le lissage."""

    def __init__(self):
        storage = PersistentStorage()
        last_odo = storage.get("last_odometer", 0.0)
        self._data = {
            "connexion_obd_moteur": False,
            "fuel_level": 100.0,
            "engine_light": "OFF",
            "odometer": last_odo
        }

        # Facteur de lissage exponentiel (1.0 = signal brut, 0.1 = filtrage fort)
        self._smoothing_factor = 1

        # Indicateurs d'état système
        self.is_starting_up = False
        self.critical_engine_error = False

    def update(self, new_data: dict):
        """Intègre les nouvelles données brutes du bus CAN."""
        if self.is_starting_up:
            return

        # 1. Intégration et filtrage passe-bas des nouvelles données
        for key, value in new_data.items():
            # On applique le lissage uniquement sur les valeurs numériques
            if key in self._data and type(value) in (int, float):
                old_val = self._data[key]
                self._data[key] = old_val + self._smoothing_factor * (value - old_val)
            else:
                self._data[key] = value

        # 2. Évaluation des états d'alerte matériels simples (Voyant Moteur)
        rpm = self._data.get("rpm", 0)
        ignition = self._data.get("ignition_on", False) or self._data.get("key_run", False)

        if self.critical_engine_error:
            self._data["engine_light"] = "RED"
        elif ignition and rpm < 300:
            self._data["engine_light"] = "ORANGE"
        else:
            self._data["engine_light"] = "OFF"

    # --- Séquences d'Initialisation ---

    def run_startup_sequence(self, duration_sec=2.0):
        """Exécute la routine de vérification matérielle visuelle (Sweep) au démarrage."""
        self.is_starting_up = True

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

            # Phase d'activation maximale
            for v in voyants_booleens: self._data[v] = True
            self._data["brightness"] = 100.0
            self._data["gear"] = "8"

            steps = 50
            sleep_time = (duration_sec / 2.0) / steps

            self._data["engine_light"] = "RED"

            # Interpolation linéaire montante
            for i in range(steps + 1):
                fraction = i / steps
                self._data["rpm"] = fraction * 7000.0
                self._data["speed"] = fraction * 200.0
                self._data["accel_pos"] = fraction * 100.0
                self._data["engine_temp"] = -20.0 + (fraction * 150.0)
                self._data["inst_cons"] = fraction * 30.0
                time.sleep(sleep_time)

            time.sleep(0.3)

            # Interpolation linéaire descendante
            for i in range(steps, -1, -1):
                fraction = i / steps
                self._data["rpm"] = fraction * 7000.0
                self._data["speed"] = fraction * 200.0
                self._data["accel_pos"] = fraction * 100.0
                self._data["engine_temp"] = -20.0 + (fraction * 150.0)
                self._data["inst_cons"] = fraction * 30.0
                time.sleep(sleep_time)

            # Rétablissement de l'état nominal
            for v in voyants_booleens: self._data[v] = False
            self._data["gear"] = "N"
            self._data["accel_pos"] = 0.0
            self._data["engine_temp"] = 0.0

            self.is_starting_up = False
            self._data["engine_light"] = "ORANGE"

        threading.Thread(target=sequence, daemon=True).start()

    def set_connection_status(self, status: bool):
        """Met à jour le statut de liaison avec le contrôleur matériel pour l'IHM."""
        if self._data.get("connexion_obd_moteur") != status:
            self._data["connexion_obd_moteur"] = status