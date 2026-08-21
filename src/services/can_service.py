import os
import glob
import threading
import time
from src.can_activity import CanActivitySource
from src.parser import DbcParser
from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType
from src.signal_processor import SignalProcessor
from src.signal_catalog import definition_for
from src.state_store import StatePatch


class CanService(BaseService):
    """Service autonome gerant le bus CAN via SocketCAN."""

    def __init__(self, name: str, runtime, storage, dbc_path: str, provider, obd_callback=None,
                 activity_source: CanActivitySource | None = None):
        super().__init__(name, storage)
        self.name = name
        self.runtime = runtime
        self.thread = None
        self.obd_callback = obd_callback

        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.provider = provider
        self.activity_source = activity_source or CanActivitySource()
        if hasattr(self.provider, "register_obd_callback") and self.obd_callback:
            self.provider.register_obd_callback(self.obd_callback)
        self._last_frame_ts = None
        self._last_decoded_frame_ts = None
        self._stale_timeout_s = 1.5
        self._decode_errors = 0
        self._last_decode_log_ts = 0.0

        # Détecte les interfaces réseau CAN disponibles.
        available_interfaces = []
        try:
            available_interfaces = [iface for iface in os.listdir('/sys/class/net') if iface.startswith('can')]
        except Exception:
            # macOS: ports série pour adaptateurs SLCAN
            serial_ports = glob.glob("/dev/cu.*") + glob.glob("/dev/tty.*")
            available_interfaces = sorted(set(serial_ports))

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
        publish_many = self.runtime.publish_many
        processor_decode = self.processor.decode
        obd_call = self.obd_callback

        last_error_publish = 0.0

        while not stop_event.is_set():
            if not self.provider.is_connected:
                self.activity_source.set_provider_connected(False)
                try:
                    self.provider.connect()
                    self.activity_source.set_provider_connected(bool(self.provider.is_connected))
                    self._last_frame_ts = None
                    self.set_warning(f"Connecté sur {self.provider.channel}, en attente de trames CAN.")
                except Exception as e:
                    self.set_error(f"Échec : {str(e)}")
                    stop_event.wait(2.0)
                    continue
            else:
                self.activity_source.set_provider_connected(True)

            # Lecture CAN et gestion des erreurs d'interface.
            try:
                frame = self.provider.read_frame(timeout=0.01)
                now = time.time()
            except Exception as e:
                self.activity_source.set_provider_connected(False)
                self.set_error(f"Perte de l'interface reseau : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)
                continue

            # Décodage de trame et agrégation des signaux.
            if frame is not None:
                self.activity_source.record_frame()
                self._last_frame_ts = now
                msg_id = frame.arbitration_id

                if msg_id in valid_ids:
                    try:
                        if 0x7E8 <= msg_id <= 0x7EF:
                            if obd_call:
                                obd_call(frame)
                        else:
                            decoded = processor_decode(frame, db[msg_id])
                            if decoded:
                                grouped = {}
                                units = {}
                                ttls = {}
                                for signal_name, value in decoded.items():
                                    definition = definition_for(signal_name)
                                    grouped.setdefault(definition.domain, {})[signal_name] = value
                                    if definition.unit:
                                        units.setdefault(definition.domain, {})[signal_name] = definition.unit
                                    ttls[definition.domain] = definition.ttl_s
                                publish_many(
                                    StatePatch(
                                        domain=domain,
                                        values=values,
                                        source=f"can:0x{msg_id:03X}",
                                        ttl_s=ttls[domain],
                                        units=units.get(domain, {}),
                                    )
                                    for domain, values in grouped.items()
                                )
                                self._last_decoded_frame_ts = now
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
                decoded_age = None if self._last_decoded_frame_ts is None else now - self._last_decoded_frame_ts
                if frame_age > self._stale_timeout_s:
                    self.set_warning(f"Aucune trame CAN depuis {frame_age:.1f}s.")
                elif decoded_age is None or decoded_age > self._stale_timeout_s:
                    self.set_warning("Trames reçues, mais aucun signal véhicule récent n'est décodé.")
                else:
                    self.set_ok(f"Trames CAN reçues sur {self.provider.channel}.")

            if now - last_error_publish >= 1.0:
                self.runtime.publish(
                    "system", {"can_decode_errors": self._decode_errors}, source="can-service", ttl_s=2.5
                )
                last_error_publish = now

    def stop(self):
        if self._stop_event is not None:
            self._stop_event.set()
        self.provider.close()
        self.activity_source.set_provider_connected(False)
        super().stop()
