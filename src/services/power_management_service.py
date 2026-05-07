import os
import time
import threading
import platform

from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


class PowerManagementService(BaseService):
    def __init__(self, api, storage, orchestrator):
        super().__init__("PowerManager", storage)
        self.api = api
        self.off_timer = None
        self.orchestrator = orchestrator
        self.has_been_started = False

        self.register_param("shutdown_delay", "Délai avant extinction (s)", ServiceParamType.SLIDER,
                            10.0, min_val=0.0, max_val=60.0)

        # Parametre definissant le declencheur d'extinction
        self.register_param("wait_key_removal", "Attendre retrait clé", "toggle", False)

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name).start()

    def _run(self, stop_event: threading.Event):
        self.set_ok("Surveillance alim : En attente du contact")

        while not stop_event.is_set():
            system_health = self.orchestrator.get_system_health()
            can_status = system_health.get("CAN_Moteur", {}).get("status")

            if can_status != "OK":
                self.set_warning(f"Suspendu : Attente du réseau CAN (Statut: {can_status})")
                self.off_timer = None
                stop_event.wait(1.0)
                continue

            safe_data = self.api.get_display_data()
            delay = self._params["shutdown_delay"]["value"]
            wait_for_key = self._params["wait_key_removal"]["value"]

            # Extraction des donnees CAN pertinentes
            is_engine_running = safe_data.get("rpm", 0) > 400
            is_key_acc = bool(safe_data.get("key_acc", False))

            # Definition de l'etat d'activite selon le mode choisi
            if wait_for_key:
                vehicle_active = is_engine_running or is_key_acc
            else:
                vehicle_active = is_engine_running

            if vehicle_active:
                self.has_been_started = True
                if self.off_timer is not None:
                    self.off_timer = None
                self.set_ok("Surveillance alim : Véhicule actif")

            elif self.has_been_started and not vehicle_active:
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
                            self.print_message(f"Extinction simulée (désactivée sur {current_os}).")
                            self.has_been_started = False
                            self.off_timer = None
                            self.set_ok("Surveillance alim : En attente du contact")
                        else:
                            self.print_message("Extinction système demandée. Arrêt des services en cours.")
                            self.orchestrator.stop_all()
                            time.sleep(1.0)
                            self.print_message("Sauvegardes terminées. Arrêt de la machine.")
                            os.system("sudo poweroff")
                            break

            stop_event.wait(1.0)

    def stop(self):
        pass