import subprocess
import threading
import time
import unittest
from unittest.mock import MagicMock

from src.can_activity import CanActivitySource
from src.runtime import VehicleRuntime
from src.services.power_management_service import (
    PowerManagementService,
    PowerState,
    SystemPowerExecutor,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakePowerExecutor:
    is_simulated = False

    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.calls = 0

    def poweroff(self):
        self.calls += 1
        return (self.succeeds, "test")


class PowerManagementServiceTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.storage = MagicMock()
        self.storage.get.side_effect = lambda _key, default=None: default
        self.runtime = VehicleRuntime(self.storage)
        self.activity = CanActivitySource(self.clock)
        self.executor = FakePowerExecutor()
        self.orchestrator = MagicMock()
        self.orchestrator.stop_all.return_value = {"errors": {}, "unresponsive": [], "stopped": []}
        self.service = PowerManagementService(
            self.runtime,
            self.storage,
            self.orchestrator,
            self.activity,
            power_executor=self.executor,
            clock=self.clock,
            sync_writes=lambda: None,
        )

    def publish_contact(self, acc=False, run=False, rpm=0):
        self.runtime.publish(
            "powertrain", {"key_acc": acc, "key_run": run, "rpm": rpm}, source="test",
        )

    def test_contact_off_uses_short_delay_and_ignores_rpm(self):
        self.publish_contact(run=True, rpm=0)
        self.assertEqual(self.service.evaluate(), PowerState.CONTACT_ON)
        self.publish_contact(run=False, rpm=5000)
        self.assertEqual(self.service.evaluate(), PowerState.CONTACT_OFF_COUNTDOWN)
        self.clock.now = 9.9
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 0)
        self.clock.now = 10.0
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 1)

    def test_contact_return_cancels_countdown(self):
        self.publish_contact(acc=True)
        self.service.evaluate()
        self.publish_contact()
        self.service.evaluate()
        self.clock.now = 5.0
        self.publish_contact(acc=True)
        self.assertEqual(self.service.evaluate(), PowerState.CONTACT_ON)
        self.clock.now = 20.0
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 0)

    def test_never_seen_can_powers_off_after_startup_delay(self):
        self.assertEqual(self.service.evaluate(), PowerState.CAN_SILENCE_COUNTDOWN)
        self.clock.now = 179.9
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 0)
        self.clock.now = 180.0
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 1)

    def test_continuous_can_activity_resets_silence_countdown(self):
        for second in range(0, 301, 30):
            self.clock.now = float(second)
            self.activity.record_frame()
            self.service.evaluate()
        self.assertEqual(self.service.state, PowerState.CAN_SILENCE_COUNTDOWN)
        self.assertEqual(self.executor.calls, 0)

        self.clock.now = 479.9
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 0)
        self.clock.now = 480.0
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 1)

    def test_can_silence_can_be_disabled(self):
        self.service.update_param("shutdown_on_can_silence", False)
        self.clock.now = 900.0
        self.assertEqual(self.service.evaluate(), PowerState.WAITING_FOR_CONTACT)
        self.assertEqual(self.executor.calls, 0)

    def test_recent_can_with_explicit_contact_off_uses_short_delay(self):
        self.clock.now = 50.0
        self.activity.record_frame()
        self.publish_contact()
        self.assertEqual(self.service.evaluate(), PowerState.CONTACT_OFF_COUNTDOWN)
        self.clock.now = 60.0
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 1)

    def test_invalid_delays_are_clamped_and_legacy_param_is_absent(self):
        self.service.update_param("shutdown_delay", 999)
        self.service.update_param("can_silence_delay", 1)
        params = {item["key"]: item for item in self.service.get_params_schema()}
        self.assertEqual(params["shutdown_delay"]["value"], 60.0)
        self.assertEqual(params["can_silence_delay"]["value"], 60.0)
        self.assertNotIn("wait_key_removal", params)

    def test_power_command_failure_is_visible_and_retried(self):
        self.executor.succeeds = False
        self.clock.now = 180.0
        self.service.evaluate()
        self.assertEqual(self.service.state, PowerState.POWER_ACTION_FAILED)
        self.assertEqual(self.executor.calls, 1)
        self.clock.now = 209.0
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 1)
        self.clock.now = 210.0
        self.service.evaluate()
        self.assertEqual(self.executor.calls, 2)

    def test_desktop_and_mock_are_always_simulated(self):
        for system, mock in (("Darwin", False), ("Windows", False), ("Linux", True)):
            executor = SystemPowerExecutor(system=system, mock=mock)
            self.assertTrue(executor.is_simulated)
            self.assertTrue(executor.poweroff()[0])

    def test_linux_executor_uses_no_shell_and_checks_return_code(self):
        runner = MagicMock(return_value=subprocess.CompletedProcess([], 4, "", "denied"))
        executor = SystemPowerExecutor(system="Linux", runner=runner)
        ok, detail = executor.poweroff()
        self.assertFalse(ok)
        self.assertIn("code 4", detail)
        self.assertEqual(runner.call_args.args[0], ["systemctl", "poweroff"])
        self.assertFalse(runner.call_args.kwargs["shell"])

    def test_linux_executor_handles_success_and_process_error(self):
        success = MagicMock(return_value=subprocess.CompletedProcess([], 0, "", ""))
        executor = SystemPowerExecutor(system="Linux", runner=success)
        self.assertTrue(executor.poweroff()[0])
        self.assertTrue(executor.reboot()[0])
        self.assertEqual(success.call_args.args[0], ["systemctl", "reboot"])
        self.assertFalse(executor.execute("suspend")[0])
        failure = MagicMock(side_effect=subprocess.TimeoutExpired(["systemctl"], 10))
        ok, detail = SystemPowerExecutor(system="Linux", runner=failure).poweroff()
        self.assertFalse(ok)
        self.assertIn("commande impossible", detail)

    def test_service_stop_failure_is_logged_but_does_not_block_host_poweroff(self):
        self.clock.now = 180.0
        self.orchestrator.stop_all.return_value = {"errors": {"save": "failed"}, "unresponsive": [], "stopped": []}
        self.service.evaluate()
        self.assertEqual(self.service.state, PowerState.POWERING_OFF)
        self.assertEqual(self.executor.calls, 1)

    def test_sync_failure_prevents_power_command(self):
        self.clock.now = 180.0
        service = PowerManagementService(
            self.runtime, self.storage, self.orchestrator, self.activity,
            power_executor=self.executor, clock=self.clock,
            sync_writes=MagicMock(side_effect=OSError("disk")),
        )
        self.orchestrator.stop_all.return_value = {"errors": {}, "unresponsive": [], "stopped": []}
        service.evaluate()
        self.assertEqual(service.state, PowerState.POWER_ACTION_FAILED)
        self.assertEqual(self.executor.calls, 0)

    def test_can_activity_connection_snapshot_and_negative_age(self):
        self.activity.set_provider_connected(True)
        self.activity.record_frame(received_at=20.0)
        snapshot = self.activity.snapshot(now=10.0)
        self.assertTrue(snapshot.has_seen_frame)
        self.assertTrue(snapshot.provider_connected)
        self.assertEqual(snapshot.last_frame_age, 0.0)

    def test_worker_lifecycle_and_simulation_reset(self):
        self.service.update_param("shutdown_on_can_silence", False)
        stop_event = threading.Event()
        self.service.start(stop_event)
        time.sleep(0.02)
        self.service.stop()
        self.assertTrue(stop_event.is_set())
        self.service.state = PowerState.POWERING_OFF
        self.service._reset_after_simulation()
        self.assertEqual(self.service.state, PowerState.WAITING_FOR_CONTACT)


if __name__ == "__main__":
    unittest.main()
