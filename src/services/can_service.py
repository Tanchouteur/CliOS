import os
import threading
import time
from src.parser import DbcParser
from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType
from src.signal_processor import SignalProcessor


class CanService(BaseService):
    """Service autonome gerant le bus CAN via SocketCAN."""

    def __init__(self, name: str, api, storage, dbc_path: str, provider, obd_callback=None):
        super().__init__(name, storage)
        self.name = name
        self.api = api
        self.thread = None
        self.obd_callback = obd_callback

        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.provider = provider
        self._last_frame_ts = None
        self._stale_timeout_s = 1.5
        self._decode_errors = 0
        self._last_decode_log_ts = 0.0

        # Détecte les interfaces réseau CAN disponibles.
        available_interfaces = []
        try:
            available_interfaces = [iface for iface in os.listdir('/sys/class/net') if iface.startswith('can')]
        except Exception:
            pass

        if not available_interfaces:
            available_interfaces = ["can0", "Aucun réseau CAN détecté"]

        self.register_param("can_interface", "Interface Réseau", ServiceParamType.LIST, available_interfaces[0], persistent=True,
                            options=available_interfaces)

        # Applique l'interface sélectionnée au provider.
        self.provider.channel = self._params["can_interface"]["value"]

    def on_param_changed(self, key: str, value):
        if key == "can_interface":
            self.provider.channel = value
            self.provider.close()

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(target=self._run, args=(stop_event,), name=self.service_name, daemon=True)
        self.thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        db = self.parser.optimized_db
        valid_ids = set(db.keys())
        valid_ids.update(range(0x7E8, 0x7F0))

        # Références locales pour réduire le coût d'accès en boucle.
        api_update = self.api.update
        processor_decode = self.processor.decode
        obd_call = self.obd_callback

        ui_refresh_rate = 1.0 / 60.0
        last_ui_update = time.time()
        batch_data = {}

        while not stop_event.is_set():
            if not self.provider.is_connected:
                try:
                    self.provider.connect()
                    self._last_frame_ts = None
                    self.set_warning(f"Connecté sur {self.provider.channel}, en attente de trames CAN.")
                except Exception as e:
                    self.set_error(f"Échec : {str(e)}")
                    stop_event.wait(2.0)
                    continue

            # Lecture CAN et gestion des erreurs d'interface.
            try:
                frame = self.provider.read_frame(timeout=0.01)
                now = time.time()
            except Exception as e:
                self.set_error(f"Perte de l'interface reseau : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)
                continue

            # Décodage de trame et agrégation des signaux.
            if frame is not None:
                self._last_frame_ts = now
                msg_id = frame.arbitration_id

                if msg_id in valid_ids and not getattr(self.api, 'is_starting_up', False):
                    try:
                        if 0x7E8 <= msg_id <= 0x7EF:
                            if obd_call:
                                obd_call(frame)
                        else:
                            decoded = processor_decode(frame, db[msg_id])
                            if decoded:
                                batch_data.update(decoded)
                    except Exception as e:
                        self._decode_errors += 1
                        if now - self._last_decode_log_ts >= 2.0:
                            self._last_decode_log_ts = now
                            self.logger.warning(
                                f"Erreurs de décodage CAN: {self._decode_errors} (dernier ID 0x{msg_id:03X}, {e})",
                                extra={"error_code": "CAN_DECODE_ERROR"}
                            )

            # Le service est nominal uniquement si des trames récentes sont reçues.
            if self._last_frame_ts is None:
                self.set_warning("Connecté mais aucune trame CAN reçue.")
            else:
                frame_age = now - self._last_frame_ts
                if frame_age > self._stale_timeout_s:
                    self.set_warning(f"Aucune trame CAN depuis {frame_age:.1f}s.")
                else:
                    self.set_ok(f"Trames CAN reçues sur {self.provider.channel}.")

            # Publie les données agrégées à cadence fixe.
            if now - last_ui_update >= ui_refresh_rate:
                if batch_data:
                    batch_data["can_decode_errors"] = self._decode_errors
                    api_update(batch_data)
                    batch_data.clear()
                last_ui_update = now

    def stop(self):
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        super().stop()