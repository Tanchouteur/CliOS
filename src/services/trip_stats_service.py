import time
import threading
from collections import deque

from src.services.base_service import BaseService


class TripStatsService(BaseService):
    """Ordinateur de bord : Calcule les statistiques instantanées et persistantes (Consommation, Distance, Entretien)."""

    def __init__(self, api, config, storage=None):
        super().__init__("TripStats", storage)
        self.api = api
        self._thread = None
        self.storage = storage

        # Verrou d'accès aux statistiques partagées.
        self._stats_lock = threading.Lock()

        # Paramètres de maintenance issus du profil véhicule.
        revision_config = config.get("maintenance", {}).get("revision", {})
        default_rev_interval = revision_config.get("interval_km", 20000)
        default_rev_warning = revision_config.get("warning_threshold_km", 2000)

        self.register_param("revision_interval", "Intervalle Révision (km)", "slider", default_rev_interval,
                            min_val=5000.0, max_val=50000.0)
        self.register_param("revision_warning", "Alerte Révision (km)", "slider", default_rev_warning, min_val=500.0,
                            max_val=10000.0)

        # Charge l'état persistant.
        self.trip_a_marker = self.storage.get("trips.a.marker", 0.0) if self.storage else 0.0
        self.trip_b_marker = self.storage.get("trips.b.marker", 0.0) if self.storage else 0.0
        self.fuel_b_accumulated = self.storage.get("trips.b.fuel", 0.0) if self.storage else 0.0
        self.last_saved_odo = self.storage.get("vehicle.last_odometer", 0.0) if self.storage else 0.0
        self.last_revision_odo = self.storage.get("vehicle.last_revision_odo", 0.0) if self.storage else 0.0
        self.fuel_price = self.storage.get("settings.last_fuel_price", 1.70) if self.storage else 1.70

        init_trip_a = max(0.0, self.last_saved_odo - self.trip_a_marker)
        init_trip_b = max(0.0, self.last_saved_odo - self.trip_b_marker)
        init_avg_cons = (self.fuel_b_accumulated / init_trip_b * 100.0) if init_trip_b > 0.05 else 0.0

        current_rev_interval = self._params["revision_interval"]["value"]
        init_km_service = max(0.0, current_rev_interval - (self.last_saved_odo - self.last_revision_odo))

        # État interne des calculateurs de consommation.
        self.last_fuel_avg = None
        self.last_time_avg = time.time()

        self.inst_window = deque(maxlen=5)
        self.last_fuel_inst = None
        self.last_time_inst = time.time()

        self._last_raw_fuel = None
        self._absolute_fuel_session = 0.0

        # Conteneur des statistiques exposées au bridge.
        self._stats = {
            "is_active": False, "distance_km": 0.0,
            "session_fuel_l": 0.0,
            "session_cost": 0.0,
            "fuel_price": self.fuel_price,
            "avg_rpm": 0, "coasting_km": 0.0, "aggressivity_pct": 0.0, "shift_time_sec": 0.0,

            # Valeurs persistantes et longue durée
            "trip_a": init_trip_a, "trip_b": init_trip_b,
            "inst_cons": 0.0, "avg_cons_b": init_avg_cons,
            "avg_cons_session": 0.0, "autonomy": 0.0,
            "km_before_service": init_km_service, "service_warning": False,

            # Télémétrie dynamique
            "g_force": 0.0
        }

        self._prev_speed = 0.0
        self._last_g_time = time.time()

        # Initialise la session avec l'odomètre courant.
        safe_data = self.api.get_display_data()
        self.reset_session(safe_data.get("odometer"))

    # Fournit une copie thread-safe pour l'interface.
    @property
    def stats(self):
        """Fournit une copie Thread-Safe du dictionnaire pour le Bridge QML."""
        with self._stats_lock:
            return self._stats.copy()

    def reset_session(self, last_odo):
        self._start_odo = last_odo if last_odo is not None else 0.0
        self._session_distance_km = 0.0
        self._rpm_sum = 0.0
        self._rpm_count = 0
        self._accel_sum = 0.0
        self._accel_count = 0
        self._coasting_dist = 0.0
        self._shift_time_sum = 0.0
        self._shift_count = 0
        self._is_shifting = False
        self._shift_start = 0.0
        self._absolute_fuel_session = 0.0

        # Réinitialise les compteurs de session.
        with self._stats_lock:
            self._stats["session_fuel_l"] = 0.0
            self._stats["session_cost"] = 0.0
            self._stats["avg_cons_session"] = 0.0

    # Commandes exposées à l'interface.
    def reset_trip_a(self):
        current_odo = self.api.get_display_data().get("odometer", self.last_saved_odo)
        self.trip_a_marker = current_odo
        if self.storage: self.storage.set("trips.a.marker", current_odo)
        with self._stats_lock:
            self._stats["trip_a"] = 0.0

    def reset_trip_b(self):
        current_odo = self.api.get_display_data().get("odometer", self.last_saved_odo)
        self.trip_b_marker = current_odo
        self.fuel_b_accumulated = 0.0
        if self.storage:
            self.storage.set_many({
                "trips.b.marker": current_odo,
                "trips.b.fuel": 0.0
            })
        with self._stats_lock:
            self._stats["trip_b"] = 0.0
            self._stats["avg_cons_b"] = 0.0

    def reset_maintenance(self):
        current_odo = self.api.get_display_data().get("odometer", self.last_saved_odo)
        self.last_revision_odo = current_odo
        if self.storage: self.storage.set("vehicle.last_revision_odo", current_odo)
        with self._stats_lock:
            self._stats["km_before_service"] = self._params["revision_interval"]["value"]
            self._stats["service_warning"] = False

    def set_fuel_price(self, new_price: float):
        self.fuel_price = new_price
        if self.storage: self.storage.set("settings.last_fuel_price", new_price)
        with self._stats_lock:
            self._stats["fuel_price"] = new_price

    def get_fuel_price(self):
        return self.fuel_price

    # Cycle de vie du worker.
    def start(self, stop_event):
        self._thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="TripStatsWorker")
        self._thread.start()
        super().start(stop_event, implemented=True)

    def stop(self):
        try:
            current_odo = self.api.get_display_data().get("odometer", self.last_saved_odo)
            if self.storage:
                self.storage.set_many({
                    "vehicle.last_odometer": current_odo,
                    "trips.b.fuel": self.fuel_b_accumulated
                })
            self.print_message("Sauvegarde finale effectuée avec succès.")
        except Exception as e:
            self.set_error(f"Échec de la sauvegarde finale : {str(e)}")
        super().stop()

    def _run(self, stop_event):
        last_calc_time = time.time()
        last_tick_time = time.time()

        try:
            while not stop_event.is_set():
                current_time = time.time()
                dt = current_time - last_tick_time
                last_tick_time = current_time

                # Lecture snapshot des données API.
                safe_data = self.api.get_display_data()
                current_odo = safe_data.get('odometer')
                raw_fuel = safe_data.get('fuel_used')
                current_speed = safe_data.get('speed', 0.0)
                session_state = safe_data.get("session_state", "IDLE")

                if current_odo is None:
                    stop_event.wait(0.1)
                    continue

                # Mise à jour thread-safe des statistiques.
                with self._stats_lock:
                    self._stats["is_active"] = (session_state == "RUNNING")

                    if raw_fuel is not None:
                        if self._last_raw_fuel is not None:
                            delta_f = raw_fuel - self._last_raw_fuel
                            if delta_f < 0:
                                delta_f += 0.02048
                        else:
                            delta_f = 0.0

                        self._last_raw_fuel = raw_fuel

                        if self._stats["is_active"]:
                            self._absolute_fuel_session += delta_f
                            self._stats["session_fuel_l"] = round(self._absolute_fuel_session, 2)
                            self._stats["session_cost"] = round(self._absolute_fuel_session * self.fuel_price, 2)

                    perfect_fuel_stream = self._absolute_fuel_session if self._stats["is_active"] else None

                self._calc_fast_telemetry(safe_data, dt, current_time, current_speed, perfect_fuel_stream)

                if current_time - last_calc_time >= 1.0:
                    self._calc_slow_telemetry(current_odo, perfect_fuel_stream, current_time)
                    last_calc_time = current_time

                stop_event.wait(0.020)
        except Exception as e:
            self.set_error(f"Crash inattendu : {str(e)}")

    # Routines de calcul.
    def _calc_fast_telemetry(self, data, dt, current_time, current_speed, perfect_fuel):
        rpm = data.get('rpm', 0)
        accel = data.get('accel_computed', 0.0)
        brake = data.get('brake', False)
        clutch = data.get('clutch', False)

        with self._stats_lock:
            # Consommation instantanée.
            if perfect_fuel is not None and self.last_fuel_inst is not None:
                dt_inst = current_time - self.last_time_inst
                if dt_inst >= 0.2:
                    delta_fuel = perfect_fuel - self.last_fuel_inst
                    delta_dist = current_speed * (dt_inst / 3600.0)

                    self.inst_window.append((delta_fuel, delta_dist))
                    w_fuel = sum(i[0] for i in self.inst_window)
                    w_dist = sum(i[1] for i in self.inst_window)

                    if w_dist > 0.001 and current_speed > 3.0:
                        raw_inst = (w_fuel / w_dist) * 100.0
                        self._stats["inst_cons"] = min(99.9, round(raw_inst, 1))
                    else:
                        self._stats["inst_cons"] = 0.0

                    self.last_fuel_inst = perfect_fuel
                    self.last_time_inst = current_time
            elif perfect_fuel is not None:
                self.last_fuel_inst = perfect_fuel

            # Indicateurs de conduite.
            if self._stats["is_active"]:
                self._session_distance_km += current_speed * (dt / 3600.0)
                if rpm > 0:
                    self._rpm_sum += rpm
                    self._rpm_count += 1
                if accel > 2.0:
                    self._accel_sum += accel
                    self._accel_count += 1
                elif current_speed > 5.0 and not brake:
                    self._coasting_dist += current_speed * (dt / 3600.0)

                # Temps moyen de passage de rapport.
                if clutch and not self._is_shifting:
                    self._is_shifting, self._shift_start = True, current_time
                elif not clutch and self._is_shifting:
                    self._is_shifting = False
                    duration = current_time - self._shift_start
                    if 0.1 < duration < 5.0:
                        self._shift_time_sum += duration
                        self._shift_count += 1

                # G-force longitudinal lissé.
                now = time.time()
                dt_g = now - self._last_g_time
                if dt_g >= 0.1:
                    dv = (current_speed - self._prev_speed) / 3.6
                    raw_g = dv / (dt_g * 9.81)
                    self._stats["g_force"] = round((self._stats["g_force"] * 0.8) + (raw_g * 0.2), 2)
                    self._prev_speed = current_speed
                    self._last_g_time = now

    def _calc_slow_telemetry(self, current_odo, perfect_fuel, current_time):
        if self.last_saved_odo == 0.0 and current_odo > 0:
            self.last_saved_odo = current_odo
            if self.trip_a_marker == 0.0:
                self.trip_a_marker = current_odo
            if self.trip_b_marker == 0.0:
                self.trip_b_marker = current_odo
            if self.last_revision_odo == 0.0:
                self.last_revision_odo = current_odo

        with self._stats_lock:
            self._stats["trip_a"] = max(0.0, current_odo - self.trip_a_marker)
            trip_b_dist = max(0.0, current_odo - self.trip_b_marker)
            self._stats["trip_b"] = trip_b_dist

            if perfect_fuel is not None:
                if self.last_fuel_avg is not None:
                    delta = perfect_fuel - self.last_fuel_avg
                    if delta > 0:
                        self.fuel_b_accumulated += delta
                self.last_fuel_avg = perfect_fuel

            self._stats["avg_cons_b"] = round((self.fuel_b_accumulated / trip_b_dist) * 100.0,
                                              1) if trip_b_dist > 0.05 else 0.0

            session_dist = self._session_distance_km
            self._stats["avg_cons_session"] = round((self._absolute_fuel_session / session_dist) * 100.0,
                                                     1) if session_dist > 0.05 else 0.0

            # Seuils de maintenance configurables à chaud.
            rev_interval = self._params["revision_interval"]["value"]
            rev_warning = self._params["revision_warning"]["value"]

            dist_depuis_rev = current_odo - self.last_revision_odo
            km_restants = max(0.0, rev_interval - dist_depuis_rev)

            self._stats["km_before_service"] = km_restants
            self._stats["service_warning"] = km_restants <= rev_warning

            if self._stats["is_active"]:
                self._stats["distance_km"] = round(self._session_distance_km, 1)
                self._stats["avg_rpm"] = int(self._rpm_sum / self._rpm_count) if self._rpm_count > 0 else 0
                self._stats["coasting_km"] = round(self._coasting_dist, 1)
                self._stats["aggressivity_pct"] = round(self._accel_sum / self._accel_count,
                                                        1) if self._accel_count > 0 else 0.0
                self._stats["shift_time_sec"] = round(self._shift_time_sum / self._shift_count,
                                                      2) if self._shift_count > 0 else 0.0

        if current_odo - self.last_saved_odo >= 1.0:
            if self.storage:
                self.storage.set_many({
                    "vehicle.last_odometer": current_odo,
                    "trips.b.fuel": self.fuel_b_accumulated
                })
            self.last_saved_odo = current_odo

