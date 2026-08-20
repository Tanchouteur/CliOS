"""Modèles de données et paramètres du véhicule pour la simulation physique et CAN."""

from dataclasses import dataclass, field
import math


@dataclass
class VehicleParameters:
    """Paramètres mécaniques, aérodynamiques et thermiques du véhicule."""

    # Identité
    label: str = "Clio 3 RS 2.0 16V"

    # Masse et géométrie
    mass_kg: float = 1240.0
    wheelbase_m: float = 2.585
    track_width_m: float = 1.520
    wheel_radius_m: float = 0.302  # Pneus 215/45 R17 -> ~0.302m
    frontal_area_m2: float = 2.15
    drag_coefficient_cd: float = 0.35
    rolling_resistance_crr: float = 0.013

    # Moteur & Courbes
    idle_rpm: float = 900.0
    redline_rpm: float = 7000.0
    max_rpm: float = 7500.0
    stall_rpm: float = 450.0
    engine_inertia: float = 0.18  # kg·m² (inertie volant moteur + équipage mobile)
    engine_braking_coefficient: float = 0.025  # Couple de frein moteur par RPM (N·m/RPM)
    starter_rpm: float = 260.0
    performance_curve: list[tuple[float, float]] = field(
        default_factory=lambda: [
            (900.0, 95.0),
            (1500.0, 130.0),
            (2500.0, 165.0),
            (3500.0, 185.0),
            (4500.0, 202.0),
            (5550.0, 215.0),
            (6500.0, 208.0),
            (7000.0, 201.0),
            (7250.0, 194.0),
            (7500.0, 180.0),
        ]
    )

    # Transmission
    gear_ratios: dict[int, float] = field(
        default_factory=lambda: {
            -1: -3.54,  # Marche arrière (Reverse)
            0: 0.0,     # Point mort (Neutral)
            1: 3.73,    # 1ère
            2: 2.05,    # 2ème
            3: 1.39,    # 3ème
            4: 1.03,    # 4ème
            5: 0.82,    # 5ème
            6: 0.69,    # 6ème (si applicable)
        }
    )
    final_drive_ratio: float = 4.31  # Rapport de pont / différentiel
    drivetrain_efficiency: float = 0.90  # Rendement chaîne cinématique
    clutch_max_torque_nm: float = 350.0  # Capacité en couple de l'embrayage

    # Freinage
    brake_max_force_n: float = 14000.0  # Force de freinage max totale (~1.15 G)
    front_brake_bias: float = 0.65       # Répartition avant / arrière (65% AV, 35% AR)
    handbrake_force_n: float = 4500.0    # Force frein à main (roues AR)

    # Réservoir & Consommation
    fuel_capacity_l: float = 55.0
    fuel_reserve_l: float = 8.25
    fuel_density_kg_l: float = 0.745
    base_fuel_rate_lph: float = 0.9  # Conso ralenti en L/h
    bsfc_g_kwh: float = 270.0        # Consommation spécifique moyenne (g / kW·h)

    # Thermique
    ambient_temp_default_c: float = 20.0
    thermostat_open_temp_c: float = 83.0
    fan_start_temp_c: float = 96.0
    fan_stop_temp_c: float = 90.0
    engine_heat_capacity_j_k: float = 45000.0  # Capacité thermique bloc + eau
    warning_temp_c: float = 105.0
    critical_temp_c: float = 115.0

    @classmethod
    def from_config(cls, config: dict) -> "VehicleParameters":
        """Construit l'instance à partir d'un dictionnaire de configuration véhicule."""
        engine_cfg = config.get("engine", {})
        tach_cfg = config.get("tachometer", {})
        fuel_cfg = config.get("fuel", {})
        temp_cfg = config.get("engine_temp", {})
        trans_cfg = config.get("transmission", {})

        # Courbe de couple
        curve = []
        for pt in engine_cfg.get("performance_curve", []):
            if isinstance(pt, dict) and "rpm" in pt and "torque_nm" in pt:
                curve.append((float(pt["rpm"]), float(pt["torque_nm"])))
        if not curve:
            max_t = float(engine_cfg.get("max_torque_nm", 200.0))
            curve = [(800.0, max_t * 0.5), (2000.0, max_t * 0.9), (4000.0, max_t), (6000.0, max_t * 0.7)]
        curve.sort(key=lambda x: x[0])

        # Rapports de boîte
        raw_ratios = trans_cfg.get("ratios", {})
        gear_ratios = {-1: -3.54, 0: 0.0}

        r_wheel = 0.302
        final_drive = 4.31
        factor_rpm_to_gear = (2 * math.pi * r_wheel * 60.0) / (1000.0 * final_drive)

        for k, v in raw_ratios.items():
            try:
                gear_num = int(k)
                v_flt = float(v)
                if v_flt > 15.0:  # Format RPM / (km/h)
                    gear_ratio = v_flt * factor_rpm_to_gear
                else:
                    gear_ratio = v_flt
                gear_ratios[gear_num] = gear_ratio
            except (ValueError, TypeError):
                continue

        if 1 not in gear_ratios:
            gear_ratios = {-1: -3.54, 0: 0.0, 1: 3.73, 2: 2.05, 3: 1.39, 4: 1.03, 5: 0.82}

        fuel_max = float(fuel_cfg.get("max_liters", 55.0))
        fuel_reserve = fuel_max * float(fuel_cfg.get("reserve_percentage", 0.15))

        return cls(
            label=str(engine_cfg.get("label", "Clio Vehicle")),
            idle_rpm=float(tach_cfg.get("idle_rpm", 900.0)),
            redline_rpm=float(tach_cfg.get("redline_rpm", 6500.0)),
            max_rpm=float(tach_cfg.get("max_rpm", 7500.0)),
            performance_curve=curve,
            gear_ratios=gear_ratios,
            final_drive_ratio=final_drive,
            wheel_radius_m=r_wheel,
            fuel_capacity_l=fuel_max,
            fuel_reserve_l=fuel_reserve,
            warning_temp_c=float(temp_cfg.get("warning", 105.0)),
        )

    def torque_at_rpm(self, rpm: float) -> float:
        """Retourne le couple moteur maximal disponible au régime donné par interpolation linéaire."""
        if not self.performance_curve:
            return 200.0
        rpm = max(0.0, float(rpm))
        if rpm <= self.performance_curve[0][0]:
            return self.performance_curve[0][1]
        for left, right in zip(self.performance_curve, self.performance_curve[1:]):
            if rpm <= right[0]:
                fraction = (rpm - left[0]) / max(1.0, right[0] - left[0])
                return left[1] + (right[1] - left[1]) * fraction
        return self.performance_curve[-1][1]


@dataclass
class SimulatedVehicleState:
    """État complet simulé en temps réel du véhicule."""

    # 1. Contact & Alimentation
    key_acc: bool = True
    key_run: bool = True
    starter_active: bool = False
    ignition_on: bool = True
    engine_running: bool = True
    engine_stalled: bool = False
    battery_voltage: float = 14.2  # Volts

    # 2. Commandes Pilote (Entrées)
    throttle_pedal: float = 0.0   # 0.0 à 100.0 %
    brake_pedal: float = 0.0      # 0.0 à 100.0 %
    clutch_pedal: float = 0.0     # 0.0 (embrayé) à 100.0 % (débrayé)
    handbrake: bool = False
    selected_gear: int = 0        # -1 = R, 0 = N, 1..6
    steering_angle_deg: float = 0.0  # Degrés (-540.0 à +540.0)
    steering_speed_dps: float = 0.0  # Degrés / sec

    # 3. Groupe Motopropulseur (Sorties)
    rpm: float = 900.0
    driver_torque_request: float = 0.0  # % (-100 à +100)
    torque_available: int = 100         # %
    engine_torque_nm: float = 0.0       # Couple effectif généré
    gear_raw: int = 100                 # Code brut Renault (100=N, 106=1, 109=2, 112=3, 113=4, 115=5, 118=R)
    clutch_slip: float = 0.0            # Différence de vitesse de rotation (rad/s)
    rev_limiter_active: bool = False

    # 4. Véhicule & Dynamique
    speed_kmh: float = 0.0
    speed_dashboard_kmh: float = 0.0
    acceleration_ms2: float = 0.0
    longitudinal_g: float = 0.0
    lateral_g: float = 0.0
    odometer_km: float = 134690.0
    distance_trip_km: float = 0.0

    # 5. Roues (Individuelles)
    wheel_fl_speed: float = 0.0
    wheel_fr_speed: float = 0.0
    wheel_rl_speed: float = 0.0
    wheel_rr_speed: float = 0.0
    wheel_fl_slip: bool = False
    wheel_fr_slip: bool = False
    wheel_rl_slip: bool = False
    wheel_rr_slip: bool = False
    wheel_fl_lock: bool = False
    wheel_fr_lock: bool = False
    wheel_rl_lock: bool = False
    wheel_rr_lock: bool = False

    # 6. Thermique
    engine_temp_c: float = 85.0
    outside_temp_c: float = 21.0
    radiator_fan_active: bool = False

    # 7. Carburant & Économie
    fuel_level_l: float = 42.0
    fuel_used_total_l: float = 0.0
    fuel_flow_lph: float = 0.9
    instant_l_100km: float = 0.0

    # 8. Carrosserie, Éclairage & Habitacle
    pos_lights: bool = False
    low_beam: bool = False
    high_beam: bool = False
    fog_front: bool = False
    fog_rear: bool = False
    turn_left: bool = False
    turn_right: bool = False
    hazard: bool = False
    brightness_pct: int = 100

    door_fl_open: bool = False
    door_fr_open: bool = False
    door_rl_open: bool = False
    door_rr_open: bool = False
    trunk_open: bool = False
    doors_locked: bool = False
    trunk_locked: bool = False
    driver_unbelted: bool = False
    passenger_disabled: bool = False

    comodo_up: bool = False
    comodo_down: bool = False

    # 9. Aides à la conduite & Régulateur
    regulateur_mode: int = 0    # 0 = Arrêt, 1 = Régulateur, 2 = Limiteur
    regulateur_statut: int = 0  # 0 = Off, 1 = Actif, 2 = En pause
    vitesse_regulateur_kmh: int = 0
    glow_plug_status: int = 0
    vehicle_age_min: int = 450000

    # 10. Diagnostic & DTCs OBD2
    active_dtcs: list[str] = field(default_factory=list)
