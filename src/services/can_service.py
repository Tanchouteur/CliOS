import os
import threading
import time
from src.parser import DbcParser
from src.services.base_service import BaseService
from src.signal_processor import SignalProcessor


class CanService(BaseService):
    """Service autonome gérant le bus CAN via SocketCAN (0% CPU overhead)."""

    def __init__(self, name: str, api, storage, dbc_path: str, provider, obd_callback=None, diag=None):
        super().__init__("Can", storage)
        self.name = name
        self.api = api
        self.thread = None
        self.obd_callback = obd_callback
        self.diag = diag or {}

        self._diag_disable_api_update = bool(self.diag.get("disable_can_api_update", False))
        self._diag_include_keys = set(self.diag.get("include_keys", []))
        self._diag_log_type_changes = bool(self.diag.get("log_type_changes", False))
        self._diag_enabled = bool(self.diag.get("enabled", False))
        self._diag_seen_types = {}
        self._diag_last_print = time.time()
        self._diag_frames = 0
        self._diag_batches = 0

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
        db = self.parser.optimized_db
        valid_ids = set(db.keys())
        valid_ids.update(range(0x7E8, 0x7F0))

        # Variables locales d'optimisation
        api_update = self.api.update
        processor_decode = self.processor.decode
        obd_call = self.obd_callback

        ui_refresh_rate = 1.0 / 60.0  # ~0.016 secondes
        last_ui_update = time.time()
        batch_data = {}  # Le "carton" de livraison

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
                # 1. Lecture rapide du noyau Linux
                frame = self.provider.read_frame(timeout=0.01)
                now = time.time()

                if frame is not None:
                    msg_id = frame.arbitration_id

                    # 2. Filtrage et Décodage
                    if msg_id in valid_ids and not getattr(self.api, 'is_starting_up', False):
                        if 0x7E8 <= msg_id <= 0x7EF:
                            if obd_call:
                                obd_call(frame)
                        else:
                            # On décode directement avec le bytearray (Optimisation du Processor)
                            decoded = processor_decode(frame.data, db[msg_id])
                            if decoded:
                                self._diag_frames += 1

                                if self._diag_include_keys:
                                    decoded = {k: v for k, v in decoded.items() if k in self._diag_include_keys}

                                # Normalisation défensive: seulement des types Python simples dans l'API.
                                sanitized = {k: self._sanitize_value(v) for k, v in decoded.items()}

                                if self._diag_log_type_changes:
                                    self._track_type_changes(sanitized)

                                batch_data.update(sanitized)

                # 3. Livraison synchronisée (60 Hz)
                if now - last_ui_update >= ui_refresh_rate:
                    if batch_data:
                        self._diag_batches += 1
                        if not self._diag_disable_api_update:
                            api_update(batch_data)
                        batch_data.clear()

                    if self._diag_enabled and (now - self._diag_last_print) >= 2.0:
                        print(f"[DIAG][CAN] frames={self._diag_frames} batches={self._diag_batches} "
                              f"api_update={'OFF' if self._diag_disable_api_update else 'ON'}")
                        self._diag_last_print = now
                    last_ui_update = now

            except Exception as e:
                self.set_error(f"Perte de l'interface réseau : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)

    def _sanitize_value(self, value):
        if isinstance(value, bool):
            return 1 if value else 0
        if value is None or isinstance(value, (int, float, str)):
            return value
        if hasattr(value, "item"):
            try:
                return self._sanitize_value(value.item())
            except Exception:
                pass
        if isinstance(value, (bytes, bytearray)):
            return list(value)
        return str(value)

    def _track_type_changes(self, decoded: dict):
        for key, value in decoded.items():
            t_name = type(value).__name__
            previous = self._diag_seen_types.get(key)
            if previous is None:
                self._diag_seen_types[key] = t_name
                continue
            if previous != t_name:
                print(f"[DIAG][CAN][TYPE] '{key}' : {previous} -> {t_name}")
                self._diag_seen_types[key] = t_name

    def stop(self):
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        super().stop()