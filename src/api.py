import threading
import time


class VehicleAPI:
    """Couche d'Abstraction Matérielle (HAL). Gère les données brutes du bus CAN."""

    def __init__(self, storage, diag=None):
        self.storage = storage
        self.diag = diag or {}
        last_odo = storage.get("last_odometer", 0.0)

        # --- NOUVEAU : Le Cadenas Anti-Crash ---
        self.data_lock = threading.Lock()

        # 1. LA VRAIE RÉALITÉ PHYSIQUE
        self._data = {
            "fuel_level": 100.0,
            "engine_light": "OFF",
            "odometer": last_odo
        }

        # 2. L'ILLUSION VISUELLE
        self._ui_data = self._data.copy()

        # Indicateurs d'état système
        self.is_starting_up = False
        self.critical_engine_error = False

        # Diagnostic runtime: permet d'identifier qui pousse des updates et avec quels types.
        self._diag_log_api = bool(self.diag.get("log_api", False))
        self._diag_api_last = time.time()
        self._diag_api_updates = 0
        self._diag_api_sources = {}
        self._diag_api_key_types = {}

    def get_display_data(self):
        """Fournit une copie 100% sécurisée au Bridge sans bloquer le CAN."""
        with self.data_lock:
            if self.is_starting_up:
                return self._ui_data.copy()
            return self._data.copy()

    def update(self, new_data: dict):
        """Intègre les nouvelles données sous haute protection."""
        if self._diag_log_api:
            self._diag_update_stats(new_data)

        # On verrouille le dictionnaire juste le temps de l'écriture
        with self.data_lock:
            self._data.update(new_data)

            rpm = self._data.get("rpm", 0)
            ignition = self._data.get("ignition_on", False) or self._data.get("key_run", False)

            if self.critical_engine_error:
                self._data["engine_light"] = "RED"
            elif ignition and rpm < 300:
                self._data["engine_light"] = "ORANGE"
            else:
                self._data["engine_light"] = "OFF"

    def _diag_update_stats(self, new_data: dict):
        self._diag_api_updates += 1
        source = threading.current_thread().name
        self._diag_api_sources[source] = self._diag_api_sources.get(source, 0) + 1

        for key, value in new_data.items():
            t_name = type(value).__name__
            prev = self._diag_api_key_types.get(key)
            if prev is None:
                self._diag_api_key_types[key] = t_name
            elif prev != t_name:
                print(f"[DIAG][API][TYPE] '{key}' : {prev} -> {t_name} (source={source})")
                self._diag_api_key_types[key] = t_name

        now = time.time()
        if now - self._diag_api_last >= 2.0:
            top_sources = ", ".join(
                f"{name}:{count}" for name, count in sorted(self._diag_api_sources.items(), key=lambda x: x[1], reverse=True)
            )
            print(f"[DIAG][API] updates={self._diag_api_updates} sources=[{top_sources}]")
            self._diag_api_last = now
            self._diag_api_updates = 0
            self._diag_api_sources = {}

    # --- Séquences d'Initialisation ---

    def run_startup_sequence(self, duration_sec=2.0):
        """Exécute la routine de vérification matérielle visuelle (Sweep)."""
        self.is_starting_up = True

        with self.data_lock:
            self._ui_data = self._data.copy()

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

            # On verrouille à chaque mise à jour de l'animation
            with self.data_lock:
                self._ui_data.update(dict.fromkeys(voyants_booleens, True))
                self._ui_data.update({"brightness": 100.0, "gear": "8", "engine_light": "RED"})

            steps = 50
            sleep_time = (duration_sec / 2.0) / steps

            for i in range(steps + 1):
                fraction = i / steps
                with self.data_lock:
                    self._ui_data.update({
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
                    self._ui_data.update({
                        "rpm": fraction * 7000.0,
                        "speed": fraction * 200.0,
                        "accel_pos": fraction * 100.0,
                        "engine_temp": -20.0 + (fraction * 150.0),
                        "inst_cons": fraction * 30.0
                    })
                time.sleep(sleep_time)

            self.is_starting_up = False

        threading.Thread(target=sequence, daemon=True).start()