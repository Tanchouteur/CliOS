import threading
import time
import os
from collections import deque

from src.storage import PersistentStorage


class VehicleAPI:
    def __init__(self, config: dict):
        self._data = {}
        # Facteur de lissage exponentiel (1.0 = signal brut, 0.1 = filtrage fort)
        self._smoothing_factor = 1

        # Registres d'état pour les calculs d'intégration temporelle
        self.last_fuel = None
        self.last_time = None

        # Mise en cache des paramètres de transmission
        trans_config = config.get("transmission", {})
        self._gear_ratios = trans_config.get("ratios", {})
        self._gear_tolerance = trans_config.get("tolerance", 5.0)

        # Configuration des intervalles de maintenance
        revision_config = config.get("maintenance", {}).get("revision", {})
        self._revision_interval = revision_config.get("interval_km", 20000)
        self._revision_warning = revision_config.get("warning_threshold_km", 2000)

        self._tank_capacity = config.get("tank_capacity", 50.0)

        # Initialisation de l'interface de stockage non volatile
        self.storage = PersistentStorage()
        self.trip_a_marker = self.storage.get("trip_a_marker", 0.0)
        self.trip_b_marker = self.storage.get("trip_b_marker", 0.0)
        self.last_saved_odo = self.storage.get("last_odometer", 0.0)
        self.fuel_b_accumulated = self.storage.get("fuel_b_accumulated", 0.0)
        self.last_revision_odo = self.storage.get("last_revision_odo", 0.0)

        # Indicateurs d'état système
        self.is_starting_up = False
        self.critical_engine_error = False

        # --- Initialisation du dictionnaire de données ---
        self._data["odometer"] = self.last_saved_odo
        self._data["fuel_level"] = 100.0
        self._data["autonomy"] = 0.0
        self._data["connexion_obd_moteur"] = False

        self._data["trip_a"] = max(0.0, self.last_saved_odo - self.trip_a_marker)

        trip_b_dist = max(0.0, self.last_saved_odo - self.trip_b_marker)
        self._data["trip_b"] = trip_b_dist

        # Pré-calcul des métriques de consommation si la distance est significative
        if trip_b_dist > 0.05:
            self._data["avg_cons_b"] = (self.fuel_b_accumulated / trip_b_dist) * 100.0
        else:
            self._data["avg_cons_b"] = 0.0

        distance_depuis_revision = self.last_saved_odo - self.last_revision_odo
        km_restants = self._revision_interval - distance_depuis_revision
        self._data["km_before_service"] = max(0.0, km_restants)
        self._data["service_warning"] = km_restants <= self._revision_warning

        self.last_fuel_avg = None
        self.last_time_avg = time.time()

        # Tampon circulaire (FIFO) pour la moyenne mobile de consommation instantanée
        self.inst_window = deque(maxlen=10)
        self.last_fuel_inst = None
        self.last_time_inst = None

    def update(self, new_data: dict):
        if self.is_starting_up:
            return

        current_time = time.time()

        # 1. Intégration et filtrage passe-bas des nouvelles données
        for key, value in new_data.items():
            if key in self._data and type(value) in (int, float) and key not in ["odometer", "fuel_used", "trip_a",
                                                                                 "trip_b", "km_before_service"]:
                old_val = self._data[key]
                self._data[key] = old_val + self._smoothing_factor * (value - old_val)
            else:
                self._data[key] = value

        # 2. Extraction des variables d'état courantes
        current_speed = self._data.get("speed")
        current_odo = self._data.get("odometer")
        rpm = self._data.get("rpm", 0)
        clutch = self._data.get("clutch", False)
        reverse = self._data.get("reverse_engaged", False)
        ignition = self._data.get("ignition_on", False) or self._data.get("key_run", False)

        # 3. Évaluation des états d'alerte simples
        if self.critical_engine_error:
            self._data["engine_light"] = "RED"
        elif ignition and rpm < 300:
            self._data["engine_light"] = "ORANGE"
        else:
            self._data["engine_light"] = "OFF"

        raw_fuel = new_data.get("fuel_used")
        current_odo = self._data.get("odometer")
        accel_pos = self._data.get("accel_pos", 0.0)

        # 4. Exécution conditionnelle des sous-routines de calcul
        if raw_fuel is not None and current_speed is not None:
            self._calculate_instant_consumption(current_time, raw_fuel, current_speed, accel_pos)
            self._update_average_consumption(current_time, raw_fuel)

        if current_speed is not None:
            self._data["gear"] = self.calculate_gear(rpm, current_speed, clutch, reverse)

        if current_odo is not None:
            self._calculate_distances_and_maintenance(current_odo)

    # --- Méthodes de Calcul Métier ---

    def _calculate_distances_and_maintenance(self, current_odo):
        """Met à jour les odomètres partiels, la maintenance et gère la persistance de l'état."""

        # Initialisation des références absolues en cas de corruption ou d'absence de données sauvegardées
        if self.last_saved_odo == 0.0 and current_odo > 0:
            self.last_saved_odo = current_odo
            if self.trip_a_marker == 0.0: self.trip_a_marker = current_odo
            if self.trip_b_marker == 0.0: self.trip_b_marker = current_odo
            if self.last_revision_odo == 0.0:
                self.last_revision_odo = current_odo
                self.storage.set("last_revision_odo", current_odo)

        # Calcul des distances relatives
        self._data["trip_a"] = max(0.0, current_odo - self.trip_a_marker)

        trip_b_dist = max(0.0, current_odo - self.trip_b_marker)
        self._data["trip_b"] = trip_b_dist

        # Actualisation du rendement moyen global
        if trip_b_dist > 0.05:
            self._data["avg_cons_b"] = (self.fuel_b_accumulated / trip_b_dist) * 100.0
        else:
            self._data["avg_cons_b"] = 0.0

        current_fuel_level = self._data.get("fuel_level", 100.0)
        self._calculate_autonomy(current_fuel_level, self._data["avg_cons_b"])

        # Évaluation des échéances de maintenance
        distance_depuis_revision = current_odo - self.last_revision_odo
        km_restants = self._revision_interval - distance_depuis_revision
        self._data["km_before_service"] = max(0.0, km_restants)
        self._data["service_warning"] = km_restants <= self._revision_warning

        # Déclenchement de la persistance cyclique (seuil d'écriture : 1.0 km)
        if current_odo - self.last_saved_odo >= 1.0:
            self.storage.set("last_odometer", current_odo)
            self.storage.set("fuel_b_accumulated", self.fuel_b_accumulated)
            self.last_saved_odo = current_odo

    def _update_average_consumption(self, current_time, current_fuel):
        """Intègre le différentiel de volume de carburant à l'accumulateur global selon un intervalle temporel."""
        if self.last_fuel_avg is None:
            self.last_fuel_avg = current_fuel
            return

        # Validation de la période d'échantillonnage
        if current_time - self.last_time_avg >= 1.0:
            if current_fuel >= self.last_fuel_avg:
                delta_fuel = current_fuel - self.last_fuel_avg
            else:
                delta_fuel = current_fuel  # Gestion de la réinitialisation du compteur source

            self.fuel_b_accumulated += delta_fuel

            self.last_fuel_avg = current_fuel
            self.last_time_avg = current_time

    def _calculate_instant_consumption(self, current_time, current_fuel, current_speed, accel_pos):
        """Calcule la consommation instantanée via une moyenne mobile à fréquence d'échantillonnage variable."""
        if self.last_fuel_inst is None or self.last_time_inst is None:
            self.last_fuel_inst = current_fuel
            self.last_time_inst = current_time
            return

        dt = current_time - self.last_time_inst
        if dt <= 0: return

        # Ajustement dynamique de la période d'échantillonnage selon la charge moteur
        refresh_rate = 0.2 if accel_pos > 5.0 else 1.0

        if dt >= refresh_rate:
            # Calcul du différentiel de carburant
            if current_fuel >= self.last_fuel_inst:
                delta_fuel = current_fuel - self.last_fuel_inst
            else:
                delta_fuel = current_fuel

            # Conversion de la vitesse angulaire/linéaire en différentiel de distance (km)
            delta_dist = current_speed * (dt / 3600.0)

            # Insertion du tuple de mesure dans le tampon circulaire
            self.inst_window.append((delta_fuel, delta_dist))

            # Agrégation et sommation des échantillons de la fenêtre courante
            window_fuel = sum(item[0] for item in self.inst_window)
            window_dist = sum(item[1] for item in self.inst_window)

            # Résolution finale du ratio de consommation (L/100km)
            if window_dist > 0.001 and current_speed > 3.0:
                self._data["inst_cons"] = (window_fuel / window_dist) * 100.0
            else:
                self._data["inst_cons"] = 0.0

            self.last_fuel_inst = current_fuel
            self.last_time_inst = current_time

    def _calculate_autonomy(self, fuel_level_pct, avg_cons):
        """Estime l'autonomie kilométrique restante basée sur la consommation moyenne."""
        remaining_liters = (fuel_level_pct / 100.0) * self._tank_capacity
        safe_cons = avg_cons if avg_cons > 0.5 else 6.0
        autonomy_km = (remaining_liters / safe_cons) * 100.0
        self._data["autonomy"] = round(max(0.0, autonomy_km))

    def calculate_gear(self, rpm, speed, clutch_pressed, reverse_engaged):
        """Détermine le rapport de transmission engagé par rapprochement vectoriel des ratios régime/vitesse."""
        if reverse_engaged: return "R"
        if clutch_pressed or speed < 3.0: return "N"

        current_ratio = rpm / speed
        best_gear = "N"
        smallest_diff = float('inf')

        for gear_name, target_ratio in self._gear_ratios.items():
            diff = abs(current_ratio - target_ratio)
            if diff <= self._gear_tolerance and diff < smallest_diff:
                smallest_diff = diff
                best_gear = gear_name

        return best_gear

    # --- Commandes Utilisateur ---

    def reset_trip_a(self):
        current_odo = self._data.get("odometer", 0.0)
        self.trip_a_marker = current_odo
        self.storage.set("trip_a_marker", current_odo)

    def reset_trip_b(self):
        current_odo = self._data.get("odometer", 0.0)
        self.trip_b_marker = current_odo
        self.fuel_b_accumulated = 0.0
        self.storage.set("trip_b_marker", current_odo)
        self.storage.set("fuel_b_accumulated", 0.0)

    def reset_maintenance(self):
        current_odo = self._data.get("odometer", 0.0)
        self.last_revision_odo = current_odo
        self.storage.set("last_revision_odo", current_odo)
        self._data["km_before_service"] = self._revision_interval

    # --- Séquences d'Initialisation ---

    def run_startup_sequence(self, duration_sec=2.0):
        """Exécute la routine de vérification matérielle visuelle (Sweep) au démarrage."""
        self.is_starting_up = True

        def sequence():
            time.sleep(1.0)
            voyants_booleens = [
                "brake", "clutch", "comodo_down", "comodo_up", "door_fl_open",
                "door_fr_open", "door_rl_open", "door_rr_open", "doors_locked",
                "driver_unbelted", "fog_front", "fog_rear", "high_beam",
                "ignition_on", "key_acc", "key_run", "low_beam", "passenger_disabled",
                "pos_lights", "reverse", "reverse_engaged", "trunk_locked",
                "trunk_open", "turn_left", "turn_right", "oil_warning",
                "battery_warning", "abs_error", "esp_active",
                "stop_warning", "service_warning"
            ]

            # Phase d'activation maximale
            for v in voyants_booleens: self._data[v] = True
            self._data["brightness"] = 100.0
            self._data["gear"] = "8"

            steps = 50
            sleep_time = (duration_sec / 2.0) / steps

            self._data["engine_light"] = "RED"

            # Interpolation linéaire montante
            for i in range(steps + 1):
                fraction = i / steps
                self._data["rpm"] = fraction * 7000.0
                self._data["speed"] = fraction * 200.0
                self._data["accel_pos"] = fraction * 100.0
                self._data["engine_temp"] = -20.0 + (fraction * 150.0)
                self._data["inst_cons"] = fraction * 30.0
                time.sleep(sleep_time)

            time.sleep(0.3)

            # Interpolation linéaire descendante
            for i in range(steps, -1, -1):
                fraction = i / steps
                self._data["rpm"] = fraction * 7000.0
                self._data["speed"] = fraction * 200.0
                self._data["accel_pos"] = fraction * 100.0
                self._data["engine_temp"] = -20.0 + (fraction * 150.0)
                self._data["inst_cons"] = fraction * 30.0
                time.sleep(sleep_time)

            # Rétablissement de l'état nominal
            for v in voyants_booleens: self._data[v] = False
            self._data["gear"] = "N"
            self._data["accel_pos"] = 0.0
            self._data["engine_temp"] = 0.0

            self.is_starting_up = False
            self._data["engine_light"] = "ORANGE"

        threading.Thread(target=sequence, daemon=True).start()

    def set_connection_status(self, status: bool):
        """Met à jour le statut de liaison avec le contrôleur matériel pour l'IHM."""
        if self._data.get("connexion_obd_moteur") != status:
            self._data["connexion_obd_moteur"] = status