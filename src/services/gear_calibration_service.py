import json
import threading
import time
from collections import defaultdict
from src.services.base_service import BaseService


class GearCalibrationService(BaseService):
    def __init__(self, api, storage, profile_manager, dynamics_service):
        super().__init__("GearCalibration", storage)
        self.api = api
        self.profile_manager = profile_manager
        self.dynamics_service = dynamics_service

        self.is_calibrating = False
        self.collected_ratios = []

        # Variables pour l'interface visuelle (Télémétrie)
        self.api._data["calibration_active"] = False
        self.api._data["calibration_ratio"] = 0.0
        self.api._data["calibration_count"] = 0

        # --- L'INTERRUPTEUR DANS LES RÉGLAGES ---
        self.register_param("calib_toggle", "Mode Étalonnage", "toggle", False, persistent=False)

    def on_param_changed(self, key: str, value):
        """Intercepte les clics de l'utilisateur dans l'interface de réglages."""
        if key == "calib_toggle":
            if value is True:
                self.start_calibration()
            else:
                self.stop_and_save_calibration()

    def start_calibration(self):
        self.is_calibrating = True
        self.collected_ratios.clear()
        self.api._data["calibration_active"] = True
        self.api._data["calibration_count"] = 0
        self.set_ok("Étalonnage en cours...")
        print("[GEAR] Début de l'étalonnage. Roulez et passez tous les rapports.")

    def stop_and_save_calibration(self):
        self.is_calibrating = False
        self.api._data["calibration_active"] = False
        self.api._data["calibration_ratio"] = 0.0

        # Sécurité si on éteint l'interrupteur sans avoir roulé
        if not self.collected_ratios:
            self.set_warning("Annulé : Aucune donnée.")
            return False

        # Regroupement par tranches pour trouver les rapports
        histogram = defaultdict(int)
        for ratio in self.collected_ratios:
            rounded_ratio = round(ratio)
            histogram[rounded_ratio] += 1

        # On garde les ratios stables (plus de 20 occurrences = 1 seconde à 50ms)
        valid_peaks = [ratio for ratio, count in histogram.items() if count > 20]

        if not valid_peaks:
            self.set_error("Échec : Données instables.")
            return False

        # Le ratio le plus élevé est la 1ère vitesse
        valid_peaks.sort(reverse=True)
        new_ratios = {str(idx + 1): float(peak) for idx, peak in enumerate(valid_peaks)}

        # Sauvegarde via le Profile Manager
        config_path = self.profile_manager.get_config_path()
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            if "transmission" not in config_data:
                config_data["transmission"] = {"tolerance": 5.0}

            config_data["transmission"]["ratios"] = new_ratios

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)

            # Rechargement à chaud dans le DynamicsService
            self.dynamics_service.reload_config(config_data)

            self.set_ok(f"Succès : {len(new_ratios)} rapports enregistrés.")
            print(f"[GEAR] Nouveaux rapports : {new_ratios}")
            return True

        except Exception as e:
            self.set_error(f"Erreur d'écriture : {str(e)}")
            return False

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="GearCalibration").start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            if self.is_calibrating:
                speed = self.api._data.get("speed", 0.0)
                rpm = self.api._data.get("rpm", 0.0)
                throttle = self.api._data.get("accel_pos", 0.0)
                clutch = self.api._data.get("clutch", False)

                if throttle > 10.0 and speed > 5.0 and not clutch:
                    current_ratio = rpm / speed
                    self.collected_ratios.append(current_ratio)

                    self.api._data["calibration_ratio"] = round(current_ratio, 1)
                    self.api._data["calibration_count"] = len(self.collected_ratios)
                else:
                    self.api._data["calibration_ratio"] = 0.0

            time.sleep(0.05)