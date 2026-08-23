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
        service = BleLedController()

        async def stop_after_first_color():
            self.assertEqual(await service._queue.get(), service._current_color)

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
            send = mock.AsyncMock(side_effect=capture)
            with mock.patch.object(service, "_send_to_device", new=send):
                await service._ble_worker()
                self.assertFalse(send.await_args.kwargs["power_on"])

        asyncio.run(run_once())


if __name__ == "__main__":
    unittest.main()
