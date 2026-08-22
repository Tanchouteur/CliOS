import contextlib
import io
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from tools import scan_ble_leds


class BleScanToolTest(unittest.IsolatedAsyncioTestCase):
    def test_each_protocol_has_a_distinct_witness_color(self):
        colors = [protocol.color for protocol in scan_ble_leds.PROTOCOLS.values()]
        self.assertEqual(len(colors), len(set(colors)))

    def test_protocol_payloads_contain_their_witness_color(self):
        color_slices = {"1": slice(4, 7), "2": slice(1, 4), "3": slice(1, 4), "4": slice(4, 7)}
        for key, protocol in scan_ble_leds.PROTOCOLS.items():
            color_payload = scan_ble_leds.build_protocol_payloads(key, *protocol.color)[1]
            self.assertEqual(tuple(color_payload[color_slices[key]]), protocol.color)

    def test_preferred_characteristic_and_write_mode_are_detected(self):
        generic = SimpleNamespace(
            uuid="11111111-1111-1111-1111-111111111111",
            properties=["write-without-response"],
        )
        preferred = SimpleNamespace(
            uuid="0000ffe1-0000-1000-8000-00805f9b34fb",
            properties=["write"],
        )
        with patch("builtins.input", return_value=""):
            selected = scan_ble_leds.select_write_characteristic([generic, preferred])

        self.assertIs(selected, preferred)
        self.assertTrue(scan_ble_leds.write_requires_response(preferred))
        self.assertFalse(scan_ble_leds.write_requires_response(generic))

    def test_protocol_result_waits_for_an_explicit_answer(self):
        with patch("builtins.input", side_effect=["invalide", ""]) as prompt:
            result = scan_ble_leds.ask_protocol_result("ROUGE")
        self.assertEqual(result, "next")
        self.assertEqual(prompt.call_count, 2)

    async def test_scan_reads_rssi_from_advertisement_data(self):
        device = SimpleNamespace(address="AA:BB:CC:DD:EE:FF", name="ELK-BLEDOM")
        advertisement = SimpleNamespace(rssi=-47)
        discover = AsyncMock(return_value={device.address: (device, advertisement)})

        output = io.StringIO()
        scanner = SimpleNamespace(discover=discover)
        client = SimpleNamespace()
        with patch.object(scan_ble_leds, "BleakScanner", scanner), \
                patch.object(scan_ble_leds, "BleakClient", client), \
                patch.object(scan_ble_leds, "BLEAK_IMPORT_ERROR", None):
            with contextlib.redirect_stdout(output):
                devices = await scan_ble_leds.scan_devices()

        self.assertEqual(devices, [device])
        self.assertIn("RSSI: -47 dBm", output.getvalue())
        discover.assert_awaited_once_with(timeout=5.0, return_adv=True)

    async def test_missing_bleak_is_reported_without_exiting_during_import(self):
        missing = ImportError("No module named 'bleak'")
        with patch.object(scan_ble_leds, "BleakScanner", None), \
                patch.object(scan_ble_leds, "BleakClient", None), \
                patch.object(scan_ble_leds, "BLEAK_IMPORT_ERROR", missing):
            with self.assertRaisesRegex(RuntimeError, "pip install bleak"):
                await scan_ble_leds.scan_devices()


if __name__ == "__main__":
    unittest.main()
