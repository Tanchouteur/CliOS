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

        print("[DIAG] Service initialisé.")

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name="Thread-Diag",
            daemon=True
        )
        self.thread.start()

    def request_scan(self):
        print("[DIAG] 🖱️ Clic détecté : Requête de scan enregistrée.")
        self._scan_requested.set()

    def receive_obd_frame(self, frame):
        """Callback: Reçoit la trame directement depuis le CanService."""
        # On formate les données en hexadécimal pour que ce soit lisible dans la console
        hex_data = " ".join([f"{b:02X}" for b in frame.data])
        print(f"[DIAG] 📥 Trame interceptée (ID: 0x{frame.arbitration_id:03X}) -> [{hex_data}]")
        self._last_obd_response = frame

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            # 1. Mise à jour de l'état de santé (Sans toucher à la connexion !)
            if not self.provider.is_connected:
                self.set_warning("En attente de la liaison CAN...")
            else:
                self.set_ok("Prêt.")

            # 2. Attente du clic sur le bouton
            if self._scan_requested.wait(timeout=1.0):
                if self.provider.is_connected:
                    self._perform_scan()
                else:
                    print("[DIAG] ❌ Impossible de scanner : Port CAN fermé.")
                    self.set_error("Driver CAN déconnecté.")

                self._scan_requested.clear()

    def _perform_scan(self):
        print("\n[DIAG] 🚀 Démarrage de la séquence de diagnostic OBD2...")
        self.api._data["diag_scanning"] = True
        self.api._data["diag_codes"] = []
        self._last_obd_response = None
        self.set_ok("Scan OBD2 en cours...")

        try:
            req_data = [0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            print(f"[DIAG] 📤 Envoi de la requête 0x7DF (Mode 03) -> [{' '.join([f'{b:02X}' for b in req_data])}]")

            if not self.provider.send_frame(0x7DF, req_data):
                raise Exception("Erreur d'envoi matériel sur le bus CAN.")

            print("[DIAG] ⏳ En attente de la réponse du calculateur (Timeout: 2s)...")
            timeout = time.time() + 2.0

            while time.time() < timeout:
                if self._last_obd_response is not None:
                    print("[DIAG] ✅ Réponse reçue, début du décodage.")
                    self._decode_dtc_response(self._last_obd_response.data)
                    break
                time.sleep(0.05)

            if self._last_obd_response is None:
                print("[DIAG] ⚠️ TIMEOUT : L'ECU n'a rien répondu.")
                self.set_warning("Aucune réponse du calculateur (0x7E8)")
            else:
                nb_defauts = len(self.api._data['diag_codes'])
                print(f"[DIAG] 🏁 Scan terminé avec succès. {nb_defauts} défaut(s) trouvé(s).")
                self.set_ok("Scan terminé.")
                self.api._data["diag_has_scanned"] = True

        except Exception as e:
            print(f"[DIAG] ❌ Erreur critique pendant le scan : {e}")
            self.set_error(str(e))
        finally:
            self.api._data["diag_scanning"] = False

    def _decode_dtc_response(self, data):
        # data[0] = taille utile, data[1] = mode en réponse (0x43)
        if len(data) < 3 or data[1] != 0x43:
            print("[DIAG] ⚠️ Trame ignorée : Ce n'est pas une réponse valide au Mode 03.")
            return

        num_dtcs = data[2]
        print(f"[DIAG] 📊 L'ECU annonce contenir {num_dtcs} code(s) défaut(s).")

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

            code_final = f"{letter}{second}{third}{fourth}{fifth}".upper()
            print(f"[DIAG] 🛠️ Défaut décodé : {code_final}")
            codes.append(code_final)

        self.api._data["diag_codes"] = codes