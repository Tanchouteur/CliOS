"""Gabarit Service API v1. À copier dans src/services après revue."""

import threading

from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


class ExampleService(BaseService):
    def __init__(self, runtime, storage=None):
        super().__init__(
            "Example",
            storage,
            service_id="community.example",
            description="Exemple de service statiquement intégré",
        )
        self.runtime = runtime
        self._thread = None
        self.register_param("enabled_feature", "Fonction exemple", ServiceParamType.TOGGLE, True)

    def start(self, stop_event: threading.Event):
        self._thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="ExampleWorker")
        self._thread.start()
        super().start(stop_event, implemented=True)

    def _run(self, stop_event: threading.Event):
        while not stop_event.wait(1.0):
            self.set_ok("Exemple actif")
