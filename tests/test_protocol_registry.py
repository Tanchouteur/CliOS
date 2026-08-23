import unittest

from src.ble.protocol_registry import ProtocolRegistry


class ProtocolRegistryTest(unittest.TestCase):
    def setUp(self):
        self.registry = ProtocolRegistry()

    def test_witness_colors_are_unique(self):
        colors = [protocol.witness_color for protocol in self.registry.all()]
        self.assertEqual(len(colors), len(set(colors)))

    def test_known_names_prioritize_confirmed_protocols(self):
        self.assertEqual(self.registry.guess_protocol_order("ELK-BLEDOM")[0], "LOTUS_9B")
        self.assertEqual(self.registry.guess_protocol_order("LEDCAR-01-DF02")[0], "LEDCAR_DMX_9B")

    def test_unknown_protocol_raises(self):
        with self.assertRaises(KeyError):
            self.registry.get("UNKNOWN")

    def test_protocol_without_brightness_command_scales_rgb_once(self):
        payloads = self.registry.build_payloads("TRIONES_7B", 100, 80, 60, 50, True)
        self.assertEqual(tuple(payloads[1][1:4]), (50, 40, 30))


if __name__ == "__main__":
    unittest.main()
