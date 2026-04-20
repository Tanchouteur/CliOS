import time
import threading
import traceback

from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType

class NotificationService(BaseService):
    def __init__(self, bridge, storage=None):
        super().__init__("Notification", storage)
        self.bridge = bridge
        self._states = {
            "obd_lost_notified": False,
            "clutch_start_time": None,
            "clutch_warned": False
        }
        self._thread = None

        self.register_param("enable_clutch_warn", "Alerte Embrayage", ServiceParamType.TOGGLE, True)
        self.register_param("clutch_time_limit", "Temps Limite (s)", ServiceParamType.SLIDER, 5.0,
                            min_val=2.0, max_val=15.0)
        self.register_param("min_speed", "Vitesse Min. (km/h)", ServiceParamType.SLIDER, 15.0,
                            min_val=0.0, max_val=50.0)
        self.register_param("notif_duration", "Durée Affichage (ms)", ServiceParamType.SLIDER, 4000.0,
                            min_val=1000.0, max_val=10000.0)

    def start(self, stop_event):
        self._thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name)
        self._thread.start()
        super().start(stop_event, implemented=True)

    def stop(self):
        super().stop()

    def check_data(self, data: dict):
        if not data:
            return
        current_time = time.time()
        # Utilise le snapshot API reçu pour éviter les lectures concurrentes.
        self._check_clutch_pressed(data.get('clutch', False), current_time, data)

    def _run(self, stop_event):
        time.sleep(1.0)

        while not stop_event.is_set():
            try:
                if self.bridge and hasattr(self.bridge, 'api'):
                    safe_data = self.bridge.api.get_display_data()
                    self.check_data(safe_data)
                else:
                    self.print_message("[ERREUR] Le bridge ou l'API n'est pas accessible.")
            except Exception as e:
                self.print_message(f"\n[ERREUR FATALE] Le service a planté : {e}")
                traceback.print_exc()
                self.set_error(f"Crash inattendu : {str(e)}")

            stop_event.wait(1.0)

    def _check_clutch_pressed(self, clutch_pressed: bool, current_time, safe_data: dict):
        if not self._params["enable_clutch_warn"]["value"]:
            self._states["clutch_start_time"] = None
            self._states["clutch_warned"] = False
            return

        time_limit = self._params["clutch_time_limit"]["value"]
        min_speed = self._params["min_speed"]["value"]
        duration = int(self._params["notif_duration"]["value"])

        if clutch_pressed:
            current_speed = safe_data.get("speed", 0.0)

            if self._states["clutch_start_time"] is None:
                self._states["clutch_start_time"] = current_time
            elif (current_time - self._states["clutch_start_time"] > time_limit) and not self._states["clutch_warned"] and current_speed > min_speed:
                self.bridge.send_notification("WARNING", "ATTENTION : EMBRAYAGE SOLLICITÉ", duration)
                self._states["clutch_warned"] = True
        else:
            self._states["clutch_start_time"] = None
            self._states["clutch_warned"] = False

    def send_notification(self,level: str ,message: str, duration: int):
        self.bridge.send_notification(level ,message, duration)