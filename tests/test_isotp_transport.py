import unittest

import can

from src.isotp import IsoTpError, IsoTpReassembler
from src.simulation.can_encoder import CanFrameEncoder


class IsoTpTransportTest(unittest.TestCase):
    def test_flow_control_maps_every_response_to_physical_request(self):
        for response_id in range(0x7E8, 0x7F0):
            transport = IsoTpReassembler()
            result = transport.feed(
                response_id, bytes([0x10, 0x08, 1, 2, 3, 4, 5, 6]), now=0.0,
            )
            self.assertEqual(result.flow_control_id, response_id - 8)

    def test_single_frame_lengths_are_checked(self):
        transport = IsoTpReassembler()
        self.assertEqual(transport.feed(0x7E8, b"\x02\x43\x00", 0.0).payload, b"\x43\x00")
        with self.assertRaises(IsoTpError):
            transport.feed(0x7E8, b"\x07\x43", 0.0)
        with self.assertRaises(IsoTpError):
            transport.feed(0x7E8, b"\x00", 0.0)

    def test_multiple_ecus_are_reassembled_independently(self):
        transport = IsoTpReassembler()
        transport.feed(0x7E8, bytes([0x10, 8, 1, 2, 3, 4, 5, 6]), 0.0)
        transport.feed(0x7E9, bytes([0x10, 9, 11, 12, 13, 14, 15, 16]), 0.0)
        first = transport.feed(0x7E8, bytes([0x21, 7, 8, 0, 0, 0, 0, 0]), 0.1)
        second = transport.feed(0x7E9, bytes([0x21, 17, 18, 19, 0, 0, 0, 0]), 0.1)
        self.assertEqual(first.payload, bytes(range(1, 9)))
        self.assertEqual(second.payload, bytes(range(11, 20)))

    def test_bad_sequence_drops_only_its_flow(self):
        transport = IsoTpReassembler()
        transport.feed(0x7E8, bytes([0x10, 8, 1, 2, 3, 4, 5, 6]), 0.0)
        transport.feed(0x7E9, bytes([0x10, 8, 1, 2, 3, 4, 5, 6]), 0.0)
        with self.assertRaises(IsoTpError):
            transport.feed(0x7E8, bytes([0x22, 7, 8]), 0.1)
        self.assertNotIn(0x7E8, transport.flows)
        self.assertIn(0x7E9, transport.flows)

    def test_sequence_wraps_from_f_to_zero(self):
        transport = IsoTpReassembler()
        length = 118
        transport.feed(0x7E8, bytes([0x10, length, 0, 1, 2, 3, 4, 5]), 0.0)
        result = None
        value = 6
        now = 0.01
        for sequence in list(range(1, 16)) + [0]:
            chunk = bytes((value + offset) & 0xFF for offset in range(7))
            value += 7
            result = transport.feed(0x7E8, bytes([0x20 | sequence]) + chunk, now)
            now += 0.01
        self.assertIsNotNone(result.payload)
        self.assertEqual(len(result.payload), length)

    def test_wrong_source_and_timeout_are_rejected(self):
        transport = IsoTpReassembler(flow_timeout_s=0.5)
        with self.assertRaises(IsoTpError):
            transport.feed(0x7DF, b"\x01\x43", 0.0)
        transport.feed(0x7E8, bytes([0x10, 8, 1, 2, 3, 4, 5, 6]), 0.0)
        self.assertEqual(transport.expire(0.6), [0x7E8])
        with self.assertRaises(IsoTpError):
            transport.feed(0x7E8, bytes([0x21, 7, 8]), 0.7)

    def test_malformed_first_consecutive_and_unsupported_frames(self):
        transport = IsoTpReassembler(flow_timeout_s=0.5)
        for data in (b"", bytes(range(9)), b"\x10\x08", bytes([0x10, 7, 1, 2, 3, 4, 5, 6])):
            with self.subTest(data=data), self.assertRaises(IsoTpError):
                transport.feed(0x7E8, data, 0.0)
        with self.assertRaises(IsoTpError):
            transport.feed(0x7E8, b"\x30\x00\x00", 0.0)
        transport.feed(0x7E8, bytes([0x10, 8, 1, 2, 3, 4, 5, 6]), 0.0)
        with self.assertRaisesRegex(IsoTpError, "délai"):
            transport.feed(0x7E8, bytes([0x21, 7, 8]), 0.6)

    def test_first_frame_claiming_payload_already_complete_is_rejected(self):
        transport = IsoTpReassembler()
        # Extended-length encoding is not supported by this classic-CAN contract.
        with self.assertRaises(IsoTpError):
            transport.feed(0x7E8, bytes([0x10, 0, 1, 2, 3, 4, 5, 6]), 0.0)

    def test_simulator_accepts_flow_control_only_on_physical_address(self):
        encoder = CanFrameEncoder()
        dtcs = ["P0300", "P0115", "P0420", "C0123"]
        request = can.Message(arbitration_id=0x7DF, data=[1, 3, 0, 0, 0, 0, 0, 0])
        encoder.handle_obd_request(request, dtcs)
        self.assertTrue(encoder._isotp_pending_consecutive)
        wrong_fc = can.Message(arbitration_id=0x7DF, data=[0x30, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(encoder.handle_obd_request(wrong_fc, dtcs), [])
        self.assertTrue(encoder._isotp_pending_consecutive)
        physical_fc = can.Message(arbitration_id=0x7E0, data=[0x30, 0, 0, 0, 0, 0, 0, 0])
        self.assertTrue(encoder.handle_obd_request(physical_fc, dtcs))
        self.assertFalse(encoder._isotp_pending_consecutive)


if __name__ == "__main__":
    unittest.main()
