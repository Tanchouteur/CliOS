import json
import os
import time
import threading
from datetime import datetime
from src.services.base_service import BaseService


class TripSessionManager(BaseService):
    def __init__(self, api, storage, stats_service, trips_dir):
        super().__init__("SessionManager", storage)
        self.api = api
        self.stats_service = stats_service

        self.trips_dir = trips_dir
        self._dir_lock = threading.RLock()
        self._pending_summaries = []
        self._ensure_trips_dir()

        # Initialise explicitement l'état de session.
        self.api.update({"session_state": "IDLE"})

        self.trip_start_time = None
        self.trip_start_odo = 0.0
        self.trip_trace = []
        self.last_trace_time = 0.0

    # Commandes exposées à l'interface.
    def resume_trip(self):
        if self.api.get_display_data().get("session_state") == "PAUSED":
            self.api.update({"session_state": "WAITING_IGNITION"})
            self.set_ok("Trajet repris, en attente de contact...")

    def end_trip(self):
        safe_data = self.api.get_display_data()

        if safe_data.get("session_state") in ["RUNNING", "PAUSED", "WAITING_IGNITION"]:
            saved = self._save_trip_summary()

            current_odo = safe_data.get("odometer", 0.0)
            self.stats_service.reset_session(current_odo)

            self.api.update({"session_state": "IDLE"})

            self.trip_start_time = None
            self.trip_trace.clear()
            if saved:
                self.set_ok("Trajet sauvegardé")
            else:
                self.set_warning("Trajet conservé en mémoire, écriture en attente")

    # Persistance de la synthèse de trajet.
    def _save_trip_summary(self):
        stats = self.stats_service.stats
        end_time = time.time()

        end_odo = self.api.get_display_data().get("odometer", 0.0)

        duration_sec = int(end_time - self.trip_start_time) if self.trip_start_time else 0

        trip_summary = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "duration_sec": duration_sec,
                "start_odo_km": self.trip_start_odo,
                "end_odo_km": end_odo,
            },
            "stats": {
                "distance_km": stats.get("distance_km", 0.0),
                "fuel_l": stats.get("session_fuel_l", 0.0),
                "cost_eur": stats.get("session_cost", 0.0),
                "avg_rpm": stats.get("avg_rpm", 0),
                "aggressivity_pct": stats.get("aggressivity_pct", 0.0),
            },
            "trace": self.trip_trace
        }

        if self._write_summary(trip_summary):
            return True
        with self._dir_lock:
            self._pending_summaries.append(trip_summary)
        return False

    def _write_summary(self, trip_summary):
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"trip_{timestamp_str}.json"
        with self._dir_lock:
            trips_dir = self.trips_dir
        filepath = os.path.join(trips_dir, filename)
        tmp_path = filepath + ".tmp"

        try:
            os.makedirs(trips_dir, exist_ok=True)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(trip_summary, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, filepath)
            self.print_message(f"Trajet exporté : {filename}")
            return True
        except Exception as exc:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            self.set_warning(f"Écriture du trajet différée : {exc}")
            return False

    def _ensure_trips_dir(self):
        try:
            os.makedirs(self.trips_dir, exist_ok=True)
            return True
        except OSError as exc:
            self.set_warning(f"Répertoire trips inaccessible : {exc}")
            return False

    def update_trips_dir(self, new_dir: str):
        """Change la cible à chaud et retente les trajets gardés en RAM."""
        with self._dir_lock:
            self.trips_dir = new_dir
        if not self._ensure_trips_dir():
            return False

        with self._dir_lock:
            pending = list(self._pending_summaries)
            self._pending_summaries.clear()
        failed = []
        for summary in pending:
            if not self._write_summary(summary):
                failed.append(summary)
        if failed:
            with self._dir_lock:
                self._pending_summaries[0:0] = failed
            return False
        return True

    # Cycle de vie du service.
    def stop(self):
        state = self.api.get_display_data().get("session_state")
        if state in ["RUNNING", "PAUSED", "WAITING_IGNITION"]:
            self.print_message("Arrêt système détecté : Sauvegarde automatique du trajet.")
            self.end_trip()
        super().stop()

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        threading.Thread(target=self._run, args=(stop_event,), daemon=True, name=self.service_name).start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            safe_data = self.api.get_display_data()

            ignition = safe_data.get("key_run", False)
            state = safe_data.get("session_state")
            current_time = time.time()
            current_speed = safe_data.get("speed", 0.0)

            # Démarre une nouvelle session.
            if ignition and state in ["IDLE", "ENDED"]:
                self.api.update({"session_state": "RUNNING"})
                self.trip_start_time = current_time
                self.trip_start_odo = safe_data.get("odometer", 0.0)
                self.trip_trace = []
                self.set_ok("Enregistrement en cours")

            # Reprise manuelle après pause.
            elif state == "WAITING_IGNITION" and (ignition or current_speed > 3.0):
                self.api.update({"session_state": "RUNNING"})
                self.set_ok("Reprise de l'enregistrement")

            # Reprise automatique sur mouvement véhicule.
            elif state == "PAUSED" and current_speed > 3.0:
                self.api.update({"session_state": "RUNNING"})
                self.set_ok("Reprise automatique (mouvement detecte)")

            # Mise en pause automatique sans contact.
            elif not ignition and state == "RUNNING":
                self.api.update({"session_state": "PAUSED"})
                self.set_warning("En attente de décision...")

            # Enregistre la trace de session.
            elif state == "RUNNING":
                if current_time - self.last_trace_time >= 5.0:
                    point = {
                        "ts": int(current_time),
                        "spd": round(safe_data.get("speed", 0.0), 1),
                        "cons": self.stats_service.stats.get("inst_cons", 0.0)
                    }
                    if point["spd"] > 1.0:
                        self.trip_trace.append(point)

                    self.last_trace_time = current_time

            stop_event.wait(0.5)
