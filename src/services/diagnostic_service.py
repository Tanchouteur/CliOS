import threading
import time
from os import name

from src.services.base_service import BaseService, ServiceStatus


class DiagnosticService(BaseService):
    def __init__(self, api, can_provider):
        super().__init__("Diag")
        self.api = api
        self.provider = can_provider
        self.thread = None
        self._scan_requested = threading.Event()

        self.api._data["diag_codes"] = []
        self.api._data["diag_scanning"] = False
        self.api._data["diag_has_scanned"] = False

        self._last_obd_response = None

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name="Thread-Diag",
            daemon=True
        )
        self.thread.start()
        super().start(stop_event, implemented=True)

    def request_scan(self):
        if self.api._data.get("key_run", False):
            self._scan_requested.set()

    def receive_obd_frame(self, frame):
        hex_data = " ".join([f"{b:02X}" for b in frame.data])
        #print(f"[DIAG] Trame interceptée (ID: 0x{frame.arbitration_id:03X}) -> [{hex_data}]")
        self._last_obd_response = frame

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            # 1. Analyse de l'état matériel et du véhicule
            is_connected = self.provider.is_connected
            ignition_on = self.api._data.get("key_run", False)

            # Mise à jour pour le QML
            self.api._data["diag_ignition_on"] = ignition_on

            # 2. Gestion des états avec set_warning
            if not is_connected:
                self.set_error("Adaptateur CAN non détecté")
            elif not ignition_on :
                self.set_warning("Contact requis pour le diagnostic")
            else:
                if not self.api._data.get("diag_scanning", False):
                    self.set_ok("Prêt pour scan")

            # 3. Gestion de la demande de scan
            if self._scan_requested.wait(timeout=0.5):
                if is_connected and ignition_on:
                    try:
                        self._perform_scan()
                    except Exception as e:
                        self.set_error("Erreur pendant le scan : "+str(e))
                #else:
                #    print("[DIAG] Abandon : Conditions non réunies (Contact/Connexion).")
                self._scan_requested.clear()

    def _perform_scan(self):
        #print("\n[DIAG] Démarrage de la séquence de diagnostic OBD2...")
        self.api._data["diag_scanning"] = True
        self.api._data["diag_codes"] = []
        self._last_obd_response = None
        self.set_ok("Scan OBD2 en cours...")

        try:
            req_data = [0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            print(f"[DIAG] Envoi de la requête 0x7DF (Mode 03) -> [{' '.join([f'{b:02X}' for b in req_data])}]")

            if not self.provider.send_frame(0x7DF, req_data):
                raise Exception("Erreur d'envoi matériel sur le bus CAN.")

            #print("[DIAG] En attente de la réponse du calculateur (Timeout: 2s)...")
            timeout = time.time() + 2.0

            while time.time() < timeout:
                if self._last_obd_response is not None:
                    print("[DIAG] Réponse reçue, début du décodage.")
                    self._decode_dtc_response(self._last_obd_response.data)
                    break
                time.sleep(0.05)

            if self._last_obd_response is None:
                print("[DIAG] TIMEOUT : L'ECU n'a rien répondu.")
                self.set_warning("Aucune réponse du calculateur (0x7E8)")
            else:
                nb_defauts = len(self.api._data['diag_codes'])
                print(f"[DIAG] Scan terminé avec succès. {nb_defauts} défaut(s) trouvé(s).")
                self.set_ok("Scan terminé.")
                self.api._data["diag_has_scanned"] = True

        except Exception as e:
            self.set_error("Erreur critique pendant le scan : "+str(e))
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