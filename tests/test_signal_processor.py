import unittest

from src.signal_processor import RawFrame, SignalProcessor


class SignalProcessorTest(unittest.TestCase):
    def _definition(self, **overrides):
        signal = {
            "start_byte": 0, "size": 1, "endian": "big", "is_bits": False,
            "mask_val": None, "shift": 0, "factor": 1.0, "offset": 0.0,
            "signed": False, "bit_length": 8, "min_value": None, "max_value": None,
        }
        signal.update(overrides)
        return {"signals": {"value": signal}}

    def test_decodes_explicit_signed_signal(self):
        frame = RawFrame(id=1, data=bytearray([0xFF]), timestamp=0.0)
        decoded = SignalProcessor().decode(frame, self._definition(signed=True))
        self.assertEqual(decoded["value"], -1.0)

    def test_rejects_value_outside_declared_physical_range(self):
        frame = RawFrame(id=1, data=bytearray([200]), timestamp=0.0)
        decoded = SignalProcessor().decode(frame, self._definition(max_value=100.0))
        self.assertNotIn("value", decoded)

