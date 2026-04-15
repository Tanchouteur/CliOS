import threading
import time

import serial.tools.list_ports
from src.parser import DbcParser
from src.services.base_service import BaseService
from src.signal_processor import SignalProcessor
from src.dispatcher import CanDispatcher


class CanService(BaseService):
    """Service autonome gérant un bus CAN spécifique (lecture, décodage, mise à jour API)."""

    def __init__(self, name: str, api, storage, dbc_path: str, provider, obd_callback=None):
        super().__init__("Can", storage)
        self.name = name
        self.api = api
        self.thread = None
        self.obd_callback = obd_callback

        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.dispatcher = CanDispatcher(self.parser, self.processor, self.api)
        self.provider = provider

        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        if not available_ports:
            available_ports = ["Aucun modem détecté", "/dev/ttyUSB0", "COM3"]

        self.register_param("modem_port", "Port du Modem", "list", available_ports[0], persistent=True,
                            options=available_ports)
        self.register_param("baudrate", "Vitesse (Bauds)", "list", 500000, persistent=True,
                            options=[125000, 250000, 500000, 1000000])

        self.provider.channel = self._params["modem_port"]["value"]
        self.provider.baudrate = self._params["baudrate"]["value"]

    def _generate_filters(self):
        """Compile les ID du parser et OBD2 en filtres matériels."""
        filters = []
        try:
            # Ton DbcParser a déjà converti les clés hexadécimales en entiers dans 'optimized_db'
            if hasattr(self.parser, 'optimized_db'):
                for can_id_int in self.parser.optimized_db.keys():
                    filters.append({"can_id": can_id_int, "can_mask": 0x7FF, "extended": False})

            # On ajoute la plage OBD2 (0x7E8 à 0x7EF)
            filters.append({"can_id": 0x7E8, "can_mask": 0x7F8, "extended": False})
        except Exception as e:
            self.print_message(f"[Attention] Erreur génération filtres matériels : {e}")

        return filters if filters else None

    def on_param_changed(self, key: str, value):
        if key == "modem_port":
            self.provider.channel = value
            self.provider.close()

        elif key == "baudrate":
            self.provider.baudrate = int(value)
            self.provider.close()

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name=self.name,
            daemon=True
        )
        self.thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        # 1. On génère la liste des filtres
        hardware_filters = self._generate_filters()

        # 2. Configuration du "métronome" 70Hz (1 trame toutes les ~14.2 ms)
        loop_interval = 1.0 / 70.0

        while not stop_event.is_set():
            loop_start = time.time()

            if not self.provider.is_connected:
                try:
                    # On injecte les filtres au module DSD Tech !
                    self.provider.connect(can_filters=hardware_filters)
                    self.set_ok(f"Connecté sur {self.provider.channel} (Filtres activés).")
                except Exception as e:
                    self.set_error(f"Échec de connexion : {str(e)}")
                    stop_event.wait(2.0)
                    continue

            try:
                # Timeout très court (10ms) pour ne pas bloquer le métronome
                frame = self.provider.read_frame(timeout=0.01)

                if frame:
                    if getattr(self.api, 'is_starting_up', False):
                        pass
                    elif 0x7E8 <= frame.arbitration_id <= 0x7EF and self.obd_callback:
                        self.obd_callback(frame)
                    else:
                        self.dispatcher.dispatch(frame)

            except Exception as e:
                self.set_error(f"Rupture de la liaison série : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)

            elapsed = time.time() - loop_start
            time_to_sleep = loop_interval - elapsed

            if time_to_sleep > 0:
                time.sleep(time_to_sleep)

    def stop(self):
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        super().stop()