from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from src.ble import scanner as scanner_module
from src.ble.scanner import BleScanner, GattCharInfo


class AsyncClient:
    def __init__(self, _address, **_kwargs):
        preferred = SimpleNamespace(
            uuid="0000fff3-0000-1000-8000-00805f9b34fb",
            properties=["write-without-response"],
        )
        ignored = SimpleNamespace(uuid="read-only", properties=["read"])
        self.services = [SimpleNamespace(characteristics=[ignored, preferred])]
        self.write_gatt_char = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class BleScannerTest(unittest.IsolatedAsyncioTestCase):
    async def test_scan_sorts_led_candidates_first(self):
        led = SimpleNamespace(address="AA", name="ELK-BLEDOM")
        other = SimpleNamespace(address="BB", name="Keyboard")
        discovered = {
            "BB": (other, SimpleNamespace(rssi=-20)),
            "AA": (led, SimpleNamespace(rssi=-50)),
        }
        with patch.object(scanner_module, "BLEAK_AVAILABLE", True), \
             patch.object(scanner_module, "BleakScanner", SimpleNamespace(discover=AsyncMock(return_value=discovered))):
            results = await BleScanner().scan(0.1)
        self.assertEqual(results[0].address, "AA")
        self.assertTrue(results[0].is_candidate)

    async def test_discovers_only_writable_characteristics(self):
        with patch.object(scanner_module, "BLEAK_AVAILABLE", True), \
             patch.object(scanner_module, "BleakClient", AsyncClient):
            chars = await BleScanner().discover_characteristics("AA")
        self.assertEqual(len(chars), 1)
        self.assertTrue(chars[0].is_preferred)
        self.assertFalse(chars[0].write_with_response)

    async def test_select_best_characteristic_prefers_known_uuid(self):
        generic = GattCharInfo("generic")
        preferred = GattCharInfo("preferred", is_preferred=True)
        self.assertIs(await BleScanner().select_best_characteristic([generic, preferred]), preferred)


if __name__ == "__main__":
    unittest.main()
