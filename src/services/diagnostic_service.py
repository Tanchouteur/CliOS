import threading
import time
from src.services.base_service import BaseService


class DiagnosticService(BaseService):
    def __init__(self, api, can_provider):
        super().__init__("DIAG")
        self.api = api
        self.provider = can_provider
        self.thread = None
        self._scan_requested = threading.Event()

        self.api._data["diag_codes"] = []
        self.api._data["diag_scanning"] = False
        self._last_obd_response = None
        self.api._data["diag_has_scanned"] = False

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name="Thread-Diag",
            daemon=True
        )
        self.thread.start()

    def request_scan(self):
        self._scan_requested.set()

    def receive_obd_frame(self, frame):
        """Callback: Reçoit la trame directement depuis le CanService."""
        self._last_obd_response = frame

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            if not self.provider.is_connected:
                self.set_error("Driver non connecter")
                success = self.provider.connect()

                if not success:
                    stop_event.wait(2.0)
                    continue
                else:
                    self.set_ok(f"Connecté avec succès sur {self.name}.")

            if self._scan_requested.wait(timeout=1.0):
                self._perform_scan()
                self._scan_requested.clear()

    def _perform_scan(self):
        self.api._data["diag_scanning"] = True
        self.api._data["diag_codes"] = []
        self._last_obd_response = None
        self.set_ok("Scan OBD2 en cours...")

        try:
            req_data = [0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            if not self.provider.send_frame(0x7DF, req_data):
                raise Exception("Erreur d'envoi CAN")

            timeout = time.time() + 2.0
            while time.time() < timeout:
                if self._last_obd_response is not None:
                    self._decode_dtc_response(self._last_obd_response.data)
                    break
                time.sleep(0.05)

            if self._last_obd_response is None:
                self.set_warning("Aucune réponse du calculateur (0x7E8)")
            else:
                self.set_ok("Scan terminé.")
                self.api._data["diag_has_scanned"] = True

        except Exception as e:
            self.set_error(str(e))
        finally:
            self.api._data["diag_scanning"] = False

    def _decode_dtc_response(self, data):
        if len(data) < 3 or data[1] != 0x43:
            return

        num_dtcs = data[2]
        codes = []
        for i in range(num_dtcs):
            idx = 3 + (i * 2)
            if idx + 1 >= len(data): break
            a, b = data[idx], data[idx + 1]

            letters = ["P", "C", "B", "U"]
            letter = letters[a >> 6]
            second = str((a >> 4) & 0b11)
            third = hex(a & 0x0F)[2:]
            fourth = hex(b >> 4)[2:]
            fifth = hex(b & 0x0F)[2:]

            codes.append(f"{letter}{second}{third}{fourth}{fifth}".upper())

        self.api._data["diag_codes"] = codes