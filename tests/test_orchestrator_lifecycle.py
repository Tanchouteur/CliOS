import threading
import unittest

from src.orchestrator import SystemOrchestrator
from src.services.base_service import BaseService


class CountingService(BaseService):
    def __init__(self):
        super().__init__("Counting")
        self.starts = 0
        self._thread = None

    def start(self, stop_event):
        self.starts += 1
        self._thread = threading.Thread(target=stop_event.wait, daemon=True)
        self._thread.start()
        super().start(stop_event, implemented=True)


class OrchestratorLifecycleTest(unittest.TestCase):
    def test_start_all_is_idempotent_and_stop_joins_worker(self):
        orchestrator = SystemOrchestrator()
        service = CountingService()
        orchestrator.add_service(service)

        orchestrator.start_all()
        first_worker = service._thread
        orchestrator.start_all()

        self.assertEqual(service.starts, 1)
        self.assertIs(service._thread, first_worker)
        orchestrator.stop_all()
        self.assertFalse(first_worker.is_alive())

    def test_hot_toggle_restarts_once(self):
        orchestrator = SystemOrchestrator()
        service = CountingService()
        orchestrator.add_service(service)
        orchestrator.start_all()
        orchestrator.stop_service("Counting")
        orchestrator.start_service("Counting")
        orchestrator.start_service("Counting")

        self.assertEqual(service.starts, 2)
        orchestrator.stop_all()

