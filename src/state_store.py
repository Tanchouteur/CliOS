"""Thread-safe, domain-oriented runtime state for the vehicle.

The flat snapshot is intentionally kept as a compatibility view. New code should
publish to/read from domains so ownership and freshness remain explicit.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable


VEHICLE_DOMAINS = (
    "powertrain",
    "motion",
    "wheels",
    "body",
    "assistance",
    "dynamics",
    "environment",
)


@dataclass(frozen=True)
class SignalMetadata:
    source: str
    domain: str
    updated_monotonic: float
    unit: str | None = None
    quality: str = "VALID"
    ttl_s: float | None = None


_EXPLICIT_DOMAINS = {
    # Powertrain
    "rpm": "powertrain", "engine_temp": "powertrain", "fuel_used": "powertrain",
    "fuel_level": "powertrain", "accel_pos": "powertrain", "throttle": "powertrain",
    "throttle_pct": "powertrain", "accel_computed": "powertrain",
    "driver_torque_request": "powertrain", "torque_available": "powertrain",
    "engine_load": "powertrain", "engine_load_pct": "powertrain",
    "estimated_torque_nm": "powertrain", "estimated_power_kw": "powertrain",
    "estimated_power_hp": "powertrain", "engine_light": "powertrain",
    "glow_plug_status": "powertrain", "oil_warning": "powertrain",
    "battery_warning": "powertrain", "ignition_on": "powertrain",
    "key_run": "powertrain", "key_acc": "powertrain",
    # Motion / transmission
    "speed": "motion", "speed_dashboard": "motion", "odometer": "motion",
    "gear": "motion", "reverse": "motion", "reverse_engaged": "motion",
    "brake": "motion", "brake_pressed": "motion", "clutch": "motion",
    "parking_brake": "motion", "handbrake": "motion", "handbrake_status": "motion",
    # Assistance
    "regulateur_mode": "assistance", "regulateur_statut": "assistance",
    "vitesse_regulateur": "assistance", "abs_error": "assistance",
    "esp_active": "assistance", "stop_warning": "assistance",
    "service_warning": "assistance",
    # Environment
    "outside_temp": "environment", "cabin_db_spl": "environment",
    "cabin_noise_db": "environment", "cabin_freq_hz": "environment",
    "audio_db_text": "environment",
    # Session
    "session_state": "session",
    # Calibration
    "calibration_state": "calibration", "calibration_gear": "calibration",
    "calibration_ratio": "calibration", "calibration_message": "calibration",
}

_UNITS = {
    "speed": "km/h", "speed_dashboard": "km/h", "odometer": "km",
    "rpm": "rpm", "engine_temp": "degC", "outside_temp": "degC",
    "fuel_used": "L", "fuel_level": "L", "accel_pos": "%",
    "throttle": "%", "throttle_pct": "%", "engine_load": "%",
    "engine_load_pct": "%", "driver_torque_request": "%",
    "torque_available": "%", "estimated_torque_nm": "N.m",
    "estimated_power_kw": "kW", "estimated_power_hp": "hp",
    "steering_angle": "deg", "steering_speed": "deg/s",
    "cabin_db_spl": "dB SPL", "cabin_freq_hz": "Hz",
}


def infer_domain(key: str) -> str:
    """Return the stable business domain owning a signal."""
    if key in _EXPLICIT_DOMAINS:
        return _EXPLICIT_DOMAINS[key]
    if key.startswith("wheel_") or key.startswith("wheel"):
        return "wheels"
    if key.startswith("diag_"):
        return "diagnostics"
    if key.startswith("calibration_"):
        return "calibration"
    if key.startswith(("app_", "system_", "storage_", "usb_", "can_")):
        return "system"
    if key.startswith(("door_", "trunk_")) or key in {
        "doors_locked", "driver_unbelted", "passenger_disabled", "pos_lights",
        "low_beam", "high_beam", "fog_front", "fog_rear", "turn_left",
        "turn_right", "indicator_left", "indicator_right", "brightness",
    }:
        return "body"
    if key.startswith(("slip_", "lock_")) or key in {
        "steering_angle", "steering_speed", "understeer", "oversteer",
    }:
        return "dynamics"
    return "misc"


class VehicleStateStore:
    """Single source of truth with atomic domain and compatibility snapshots."""

    def __init__(self, initial: dict[str, Any] | None = None):
        self._lock = threading.RLock()
        self._domains: dict[str, dict[str, Any]] = {}
        self._flat: dict[str, Any] = {}
        self._metadata: dict[str, SignalMetadata] = {}
        self._revision = 0
        self._domain_revisions: dict[str, int] = {}
        if initial:
            self.update(initial, source="bootstrap")

    def update(
        self,
        values: dict[str, Any],
        *,
        source: str,
        domain: str | None = None,
        timestamp: float | None = None,
        quality: str = "VALID",
        units: dict[str, str] | None = None,
        ttl_s: float | None = None,
    ) -> int:
        if not isinstance(values, dict):
            raise TypeError("values must be a dict")
        if not values:
            return self.revision

        updated_at = time.monotonic() if timestamp is None else float(timestamp)
        touched: set[str] = set()
        with self._lock:
            for key, value in values.items():
                key = str(key)
                owner = domain or infer_domain(key)
                self._domains.setdefault(owner, {})[key] = value
                self._flat[key] = value
                self._metadata[key] = SignalMetadata(
                    source=source,
                    domain=owner,
                    updated_monotonic=updated_at,
                    unit=(units or {}).get(key, _UNITS.get(key)),
                    quality=quality,
                    ttl_s=ttl_s,
                )
                touched.add(owner)
            self._revision += 1
            for owner in touched:
                self._domain_revisions[owner] = self._revision
            return self._revision

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def flat_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._flat.copy()

    def domain_snapshot(
        self,
        domains: Iterable[str] | None = None,
        *,
        include_meta: bool = True,
    ) -> dict[str, Any]:
        with self._lock:
            selected = tuple(domains) if domains is not None else tuple(self._domains)
            snapshot = {name: self._domains.get(name, {}).copy() for name in selected}
            if include_meta:
                snapshot["_meta"] = {
                    "revision": self._revision,
                    "domain_revisions": {
                        name: self._domain_revisions.get(name, 0) for name in selected
                    },
                }
            return snapshot

    def metadata_snapshot(self) -> dict[str, dict[str, Any]]:
        now = time.monotonic()
        with self._lock:
            return {
                key: {
                    "source": meta.source,
                    "domain": meta.domain,
                    "unit": meta.unit,
                    "quality": (
                        "STALE"
                        if meta.quality == "VALID" and meta.ttl_s is not None
                        and now - meta.updated_monotonic > meta.ttl_s
                        else meta.quality
                    ),
                    "age_ms": max(0.0, (now - meta.updated_monotonic) * 1000.0),
                    "ttl_ms": None if meta.ttl_s is None else meta.ttl_s * 1000.0,
                }
                for key, meta in self._metadata.items()
            }

    def signal_age(self, key: str) -> float | None:
        with self._lock:
            meta = self._metadata.get(key)
            if meta is None:
                return None
            return max(0.0, time.monotonic() - meta.updated_monotonic)

    def is_fresh(self, key: str, max_age_s: float) -> bool:
        age = self.signal_age(key)
        return age is not None and age <= max_age_s
