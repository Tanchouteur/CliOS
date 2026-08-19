import threading
import time
import collections

from src.services.base_service import BaseService


class DiagnosticService(BaseService):
    """
    Service de diagnostic OBD2 universel.
    Gere le protocole de transport ISO-TP (Multi-trame) et le decodage DTC.
    """

    def __init__(self, runtime, can_provider):
        super().__init__("Diag")
        self.runtime = runtime
        self.provider = can_provider
        self.thread = None
        self._scan_requested = threading.Event()

        # File d'attente thread-safe pour les trames recues
        self._rx_buffer = collections.deque(maxlen=100)

        self.runtime.publish("diagnostics", {
            "codes": [],
            "scanning": False,
            "has_scanned": False,
            "ignition_on": False
        }, source="diagnostics")

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name=self.service_name,
            daemon=True
        )
        self.thread.start()
        super().start(stop_event, implemented=True)

    def request_scan(self):
        self._scan_requested.set()

    def receive_obd_frame(self, frame):
        """
        Callback asynchrone declenche par le fournisseur CAN.
        Filtre uniquement les reponses standard des calculateurs OBD2 (0x7E8 a 0x7EF).
        """
        if 0x7E8 <= frame.arbitration_id <= 0x7EF:
            self._rx_buffer.append(frame)

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            snapshot = self.runtime.snapshot()
            powertrain = snapshot.domain("powertrain")
            diagnostics = snapshot.domain("diagnostics")
            is_connected = self.provider.is_connected
            ignition_on = powertrain.get("key_run", False)

            self.runtime.publish("diagnostics", {"ignition_on": ignition_on}, source="diagnostics")

            if not is_connected:
                self.set_error("Adaptateur CAN non detecte")
            elif not diagnostics.get("scanning", False):
                self.set_ok("Pret pour scan")

            if self._scan_requested.wait(timeout=0.5):
                if is_connected:
                    try:
                        self._perform_scan()
                    except Exception as e:
                        self.set_error("Erreur systeme pendant le scan : " + str(e))
                        self.print_message(f"[SYS] Erreur fatale scan : {e}")
                self._scan_requested.clear()

    def _perform_scan(self):
        """
        Orchestre la requete OBD2 et la machine a etats de reception ISO-TP.
        """
        self.runtime.publish("diagnostics", {"scanning": True, "codes": []}, source="diagnostics")
        self.set_ok("Initialisation de la communication...")
        self._rx_buffer.clear()

        try:
            # 1. PING DE REVEIL (Keep-Alive)
            self.print_message("[OBD2] Envoi du signal de reveil (Mode 01 PID 00)")
            wake_up_data = [0x02, 0x01, 0x00, 0x55, 0x55, 0x55, 0x55, 0x55]
            self.provider.send_frame(0x7DF, wake_up_data)
            time.sleep(0.15)
            self._rx_buffer.clear()

            # 2. REQUETE DTC (Mode 03)
            self.print_message("[OBD2] Envoi de la requete DTC (Mode 03)")
            req_data = [0x01, 0x03, 0x55, 0x55, 0x55, 0x55, 0x55, 0x55]
            if not self.provider.send_frame(0x7DF, req_data):
                raise Exception("Impossible d'ecrire sur le bus materiel.")

            # Variables d'etat ISO-TP
            timeout = time.time() + 2.5
            expected_length = 0
            payload = bytearray()
            receiving_multi_frame = False

            self.print_message("[ISO-TP] Ecoute du reseau pour reponse ECU...")

            while time.time() < timeout:
                if self._rx_buffer:
                    frame = self._rx_buffer.popleft()
                    data = frame.data

                    # Analyse du Protocol Control Information (PCI)
                    frame_type = data[0] >> 4

                    if frame_type == 0:  # Single Frame (SF)
                        length = data[0] & 0x0F
                        payload = bytearray(data[1: 1 + length])
                        self.print_message(f"[ISO-TP] Trame Unique recue (Taille: {length} octets).")
                        break

                    elif frame_type == 1:  # First Frame (FF)
                        length = ((data[0] & 0x0F) << 8) + data[1]
                        expected_length = length
                        payload = bytearray(data[2:8])
                        receiving_multi_frame = True

                        self.print_message(f"[ISO-TP] Premiere Trame (Attendu: {length} octets). Envoi Flow Control.")

                        # Accuse de reception pour debloquer le calculateur (0x30 = Continue to Send)
                        fc_data = [0x30, 0x00, 0x00, 0x55, 0x55, 0x55, 0x55, 0x55]
                        self.provider.send_frame(0x7DF, fc_data)

                        # Rallonge le timeout en prevision du transfert de masse
                        timeout = time.time() + 2.0

                    elif frame_type == 2 and receiving_multi_frame:  # Consecutive Frame (CF)
                        seq_num = data[0] & 0x0F
                        payload.extend(data[1:8])
                        self.print_message(
                            f"[ISO-TP] Trame Consecutive recue (Seq: {seq_num}). Progression: {len(payload)}/{expected_length}")

                        if len(payload) >= expected_length:
                            payload = payload[:expected_length]
                            self.print_message("[ISO-TP] Transfert Multi-Trame termine avec succes.")
                            break

                else:
                    # Relache le processeur si le buffer est vide
                    time.sleep(0.01)

            if not payload:
                self.print_message("[OBD2] Echec: Aucune reponse valide avant expiration du delai.")
                self.set_warning("Aucune reponse du calculateur")
            else:
                self._decode_dtc_payload(payload)

        except Exception as e:
            self.print_message(f"[OBD2] Interruption anormale : {str(e)}")
            self.set_error("Echec d'analyse : " + str(e))
        finally:
            self.runtime.publish("diagnostics", {"scanning": False}, source="diagnostics")

    def _decode_dtc_payload(self, payload):
        """
        Extrait les codes defauts (DTC) d'un payload ISO-TP reconstruit.
        """
        self.print_message(f"[OBD2] Analyse de la donnee brute : {payload.hex(' ')}")

        # Validation de l'entete Mode 03 (43)
        if len(payload) < 2 or payload[0] != 0x43:
            self.print_message("[OBD2] Rejet: La reponse n'appartient pas au service 03.")
            return

        num_dtcs = payload[1]
        self.print_message(f"[OBD2] Le calculateur signale {num_dtcs} defaut(s) en memoire.")

        codes = []
        for i in range(num_dtcs):
            idx = 2 + (i * 2)
            if idx + 1 >= len(payload):
                self.print_message(f"[OBD2] Avertissement: Payload coupe avant le DTC #{i + 1}")
                break

            a = payload[idx]
            b = payload[idx + 1]

            # Filtrage du padding residuel
            if a == 0x00 and b == 0x00:
                continue

            letters = ["P", "C", "B", "U"]
            letter = letters[a >> 6]
            second = str((a >> 4) & 0b11)
            third = hex(a & 0x0F)[2:]
            fourth = hex(b >> 4)[2:]
            fifth = hex(b & 0x0F)[2:]

            dtc_str = f"{letter}{second}{third}{fourth}{fifth}".upper()
            codes.append(dtc_str)
            self.print_message(f"[OBD2] DTC decode : {dtc_str}")

        self.runtime.publish("diagnostics", {
            "codes": codes,
            "has_scanned": True
        }, source="diagnostics")
        self.set_ok(f"Termine. {len(codes)} defaut(s) lus.")
