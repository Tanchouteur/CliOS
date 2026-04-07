import threading
from src.parser import DbcParser
from src.services.base_service import BaseService
from src.signal_processor import SignalProcessor
from src.dispatcher import CanDispatcher


class CanService(BaseService):
    """Service autonome gérant un bus CAN spécifique (lecture, décodage, mise à jour API)."""

    def __init__(self, name: str, api, dbc_path: str, provider, obd_callback=None):
        super().__init__(service_name="CAN")
        self.name = name
        self.api = api
        self.thread = None
        self.obd_callback = obd_callback

        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.dispatcher = CanDispatcher(self.parser, self.processor, self.api)
        self.provider = provider

    def start(self, stop_event: threading.Event):
        self.thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            name=f"Thread-{self.name}",
            daemon=True
        )
        self.thread.start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            if not self.provider.is_connected:
                self.set_error("Déconnecté. Tentative de connexion...")
                success = self.provider.connect()

                if not success:
                    stop_event.wait(2.0)
                    continue
                else:
                    self.set_ok(f"Connecté avec succès sur {self.name}.")

            try:
                frame = self.provider.read_frame(timeout=0.2)
                if frame:
                    if getattr(self.api, 'is_starting_up', False):
                        continue

                    if 0x7E8 <= frame.arbitration_id <= 0x7EF and self.obd_callback:
                        self.obd_callback(frame)
                    else:
                        self.dispatcher.dispatch(frame)

            except Exception as e:
                print(f"[ATTENTION] {self.name} : Rupture de la liaison série.")
                self.set_error(f"Rupture de la liaison série : {str(e)}")
                self.provider.close()
                stop_event.wait(1.0)

    def stop(self):
        self.provider.close()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)