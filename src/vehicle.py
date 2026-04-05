import threading
import time

from src.storage import PersistentStorage


class VehicleAPI:
    """Couche d'Abstraction Matérielle (HAL). Gère uniquement les données brutes du bus CAN."""

    def __init__(self):
        storage = PersistentStorage()
        last_odo = storage.get("last_odometer", 0.0)

        self._data = {
            "fuel_level": 100.0,
            "engine_light": "OFF",
            "odometer": last_odo
        }

        # Indicateurs d'état système
        self.is_starting_up = False
        self.critical_engine_error = False

    def update(self, new_data: dict):
        """Intègre les nouvelles données brutes du bus CAN (exécuté très fréquemment)."""
        if self.is_starting_up:
            return

        self._data.update(new_data)

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

            # Phase d'activation maximale (Optimisé en une seule ligne)
            self._data.update(dict.fromkeys(voyants_booleens, True))
            self._data.update({"brightness": 100.0, "gear": "8", "engine_light": "RED"})

            steps = 50
            sleep_time = (duration_sec / 2.0) / steps

            # Interpolation linéaire montante
            for i in range(steps + 1):
                fraction = i / steps
                self._data.update({
                    "rpm": fraction * 7000.0,
                    "speed": fraction * 200.0,
                    "accel_pos": fraction * 100.0,
                    "engine_temp": -20.0 + (fraction * 150.0),
                    "inst_cons": fraction * 30.0
                })
                time.sleep(sleep_time)

            time.sleep(0.3)

            # Interpolation linéaire descendante
            for i in range(steps, -1, -1):
                fraction = i / steps
                self._data.update({
                    "rpm": fraction * 7000.0,
                    "speed": fraction * 200.0,
                    "accel_pos": fraction * 100.0,
                    "engine_temp": -20.0 + (fraction * 150.0),
                    "inst_cons": fraction * 30.0
                })
                time.sleep(sleep_time)

            # Rétablissement de l'état nominal
            self._data.update(dict.fromkeys(voyants_booleens, False))
            self._data.update({
                "gear": "N",
                "accel_pos": 0.0,
                "engine_temp": 0.0,
                "engine_light": "ORANGE"
            })

            self.is_starting_up = False

        threading.Thread(target=sequence, daemon=True).start()