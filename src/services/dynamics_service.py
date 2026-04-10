import threading
import time
from src.services.base_service import BaseService


class DynamicsService(BaseService):
    def __init__(self, api):
        super().__init__("Dynamics")
        self.api = api
        self.thread = None

        # Variables pour le RaceTab
        self.api._data["wheel_slip_fl"] = False
        self.api._data["wheel_slip_fr"] = False
        self.api._data["wheel_slip_rl"] = False
        self.api._data["wheel_slip_rr"] = False

        self.api._data["wheel_lock_fl"] = False
        self.api._data["wheel_lock_fr"] = False
        self.api._data["dynamic_warning"] = "OK"

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True)
        self.thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            # Utilisation des nouveaux noms du JSON
            w_fl = self.api._data.get("wheel_fl_speed", 0.0)
            w_fr = self.api._data.get("wheel_fr_speed", 0.0)
            w_rl = self.api._data.get("wheel_rl_speed", 0.0)
            w_rr = self.api._data.get("wheel_rr_speed", 0.0)

            # Référence : Moyenne des roues arrière
            v_ref = (w_rl + w_rr) / 2.0

            if v_ref > 5.0:
                # Patinage (Slip) -> Seuil 15%
                self.api._data["wheel_slip_fl"] = w_fl > (v_ref * 1.15)
                self.api._data["wheel_slip_fr"] = w_fr > (v_ref * 1.15)
                # Blocage (Lock) -> Seuil 30% de la vitesse ref
                self.api._data["wheel_lock_fl"] = w_fl < (v_ref * 0.3)
                self.api._data["wheel_lock_fr"] = w_fr < (v_ref * 0.3)

            time.sleep(0.05)