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
            ignition_on = self.api._data.get("key_run", False)
            delay = self._params["shutdown_delay"]["value"]

            # CAS 1 : Le contact est mis
            if ignition_on:
                self.has_been_started = True  # On mémorise que le système a été utilisé

                if self.off_timer is not None:
                    self.off_timer = None  # Annulation du chrono si on a remis le contact à temps

                self.set_ok("Surveillance alim : Moteur allumé")

            # CAS 2 : Le contact vient d'être coupé (ET il avait été mis avant)
            elif self.has_been_started and not ignition_on:
                if self.off_timer is None:
                    self.off_timer = time.time()  # Démarrage du chrono
                else:
                    time_elapsed = time.time() - self.off_timer
                    time_left = int(delay - time_elapsed)

                    if time_left > 0:
                        self.set_warning(f"Extinction dans {time_left}s...")
                    else:
                        self.set_error("Extinction en cours...")

                        # --- SECURITÉ POUR LE DÉVELOPPEMENT ---
                        current_os = platform.system()
                        if current_os == "Darwin" or current_os == "Windows":
                            print(f"[POWER] Ordre de coupure simulé (Bloqué par sécurité sur {current_os}).")
                            self.has_been_started = False
                            self.off_timer = None
                            self.set_ok("Surveillance alim : En attente du contact")

                        else:
                            # C'est un Raspberry Pi (Linux), on coupe proprement !
                            print("\n[POWER] Arrêt du système demandé. Délégation à l'orchestrateur...")

                            # 1. L'orchestrateur appelle le stop() de TOUS les services proprement
                            self.orchestrator.stop_all()

                            # 2. On laisse 1 seconde au disque dur/carte SD pour finir d'écrire les JSON
                            time.sleep(1.0)

                            # 3. Coupure physique
                            print("[POWER] Sauvegardes terminées. Arrêt du Raspberry Pi...")
                            os.system("sudo poweroff")
                            break

            else:
                pass

            time.sleep(1.0)

    def stop(self):
        """Surcharge : Le PowerManager ignore l'ordre d'arrêt car c'est lui qui le donne."""
        pass