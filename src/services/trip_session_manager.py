import json
import os
import threading
import time
from datetime import datetime

from src.services.base_service import BaseService


class TripSessionManager(BaseService):
    VALID_STATES = {
        "IDLE", "RUNNING", "PAUSED", "WAITING_IGNITION", "SUSPENDED",
        "RECOVERY_PENDING", "ENDING", "ENDED",
    }
    CHECKPOINT_SCHEMA_VERSION = 1
    # Deliberately not suffixed .json: ExportService scans JSON files and must
    # never copy or delete an active checkpoint.
    CHECKPOINT_FILENAME = ".active_trip.checkpoint"
    CHECKPOINT_INTERVAL_S = 5.0
    RECOVERY_TIMEOUT_S = 30.0

    def __init__(self, runtime, storage, stats_service, trips_dir):
        super().__init__("SessionManager", storage)
        self.runtime = runtime
        self.stats_service = stats_service
        self.trips_dir = trips_dir
        self._dir_lock = threading.RLock()
        self._session_lock = threading.RLock()
        self._pending_summaries = []
        self._recovery_checkpoint = None
        self._recovery_deadline = None
        self._ensure_trips_dir()

        self.trip_start_time = None
        self.trip_start_odo = 0.0
        self.trip_trace = []
        self.last_trace_time = 0.0
        self.last_checkpoint_time = 0.0

        self._recovery_checkpoint = self._load_checkpoint()
        if self._recovery_checkpoint is not None:
            self._publish_session("RECOVERY_PENDING", self.RECOVERY_TIMEOUT_S)
        else:
            self._publish_session("IDLE")

    def resume_trip(self):
        with self._session_lock:
            snapshot = self.runtime.snapshot()
            state = snapshot.domain("session").get("state")
            if state == "RECOVERY_PENDING" and self._recovery_checkpoint is not None:
                checkpoint = self._recovery_checkpoint
                try:
                    self.stats_service.restore_session_checkpoint(checkpoint["stats_state"])
                    self.trip_start_time = float(checkpoint["metadata"]["started_at"])
                    self.trip_start_odo = float(checkpoint["metadata"]["start_odo_km"])
                    self.trip_trace = list(checkpoint.get("trace", []))
                except (KeyError, RuntimeError, TypeError, ValueError) as exc:
                    self.set_error(f"Reprise du trajet impossible : {exc}")
                    return False

                self._recovery_deadline = None
                ignition = bool(snapshot.domain("powertrain").get("key_run", False))
                self._publish_session("RUNNING" if ignition else "WAITING_IGNITION")
                self.last_checkpoint_time = time.monotonic()
                self.set_ok("Trajet précédent repris")
                return True

            if state == "PAUSED":
                self._publish_session("WAITING_IGNITION")
                self.set_ok("Trajet repris, en attente de contact...")
                return True
        return False

    def start_new_trip(self):
        """Archive the recoverable trip before starting a clean session."""
        with self._session_lock:
            state = self.runtime.snapshot().domain("session").get("state")
            if state != "RECOVERY_PENDING" or self._recovery_checkpoint is None:
                return False
            if not self._archive_recovery_checkpoint():
                self._publish_session("RECOVERY_PENDING", 0)
                self.set_warning("Impossible d'archiver l'ancien trajet; nouvelle tentative en cours")
                return False

            self._recovery_deadline = None
            self._recovery_checkpoint = None
            self._publish_session("IDLE")
            snapshot = self.runtime.snapshot()
            if bool(snapshot.domain("powertrain").get("key_run", False)):
                self._begin_new_session(snapshot)
            return True

    def end_trip(self):
        with self._session_lock:
            snapshot = self.runtime.snapshot()
            state = snapshot.domain("session").get("state")
            if state not in ["RUNNING", "PAUSED", "WAITING_IGNITION", "SUSPENDED"]:
                return False
            self._publish_session("ENDING")
            current_odo = snapshot.domain("motion").get("odometer", 0.0)
            final_stats = self.stats_service.finish_session(current_odo)
            saved = self._save_trip_summary(final_stats, current_odo)
            self._publish_session("IDLE")
            self.trip_start_time = None
            self.trip_trace.clear()
            if saved:
                self._remove_checkpoint()
                self._recovery_checkpoint = None
                self.set_ok("Trajet sauvegardé")
            else:
                self.set_warning("Trajet conservé en mémoire, écriture en attente")
            return saved

    def _publish_session(self, state, recovery_seconds=None):
        summary = {}
        if state == "RECOVERY_PENDING" and self._recovery_checkpoint is not None:
            checkpoint = self._recovery_checkpoint
            stats = checkpoint.get("stats_state", {}).get("stats", {})
            metadata = checkpoint.get("metadata", {})
            summary = {
                "date": metadata.get("suspended_at_iso", ""),
                "distance_km": stats.get("distance_km", 0.0),
                "cost_eur": stats.get("session_cost", 0.0),
            }
        self.runtime.publish(
            "session",
            {
                "state": state,
                "resume_available": state == "RECOVERY_PENDING",
                "resume_seconds": recovery_seconds,
                "resume_trip": summary,
            },
            source="session-manager",
        )

    def _begin_new_session(self, snapshot):
        current_odo = snapshot.domain("motion").get("odometer", 0.0)
        self.stats_service.begin_session(current_odo)
        self.trip_start_time = time.time()
        self.trip_start_odo = current_odo
        self.trip_trace = []
        self.last_trace_time = 0.0
        self._publish_session("RUNNING")
        self._write_checkpoint(current_odo)
        self.last_checkpoint_time = time.monotonic()
        self.set_ok("Enregistrement en cours")

    def _build_trip_summary(self, stats, end_odo, *, ended_at=None):
        end_time = time.time() if ended_at is None else float(ended_at)
        duration_sec = int(end_time - self.trip_start_time) if self.trip_start_time else 0
        return {
            "metadata": {
                "date": datetime.fromtimestamp(end_time).isoformat(),
                "duration_sec": max(0, duration_sec),
                "start_odo_km": self.trip_start_odo,
                "end_odo_km": end_odo,
            },
            "stats": {
                "distance_km": stats.get("distance_km", 0.0),
                "fuel_l": stats.get("session_fuel_l", 0.0),
                "cost_eur": stats.get("session_cost", 0.0),
                "avg_rpm": stats.get("avg_rpm", 0),
                "aggressivity_pct": stats.get("aggressivity_pct", 0.0),
                "deceleration_without_throttle_km": stats.get(
                    "deceleration_without_throttle_km", 0.0
                ),
                "longitudinal_g_last": stats.get("longitudinal_g", 0.0),
            },
            "trace": list(self.trip_trace),
        }

    def _save_trip_summary(self, stats, end_odo):
        trip_summary = self._build_trip_summary(stats, end_odo)
        if self._write_summary(trip_summary):
            return True
        with self._dir_lock:
            self._pending_summaries.append(trip_summary)
        return False

    def _write_summary(self, trip_summary):
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"trip_{timestamp_str}.json"
        with self._dir_lock:
            filepath = os.path.join(self.trips_dir, filename)
        try:
            self._write_json_atomic(filepath, trip_summary)
            self.print_message(f"Trajet exporté : {filename}")
            return True
        except (OSError, TypeError, ValueError) as exc:
            self.set_warning(f"Écriture du trajet différée : {exc}")
            return False

    @staticmethod
    def _write_json_atomic(filepath, payload):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        tmp_path = filepath + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=4)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_path, filepath)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise

    def _checkpoint_path(self, trips_dir=None):
        return os.path.join(trips_dir or self.trips_dir, self.CHECKPOINT_FILENAME)

    def _make_checkpoint(self, end_odo):
        now = time.time()
        return {
            "schema_version": self.CHECKPOINT_SCHEMA_VERSION,
            "metadata": {
                "started_at": self.trip_start_time or now,
                "start_odo_km": self.trip_start_odo,
                "end_odo_km": end_odo,
                "suspended_at": now,
                "suspended_at_iso": datetime.fromtimestamp(now).isoformat(),
            },
            "stats_state": self.stats_service.export_session_checkpoint(),
            "trace": list(self.trip_trace),
        }

    def _write_checkpoint(self, end_odo):
        try:
            checkpoint = self._make_checkpoint(end_odo)
            with self._dir_lock:
                self._write_json_atomic(self._checkpoint_path(), checkpoint)
            self._recovery_checkpoint = checkpoint
            return True
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self.set_warning(f"Checkpoint du trajet impossible : {exc}")
            return False

    def _load_checkpoint(self):
        filepath = self._checkpoint_path()
        if not os.path.isfile(filepath):
            return None
        try:
            with open(filepath, encoding="utf-8") as stream:
                checkpoint = json.load(stream)
            required_stats_state = {
                "stats", "start_odo", "session_distance_km", "absolute_fuel_session",
                "rpm_integral", "engine_time", "aggressive_time", "motion_time",
                "deceleration_without_throttle_dist", "shift_time_sum", "shift_count",
            }
            if (
                not isinstance(checkpoint, dict)
                or checkpoint.get("schema_version") != self.CHECKPOINT_SCHEMA_VERSION
                or not isinstance(checkpoint.get("metadata"), dict)
                or not isinstance(checkpoint.get("stats_state"), dict)
                or not required_stats_state.issubset(checkpoint["stats_state"])
                or not isinstance(checkpoint["stats_state"].get("stats"), dict)
                or "started_at" not in checkpoint["metadata"]
                or "start_odo_km" not in checkpoint["metadata"]
            ):
                raise ValueError("format incomplet")
            return checkpoint
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            invalid_path = f"{filepath}.invalid.{int(time.time())}"
            try:
                os.replace(filepath, invalid_path)
            except OSError:
                pass
            self.set_warning(f"Checkpoint de trajet isolé : {exc}")
            return None

    def _archive_recovery_checkpoint(self):
        checkpoint = self._recovery_checkpoint
        if checkpoint is None:
            return True
        metadata = checkpoint["metadata"]
        stats = checkpoint["stats_state"].get("stats", {})
        previous = (self.trip_start_time, self.trip_start_odo, self.trip_trace)
        self.trip_start_time = float(metadata["started_at"])
        self.trip_start_odo = float(metadata["start_odo_km"])
        self.trip_trace = list(checkpoint.get("trace", []))
        try:
            summary = self._build_trip_summary(
                stats,
                metadata.get("end_odo_km", self.trip_start_odo),
                ended_at=metadata.get("suspended_at", time.time()),
            )
            if not self._write_summary(summary):
                return False
            self._remove_checkpoint()
            return True
        finally:
            self.trip_start_time, self.trip_start_odo, self.trip_trace = previous

    def _remove_checkpoint(self, trips_dir=None):
        try:
            os.remove(self._checkpoint_path(trips_dir))
        except FileNotFoundError:
            pass
        except OSError as exc:
            self.set_warning(f"Nettoyage du checkpoint impossible : {exc}")

    def _ensure_trips_dir(self):
        try:
            os.makedirs(self.trips_dir, exist_ok=True)
            return True
        except OSError as exc:
            self.set_warning(f"Répertoire trips inaccessible : {exc}")
            return False

    def update_trips_dir(self, new_dir: str):
        """Change la cible à chaud et conserve le checkpoint actif."""
        with self._dir_lock:
            old_dir = self.trips_dir
            self.trips_dir = new_dir
        if not self._ensure_trips_dir():
            return False

        if self._recovery_checkpoint is not None:
            try:
                self._write_json_atomic(self._checkpoint_path(), self._recovery_checkpoint)
                if os.path.abspath(old_dir) != os.path.abspath(new_dir):
                    self._remove_checkpoint(old_dir)
            except (OSError, TypeError, ValueError) as exc:
                self.set_warning(f"Déplacement du checkpoint impossible : {exc}")
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

    def _suspend_trip(self, snapshot):
        if snapshot.domain("session").get("state") == "RUNNING":
            self._publish_session("SUSPENDED")
        current_odo = snapshot.domain("motion").get("odometer", 0.0)
        saved = self._write_checkpoint(current_odo)
        if saved:
            self.set_warning("Trajet conservé; reprise proposée au prochain démarrage")
        return saved

    def stop(self):
        super().stop()
        with self._session_lock:
            snapshot = self.runtime.snapshot()
            state = snapshot.domain("session").get("state")
            if state in ["RUNNING", "PAUSED", "WAITING_IGNITION", "SUSPENDED"]:
                self.print_message("Arrêt système détecté : checkpoint du trajet en cours.")
                self._suspend_trip(snapshot)

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        if self._recovery_checkpoint is not None:
            self._recovery_deadline = time.monotonic() + self.RECOVERY_TIMEOUT_S
            self._publish_session("RECOVERY_PENDING", self.RECOVERY_TIMEOUT_S)
        self._thread = threading.Thread(
            target=self._run, args=(stop_event,), daemon=True, name=self.service_name
        )
        self._thread.start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            snapshot = self.runtime.snapshot()
            powertrain = snapshot.domain("powertrain")
            motion = snapshot.domain("motion")
            state = snapshot.domain("session").get("state")
            ignition = bool(powertrain.get("key_run", False))
            wall_time = time.time()
            monotonic_time = time.monotonic()
            current_speed = motion.get("speed", 0.0)

            if state == "RECOVERY_PENDING" and self._recovery_deadline is not None:
                remaining = max(0, int(self._recovery_deadline - monotonic_time + 0.999))
                self._publish_session("RECOVERY_PENDING", remaining)
                if remaining == 0:
                    self.start_new_trip()
            elif ignition and state in ["IDLE", "ENDED"]:
                with self._session_lock:
                    self._begin_new_session(snapshot)
            elif state in ["WAITING_IGNITION", "SUSPENDED"] and (ignition or current_speed > 3.0):
                self._publish_session("RUNNING")
                self.set_ok("Reprise de l'enregistrement")
            elif state == "PAUSED" and current_speed > 3.0:
                self._publish_session("RUNNING")
                self.set_ok("Reprise automatique (mouvement détecté)")
            elif not ignition and state == "RUNNING":
                with self._session_lock:
                    self._suspend_trip(snapshot)
            elif state == "RUNNING":
                if wall_time - self.last_trace_time >= self.CHECKPOINT_INTERVAL_S:
                    point = {
                        "ts": int(wall_time),
                        "spd": round(current_speed, 1),
                        "cons": snapshot.domain("trip").get("inst_cons", 0.0),
                    }
                    if point["spd"] > 1.0:
                        self.trip_trace.append(point)
                    self.last_trace_time = wall_time
                if monotonic_time - self.last_checkpoint_time >= self.CHECKPOINT_INTERVAL_S:
                    self._write_checkpoint(motion.get("odometer", 0.0))
                    self.last_checkpoint_time = monotonic_time

            stop_event.wait(0.5)
