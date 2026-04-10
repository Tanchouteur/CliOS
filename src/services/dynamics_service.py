import threading
import time
from src.services.base_service import BaseService


class DynamicsService(BaseService):
    def __init__(self, api, storage=None):
        super().__init__("Dynamics", storage)
        self.api = api
        self.thread = None

        # --- INITIALISATION : Les 4 roues pour le RaceTab et les LEDs GT3 ---
        self.api._data["wheel_slip_fl"] = False
        self.api._data["wheel_slip_fr"] = False
        self.api._data["wheel_slip_rl"] = False
        self.api._data["wheel_slip_rr"] = False

        self.api._data["wheel_lock_fl"] = False
        self.api._data["wheel_lock_fr"] = False
        self.api._data["wheel_lock_rl"] = False
        self.api._data["wheel_lock_rr"] = False

        self.api._data["dynamic_warning"] = "OK"

        # --- DÉCLARATION DES PARAMÈTRES DYNAMIQUES ---
        self.register_param("min_speed", "Vitesse Min (km/h)", "slider", 5.0, min_val=1.0, max_val=30.0)
        self.register_param("slip_margin", "Tolérance Patinage (%)", "slider", 15.0, min_val=5.0, max_val=50.0)
        self.register_param("lock_margin", "Seuil de Blocage (%)", "slider", 30.0, min_val=5.0, max_val=80.0)

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True)
        self.thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            w_fl = self.api._data.get("wheel_fl_speed", 0.0)
            w_fr = self.api._data.get("wheel_fr_speed", 0.0)
            w_rl = self.api._data.get("wheel_rl_speed", 0.0)
            w_rr = self.api._data.get("wheel_rr_speed", 0.0)

            # Vitesse réelle d'avancement de la voiture
            # Idéalement, on prend la vitesse tableau de bord. Sinon, on moyenne les 4 roues.
            v_ref = self.api._data.get("speed", (w_fl + w_fr + w_rl + w_rr) / 4.0)

            # --- LECTURE DES PARAMÈTRES EN TEMPS RÉEL ---
            min_v = self._params["min_speed"]["value"]
            # Ex: 15% devient 1.15
            slip_mult = 1.0 + (self._params["slip_margin"]["value"] / 100.0)
            # Ex: 30% devient 0.30
            lock_mult = self._params["lock_margin"]["value"] / 100.0

            if v_ref > min_v:
                # PATINAGE (La roue tourne beaucoup plus vite que la voiture n'avance)
                self.api._data["wheel_slip_fl"] = w_fl > (v_ref * slip_mult)
                self.api._data["wheel_slip_fr"] = w_fr > (v_ref * slip_mult)
                self.api._data["wheel_slip_rl"] = w_rl > (v_ref * slip_mult)
                self.api._data["wheel_slip_rr"] = w_rr > (v_ref * slip_mult)

                # BLOCAGE (La roue est à l'arrêt ou presque, mais la voiture avance encore)
                self.api._data["wheel_lock_fl"] = w_fl < (v_ref * lock_mult)
                self.api._data["wheel_lock_fr"] = w_fr < (v_ref * lock_mult)
                self.api._data["wheel_lock_rl"] = w_rl < (v_ref * lock_mult)
                self.api._data["wheel_lock_rr"] = w_rr < (v_ref * lock_mult)
            else:
                # À très basse vitesse (dans les bouchons), on coupe tout pour éviter les faux positifs
                self.api._data["wheel_slip_fl"] = False
                self.api._data["wheel_slip_fr"] = False
                self.api._data["wheel_slip_rl"] = False
                self.api._data["wheel_slip_rr"] = False
                self.api._data["wheel_lock_fl"] = False
                self.api._data["wheel_lock_fr"] = False
                self.api._data["wheel_lock_rl"] = False
                self.api._data["wheel_lock_rr"] = False

            time.sleep(0.05)