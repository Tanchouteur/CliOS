"""Strict domain-oriented runtime state."""

from __future__ import annotations

import threading
import time
import copy
from dataclasses import dataclass, field
from typing import Any


DOMAINS = (
    "powertrain", "motion", "wheels", "body", "assistance", "dynamics",
    "environment", "controls", "alerts", "trip", "diagnostics", "session",
    "calibration", "system",
)
VEHICLE_DOMAINS = DOMAINS[:9]


@dataclass(frozen=True)
class StatePatch:
    domain: str
    values: dict[str, Any]
    source: str
    ttl_s: float | None = None
    units: dict[str, str] = field(default_factory=dict)
    timestamp: float | None = None


@dataclass(frozen=True)
class RuntimeSnapshot:
    domains: dict[str, dict[str, Any]]
    revision: int
    domain_revisions: dict[str, int]

    def domain(self, name: str) -> dict[str, Any]:
        if name not in DOMAINS:
            raise KeyError(f"Domaine runtime inconnu: {name}")
        return self.domains[name]

    def as_dict(self, selected: tuple[str, ...] | None = None) -> dict[str, Any]:
        names = selected or DOMAINS
        revisions = {name: self.domain_revisions.get(name, 0) for name in names}
        result = {name: self.domains[name].copy() for name in names}
        result["_meta"] = {
            "revision": max(revisions.values(), default=0),
            "domain_revisions": revisions,
        }
        return result


@dataclass(frozen=True)
class SignalMetadata:
    source: str
    updated_monotonic: float
    unit: str | None
    quality: str
    ttl_s: float | None


class VehicleStateStore:
    """Single source of truth; all writes require an explicit domain."""

    def __init__(self):
        self._lock = threading.RLock()
        self._domains = {domain: {} for domain in DOMAINS}
        self._metadata = {domain: {} for domain in DOMAINS}
        self._revision = 0
        self._domain_revisions = {domain: 0 for domain in DOMAINS}

    def publish(self, patch: StatePatch) -> int:
        return self.publish_many((patch,))

    def publish_many(self, patches) -> int:
        patches = tuple(patches)
        if not patches:
            return self.revision
        for patch in patches:
            if patch.domain not in DOMAINS:
                raise ValueError(f"Domaine runtime inconnu: {patch.domain}")
            if not isinstance(patch.values, dict):
                raise TypeError("StatePatch.values doit être un dictionnaire")

        with self._lock:
            touched = set()
            for patch in patches:
                updated_at = time.monotonic() if patch.timestamp is None else float(patch.timestamp)
                domain_values = self._domains[patch.domain]
                domain_meta = self._metadata[patch.domain]
                for key, value in patch.values.items():
                    key = str(key)
                    domain_values[key] = copy.deepcopy(value)
                    domain_meta[key] = SignalMetadata(
                        source=patch.source,
                        updated_monotonic=updated_at,
                        unit=patch.units.get(key),
                        quality="VALID",
                        ttl_s=patch.ttl_s,
                    )
                touched.add(patch.domain)
            self._revision += 1
            for domain in touched:
                self._domain_revisions[domain] = self._revision
            return self._revision

    @property
    def revision(self):
        with self._lock:
            return self._revision

    def snapshot(self) -> RuntimeSnapshot:
        with self._lock:
            return RuntimeSnapshot(
                domains={name: copy.deepcopy(values) for name, values in self._domains.items()},
                revision=self._revision,
                domain_revisions=self._domain_revisions.copy(),
            )

    def metadata_snapshot(self) -> dict[str, dict[str, dict[str, Any]]]:
        now = time.monotonic()
        with self._lock:
            result = {}
            for domain, signals in self._metadata.items():
                result[domain] = {}
                for key, meta in signals.items():
                    age_s = max(0.0, now - meta.updated_monotonic)
                    quality = meta.quality
                    if quality == "VALID" and meta.ttl_s is not None and age_s > meta.ttl_s:
                        quality = "STALE"
                    result[domain][key] = {
                        "source": meta.source,
                        "unit": meta.unit,
                        "quality": quality,
                        "age_ms": age_s * 1000.0,
                        "ttl_ms": None if meta.ttl_s is None else meta.ttl_s * 1000.0,
                    }
            return result
