import time
import threading
import os
import psutil
from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


class SystemMonitorService(BaseService):
    """Surveille la consommation CPU/RAM globale et par service."""

    def __init__(self, api, storage=None):
        super().__init__("Monitor", storage)
        self.api = api

        self.process = psutil.Process(os.getpid())
        self.last_thread_times = {}
        self.last_time = time.time()
        self.num_cores = psutil.cpu_count() or 1

        self.register_param("refresh_rate", "Rafraîchissement (s)", ServiceParamType.SLIDER, 1.0,
                            min_val=0.5, max_val=10.0)
        self.register_param("cpu_alert", "Alerte CPU (%)", ServiceParamType.SLIDER, 80.0,
                            min_val=20.0, max_val=100.0)
        self.register_param("ram_alert", "Alerte RAM (MB)", ServiceParamType.SLIDER, 500.0,
                            min_val=100.0, max_val=2000.0)
        self.register_param("console_debug", "Afficher Logs Console", ServiceParamType.TOGGLE, False)

    def start(self, stop_event):
        """Lance la boucle de surveillance dans un thread dédié."""
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name).start()
        super().start(stop_event, implemented=True)

    def stop(self):
        """Arrêt propre du service."""
        super().stop()
        pass

    def _run(self, stop_event):
        self.process.cpu_percent()
        self.last_time = time.monotonic()

        while not stop_event.is_set():
            sleep_time = self._params["refresh_rate"]["value"]

            stop_event.wait(sleep_time)

            if stop_event.is_set():
                break

            now = time.monotonic()
            dt = now - self.last_time
            self.last_time = now

            try:
                cpu_process_raw = self.process.cpu_percent()
                cpu_total = round(cpu_process_raw / self.num_cores, 1)

                ram_mb = round(self.process.memory_info().rss / (1024 * 1024), 1)

                # Preparation du dictionnaire de mise a jour
                updates = {
                    "app_cpu_total_pct": cpu_total,
                    "app_ram_mb": ram_mb
                }

                current_thread_times = {t.id: (t.user_time + t.system_time) for t in self.process.threads()}
                active_threads = {t.native_id: t.name for t in threading.enumerate() if hasattr(t, 'native_id')}

                for tid, cpu_time in current_thread_times.items():
                    if tid in self.last_thread_times:
                        delta_cpu = cpu_time - self.last_thread_times[tid]

                        if delta_cpu < 0:
                            delta_cpu = 0.0

                        cpu_percent = (delta_cpu / dt) * 100.0

                        if tid in active_threads:
                            thread_name = active_threads[tid]
                        else:
                            thread_name = f"Thread_Mac_{tid}"

                        safe_name = f"app_cpu_{thread_name.replace('-', '_').lower()}"
                        # Ajout des statistiques par thread dans le dictionnaire local
                        updates[safe_name] = round(cpu_percent, 1)

                self.last_thread_times = current_thread_times

                # Ecriture securisee via le Lock de l'API
                self.api.update(updates)

                cpu_limit = self._params["cpu_alert"]["value"]
                ram_limit = self._params["ram_alert"]["value"]

                if cpu_total > cpu_limit or ram_mb > ram_limit:
                    self.set_warning(f"Surcharge CPU ({cpu_total}%) ou RAM ({ram_mb} MB)")
                else:
                    self.set_ok("Ressources nominales.")

                if self._params["console_debug"]["value"]:
                    # Lecture securisee via la copie de l'API pour ne pas bloquer les autres threads
                    safe_data = self.api.get_display_data()

                    print("\n" + "=" * 45)
                    print(
                        f"APP GLOBALE : {safe_data.get('app_cpu_total_pct', 0):>5.1f} % CPU  |  {safe_data.get('app_ram_mb', 0):>6.1f} MB RAM")
                    print("-" * 45)

                    for cle, valeur in safe_data.items():
                        if cle.startswith("app_cpu_") and cle != "app_cpu_total_pct":
                            nom_propre = cle.replace("app_cpu_", "").upper()
                            print(f" - {nom_propre:<20} : {valeur:>5.1f} %")

                    print("=" * 45 + "\n")

            except Exception as e:
                self.set_error(f"Erreur de lecture CPU : {e}")