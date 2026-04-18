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
        os.makedirs(self.trips_dir, exist_ok=True)

        # --- CORRECTION : Écriture sécurisée ---
        self.api.update({"session_state": "IDLE"})

        self.trip_start_time = None
        self.trip_start_odo = 0.0
        self.trip_trace = []
        self.last_trace_time = 0.0

    # ==========================================
    # COMMANDES UI
    # ==========================================
    def resume_trip(self):
        # --- CORRECTION : Lecture sécurisée ---
        if self.api.get_display_data().get("session_state") == "PAUSED":
            self.api.update({"session_state": "WAITING_IGNITION"})
            self.set_ok("Trajet repris, en attente de contact...")

    def end_trip(self):
        # --- CORRECTION : Lecture sécurisée ---
        safe_data = self.api.get_display_data()

        if safe_data.get("session_state") in ["RUNNING", "PAUSED", "WAITING_IGNITION"]:
            self._save_trip_summary()

            current_odo = safe_data.get("odometer", 0.0)
            self.stats_service.reset_session(current_odo)

            self.api.update({"session_state": "IDLE"})

            self.trip_start_time = None
            self.trip_trace.clear()
            self.set_ok("Trajet sauvegardé")

    # ==========================================
    # SAUVEGARDE
    # ==========================================
    def _save_trip_summary(self):
        stats = self.stats_service.stats
        end_time = time.time()

        # --- CORRECTION : Lecture sécurisée ---
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

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trip_{timestamp_str}.json"
        filepath = os.path.join(self.trips_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(trip_summary, f, indent=4)
            self.print_message(f"Trajet exporté : {filename}")
        except Exception as e:
            self.set_error(f"Erreur d'écriture : {e}")

    # ==========================================
    # CYCLE DE VIE
    # ==========================================
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

            # 1. NOUVEAU TRAJET (Démarrage à froid ou après avoir validé le trajet précédent)
            if ignition and state in ["IDLE", "ENDED"]:
                self.api.update({"session_state": "RUNNING"})
                self.trip_start_time = current_time
                self.trip_start_odo = safe_data.get("odometer", 0.0)
                self.trip_trace = []
                self.set_ok("Enregistrement en cours")

            # 1b. REPRISE MANUELLE (En attente suite a une action sur l'interface)
            elif state == "WAITING_IGNITION" and (ignition or current_speed > 3.0):
                self.api.update({"session_state": "RUNNING"})
                self.set_ok("Reprise de l'enregistrement")

            # 1c. REPRISE AUTOMATIQUE (Declenchement exclusif par le mouvement du vehicule)
            elif state == "PAUSED" and current_speed > 3.0:
                self.api.update({"session_state": "RUNNING"})
                self.set_ok("Reprise automatique (mouvement detecte)")

            # 2. MISE EN PAUSE AUTOMATIQUE
            elif not ignition and state == "RUNNING":
                self.api.update({"session_state": "PAUSED"})
                self.set_warning("En attente de décision...")

            # 3. ENREGISTREMENT DE LA TRACE
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