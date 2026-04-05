import time
import threading
from collections import deque
from src.storage import PersistentStorage


class TripStatsService:
    """Ordinateur de bord complet : Calcule les statistiques instantanées et persistantes."""

    def __init__(self, api, config):
        self.api = api
        self._thread = None
        self.storage = PersistentStorage()

        # --- Configuration Véhicule ---
        self._tank_capacity = config.get("tank_capacity", 50.0)
        trans_config = config.get("transmission", {})
        self._gear_ratios = trans_config.get("ratios", {})
        self._gear_tolerance = trans_config.get("tolerance", 5.0)

        revision_config = config.get("maintenance", {}).get("revision", {})
        self._revision_interval = revision_config.get("interval_km", 20000)
        self._revision_warning = revision_config.get("warning_threshold_km", 2000)

        # --- Chargement de la Persistance (Disque Dur) ---
        self.trip_a_marker = self.storage.get("trip_a_marker", 0.0)
        self.trip_b_marker = self.storage.get("trip_b_marker", 0.0)
        self.fuel_b_accumulated = self.storage.get("fuel_b_accumulated", 0.0)
        self.last_saved_odo = self.storage.get("last_odometer", 0.0)
        self.last_revision_odo = self.storage.get("last_revision_odo", 0.0)

        init_trip_a = max(0.0, self.last_saved_odo - self.trip_a_marker)
        init_trip_b = max(0.0, self.last_saved_odo - self.trip_b_marker)
        init_avg_cons = (self.fuel_b_accumulated / init_trip_b * 100.0) if init_trip_b > 0.05 else 0.0
        init_km_service = max(0.0, self._revision_interval - (self.last_saved_odo - self.last_revision_odo))

        # --- Variables de calcul (Conso) ---
        self.last_fuel_avg = None
        self.last_time_avg = time.time()
        self.inst_window = deque(maxlen=10)
        self.last_fuel_inst = None
        self.last_time_inst = time.time()

        # --- Le Dictionnaire Public (Lu par le Bridge) ---
        self.stats = {
            # Session de conduite (Moteur Allumé)
            "is_active": False, "distance_km": 0.0, "fuel_used_l": 0.0,
            "avg_rpm": 0, "coasting_km": 0.0, "aggressivity_pct": 0.0, "shift_time_sec": 0.0,

            # Global & Persistant
            "trip_a": 0.0, "trip_b": 0.0,
            "inst_cons": 0.0, "avg_cons_b": 0.0, "autonomy": 0.0,
            "gear": "N",
            "km_before_service": self._revision_interval, "service_warning": False
        }

        self._reset_session_accumulators()

    def _reset_session_accumulators(self):
        """Remet à zéro uniquement les données du trajet en cours."""
        self._trip_start_odo = 0.0
        self._trip_start_fuel = 0.0
        self._rpm_sum = 0.0
        self._rpm_count = 0
        self._accel_sum = 0.0
        self._accel_count = 0
        self._coasting_dist = 0.0
        self._shift_time_sum = 0.0
        self._shift_count = 0
        self._is_shifting = False
        self._shift_start = 0.0

    # ==========================================
    # COMMANDES UTILISATEUR (Appelées par le QML via le Bridge)
    # ==========================================
    def reset_trip_a(self):
        current_odo = self.api._data.get("odometer", self.last_saved_odo)
        self.trip_a_marker = current_odo
        self.storage.set("trip_a_marker", current_odo)
        self.stats["trip_a"] = 0.0

    def reset_trip_b(self):
        current_odo = self.api._data.get("odometer", self.last_saved_odo)
        self.trip_b_marker = current_odo
        self.fuel_b_accumulated = 0.0
        self.storage.set("trip_b_marker", current_odo)
        self.storage.set("fuel_b_accumulated", 0.0)
        self.stats["trip_b"] = 0.0
        self.stats["avg_cons_b"] = 0.0

    def reset_maintenance(self):
        current_odo = self.api._data.get("odometer", self.last_saved_odo)
        self.last_revision_odo = current_odo
        self.storage.set("last_revision_odo", current_odo)
        self.stats["km_before_service"] = self._revision_interval
        self.stats["service_warning"] = False

    # ==========================================
    # CYCLE DE VIE DU THREAD
    # ==========================================
    def start(self, stop_event):
        self._thread = threading.Thread(target=self._run, args=(stop_event,), daemon=True, name="TripStatsWorker")
        self._thread.start()

    def stop(self):
        pass

    def _run(self, stop_event):
        print("[STATS] Ordinateur de bord lancé.")
        last_calc_time = time.time()
        last_tick_time = time.time()

        while not stop_event.is_set():
            current_time = time.time()
            dt = current_time - last_tick_time
            last_tick_time = current_time

            data = self.api._data.copy()
            current_odo = data.get('odometer')
            current_fuel = data.get('fuel_used')
            current_speed = data.get('speed', 0.0)
            ignition = data.get('ignition_on', False) or data.get('key_run', False)

            # On attend que le CAN ait envoyé les premières vraies données
            if current_odo is None:
                time.sleep(0.1)
                continue

            # --- GESTION DE LA SESSION ---
            if ignition and not self.stats["is_active"]:
                self._reset_session_accumulators()
                self._trip_start_odo = current_odo
                self._trip_start_fuel = current_fuel if current_fuel else 0.0
                self.stats["is_active"] = True

            elif not ignition and self.stats["is_active"]:
                self.stats["is_active"] = False

            # --- BOUCLE RAPIDE (~50Hz) : Calculs instantanés ---
            self._calc_fast_telemetry(data, dt, current_time, current_speed)

            # --- BOUCLE LENTE (1Hz) : Calculs Globaux et Persistance ---
            if current_time - last_calc_time >= 1.0:
                self._calc_slow_telemetry(current_odo, current_fuel, current_time)
                last_calc_time = current_time

            time.sleep(0.020)

    # ==========================================
    # ROUTINES MATHÉMATIQUES
    # ==========================================
    def _calc_fast_telemetry(self, data, dt, current_time, current_speed):
        """Calculs nécessitant une haute fréquence (Conso instantanée, Rapport de boîte, Session)."""
        rpm = data.get('rpm', 0)
        accel = data.get('accel_pos', 0.0)
        clutch = data.get('clutch', False)
        reverse = data.get('reverse_engaged', False)
        current_fuel = data.get('fuel_used')

        # 1. Calcul du rapport de boîte
        if reverse:
            self.stats["gear"] = "R"
        elif clutch or current_speed < 3.0:
            self.stats["gear"] = "N"
        else:
            current_ratio = rpm / current_speed if current_speed > 0 else 0
            best_gear, smallest_diff = "N", float('inf')
            for gear_name, target_ratio in self._gear_ratios.items():
                diff = abs(current_ratio - target_ratio)
                if diff <= self._gear_tolerance and diff < smallest_diff:
                    smallest_diff, best_gear = diff, gear_name
            self.stats["gear"] = best_gear

        # 2. Conso Instantanée (Moyenne mobile dynamique)
        if current_fuel is not None and self.last_fuel_inst is not None:
            dt_inst = current_time - self.last_time_inst
            refresh_rate = 0.2 if accel > 5.0 else 1.0

            if dt_inst >= refresh_rate:
                delta_fuel = current_fuel - self.last_fuel_inst if current_fuel >= self.last_fuel_inst else current_fuel
                delta_dist = current_speed * (dt_inst / 3600.0)

                self.inst_window.append((delta_fuel, delta_dist))
                w_fuel, w_dist = sum(i[0] for i in self.inst_window), sum(i[1] for i in self.inst_window)

                self.stats["inst_cons"] = round((w_fuel / w_dist) * 100.0,
                                                1) if w_dist > 0.001 and current_speed > 3.0 else 0.0

                self.last_fuel_inst, self.last_time_inst = current_fuel, current_time
        elif current_fuel is not None:
            self.last_fuel_inst = current_fuel

        # 3. Accumulateurs de Session
        if self.stats["is_active"]:
            if rpm > 0:
                self._rpm_sum += rpm
                self._rpm_count += 1
            if accel > 0:
                self._accel_sum += accel
                self._accel_count += 1
            elif current_speed > 5.0:
                self._coasting_dist += current_speed * (dt / 3600.0)

            if clutch and not self._is_shifting:
                self._is_shifting, self._shift_start = True, current_time
            elif not clutch and self._is_shifting:
                self._is_shifting = False
                duration = current_time - self._shift_start
                if 0.1 < duration < 5.0:
                    self._shift_time_sum += duration
                    self._shift_count += 1

    def _calc_slow_telemetry(self, current_odo, current_fuel, current_time):
        """Calculs lents (Trip A/B, Autonomie, Maintenance, Sauvegarde)."""
        # Initialisation sécurisée de l'Odo au premier boot
        if self.last_saved_odo == 0.0 and current_odo > 0:
            self.last_saved_odo = self.trip_a_marker = self.trip_b_marker = self.last_revision_odo = current_odo

        # --- Trips Globaux ---
        self.stats["trip_a"] = max(0.0, current_odo - self.trip_a_marker)
        trip_b_dist = max(0.0, current_odo - self.trip_b_marker)
        self.stats["trip_b"] = trip_b_dist

        # --- Conso Moyenne B ---
        if current_fuel is not None:
            if self.last_fuel_avg is not None:
                delta = current_fuel - self.last_fuel_avg if current_fuel >= self.last_fuel_avg else current_fuel
                self.fuel_b_accumulated += delta
            self.last_fuel_avg = current_fuel

        self.stats["avg_cons_b"] = round((self.fuel_b_accumulated / trip_b_dist) * 100.0,
                                         1) if trip_b_dist > 0.05 else 0.0

        # --- Autonomie ---
        fuel_level_pct = self.api._data.get("fuel_level", 100.0)
        remaining_l = (fuel_level_pct / 100.0) * self._tank_capacity
        safe_cons = self.stats["avg_cons_b"] if self.stats["avg_cons_b"] > 0.5 else 6.0
        self.stats["autonomy"] = round((remaining_l / safe_cons) * 100.0)

        # --- Maintenance ---
        dist_depuis_rev = current_odo - self.last_revision_odo
        km_restants = max(0.0, self._revision_interval - dist_depuis_rev)
        self.stats["km_before_service"] = km_restants
        self.stats["service_warning"] = km_restants <= self._revision_warning

        # --- Stats de Session ---
        if self.stats["is_active"]:
            self.stats["distance_km"] = round(max(0.0, current_odo - self._trip_start_odo), 2)
            if current_fuel is not None:
                self.stats["fuel_used_l"] = round(max(0.0, current_fuel - self._trip_start_fuel), 2)
            self.stats["avg_rpm"] = int(self._rpm_sum / self._rpm_count) if self._rpm_count > 0 else 0
            self.stats["coasting_km"] = round(self._coasting_dist, 2)
            self.stats["aggressivity_pct"] = round(self._accel_sum / self._accel_count,
                                                   1) if self._accel_count > 0 else 0.0
            self.stats["shift_time_sec"] = round(self._shift_time_sum / self._shift_count,
                                                 2) if self._shift_count > 0 else 0.0

        # --- Sauvegarde sur disque (Tous les 1 km) ---
        if current_odo - self.last_saved_odo >= 1.0:
            self.storage.set("last_odometer", current_odo)
            self.storage.set("fuel_b_accumulated", self.fuel_b_accumulated)
            self.last_saved_odo = current_odo