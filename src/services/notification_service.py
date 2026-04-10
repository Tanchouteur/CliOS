import time
import threading
import traceback

from src.services.base_service import BaseService


class NotificationService(BaseService):
    def __init__(self, bridge):
        super().__init__("Notification")
        self.bridge = bridge
        self._states = {
            "obd_lost_notified": False,
            "clutch_start_time": None,
            "clutch_warned": False
        }
        self._thread = None

    def start(self, stop_event):
        self._thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="NotifWorker")
        self._thread.start()
        super().start(stop_event, implemented=True)

    def stop(self):
        super().stop()

    def check_data(self, data: dict):
        if not data:
            return

        current_time = time.time()

        self._check_clutch_pressed(data.get('clutch', False), current_time)

    def _run(self, stop_event):
        time.sleep(1.0)

        while not stop_event.is_set():
            try:
                if self.bridge and hasattr(self.bridge, 'api'):
                    self.check_data(self.bridge.api._data)
                else:
                    print("[ERREUR NOTIF] Le bridge ou l'API n'est pas accessible.")
            except Exception as e:
                print(f"\n[ERREUR FATALE NOTIF] Le service a planté : {e}")
                traceback.print_exc()
                self.set_error(f"[Notif] Crash inattendu : {str(e)}")

            time.sleep(1.0)

    def _check_clutch_pressed(self, clutch_pressed: bool, current_time):
        is_clutch_pressed = clutch_pressed

        if is_clutch_pressed:
            if self._states["clutch_start_time"] is None:
                self._states["clutch_start_time"] = current_time

            elif (current_time - self._states["clutch_start_time"] > 5.0) and not self._states["clutch_warned"] and self.bridge._data["speed"] > 15:
                self.bridge.send_notification("WARNING", "ATTENTION : EMBRAYAGE SOLLICITÉ", 4000)
                self._states["clutch_warned"] = True
        else:
            self._states["clutch_start_time"] = None
            self._states["clutch_warned"] = False