import threading
import time
from src.services.base_service import BaseService


class DynamicsService(BaseService):
    def __init__(self, api, config, storage=None):
        super().__init__("Dynamics", storage)
        self.api = api
        self.thread = None

        # --- INITIALISATION DE LA BOÎTE DE VITESSES ---
        trans_config = config.get("transmission", {})
        self._gear_ratios = trans_config.get("ratios", {})
        self._gear_tolerance = trans_config.get("tolerance", 5.0)
        self._last_gear_rpm = -100
        self._last_gear_speed = -100

        self.api._data["gear"] = "N"

        # --- INITIALISATION ROUES ---
        self.api._data["wheel_slip_fl"] = False
        self.api._data["wheel_slip_fr"] = False
        self.api._data["wheel_slip_rl"] = False
        self.api._data["wheel_slip_rr"] = False
        self.api._data["wheel_lock_fl"] = False
        self.api._data["wheel_lock_fr"] = False
        self.api._data["wheel_lock_rl"] = False
        self.api._data["wheel_lock_rr"] = False

        self.api._data["dynamic_warning"] = "OK"

        self.register_param("min_speed", "Vitesse Min (km/h)", "slider", 5.0, min_val=1.0, max_val=30.0)
        self.register_param("slip_margin", "Tolérance Patinage (%)", "slider", 15.0, min_val=5.0, max_val=50.0)
        self.register_param("lock_margin", "Seuil de Blocage (%)", "slider", 30.0, min_val=5.0, max_val=80.0)

    def reload_config(self, new_config: dict):
        """Met à jour les rapports en RAM après un étalonnage."""
        trans_config = new_config.get("transmission", {})
        self._gear_ratios = trans_config.get("ratios", self._gear_ratios)
        self._gear_tolerance = trans_config.get("tolerance", self._gear_tolerance)
        self.print_message(f"Rapports de boîte rechargés ({len(self._gear_ratios)} rapports).")

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="DynamicsService")
        self.thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            w_fl = self.api._data.get("wheel_fl_speed", 0.0)
            w_fr = self.api._data.get("wheel_fr_speed", 0.0)
            w_rl = self.api._data.get("wheel_rl_speed", 0.0)
            w_rr = self.api._data.get("wheel_rr_speed", 0.0)

            v_ref = self.api._data.get("speed", (w_fl + w_fr + w_rl + w_rr) / 4.0)

            min_v = self._params["min_speed"]["value"]
            slip_mult = 1.0 + (self._params["slip_margin"]["value"] / 100.0)
            lock_mult = self._params["lock_margin"]["value"] / 100.0

            if v_ref > min_v:
                self.api._data["wheel_slip_fl"] = w_fl > (v_ref * slip_mult)
                self.api._data["wheel_slip_fr"] = w_fr > (v_ref * slip_mult)
                self.api._data["wheel_slip_rl"] = w_rl > (v_ref * slip_mult)
                self.api._data["wheel_slip_rr"] = w_rr > (v_ref * slip_mult)

                self.api._data["wheel_lock_fl"] = w_fl < (v_ref * lock_mult)
                self.api._data["wheel_lock_fr"] = w_fr < (v_ref * lock_mult)
                self.api._data["wheel_lock_rl"] = w_rl < (v_ref * lock_mult)
                self.api._data["wheel_lock_rr"] = w_rr < (v_ref * lock_mult)
            else:
                for w in ["fl", "fr", "rl", "rr"]:
                    self.api._data[f"wheel_slip_{w}"] = False
                    self.api._data[f"wheel_lock_{w}"] = False

            # --- CALCUL DU RAPPORT DE BOÎTE ---
            rpm = self.api._data.get("rpm", 0)
            clutch = self.api._data.get("clutch", False)
            reverse = self.api._data.get("reverse_engaged", False)

            if reverse:
                self.api._data["gear"] = "R"
            elif clutch or v_ref < 3.0:
                self.api._data["gear"] = "N"
            else:
                if abs(rpm - self._last_gear_rpm) > 50 or abs(v_ref - self._last_gear_speed) > 1.0:
                    current_ratio = rpm / v_ref if v_ref > 0 else 0
                    best_gear, smallest_diff = "N", float('inf')
                    for gear_name, target_ratio in self._gear_ratios.items():
                        diff = abs(current_ratio - float(target_ratio))
                        if diff <= self._gear_tolerance and diff < smallest_diff:
                            smallest_diff, best_gear = diff, gear_name

                    self.api._data["gear"] = best_gear
                    self._last_gear_rpm = rpm
                    self._last_gear_speed = v_ref

            time.sleep(0.05)