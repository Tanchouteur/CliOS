"""Deterministic ignition/CAN-silence shutdown management."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
import time
from enum import Enum
from typing import Callable

from src.can_activity import CanActivitySource
from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType


class PowerState(str, Enum):
    WAITING_FOR_CONTACT = "WAITING_FOR_CONTACT"
    CONTACT_ON = "CONTACT_ON"
    CONTACT_OFF_COUNTDOWN = "CONTACT_OFF_COUNTDOWN"
    CAN_SILENCE_COUNTDOWN = "CAN_SILENCE_COUNTDOWN"
    POWERING_OFF = "POWERING_OFF"
    POWER_ACTION_FAILED = "POWER_ACTION_FAILED"


class SystemPowerExecutor:
    """Runs a real power action only on a non-mock Linux system."""

    def __init__(self, *, mock: bool = False, system: str | None = None,
                 runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
                 timeout_s: float = 10.0):
        self.mock = mock
        self.system = system or platform.system()
        self.runner = runner
        self.timeout_s = timeout_s

    @property
    def is_simulated(self) -> bool:
        return self.mock or self.system != "Linux"

    def execute(self, action: str) -> tuple[bool, str]:
        if action not in {"poweroff", "reboot"}:
            return False, f"action système interdite: {action}"
        if self.is_simulated:
            return True, f"Action {action} simulée ({'mock' if self.mock else self.system})"
        try:
            completed = self.runner(
                ["systemctl", action],
                shell=False,
                timeout=self.timeout_s,
                check=False,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"commande impossible: {exc}"
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "sans détail").strip()
            return False, f"code {completed.returncode}: {detail}"
        return True, f"Action système demandée: {action}"

    def poweroff(self) -> tuple[bool, str]:
        return self.execute("poweroff")

    def reboot(self) -> tuple[bool, str]:
        return self.execute("reboot")


class PowerManagementService(BaseService):
    POLL_INTERVAL_S = 0.25
    RETRY_DELAY_S = 30.0

    def __init__(self, runtime, storage, orchestrator, can_activity: CanActivitySource,
                 *, power_executor: SystemPowerExecutor | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 sync_writes: Callable[[], None] | None = None):
        super().__init__("PowerManager", storage)
        self.runtime = runtime
        self.orchestrator = orchestrator
        self.can_activity = can_activity
        self.power_executor = power_executor or SystemPowerExecutor()
        self.clock = clock
        if sync_writes is not None:
            self.sync_writes: Callable[[], None] = sync_writes
        elif hasattr(os, "sync"):
            self.sync_writes = os.sync
        else:
            self.sync_writes = lambda: None
        self.state = PowerState.WAITING_FOR_CONTACT
        self.shutdown_reason = ""
        self._countdown_started_at: float | None = None
        self._last_contact_active: bool | None = None
        self._retry_at: float | None = None
        self._action_lock = threading.Lock()

        self.register_param(
            "shutdown_delay", "Délai avant extinction (s)", ServiceParamType.SLIDER,
            10.0, min_val=0.0, max_val=60.0,
        )
        self.register_param(
            "shutdown_on_can_silence", "Arrêt sur silence CAN", ServiceParamType.TOGGLE, True,
        )
        self.register_param(
            "can_silence_delay", "Délai de silence CAN (s)", ServiceParamType.SLIDER,
            180.0, min_val=60.0, max_val=900.0,
        )
        self._publish_state(None)

    def start(self, stop_event: threading.Event, implemented=False):
        super().start(stop_event, implemented=True)
        self._thread = threading.Thread(
            target=self._run, args=(stop_event,), daemon=True, name=self.service_name,
        )
        self._thread.start()

    def _run(self, stop_event: threading.Event):
        self.set_ok("Surveillance alimentation active")
        while not stop_event.is_set():
            self.evaluate()
            if self.state is PowerState.POWERING_OFF and self.power_executor.is_simulated:
                self._reset_after_simulation()
            stop_event.wait(self.POLL_INTERVAL_S)

    def evaluate(self, now: float | None = None) -> PowerState:
        """Advance the state machine once; public for deterministic tests."""
        current = self.clock() if now is None else now
        powertrain = self.runtime.snapshot().domain("powertrain")
        has_contact_signal = "key_acc" in powertrain or "key_run" in powertrain
        contact_active = bool(powertrain.get("key_acc", False) or powertrain.get("key_run", False))
        activity = self.can_activity.snapshot(current)

        if contact_active:
            self._last_contact_active = True
            self._set_state(PowerState.CONTACT_ON, "", countdown_started_at=None)
            self.set_ok("Contact actif")
            return self.state

        if self.state is PowerState.POWER_ACTION_FAILED:
            if self._retry_at is not None and current >= self._retry_at:
                self._request_poweroff(current)
            else:
                remaining = 0.0 if self._retry_at is None else max(0.0, self._retry_at - current)
                self._publish_state(remaining)
            return self.state

        contact_just_turned_off = self._last_contact_active is True
        if has_contact_signal:
            self._last_contact_active = False

        if contact_just_turned_off:
            self._begin_countdown(PowerState.CONTACT_OFF_COUNTDOWN, "contact_off", current)
        elif self.state is PowerState.CONTACT_OFF_COUNTDOWN:
            self._continue_countdown(float(self._params["shutdown_delay"]["value"]), current)
        elif has_contact_signal and activity.has_seen_frame and activity.last_frame_age < self.POLL_INTERVAL_S * 4:
            # CAN returned while the contact is explicitly off: use the normal short delay.
            self._begin_countdown(PowerState.CONTACT_OFF_COUNTDOWN, "contact_off", current)
        elif bool(self._params["shutdown_on_can_silence"]["value"]):
            delay = float(self._params["can_silence_delay"]["value"])
            started = current - min(activity.last_frame_age, delay)
            if (
                self.state is not PowerState.CAN_SILENCE_COUNTDOWN
                or self._countdown_started_at is None
                or started > self._countdown_started_at
            ):
                self._begin_countdown(PowerState.CAN_SILENCE_COUNTDOWN, "can_silence", started)
            self._continue_countdown(delay, current)
        else:
            self._set_state(PowerState.WAITING_FOR_CONTACT, "", countdown_started_at=None)
            self.set_ok("En attente du contact")

        return self.state

    def _begin_countdown(self, state: PowerState, reason: str, started_at: float) -> None:
        self._set_state(state, reason, countdown_started_at=started_at)

    def _continue_countdown(self, delay: float, now: float) -> None:
        if self._countdown_started_at is None:
            self._countdown_started_at = now
        remaining = max(0.0, delay - (now - self._countdown_started_at))
        if remaining <= 0.0:
            self._request_poweroff(now)
        else:
            self._publish_state(remaining)
            self.set_warning(f"Extinction ({self.shutdown_reason}) dans {int(remaining + 0.999)} s")

    def _request_poweroff(self, now: float) -> None:
        if not self._action_lock.acquire(blocking=False):
            return
        try:
            self.state = PowerState.POWERING_OFF
            self._publish_state(0.0)
            self.set_error("Extinction ordonnée en cours")
            report = self.orchestrator.stop_all()
            if report.get("errors") or report.get("unresponsive"):
                self.logger.error(
                    "Arrêt incomplet des services avant extinction: %s",
                    report,
                    extra={"error_code": "POWER_SERVICE_STOP_INCOMPLETE"},
                )
            self._flush_logs()
            try:
                self.sync_writes()
            except OSError as exc:
                self._power_failed(f"synchronisation impossible: {exc}", now)
                return
            ok, message = self.power_executor.poweroff()
            if not ok:
                self._power_failed(message, now)
                return
            self.print_message(message)
        finally:
            self._action_lock.release()

    def _power_failed(self, detail: str, now: float) -> None:
        self._retry_at = now + self.RETRY_DELAY_S
        self.state = PowerState.POWER_ACTION_FAILED
        self._publish_state(self.RETRY_DELAY_S)
        self.set_error(f"Échec de l'extinction; nouvelle tentative dans 30 s: {detail}")

    @staticmethod
    def _flush_logs() -> None:
        for logger in [logging.getLogger(), *logging.Logger.manager.loggerDict.values()]:
            if not isinstance(logger, logging.Logger):
                continue
            for handler in logger.handlers:
                try:
                    handler.flush()
                except (OSError, ValueError):
                    continue

    def _reset_after_simulation(self) -> None:
        self._last_contact_active = None
        self._retry_at = None
        self._set_state(PowerState.WAITING_FOR_CONTACT, "", countdown_started_at=None)
        self.set_ok("Extinction simulée; en attente du contact")

    def _set_state(self, state: PowerState, reason: str, countdown_started_at: float | None) -> None:
        self.state = state
        self.shutdown_reason = reason
        self._countdown_started_at = countdown_started_at
        self._publish_state(None)

    def _publish_state(self, seconds: float | None) -> None:
        self.runtime.publish(
            "system",
            {
                "power_state": self.state.value,
                "power_shutdown_reason": self.shutdown_reason,
                "power_shutdown_seconds": None if seconds is None else max(0, int(seconds + 0.999)),
            },
            source="power-manager",
        )

    def stop(self):
        super().stop()
