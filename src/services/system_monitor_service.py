import time
import threading
import os
import psutil
from src.services.base_service import BaseService


class SystemMonitorService(BaseService):
    """Surveille la consommation CPU/RAM globale et par service."""

    def __init__(self, api, storage=None):  # NOUVEAU : On ajoute le storage
        super().__init__("Monitor", storage)
        self.api = api

        # On cible le processus actuel (ton application entière)
        self.process = psutil.Process(os.getpid())
        self.last_thread_times = {}
        self.last_time = time.time()

        # --- DÉCLARATION DES PARAMÈTRES DYNAMIQUES ---
        self.register_param("refresh_rate", "Rafraîchissement (s)", "slider", 1.0, min_val=0.5, max_val=10.0)
        self.register_param("cpu_alert", "Alerte CPU (%)", "slider", 80.0, min_val=20.0, max_val=100.0)
        self.register_param("ram_alert", "Alerte RAM (MB)", "slider", 500.0, min_val=100.0, max_val=2000.0)
        self.register_param("console_debug", "Afficher Logs Console", "toggle", False)

    def start(self, stop_event):
        """Lance la boucle de surveillance dans un thread dédié."""
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="SystemMonitorWorker").start()
        super().start(stop_event, implemented=True)

    def stop(self):
        """Arrêt propre du service."""
        super().stop()
        pass

    def _run(self, stop_event):
        self.process.cpu_percent()
        self.last_time = time.monotonic()

        while not stop_event.is_set():
            # 1. Lecture du délai demandé par l'utilisateur
            sleep_time = self._params["refresh_rate"]["value"]

            # Utilise wait() au lieu de sleep() permet de quitter le thread instantanément
            # quand l'orchestrateur demande l'arrêt global !
            stop_event.wait(sleep_time)

            if stop_event.is_set():
                break

            now = time.monotonic()
            dt = now - self.last_time
            self.last_time = now

            try:
                # --- CALCUL DES RESSOURCES ---
                cpu_total = round(self.process.cpu_percent(), 1)
                ram_mb = round(self.process.memory_info().rss / (1024 * 1024), 1)

                self.api._data["app_cpu_total_pct"] = cpu_total
                self.api._data["app_ram_mb"] = ram_mb

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

                # --- 2. GESTION DES ALERTES (STATUS) ---
                cpu_limit = self._params["cpu_alert"]["value"]
                ram_limit = self._params["ram_alert"]["value"]

                if cpu_total > cpu_limit or ram_mb > ram_limit:
                    self.set_warning(f"Surcharge CPU ({cpu_total}%) ou RAM ({ram_mb} MB)")
                else:
                    self.set_ok("Ressources nominales.")

                # --- 3. AFFICHAGE DEBUG DYNAMIQUE ---
                if self._params["console_debug"]["value"]:
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