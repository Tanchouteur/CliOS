import asyncio
import unittest
from unittest import mock

from src.ble.device_catalog import BleDevice, DeviceCatalog
from src.services.led_service import BleLedController


class MemoryStorage:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class BleLedControllerTest(unittest.TestCase):
    def test_registers_only_the_global_brightness_parameter(self):
        service = BleLedController()
        self.assertEqual(list(service._params), ["global_brightness"])

    def test_ledcar_dmx_payloads_match_the_confirmed_hardware_frames(self):
        service = BleLedController()
        payloads = service._registry.build_payloads("LEDCAR_DMX_9B", 1, 2, 3, 100, True)
        self.assertEqual(bytes(payloads[0]), bytes.fromhex("7b ff 04 03 ff ff ff ff bf"))
        self.assertEqual(bytes(payloads[1]), bytes.fromhex("7b ff 01 20 64 00 ff ff bf"))
        self.assertEqual(bytes(payloads[2]), bytes.fromhex("7b 00 07 01 02 03 00 ff bf"))

    def test_ledcar_power_off_uses_the_confirmed_dmx_channel(self):
        service = BleLedController()
        payloads = service._registry.build_power_off("LEDCAR_DMX_9B")
        self.assertEqual(bytes(payloads[0]), bytes.fromhex("7b ff 04 02 ff ff ff ff bf"))

    def test_worker_queues_the_initial_color_before_waiting(self):
        service = BleLedController(initial_color="#A1B2C3")

        async def stop_after_first_color():
            self.assertEqual(await service._queue.get(), "#A1B2C3")

        with mock.patch.object(service, "_ble_worker", side_effect=stop_after_first_color):
            service._run_event_loop()

    def test_disabled_devices_are_routed_as_power_off(self):
        catalog = DeviceCatalog(None)
        catalog.add_device(BleDevice(
            id="dev_test", name="Test", ble_address="AA", protocol="LOTUS_9B",
            gatt_char_uuid="fff3", write_with_response=False, advertised_name="LED",
            enabled=False,
        ))
        service = BleLedController(catalog=catalog)
        service._running = True

        async def run_once():
            service._queue = asyncio.Queue()
            await service._queue.put("#112233")
            async def capture(*args, **kwargs):
                service._running = False
                return True
            send = mock.AsyncMock(side_effect=capture)
            with mock.patch.object(service, "_send_to_device", new=send):
                await service._ble_worker()
                self.assertFalse(send.await_args.kwargs["power_on"])

        asyncio.run(run_once())

    def test_startup_dispatch_retries_but_later_updates_do_not(self):
        catalog = DeviceCatalog(None)
        catalog.add_device(BleDevice(
            id="dev_test", name="Test", ble_address="AA", protocol="LOTUS_9B",
            gatt_char_uuid="fff3", write_with_response=False, advertised_name="LED",
        ))
        service = BleLedController(catalog=catalog)
        service._running = True

        async def run_two_colors():
            service._queue = asyncio.Queue()
            await service._queue.put("#112233")
            attempts = []

            async def capture(*args, **kwargs):
                attempts.append(kwargs["attempts"])
                if len(attempts) == 1:
                    await service._queue.put("#445566")
                else:
                    service._running = False
                return True

            with mock.patch.object(service, "_send_to_device", side_effect=capture):
                await service._ble_worker()
            self.assertEqual(attempts, [3, 1])

        asyncio.run(run_two_colors())

    def test_startup_send_retries_transient_failures(self):
        device = BleDevice(
            id="dev_test", name="Test", ble_address="AA", protocol="LOTUS_9B",
            gatt_char_uuid="fff3", write_with_response=False, advertised_name="LED",
        )
        service = BleLedController()
        service._running = True

        async def retry_until_success():
            service._queue = asyncio.Queue()
            send_once = mock.AsyncMock(side_effect=[False, False, True])
            with mock.patch.object(service, "STARTUP_RETRY_DELAYS", (0.0, 0.0)), \
                    mock.patch.object(service, "_send_to_device_once", new=send_once):
                success = await service._send_to_device(
                    device, 1, 2, 3, 100.0, True, attempts=3,
                )
            self.assertTrue(success)
            self.assertEqual(send_once.await_count, 3)

        asyncio.run(retry_until_success())

if __name__ == "__main__":
    unittest.main()
