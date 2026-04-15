import threading
import time
import serial.tools.list_ports
from src.parser import DbcParser
from src.services.base_service import BaseService
from src.signal_processor import SignalProcessor, RawFrame


class CanService(BaseService):
    """Service autonome gérant le bus CAN avec une boucle 'Flat' ultra-optimisée."""

    def __init__(self, name: str, api, storage, dbc_path: str, provider, obd_callback=None):
        super().__init__("Can", storage)
        self.name = name
        self.api = api
        self.thread = None
        self.obd_callback = obd_callback

        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.provider = provider

        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        if not available_ports:
            available_ports = ["Aucun modem détecté", "/dev/ttyUSB0", "COM3"]

        self.register_param("modem_port", "Port", "list", available_ports[0], persistent=True, options=available_ports)
        self.register_param("baudrate", "Bauds", "list", 500000, persistent=True,
                            options=[125000, 250000, 500000, 1000000])

        self.provider.channel = self._params["modem_port"]["value"]
        self.provider.baudrate = self._params["baudrate"]["value"]

    def on_param_changed(self, key: str, value):
        if key == "modem_port":
            self.provider.channel = value
            self.provider.close()
        elif key == "baudrate":
            self.provider.baudrate = int(value)
            self.provider.close()

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(target=self._run, args=(stop_event,), name=self.name, daemon=True)
        self.thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        # ==========================================
        # 1. CRÉATION DE L'INDEX (L'idée de génie)
        # ==========================================
        # Un 'set' en Python permet une vérification instantanée (Complexité O(1))
        db = self.parser.optimized_db
        valid_ids = set(db.keys())
        valid_ids.update(range(0x7E8, 0x7F0))  # On ajoute la plage OBD2

        # Variables locales pour éviter les "self." (accélère l'exécution)
        rate_limit = 1.0 / 70.0
        last_seen = {}
        api_update = self.api.update
        processor_decode = self.processor.decode
        obd_call = self.obd_callback

        while not stop_event.is_set():
            if not self.provider.is_connected:
                try:
                    self.provider.connect()  # Plus besoin des filtres ici, on gère en Python
                    self.set_ok(f"Connecté sur {self.provider.channel}.")
                except Exception as e:
                    self.set_error(f"Échec : {str(e)}")
                    stop_event.wait(2.0)
                    continue

            try:
                # Lecture brute (C'est ici que python-can travaille)
                frame = self.provider.read_frame(timeout=0.01)

                if frame is None:
                    time.sleep(0.001)
                    continue

                msg_id = frame.arbitration_id

                # ==========================================
                # 2. FILTRAGE À LA SOURCE
                # ==========================================
                # Si l'ID n'est pas dans notre index, on passe directement à la trame suivante
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
                # 4. TRAITEMENT DIRECT (Sans Dispatcher)
                # ==========================================
                if 0x7E8 <= msg_id <= 0x7EF:
                    if obd_call:
                        obd_call(frame)
                else:
                    # On ne crée le RawFrame que pour les 70 trames par seconde qui passent le filtre !
                    raw = RawFrame(id=msg_id, data=frame.data, timestamp=frame.timestamp)
                    decoded = processor_decode(raw, db[msg_id])
                    if decoded:
                        api_update(decoded)

            except Exception as e:
                self.set_error(f"Rupture de la liaison série : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)

    def stop(self):
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        super().stop()