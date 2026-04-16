import os
import time
import threading
import platform

from src import orchestrator
from src.services.base_service import BaseService


class PowerManagementService(BaseService):
    def __init__(self, api, storage, orchestrator):
        super().__init__("PowerManager", storage)
        self.api = api
        self.off_timer = None
        self.orchestrator = orchestrator
        self.has_been_started = False

        self.register_param("shutdown_delay", "Délai avant extinction (s)", "slider", 10.0, min_val=0.0, max_val=60.0)

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="PowerManager").start()

    def _run(self, stop_event: threading.Event):
        self.set_ok("Surveillance alim : En attente du contact")

        while not stop_event.is_set():
            # --- CORRECTION : Lecture 100% sécurisée ---
            safe_data = self.api.get_display_data()
            ignition_on = safe_data.get("key_run", False)
            delay = self._params["shutdown_delay"]["value"]

            if ignition_on:
                self.has_been_started = True
                if self.off_timer is not None:
                    self.off_timer = None
                self.set_ok("Surveillance alim : Moteur allumé")

            elif self.has_been_started and not ignition_on:
                if self.off_timer is None:
                    self.off_timer = time.time()
                else:
                    time_elapsed = time.time() - self.off_timer
                    time_left = int(delay - time_elapsed)

                    if time_left > 0:
                        self.set_warning(f"Extinction dans {time_left}s...")
                    else:
                        self.set_error("Extinction en cours...")

                        current_os = platform.system()
                        if current_os == "Darwin" or current_os == "Windows":
                            print(f"[POWER] Ordre de coupure simulé (Bloqué par sécurité sur {current_os}).")
                            self.has_been_started = False
                            self.off_timer = None
                            self.set_ok("Surveillance alim : En attente du contact")
                        else:
                            print("\n[POWER] Arrêt du système demandé. Délégation à l'orchestrateur...")
                            self.orchestrator.stop_all()
                            time.sleep(1.0)
                            print("[POWER] Sauvegardes terminées. Arrêt du Raspberry Pi...")
                            os.system("sudo poweroff")
                            break

            stop_event.wait(1.0) # Optimisation CPU

    def stop(self):
        pass