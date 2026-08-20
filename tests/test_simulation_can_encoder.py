"""Tests d'encodage binaire des trames CAN et validation miroir avec SignalProcessor."""

import os
import unittest
from src.parser import DbcParser
from src.signal_processor import SignalProcessor, RawFrame
from src.simulation.models import SimulatedVehicleState
from src.simulation.can_encoder import CanFrameEncoder

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SimulationCanEncoderTest(unittest.TestCase):
    def setUp(self):
        dbc_path = os.path.join(ROOT, "data", "can", "can_moteur_clio3.json")
        self.parser = DbcParser(dbc_path)
        self.processor = SignalProcessor()
        self.encoder = CanFrameEncoder()
        self.state = SimulatedVehicleState()

    def _decode_frame(self, frame):
        definition = self.parser.get_definition(frame.arbitration_id)
        self.assertIsNotNone(definition, f"Définition manquante pour ID 0x{frame.arbitration_id:03X}")
        raw = RawFrame(id=frame.arbitration_id, data=frame.data, timestamp=frame.timestamp)
        return self.processor.decode(raw, definition)

    def test_encode_and_decode_engine_data_0x181(self):
        self.state.rpm = 3200.0
        self.state.throttle_pedal = 45.0
        self.state.brake_pedal = 0.0
        self.state.clutch_pedal = 0.0

        frame = self.encoder.encode_frame(0x181, self.state)
        decoded = self._decode_frame(frame)

        self.assertAlmostEqual(decoded["rpm"], 3200.0, delta=2.0)
        self.assertAlmostEqual(decoded["accel_pos"], 45.0, delta=1.0)
        self.assertFalse(decoded["brake"])
        self.assertFalse(decoded["clutch"])

    def test_encode_and_decode_vehicle_dynamics_0x354(self):
        self.state.speed_kmh = 85.5
        self.state.distance_trip_km = 12.3
        self.state.brake_pedal = 50.0

        frame = self.encoder.encode_frame(0x354, self.state)
        decoded = self._decode_frame(frame)

        self.assertAlmostEqual(decoded["speed"], 85.5, delta=0.1)
        self.assertAlmostEqual(decoded["distance"], 12.3, delta=0.1)
        self.assertTrue(decoded["brake_pressed"])

    def test_encode_and_decode_wheel_speeds_0x284_0x285(self):
        self.state.wheel_fl_speed = 70.2
        self.state.wheel_fr_speed = 70.4
        self.state.wheel_rl_speed = 69.8
        self.state.wheel_rr_speed = 69.9

        f_front = self.encoder.encode_frame(0x284, self.state)
        f_rear = self.encoder.encode_frame(0x285, self.state)

        dec_front = self._decode_frame(f_front)
        dec_rear = self._decode_frame(f_rear)

        self.assertAlmostEqual(dec_front["wheel_fl_speed"], 70.2, delta=0.1)
        self.assertAlmostEqual(dec_front["wheel_fr_speed"], 70.4, delta=0.1)
        self.assertAlmostEqual(dec_rear["wheel_rl_speed"], 69.8, delta=0.1)
        self.assertAlmostEqual(dec_rear["wheel_rr_speed"], 69.9, delta=0.1)

    def test_encode_and_decode_body_status_0x60D(self):
        self.state.low_beam = True
        self.state.high_beam = False
        self.state.turn_left = True
        self.state.outside_temp_c = 18.0
        self.state.door_fl_open = True

        frame = self.encoder.encode_frame(0x60D, self.state)
        decoded = self._decode_frame(frame)

        self.assertTrue(decoded["low_beam"])
        self.assertTrue(decoded["turn_left"])
        self.assertTrue(decoded["door_fl_open"])
        self.assertFalse(decoded["high_beam"])
        self.assertAlmostEqual(decoded["outside_temp"], 18.0, delta=1.0)

    def test_encode_and_decode_engine_env_0x551(self):
        self.state.engine_temp_c = 92.0
        self.state.gear_raw = 109  # 2ème
        self.state.vitesse_regulateur_kmh = 130
        self.state.regulateur_mode = 1
        self.state.regulateur_statut = 1

        frame = self.encoder.encode_frame(0x551, self.state)
        decoded = self._decode_frame(frame)

        self.assertAlmostEqual(decoded["engine_temp"], 92.0, delta=1.0)
        self.assertEqual(decoded["gear_raw"], 109)
        self.assertEqual(decoded["vitesse_regulateur"], 130)
        self.assertEqual(decoded["regulateur_mode"], 1)
        self.assertEqual(decoded["regulateur_statut"], 1)


if __name__ == "__main__":
    unittest.main()
