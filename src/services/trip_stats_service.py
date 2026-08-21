import time
import threading
from collections import deque

from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


class TripStatsService(BaseService):
    """Ordinateur de bord : Calcule les statistiques instantanées et persistantes (Consommation, Distance, Entretien)."""

    TRIP_UNITS = {
        "distance_km": "km", "session_fuel_l": "L", "session_cost": "EUR",
        "fuel_price": "EUR/L", "avg_rpm": "rpm",
        "deceleration_without_throttle_km": "km", "aggressivity_pct": "%",
        "shift_time_sec": "s", "trip_b_fuel": "L", "trip_a": "km",
        "trip_b": "km", "inst_cons": "L/100km", "avg_cons_b": "L/100km",
        "avg_cons_session": "L/100km", "autonomy": "km",
        "km_before_service": "km", "longitudinal_g": "G",
    }

    def __init__(self, runtime, config, storage=None):
        super().__init__("TripStats", storage)
        self.runtime = runtime
        self._thread = None
        self.storage = storage

        # --- Configuration des fréquences de rafraîchissement (en secondes) ---
        self.RATE_FAST_LOOP = 0.020           # Boucle matérielle principale (50 Hz)
        self.RATE_INST_CONS = 1.0 / 24.0      # Calcul conso instantanée (~41ms / 24 Hz)
        self.RATE_SLOW_TELEMETRY = 1.0 / 20.0 # Contrat UI : ne pas descendre sous 20 Hz
        self.INST_CONS_WINDOW_SECONDS = 3.0

        fuel_config = config.get("fuel", {})
        # Valeur observée sur le compteur 8 bits de la Clio (256 * 0,00008 L).
        self._fuel_counter_modulus_l = float(fuel_config.get("counter_modulus_l", 0.02048))
        self._max_fuel_rate_lph = float(fuel_config.get("max_plausible_rate_lph", 80.0))

        # Verrou d'accès aux statistiques partagées.
        self._stats_lock = threading.RLock()

        # Paramètres de maintenance issus du profil véhicule.
        revision_config = config.get("maintenance", {}).get("revision", {})
        default_rev_interval = revision_config.get("interval_km", 20000)
        default_rev_warning = revision_config.get("warning_threshold_km", 2000)

        self.register_param("revision_interval", "Intervalle Révision (km)", ServiceParamType.SLIDER, default_rev_interval,
                            min_val=5000.0, max_val=50000.0)
        self.register_param("revision_warning", "Alerte Révision (km)", ServiceParamType.SLIDER, default_rev_warning, min_val=500.0,
                            max_val=30000.0)

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
        self.last_time_avg = time.monotonic()

        self.inst_window = deque(maxlen=200)  # Fenêtre temporelle (~3 s), indépendante du jitter
        self.last_fuel_inst = None
        self.last_time_inst = time.monotonic()

        self._last_raw_fuel = None
        self._absolute_fuel_session = 0.0
        self._accept_running = False

        # Conteneur des statistiques publiées dans le domaine trip.
        self._stats = {
            "is_active": False, "distance_km": 0.0,
            "session_fuel_l": 0.0,
            "session_cost": 0.0,
            "fuel_price": self.fuel_price,
            "avg_rpm": 0, "deceleration_without_throttle_km": 0.0,
            "aggressivity_pct": 0.0, "shift_time_sec": 0.0,
            "trip_b_fuel": round(self.fuel_b_accumulated, 2),
            "trip_a": init_trip_a, "trip_b": init_trip_b,
            "inst_cons": 0.0, "avg_cons_b": init_avg_cons,
            "avg_cons_session": 0.0, "autonomy": 0.0,
            "km_before_service": init_km_service, "service_warning": False,
            "longitudinal_g": 0.0
        }

        self._prev_speed = 0.0
        self._last_g_time = time.monotonic()

        self.reset_session(self.runtime.snapshot().domain("motion").get("odometer"))

    def _stats_snapshot(self):
        with self._stats_lock:
            return self._stats.copy()

    def reset_session(self, last_odo):
        with self._stats_lock:
            self._start_odo = last_odo if last_odo is not None else 0.0
            self._session_distance_km = 0.0
            self._rpm_integral = 0.0
            self._engine_time = 0.0
            self._aggressive_time = 0.0
            self._motion_time = 0.0
            self._deceleration_without_throttle_dist = 0.0
            self._shift_time_sum = 0.0
            self._shift_count = 0
            self._is_shifting = False
            self._shift_start = 0.0
            self._absolute_fuel_session = 0.0
            self._was_active = False
            self._last_raw_fuel = None
            self._last_raw_fuel_time = None
            self.last_fuel_avg = None
            self.last_fuel_inst = None
            self.last_time_inst = time.monotonic()
            self.inst_window.clear()
            self._prev_speed = 0.0
            self._last_g_time = time.monotonic()
            self._stats.update({
                "is_active": False,
                "distance_km": 0.0,
                "session_fuel_l": 0.0,
                "session_cost": 0.0,
                "avg_cons_session": 0.0,
                "inst_cons": 0.0,
                "avg_rpm": 0,
                "deceleration_without_throttle_km": 0.0,
                "aggressivity_pct": 0.0,
                "shift_time_sec": 0.0,
                "longitudinal_g": 0.0,
            })
        self._publish_stats()

    def begin_session(self, last_odo):
        """Starts a fresh accumulator before SessionManager publishes RUNNING."""
        self.reset_session(last_odo)
        with self._stats_lock:
            self._accept_running = True

    def _publish_stats(self):
        self.runtime.publish(
            "trip", self._stats_snapshot(), source="trip-stats", ttl_s=0.25,
            units=self.TRIP_UNITS,
        )

    def finish_session(self, last_odo):
        """Atomically captures the final trip values and resets the accumulator."""
        with self._stats_lock:
            self._accept_running = False
            final_stats = self._stats.copy()
            self.reset_session(last_odo)
            return final_stats

    def reset_trip_a(self):
        current_odo = self.runtime.snapshot().domain("motion").get("odometer", self.last_saved_odo)
        self.trip_a_marker = current_odo
        if self.storage:
            self.storage.set("trips.a.marker", current_odo)
        with self._stats_lock:
            self._stats["trip_a"] = 0.0
        self._publish_stats()

    def reset_trip_b(self):
        current_odo = self.runtime.snapshot().domain("motion").get("odometer", self.last_saved_odo)
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
        self._publish_stats()

    def set_trip_b_fuel(self, new_fuel: float):
        self.fuel_b_accumulated = max(0.0, new_fuel)
        if self.storage:
            self.storage.set("trips.b.fuel", self.fuel_b_accumulated)
        with self._stats_lock:
            self._stats["trip_b_fuel"] = round(self.fuel_b_accumulated, 2)
            trip_b_dist = self._stats.get("trip_b", 0.0)
            self._stats["avg_cons_b"] = round((self.fuel_b_accumulated / trip_b_dist) * 100.0,
                                              1) if trip_b_dist > 0.05 else 0.0
        self._publish_stats()

    def set_trip_b_distance(self, new_distance: float):
        current_odo = self.runtime.snapshot().domain("motion").get("odometer", self.last_saved_odo)
        new_distance = max(0.0, new_distance)
        self.trip_b_marker = current_odo - new_distance
        if self.storage:
            self.storage.set("trips.b.marker", self.trip_b_marker)
        with self._stats_lock:
            self._stats["trip_b"] = round(new_distance, 1)
            trip_b_dist = new_distance
            self._stats["avg_cons_b"] = round((self.fuel_b_accumulated / trip_b_dist) * 100.0,
                                              1) if trip_b_dist > 0.05 else 0.0
        self._publish_stats()

    def reset_maintenance(self):
        current_odo = self.runtime.snapshot().domain("motion").get("odometer", self.last_saved_odo)
        self.last_revision_odo = current_odo
        if self.storage:
            self.storage.set("vehicle.last_revision_odo", current_odo)
        with self._stats_lock:
            self._stats["km_before_service"] = self._params["revision_interval"]["value"]
            self._stats["service_warning"] = False
        self._publish_stats()

    def set_fuel_price(self, new_price: float):
        self.fuel_price = new_price
        if self.storage:
            self.storage.set("settings.last_fuel_price", new_price)
        with self._stats_lock:
            self._stats["fuel_price"] = new_price
        self._publish_stats()

    def get_fuel_price(self):
        return self.fuel_price

    def start(self, stop_event):
        self._thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="TripStatsWorker")
        self._thread.start()
        super().start(stop_event, implemented=True)

    def stop(self):
        super().stop()
        try:
            current_odo = self.runtime.snapshot().domain("motion").get("odometer", self.last_saved_odo)
            if self.storage:
                self.storage.set_many({
                    "vehicle.last_odometer": current_odo,
                    "trips.b.fuel": self.fuel_b_accumulated
                })
            self.print_message("Sauvegarde finale effectuée avec succès.")
        except Exception as e:
            self.set_error(f"Échec de la sauvegarde finale : {str(e)}")

    def _run(self, stop_event):
        last_calc_time = time.monotonic()
        last_tick_time = time.monotonic()

        try:
            while not stop_event.is_set():
                current_time = time.monotonic()
                # Évite d'ajouter une distance fictive après suspension ou gel système.
                dt = min(0.25, max(0.0, current_time - last_tick_time))
                last_tick_time = current_time

                snapshot = self.runtime.snapshot()
                powertrain = snapshot.domain("powertrain")
                motion = snapshot.domain("motion")
                session = snapshot.domain("session")
                current_odo = motion.get('odometer')
                raw_fuel = powertrain.get('fuel_used')
                current_speed = motion.get('speed', 0.0)
                session_state = session.get("state", "IDLE")

                if current_odo is None:
                    stop_event.wait(0.1)
                    continue

                with self._stats_lock:
                    # _accept_running closes the race where a loop that captured
                    # RUNNING just before finish_session would otherwise write
                    # into the freshly reset accumulator.
                    is_active = session_state == "RUNNING" and self._accept_running
                    self._stats["is_active"] = is_active
                    if is_active != self._was_active:
                        self.inst_window.clear()
                        self.last_fuel_inst = self._absolute_fuel_session if is_active else None
                        self.last_time_inst = current_time
                        self._stats["inst_cons"] = 0.0
                        self._prev_speed = current_speed
                        self._last_g_time = current_time
                        self._was_active = is_active

                    if raw_fuel is not None:
                        if self._last_raw_fuel is not None and raw_fuel != self._last_raw_fuel:
                            delta_f = raw_fuel - self._last_raw_fuel
                            if delta_f < 0:
                                delta_f += self._fuel_counter_modulus_l
                            elapsed = max(0.001, current_time - self._last_raw_fuel_time)
                            plausible_max = max(0.002, self._max_fuel_rate_lph / 3600.0 * elapsed * 3.0)
                            if delta_f < 0.0 or delta_f > plausible_max:
                                self.logger.warning(
                                    f"Saut compteur carburant rejeté: {delta_f:.5f} L",
                                    extra={"error_code": "FUEL_COUNTER_IMPLAUSIBLE"},
                                )
                                delta_f = 0.0
                            self._last_raw_fuel = raw_fuel
                            self._last_raw_fuel_time = current_time
                        elif self._last_raw_fuel is not None:
                            delta_f = 0.0
                        else:
                            delta_f = 0.0
                            self._last_raw_fuel = raw_fuel
                            self._last_raw_fuel_time = current_time

                        if is_active:
                            self._absolute_fuel_session += delta_f
                            self._stats["session_fuel_l"] = round(self._absolute_fuel_session, 2)
                            self._stats["session_cost"] = round(self._absolute_fuel_session * self.fuel_price, 2)

                    perfect_fuel_stream = self._absolute_fuel_session if is_active else None

                telemetry_inputs = {
                    "rpm": powertrain.get("rpm", 0),
                    "accel_computed": powertrain.get("accel_computed", 0.0),
                    "accel_pos": powertrain.get("accel_pos"),
                    "driver_torque_request": powertrain.get("driver_torque_request"),
                    "clutch": motion.get("clutch", False),
                }
                self._calc_fast_telemetry(
                    telemetry_inputs, dt, current_time, current_speed, perfect_fuel_stream
                )

                if current_time - last_calc_time >= self.RATE_SLOW_TELEMETRY:
                    self._calc_slow_telemetry(
                        current_odo, perfect_fuel_stream, current_time,
                        powertrain.get("fuel_level", 0.0),
                    )
                    self._publish_stats()
                    last_calc_time = current_time

                stop_event.wait(self.RATE_FAST_LOOP)
        except Exception as e:
            self.set_error(f"Crash inattendu : {str(e)}")

    def _calc_fast_telemetry(self, data, dt, current_time, current_speed, perfect_fuel):
        rpm = data.get('rpm', 0)
        accel = data.get('accel_computed', 0.0)
        clutch = data.get('clutch', False)

        torque_request = data.get('driver_torque_request')

        with self._stats_lock:
            # Exploitation de la variable de rafraîchissement personnalisée
            if perfect_fuel is not None and self.last_fuel_inst is not None:
                dt_inst = current_time - self.last_time_inst
                if dt_inst >= self.RATE_INST_CONS:
                    delta_fuel = perfect_fuel - self.last_fuel_inst
                    delta_dist = current_speed * (dt_inst / 3600.0)

                    self.inst_window.append((current_time, delta_fuel, delta_dist))
                    cutoff = current_time - self.INST_CONS_WINDOW_SECONDS
                    while self.inst_window and self.inst_window[0][0] < cutoff:
                        self.inst_window.popleft()
                    w_fuel = sum(item[1] for item in self.inst_window)
                    w_dist = sum(item[2] for item in self.inst_window)

                    if w_dist > 0.001 and current_speed > 3.0:
                        raw_inst = (w_fuel / w_dist) * 100.0
                        self._stats["inst_cons"] = min(99.9, round(raw_inst, 1))
                    else:
                        self._stats["inst_cons"] = 0.0

                    self.last_fuel_inst = perfect_fuel
                    self.last_time_inst = current_time
            elif perfect_fuel is not None:
                self.last_fuel_inst = perfect_fuel

            if self._stats["is_active"]:
                self._session_distance_km += current_speed * (dt / 3600.0)
                if rpm > 0:
                    self._rpm_integral += rpm * dt
                    self._engine_time += dt

                if current_speed > 3.0:
                    self._motion_time += dt
                    if accel > 2.0:
                        self._aggressive_time += dt

                # Décélération sans accélérateur (souvent frein moteur). Ce n'est
                # pas une vraie roue libre sans signal de rapport neutre/embrayage ouvert.
                if torque_request is not None:
                    is_decelerating = float(torque_request) < 0.0
                else:
                    # Mode de repli (ex: si le signal CAN de couple n'est pas encore disponible)
                    accel_pos = data.get('accel_pos')
                    if accel_pos is not None:
                        is_decelerating = float(accel_pos) <= 0.0
                    else:
                        is_decelerating = accel < 0.0

                if is_decelerating and current_speed > 5.0:
                    self._deceleration_without_throttle_dist += current_speed * (dt / 3600.0)

                if clutch and not self._is_shifting:
                    self._is_shifting, self._shift_start = True, current_time
                elif not clutch and self._is_shifting:
                    self._is_shifting = False
                    duration = current_time - self._shift_start
                    if 0.1 < duration < 5.0:
                        self._shift_time_sum += duration
                        self._shift_count += 1

                dt_g = current_time - self._last_g_time
                if dt_g >= 0.1:
                    dv = (current_speed - self._prev_speed) / 3.6
                    raw_g = dv / (dt_g * 9.81)
                    longitudinal_g = round((self._stats["longitudinal_g"] * 0.8) + (raw_g * 0.2), 2)
                    self._stats["longitudinal_g"] = longitudinal_g
                    self._prev_speed = current_speed
                    self._last_g_time = current_time

    def _calc_slow_telemetry(self, current_odo, perfect_fuel, current_time, fuel_level=None):
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

            self._stats["trip_b_fuel"] = round(self.fuel_b_accumulated, 2)

            self._stats["avg_cons_b"] = round((self.fuel_b_accumulated / trip_b_dist) * 100.0,
                                              1) if trip_b_dist > 0.05 else 0.0

            session_dist = self._session_distance_km
            self._stats["avg_cons_session"] = round((self._absolute_fuel_session / session_dist) * 100.0,
                                                     1) if session_dist > 0.05 else 0.0

            reference_consumption = self._stats["avg_cons_session"] or self._stats["avg_cons_b"]
            if fuel_level is None:
                fuel_level = self.runtime.snapshot().domain("powertrain").get("fuel_level", 0.0)
            self._stats["autonomy"] = round(
                max(0.0, float(fuel_level)) / reference_consumption * 100.0, 0
            ) if reference_consumption > 0.1 else 0.0

            rev_interval = self._params["revision_interval"]["value"]
            rev_warning = self._params["revision_warning"]["value"]

            dist_depuis_rev = current_odo - self.last_revision_odo
            km_restants = max(0.0, rev_interval - dist_depuis_rev)

            self._stats["km_before_service"] = km_restants
            self._stats["service_warning"] = km_restants <= rev_warning

            if self._stats["is_active"]:
                self._stats["distance_km"] = round(self._session_distance_km, 1)
                self._stats["avg_rpm"] = int(
                    self._rpm_integral / self._engine_time
                ) if self._engine_time > 0 else 0
                decel_km = round(self._deceleration_without_throttle_dist, 1)
                self._stats["deceleration_without_throttle_km"] = decel_km
                self._stats["aggressivity_pct"] = round(
                    self._aggressive_time / self._motion_time * 100.0, 1
                ) if self._motion_time > 0 else 0.0
                self._stats["shift_time_sec"] = round(self._shift_time_sum / self._shift_count,
                                                      2) if self._shift_count > 0 else 0.0

        if current_odo - self.last_saved_odo >= 1.0:
            if self.storage:
                self.storage.set_many({
                    "vehicle.last_odometer": current_odo,
                    "trips.b.fuel": self.fuel_b_accumulated
                })
            self.last_saved_odo = current_odo
