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

        # --- 1. DÉTECTION DYNAMIQUE DES PORTS ---
        # On scanne les ports COM/USB disponibles sur la machine
        available_ports = [port.device for port in serial.tools.list_ports.comports()]
        if not available_ports:
            # Fallback visuel si rien n'est branché
            available_ports = ["Aucun modem détecté", "/dev/ttyUSB0", "COM3"]

            # --- 2. DÉCLARATION DES PARAMÈTRES ---
        self.register_param("modem_port", "Port du Modem", "list", available_ports[0], persistent=True,
                            options=available_ports)
        self.register_param("baudrate", "Vitesse (Bauds)", "list", 500000, persistent=True,
                            options=[125000, 250000, 500000, 1000000])

        # On force le provider à utiliser les valeurs (soit par défaut, soit celles du save.json)
        self.provider.channel = self._params["modem_port"]["value"]
        self.provider.baudrate = self._params["baudrate"]["value"]

    # --- 3. RÉACTION AU CHANGEMENT DEPUIS LE FRONTEND ---
    def on_param_changed(self, key: str, value):
        if key == "modem_port":
            self.print_message(f"Changement de port demandé : {value}")
            self.provider.channel = value
            self.provider.close()

        elif key == "baudrate":
            self.print_message(f"Changement de vitesse demandé : {value}")
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
        while not stop_event.is_set():
            if not self.provider.is_connected:
                try:
                    self.provider.connect()
                    self.set_ok(f"Connecté avec succès sur {self.provider.channel}.")
                except Exception as e:
                    self.set_error(f"Échec de connexion : {str(e)}")
                    stop_event.wait(2.0)  # On évite de spammer les tentatives si ça foire
                    continue  # On passe au tour de boucle suivant

            try:
                frame = self.provider.read_frame(timeout=0.1)

                if frame is None:
                    time.sleep(0.005)
                    continue

                if frame:
                    if getattr(self.api, 'is_starting_up', False):
                        continue

                    if 0x7E8 <= frame.arbitration_id <= 0x7EF and self.obd_callback:
                        self.obd_callback(frame)
                    else:
                        self.dispatcher.dispatch(frame)

            except Exception as e:
                self.set_error(f"Rupture de la liaison série : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)

    def stop(self):
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        super().stop()