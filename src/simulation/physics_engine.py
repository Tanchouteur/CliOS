"""Moteur physique haute fidélité pour simulation automobile CliOS.

Gère la dynamique longitudinale/latérale, la chaîne cinématique (moteur, volant,
embrayage, boîte), la thermique, le modèle électrique et la consommation de carburant.
"""

import math
import time
from src.simulation.models import VehicleParameters, SimulatedVehicleState


class PhysicsEngine:
    """Moteur physique temps réel exécutant des pas d'intégration discrets."""

    def __init__(self, params: VehicleParameters | None = None):
        self.params = params or VehicleParameters()
        self.state = SimulatedVehicleState()

        # Initialisation de l'odomètre et du carburant depuis les paramètres
        self.state.fuel_level_l = self.params.fuel_capacity_l * 0.75
        self.state.engine_temp_c = self.params.ambient_temp_default_c
        self.state.outside_temp_c = self.params.ambient_temp_default_c

        # Variables d'état internes
        self._wheel_speed_ms = 0.0
        self._engine_angular_vel = (self.params.idle_rpm * 2.0 * math.pi) / 60.0
        self._last_flasher_time = time.time()
        self._flasher_state = False
        self._torque_request_filtered = 0.0

    def reset_state(self, odo_km: float = 134690.0, fuel_l: float | None = None, temp_c: float | None = None):
        """Réinitialise l'état physique du véhicule."""
        self.state.speed_kmh = 0.0
        self.state.speed_dashboard_kmh = 0.0
        self.state.acceleration_ms2 = 0.0
        self.state.rpm = self.params.idle_rpm
        self.state.engine_running = True
        self.state.engine_stalled = False
        self.state.ignition_on = True
        self.state.key_run = True
        self.state.key_acc = True
        self.state.odometer_km = odo_km
        self.state.distance_trip_km = 0.0
        self.state.fuel_used_total_l = 0.0
        self.state.selected_gear = 0
        self.state.gear_raw = 100
        self.state.clutch_pedal = 0.0
        self.state.throttle_pedal = 0.0
        self.state.brake_pedal = 0.0
        self.state.handbrake = False
        if fuel_l is not None:
            self.state.fuel_level_l = fuel_l
        if temp_c is not None:
            self.state.engine_temp_c = temp_c
            self.state.outside_temp_c = temp_c

    def update(self, dt: float) -> SimulatedVehicleState:
        """Exécute un pas de simulation physique de durée dt secondes."""
        if dt <= 0.0:
            return self.state

        # 1. Gestion du Clignotant (Flasher 1.5 Hz)
        now = time.time()
        if now - self._last_flasher_time >= 0.35:
            self._flasher_state = not self._flasher_state
            self._last_flasher_time = now

        # 2. Gestion du Contact, Démarreur et Allumage
        if self.state.starter_active:
            self.state.battery_voltage = 10.4 + (0.3 * math.sin(now * 30))
            if self.state.key_run and self.state.ignition_on:
                self.state.rpm += (self.params.starter_rpm - self.state.rpm) * 15.0 * dt
                if self.state.rpm >= self.params.starter_rpm * 0.7:
                    self.state.engine_running = True
                    self.state.engine_stalled = False
        elif self.state.engine_running:
            self.state.battery_voltage = 14.2
        elif self.state.key_run or self.state.key_acc:
            self.state.battery_voltage = 12.4
        else:
            self.state.battery_voltage = 12.6

        # Coupure contact
        if not self.state.key_run or not self.state.ignition_on:
            self.state.engine_running = False

        # 3. Transmission et Rapports
        gear = self.state.selected_gear
        ratio_gear = self.params.gear_ratios.get(gear, 0.0)
        ratio_total = ratio_gear * self.params.final_drive_ratio

        # Encodage code brut Renault boîte de vitesses
        gear_raw_map = {-1: 118, 0: 100, 1: 106, 2: 109, 3: 112, 4: 113, 5: 115, 6: 116}
        self.state.gear_raw = gear_raw_map.get(gear, 100)

        # 4. Modèle d'Embrayage et Régime Moteur
        # clutch_pedal: 0% = embrayé (collé), 100% = débrayé (décollé)
        clutch_engaged_ratio = max(0.0, min(1.0, 1.0 - (self.state.clutch_pedal / 100.0)))

        # Couple demandé par le conducteur (Charge ECU)
        if not self.state.engine_running:
            target_torque_pct = 0.0
        elif gear == 0 or clutch_engaged_ratio < 0.1:
            target_torque_pct = self.state.throttle_pedal * 0.4
        elif self.state.throttle_pedal <= 0.0:
            target_torque_pct = -15.0  # Frein moteur / décélération
        else:
            target_torque_pct = self.state.throttle_pedal

        self._torque_request_filtered += (target_torque_pct - self._torque_request_filtered) * 6.0 * dt
        self.state.driver_torque_request = round(self._torque_request_filtered, 1)

        # Couple maximal et puissance moteur disponible
        max_torque_nm = self.params.torque_at_rpm(self.state.rpm)
        effective_torque_nm = 0.0

        if self.state.engine_running:
            throttle_norm = max(0.0, min(1.0, self.state.throttle_pedal / 100.0))
            if throttle_norm > 0:
                effective_torque_nm = max_torque_nm * (0.15 + 0.85 * throttle_norm)
            else:
                # Frein moteur
                effective_torque_nm = - (self.state.rpm * self.params.engine_braking_coefficient)

        # Calcul du régime cible si moteur libre (Point mort ou débrayé)
        free_target_rpm = self.params.idle_rpm + (self.state.throttle_pedal / 100.0) * (self.params.max_rpm - self.params.idle_rpm)

        # Régime d'entraînement lié aux roues
        wheel_rpm = (abs(self.state.speed_kmh) / (3.6 * 2.0 * math.pi * self.params.wheel_radius_m)) * 60.0
        drivetrain_rpm = wheel_rpm * abs(ratio_total)

        if not self.state.engine_running:
            # Moteur arrêté : RPM chute vers 0 (sauf si entraîné par démarreur ou roues)
            if self.state.starter_active:
                pass
            elif clutch_engaged_ratio > 0.5 and gear != 0 and abs(self.state.speed_kmh) > 5.0:
                # Démarrage à la poussette / entraîné par les roues
                self.state.rpm = max(0.0, drivetrain_rpm)
                if self.state.key_run and self.state.ignition_on:
                    self.state.engine_running = True
                    self.state.engine_stalled = False
            else:
                self.state.rpm = max(0.0, self.state.rpm - (self.state.rpm * 8.0 * dt))

        elif gear == 0 or clutch_engaged_ratio < 0.05:
            # Débrayé ou Point Mort : le moteur tourne librement selon l'accélérateur
            self.state.rpm += (free_target_rpm - self.state.rpm) * 10.0 * dt

        else:
            # Embrayage en prise (partielle ou totale)
            if clutch_engaged_ratio >= 0.85:
                # Prise directe
                if self.state.speed_kmh < 1.0 and self.state.throttle_pedal < 10.0 and gear > 0:
                    # Risque de calage si vitesse nulle et pas de gaz
                    target_rpm = drivetrain_rpm
                    if target_rpm < self.params.stall_rpm:
                        # Moteur cale !
                        self.state.engine_running = False
                        self.state.engine_stalled = True
                        self.state.rpm = 0.0
                    else:
                        self.state.rpm += (target_rpm - self.state.rpm) * 14.0 * dt
                else:
                    target_rpm = max(self.params.idle_rpm, drivetrain_rpm)
                    self.state.rpm += (target_rpm - self.state.rpm) * 14.0 * dt
            else:
                # Patinage progressif
                blended_rpm = (1.0 - clutch_engaged_ratio) * free_target_rpm + clutch_engaged_ratio * max(self.params.idle_rpm, drivetrain_rpm)
                self.state.rpm += (blended_rpm - self.state.rpm) * 10.0 * dt

        # Gestion du Rupteur (Rev Limiter avec effet Bounce)
        self.state.rev_limiter_active = False
        if self.state.rpm >= self.params.redline_rpm and self.state.engine_running:
            self.state.rev_limiter_active = True
            bounce = math.sin(now * 45.0) * 220.0
            self.state.rpm = self.params.redline_rpm + max(-150.0, bounce)
            effective_torque_nm *= 0.15  # Coupure d'injection partielle

        if self.state.rpm > self.params.max_rpm:
            self.state.rpm = self.params.max_rpm - (time.time() % 0.05) * 300.0
            effective_torque_nm = 0.0

        if self.state.engine_running and self.state.rpm < self.params.idle_rpm * 0.8:
            self.state.rpm = self.params.idle_rpm * 0.8

        self.state.engine_torque_nm = round(effective_torque_nm, 1)

        # 5. Forces et Dynamique Longitudinale
        # Force motrice aux roues
        if self.state.engine_running and gear != 0 and clutch_engaged_ratio > 0.05:
            clutch_torque = effective_torque_nm * clutch_engaged_ratio
            wheel_torque = clutch_torque * ratio_total * self.params.drivetrain_efficiency
            traction_force = wheel_torque / self.params.wheel_radius_m
        else:
            traction_force = 0.0

        # Résistance de l'air : 0.5 * rho * Cd * A * v^2
        v_ms = abs(self.state.speed_kmh) / 3.6
        air_density = 1.225
        drag_force = 0.5 * air_density * self.params.drag_coefficient_cd * self.params.frontal_area_m2 * (v_ms ** 2)
        if self.state.speed_kmh < 0:
            drag_force = -drag_force

        # Résistance au roulement : Crr * m * g
        rolling_force = self.params.rolling_resistance_crr * self.params.mass_kg * 9.81 if abs(self.state.speed_kmh) > 0.1 else 0.0
        if self.state.speed_kmh < 0:
            rolling_force = -rolling_force

        # Force de freinage
        brake_norm = max(0.0, min(1.0, self.state.brake_pedal / 100.0))
        brake_force = brake_norm * self.params.brake_max_force_n
        if self.state.handbrake:
            brake_force += self.params.handbrake_force_n

        # Signe du freinage selon le sens de marche
        if self.state.speed_kmh > 0.1:
            total_resistance = drag_force + rolling_force + brake_force
        elif self.state.speed_kmh < -0.1:
            total_resistance = drag_force + rolling_force - brake_force
        else:
            total_resistance = 0.0
            if brake_force > abs(traction_force):
                traction_force = 0.0

        net_force = traction_force - total_resistance
        acceleration = net_force / self.params.mass_kg

        # Mise à jour de la vitesse véhicule
        speed_ms = (self.state.speed_kmh / 3.6) + (acceleration * dt)

        # Arrêt complet si freinage à très basse vitesse
        if abs(speed_ms) < 0.05 and brake_norm > 0.05 and abs(traction_force) < 50.0:
            speed_ms = 0.0
            acceleration = 0.0

        # Empêche de reculer en marche avant juste à cause du frein
        if self.state.speed_kmh > 0.0 and speed_ms < 0.0 and gear >= 0:
            speed_ms = 0.0

        self.state.speed_kmh = round(speed_ms * 3.6, 2)
        # Légère majoration légale de l'indicateur combiné dashboard (+1 à 2 km/h)
        self.state.speed_dashboard_kmh = round(self.state.speed_kmh * 1.02, 1) if self.state.speed_kmh > 2.0 else self.state.speed_kmh
        self.state.acceleration_ms2 = round(acceleration, 2)
        self.state.longitudinal_g = round(acceleration / 9.81, 2)

        # Odomètre
        delta_distance_km = (abs(self.state.speed_kmh) * (dt / 3600.0))
        self.state.odometer_km += delta_distance_km
        self.state.distance_trip_km += delta_distance_km

        # 6. Dynamique Latérale & 4 Roues
        # Différentiel en virage selon l'angle de braquage (Ackermann)
        steer_rad = math.radians(self.state.steering_angle_deg / 16.0)  # Démultiplication colonne direction ~16:1
        base_v = self.state.speed_kmh

        if abs(steer_rad) > 0.01:
            turn_radius = self.params.wheelbase_m / math.tan(abs(steer_rad))
            turn_radius = max(2.5, turn_radius)
            diff_factor = (self.params.track_width_m / (2.0 * turn_radius))

            if self.state.steering_angle_deg > 0:  # Virage à droite
                v_left = base_v * (1.0 + diff_factor)
                v_right = base_v * (1.0 - diff_factor)
            else:  # Virage à gauche
                v_left = base_v * (1.0 - diff_factor)
                v_right = base_v * (1.0 + diff_factor)

            self.state.lateral_g = round(((v_ms ** 2) / turn_radius) / 9.81 * (1 if self.state.steering_angle_deg > 0 else -1), 2)
        else:
            v_left = base_v
            v_right = base_v
            self.state.lateral_g = 0.0

        # Patinage des roues motrices avant à l'accélération
        front_slip = False
        if self.state.throttle_pedal > 75.0 and base_v < 40.0 and gear in (1, 2) and self.state.engine_running:
            front_slip = True
            slip_boost = (self.state.throttle_pedal - 60.0) * 0.4
            v_fl = v_left + slip_boost
            v_fr = v_right + slip_boost
        else:
            v_fl = v_left
            v_fr = v_right

        # Blocage des roues au gros freinage (avec simulation ABS)
        fl_lock = fr_lock = rl_lock = rr_lock = False
        if brake_norm > 0.85 and base_v > 5.0:
            abs_pulse = (math.sin(now * 35.0) > 0.0)
            if not abs_pulse:
                fl_lock = fr_lock = True
                v_fl *= 0.4
                v_fr *= 0.4
                if self.state.handbrake:
                    rl_lock = rr_lock = True
                    v_left *= 0.1
                    v_right *= 0.1

        self.state.wheel_fl_speed = round(max(0.0, v_fl), 1)
        self.state.wheel_fr_speed = round(max(0.0, v_fr), 1)
        self.state.wheel_rl_speed = round(max(0.0, v_left), 1)
        self.state.wheel_rr_speed = round(max(0.0, v_right), 1)

        self.state.wheel_fl_slip = front_slip
        self.state.wheel_fr_slip = front_slip
        self.state.wheel_fl_lock = fl_lock
        self.state.wheel_fr_lock = fr_lock
        self.state.wheel_rl_lock = rl_lock
        self.state.wheel_rr_lock = rr_lock

        # 7. Modèle Thermique Moteur
        if self.state.engine_running:
            # Chaleur générée par combustion + frottement
            heat_power_kw = (effective_torque_nm * self.state.rpm / 9549.0) * 1.6 + (self.state.rpm * 0.003)
            heat_power_kw = max(0.8, heat_power_kw)
        else:
            heat_power_kw = 0.0

        # Refroidissement : convection naturelle + flux d'air calandre + ventilateur
        airflow_cooling = 0.05 + (abs(self.state.speed_kmh) * 0.003)
        if self.state.engine_temp_c >= self.params.fan_start_temp_c:
            self.state.radiator_fan_active = True
        elif self.state.engine_temp_c <= self.params.fan_stop_temp_c:
            self.state.radiator_fan_active = False

        if self.state.radiator_fan_active:
            airflow_cooling += 0.15

        # Thermostat : ouverture progressive au-dessus de thermostat_open_temp_c
        if self.state.engine_temp_c > self.params.thermostat_open_temp_c:
            radiator_factor = min(1.0, (self.state.engine_temp_c - self.params.thermostat_open_temp_c) / 8.0)
            cooling_power_kw = (self.state.engine_temp_c - self.state.outside_temp_c) * airflow_cooling * radiator_factor
        else:
            cooling_power_kw = (self.state.engine_temp_c - self.state.outside_temp_c) * 0.02

        temp_delta = (heat_power_kw - cooling_power_kw) * (dt / (self.params.engine_heat_capacity_j_k / 1000.0))
        self.state.engine_temp_c = round(self.state.engine_temp_c + temp_delta, 1)

        # 8. Modèle Carburant & Économie
        if self.state.engine_running:
            power_kw = max(0.0, effective_torque_nm * self.state.rpm / 9549.0)
            fuel_rate_lph = self.params.base_fuel_rate_lph + (power_kw * self.params.bsfc_g_kwh) / (self.params.fuel_density_kg_l * 1000.0)
            if self.state.throttle_pedal <= 0.0 and self.state.rpm > 1400.0:
                # Coupure d'injection en décélération
                fuel_rate_lph = 0.0
        else:
            fuel_rate_lph = 0.0

        self.state.fuel_flow_lph = round(fuel_rate_lph, 2)
        fuel_delta_l = (fuel_rate_lph / 3600.0) * dt
        self.state.fuel_used_total_l += fuel_delta_l
        self.state.fuel_level_l = max(0.0, self.state.fuel_level_l - fuel_delta_l)

        if self.state.speed_kmh > 4.0:
            self.state.instant_l_100km = round((fuel_rate_lph / self.state.speed_kmh) * 100.0, 1)
        else:
            self.state.instant_l_100km = 0.0

        return self.state
