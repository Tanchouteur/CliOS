"""Thread-safe, monotonic view of CAN bus activity."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CanActivitySnapshot:
    has_seen_frame: bool
    last_frame_age: float
    provider_connected: bool


class CanActivitySource:
    """Tracks raw CAN activity independently from decoding/service health."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._started_at = clock()
        self._last_frame_at: float | None = None
        self._provider_connected = False
        self._lock = threading.RLock()

    def set_provider_connected(self, connected: bool) -> None:
        with self._lock:
            self._provider_connected = bool(connected)

    def record_frame(self, received_at: float | None = None) -> None:
        with self._lock:
            self._last_frame_at = self._clock() if received_at is None else received_at

    def snapshot(self, now: float | None = None) -> CanActivitySnapshot:
        current = self._clock() if now is None else now
        with self._lock:
            reference = self._last_frame_at if self._last_frame_at is not None else self._started_at
            return CanActivitySnapshot(
                has_seen_frame=self._last_frame_at is not None,
                last_frame_age=max(0.0, current - reference),
                provider_connected=self._provider_connected,
            )
