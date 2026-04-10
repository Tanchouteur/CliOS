import time
import threading
import os
import psutil
from src.services.base_service import BaseService


class SystemMonitorService(BaseService):
    """Surveille la consommation CPU/RAM globale et par service."""

    def __init__(self, api):
        super().__init__("Monitor")
        self.api = api

        # On cible le processus actuel (ton application entière)
        self.process = psutil.Process(os.getpid())
        self.last_thread_times = {}
        self.last_time = time.time()

    def start(self, stop_event):
        """Lance la boucle de surveillance dans un thread dédié."""
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="SystemMonitorWorker").start()

    def stop(self):
        """Arrêt propre du service."""
        pass

    def _run(self, stop_event):
        self.process.cpu_percent()

        self.last_time = time.monotonic()

        while not stop_event.is_set():
            time.sleep(1.0)
            now = time.monotonic()
            dt = now - self.last_time
            self.last_time = now

            try:
                self.api._data["app_cpu_total_pct"] = round(self.process.cpu_percent(), 1)
                self.api._data["app_ram_mb"] = round(self.process.memory_info().rss / (1024 * 1024), 1)

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
                        self.api._data[safe_name] = round(cpu_percent, 1)

                self.last_thread_times = current_thread_times

                debug = False
                if debug :
                    print("\n" + "=" * 45)
                    print(
                        f"🖥️  APP GLOBALE : {self.api._data['app_cpu_total_pct']:>5.1f} % CPU  |  {self.api._data['app_ram_mb']:>6.1f} MB RAM")
                    print("-" * 45)

                    for cle, valeur in self.api._data.items():
                        if cle.startswith("app_cpu_") and cle != "app_cpu_total_pct":
                            nom_propre = cle.replace("app_cpu_", "").upper()
                            print(f" 🔹 {nom_propre:<20} : {valeur:>5.1f} %")

                    print("=" * 45 + "\n")

            except Exception as e:
                self.set_error(f"Erreur de lecture CPU : {e}")