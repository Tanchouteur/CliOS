"""Canonical signal ownership for decoded CAN data.

Runtime services publish to an explicit domain. The catalog is deliberately
strict for CAN: a newly decoded signal must be assigned before it can enter the
runtime state.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalDefinition:
    domain: str
    unit: str | None = None
    ttl_s: float | None = 1.5


SIGNALS: dict[str, SignalDefinition] = {}


def _register(domain: str, names: str, unit: str | None = None, ttl_s: float | None = 1.5):
    for name in names.split():
        SIGNALS[name] = SignalDefinition(domain, unit, ttl_s)


_register("powertrain", "rpm", "rpm")
_register("powertrain", "engine_temp", "degC")
_register("powertrain", "fuel_used fuel_level", "L")
_register("powertrain", "accel_pos accel_computed driver_torque_request torque_available", "%")
_register("powertrain", "glow_plug_status ignition_on key_acc key_run")

_register("motion", "speed speed_dashboard", "km/h")
_register("motion", "distance odometer odometer2", "km")
_register("motion", "brake brake_pressed clutch handbrake reverse reverse_engaged gear_raw")

_register("wheels", "wheel_fl_speed wheel_fr_speed wheel_rl_speed wheel_rr_speed", "km/h")
_register("wheels", "wheel_fl_status wheel_fr_status wheel_rl_status wheel_rr_status")

_register("body", "door_fl_open door_fr_open door_rl_open door_rr_open trunk_open")
_register("body", "doors_locked trunk_locked driver_unbelted passenger_disabled")
_register("body", "pos_lights low_beam high_beam fog_front fog_rear turn_left turn_right")
_register("body", "brightness", "%")

_register("assistance", "regulateur_mode regulateur_statut")
_register("assistance", "vitesse_regulateur", "km/h")
_register("dynamics", "steering_angle", "deg")
_register("dynamics", "steering_speed", "deg/s")
_register("environment", "outside_temp", "degC")
_register("controls", "comodo_down comodo_up")
_register("system", "vehicle_age_min", "min", ttl_s=None)


def definition_for(signal_name: str) -> SignalDefinition:
    try:
        return SIGNALS[signal_name]
    except KeyError as exc:
        raise KeyError(f"Signal CAN non catalogue: {signal_name}") from exc
