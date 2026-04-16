import os
import threading
import time
from src.parser import DbcParser
from src.services.base_service import BaseService
from src.signal_processor import SignalProcessor, RawFrame


class CanService(BaseService):
    """Service autonome gérant le bus CAN via SocketCAN (0% CPU overhead)."""

    def __init__(self, name: str, api, storage, dbc_path: str, provider, obd_callback=None):
        super().__init__("Can", storage)
        self.name = name
        self.api = api
        self.thread = None
        self.obd_callback = obd_callback

        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.provider = provider

        # --- RECHERCHE DES CARTES RÉSEAUX CAN (Linux Natif) ---
        available_interfaces = []
        try:
            # On liste les interfaces comme "can0", "can1"
            available_interfaces = [iface for iface in os.listdir('/sys/class/net') if iface.startswith('can')]
        except Exception:
            pass

        if not available_interfaces:
            available_interfaces = ["can0", "Aucun réseau CAN détecté"]

        # On enregistre uniquement l'interface (plus de ports série, plus de vitesse !)
        self.register_param("can_interface", "Interface Réseau", "list", available_interfaces[0], persistent=True, options=available_interfaces)

        # On attribue "can0" au driver
        self.provider.channel = self._params["can_interface"]["value"]

    def on_param_changed(self, key: str, value):
        if key == "can_interface":
            self.provider.channel = value
            self.provider.close()

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(target=self._run, args=(stop_event,), name=self.name, daemon=True)
        self.thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        # ==========================================
        # 1. CRÉATION DE L'INDEX
        # ==========================================
        db = self.parser.optimized_db
        valid_ids = set(db.keys())
        valid_ids.update(range(0x7E8, 0x7F0))

        rate_limit = 1.0 / 70.0
        last_seen = {}
        api_update = self.api.update
        processor_decode = self.processor.decode
        obd_call = self.obd_callback

        while not stop_event.is_set():
            if not self.provider.is_connected:
                try:
                    self.provider.connect()
                    self.set_ok(f"Connecté sur {self.provider.channel}.")
                except Exception as e:
                    self.set_error(f"Échec : {str(e)}")
                    stop_event.wait(2.0)
                    continue

            try:
                # Lecture via le noyau Linux (très rapide)
                frame = self.provider.read_frame(timeout=0.01)

                if frame is None:
                    time.sleep(0.001)
                    continue

                msg_id = frame.arbitration_id

                # ==========================================
                # 2. FILTRAGE À LA SOURCE
                # ==========================================
                if msg_id not in valid_ids:
                    continue

                if getattr(self.api, 'is_starting_up', False):
                    continue

                # ==========================================
                # 3. RATE LIMITING (70 Hz)
                # ==========================================
                now = time.time()
                if now - last_seen.get(msg_id, 0.0) < rate_limit:
                    continue
                last_seen[msg_id] = now

                # ==========================================
                # 4. TRAITEMENT DIRECT
                # ==========================================
                if 0x7E8 <= msg_id <= 0x7EF:
                    if obd_call:
                        obd_call(frame)
                else:
                    raw = RawFrame(id=msg_id, data=frame.data, timestamp=frame.timestamp)
                    decoded = processor_decode(raw, db[msg_id])
                    if decoded:
                        api_update(decoded)

            except Exception as e:
                self.set_error(f"Perte de l'interface réseau : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)

    def stop(self):
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        super().stop()