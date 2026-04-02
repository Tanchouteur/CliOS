import os
import threading
from src.driver import Slcan
from src.mock_driver import MockProvider
from src.parser import DbcParser
from src.signal_processor import SignalProcessor
from src.dispatcher import CanDispatcher

class CanService:
    """Service autonome gérant un bus CAN spécifique (lecture, décodage, mise à jour API)."""

    def __init__(self, name: str, api, dbc_path: str, port: str, baudrate: int, is_mock: bool, status_key: str):
        self.name = name
        self.api = api
        self.status_key = status_key
        self.thread = None

        # Instanciation de l'architecture Core propre à CE bus CAN
        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.dispatcher = CanDispatcher(self.parser, self.processor, self.api)

        # Choix du pilote matériel
        if is_mock:
            self.provider = MockProvider(dbc_path)
        else:
            self.provider = Slcan(channel=port, baudrate=baudrate)

        # On initialise la variable d'état dans l'API
        self.api._data[self.status_key] = False

    def start(self, stop_event: threading.Event):
        """Lance la boucle de lecture dans un thread dédié."""
        self.thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name=f"Thread-{self.name}",
            daemon=True
        )
        self.thread.start()

    def _run(self, stop_event: threading.Event):
        """Boucle principale de la machine à états (Anciennement can_listener_loop)."""
        while not stop_event.is_set():
            if not self.provider.is_connected:
                self.api._data[self.status_key] = False
                success = self.provider.connect()

                if not success:
                    stop_event.wait(2.0)
                    continue
                else:
                    self.api._data[self.status_key] = True

            try:
                frame = self.provider.read_frame(timeout=0.2)
                if frame:
                    if getattr(self.api, 'is_starting_up', False):
                        continue
                    self.dispatcher.dispatch(frame)
            except Exception:
                print(f"[ATTENTION] {self.name} : Rupture de la liaison série.")
                self.api._data[self.status_key] = False
                self.provider.close()
                stop_event.wait(1.0)

    def stop(self):
        """Ferme la liaison matérielle et attend la fin du thread."""
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)