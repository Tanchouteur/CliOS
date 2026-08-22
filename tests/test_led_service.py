import unittest
from unittest import mock

from src.services.led_service import (
    DEFAULT_DASH_PROTOCOL,
    DEFAULT_FOOT_PROTOCOL,
    DEFAULT_MAC_DASHBOARD,
    BleLedController,
)


class MemoryStorage:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class BleLedControllerTest(unittest.TestCase):
    def test_validated_devices_have_safe_default_protocols(self):
        service = BleLedController()

        self.assertEqual(service._params["dash_proto"]["value"], DEFAULT_DASH_PROTOCOL)
        self.assertEqual(service._params["foot_proto"]["value"], DEFAULT_FOOT_PROTOCOL)
        self.assertIn(DEFAULT_DASH_PROTOCOL, service._params["dash_proto"]["options"])

    def test_old_dashboard_protocol_is_migrated_for_the_confirmed_device(self):
        prefix = "services.Leds.params."
        storage = MemoryStorage({
            prefix + "dash_mac": DEFAULT_MAC_DASHBOARD,
            prefix + "dash_proto": "LED_LAMP_9B",
        })

        service = BleLedController(storage)

        self.assertEqual(service._params["dash_proto"]["value"], DEFAULT_DASH_PROTOCOL)
        self.assertEqual(storage.values[prefix + "dash_proto"], DEFAULT_DASH_PROTOCOL)

    def test_ledcar_dmx_payloads_match_the_confirmed_hardware_frames(self):
        service = BleLedController()
        service._params["brightness"]["value"] = 100

        payloads = service._build_payloads("LEDCAR_DMX_9B", 1, 2, 3, True)

        self.assertEqual(bytes(payloads[0]), bytes.fromhex("7b ff 04 03 ff ff ff ff bf"))
        self.assertEqual(bytes(payloads[1]), bytes.fromhex("7b ff 01 20 64 00 ff ff bf"))
        self.assertEqual(bytes(payloads[2]), bytes.fromhex("7b 00 07 01 02 03 00 ff bf"))

    def test_ledcar_power_off_uses_the_confirmed_dmx_channel(self):
        service = BleLedController()

        payloads = service._build_payloads("LEDCAR_DMX_9B", 0, 0, 0, False)

        self.assertEqual(bytes(payloads[0]), bytes.fromhex("7b ff 04 02 ff ff ff ff bf"))

    def test_worker_queues_the_initial_color_before_waiting(self):
        service = BleLedController()

        async def stop_after_first_color():
            self.assertEqual(await service._queue.get(), service._current_color)

        with mock.patch.object(service, "_ble_worker", side_effect=stop_after_first_color):
            service._run_event_loop()


if __name__ == "__main__":
    unittest.main()
