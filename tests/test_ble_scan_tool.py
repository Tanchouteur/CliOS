import contextlib
import io
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from tools import scan_ble_leds


class BleScanToolTest(unittest.IsolatedAsyncioTestCase):
    async def test_scan_reads_rssi_from_advertisement_data(self):
        device = SimpleNamespace(address="AA:BB:CC:DD:EE:FF", name="ELK-BLEDOM")
        advertisement = SimpleNamespace(rssi=-47)
        discover = AsyncMock(return_value={device.address: (device, advertisement)})

        output = io.StringIO()
        with patch.object(scan_ble_leds.BleakScanner, "discover", discover):
            with contextlib.redirect_stdout(output):
                devices = await scan_ble_leds.scan_devices()

        self.assertEqual(devices, [device])
        self.assertIn("RSSI: -47 dBm", output.getvalue())
        discover.assert_awaited_once_with(timeout=5.0, return_adv=True)


if __name__ == "__main__":
    unittest.main()
