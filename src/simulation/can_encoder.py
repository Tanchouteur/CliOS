"""Encodeur binaire de trames CAN et émulateur de calculateur OBD-II (ISO-TP).

Génère des trames can.Message authentiques conformes aux spécifications Renault Clio 3
et répond aux requêtes de diagnostic standard OBD2 (Mode 01, Mode 03, Mode 04).
"""

import time
import collections
import can
from src.simulation.models import SimulatedVehicleState


class CanFrameEncoder:
    """Encodeur binaire de trames CAN et répondeur ISO-TP / OBD2."""

    def __init__(self):
        # File d'attente FIFO pour les trames générées
        self.frame_queue = collections.deque(maxlen=1000)

        # Planificateur de cadence pour chaque trame CAN
        self._schedules = {
            0x181: {"interval_s": 0.01,  "last_ts": 0.0},  # ENGINE_DATA (100 Hz)
            0x284: {"interval_s": 0.01,  "last_ts": 0.0},  # WHEEL_SPEED_FRONT (100 Hz)
            0x285: {"interval_s": 0.01,  "last_ts": 0.0},  # WHEEL_SPEED_REAR (100 Hz)
            0x354: {"interval_s": 0.02,  "last_ts": 0.0},  # VEHICLE_DYNAMICS (50 Hz)
            0x161: {"interval_s": 0.02,  "last_ts": 0.0},  # ENGINE_TORQUE (50 Hz)
            0x0C2: {"interval_s": 0.02,  "last_ts": 0.0},  # STEERING_DATA (50 Hz)
            0x1F9: {"interval_s": 0.05,  "last_ts": 0.0},  # ENGINE_RPM_ALT (20 Hz)
            0x215: {"interval_s": 0.05,  "last_ts": 0.0},  # GEAR_STATUS (20 Hz)
            0x551: {"interval_s": 0.10,  "last_ts": 0.0},  # ENGINE_ENV (10 Hz)
            0x60D: {"interval_s": 0.10,  "last_ts": 0.0},  # BODY_STATUS (10 Hz)
            0x645: {"interval_s": 0.10,  "last_ts": 0.0},  # DASHBOARD (10 Hz)
            0x651: {"interval_s": 0.20,  "last_ts": 0.0},  # SAFETY (5 Hz)
            0x5C5: {"interval_s": 0.50,  "last_ts": 0.0},  # VEHICLE_STATUS (2 Hz)
            0x5FD: {"interval_s": 1.00,  "last_ts": 0.0},  # VEHICLE_LIFETIME (1 Hz)
            0x715: {"interval_s": 1.00,  "last_ts": 0.0},  # ODOMETER_ALT (1 Hz)
        }

        # Contexte ISO-TP multi-trames
        self._isotp_pending_consecutive = []

    def encode_frame(self, can_id: int, state: SimulatedVehicleState, timestamp: float | None = None) -> can.Message | None:
        """Encode l'état courant dans une trame binaire CAN d'identifiant spécifié."""
        ts = timestamp or time.time()
        data = bytearray(8)

        if can_id == 0x0C2:  # STEERING_DATA
            raw_angle = int(round((state.steering_angle_deg + 3276.8) * 10.0)) & 0xFFFF
            data[0] = (raw_angle >> 8) & 0xFF
            data[1] = raw_angle & 0xFF
            raw_speed = int(round(state.steering_speed_dps + 32768.0)) & 0xFFFF
            data[2] = (raw_speed >> 8) & 0xFF
            data[3] = raw_speed & 0xFF

        elif can_id == 0x161:  # ENGINE_TORQUE
            raw_req = int(round((state.driver_torque_request + 100.0) / 2.0))
            data[0] = max(0, min(255, raw_req))
            data[2] = max(0, min(255, state.torque_available))

        elif can_id == 0x181:  # ENGINE_DATA
            raw_rpm = int(round(state.rpm * 8.0)) & 0xFFFF
            data[0] = (raw_rpm >> 8) & 0xFF
            data[1] = raw_rpm & 0xFF
            raw_accel = int(round((state.throttle_pedal + 7.0) / 0.4201))
            data[3] = max(0, min(255, raw_accel))
            raw_accel_comp = int(round(state.throttle_pedal + 20.0))
            data[4] = max(0, min(255, raw_accel_comp))
            brake_bit = 1 if (state.brake_pedal > 0.0 or state.handbrake) else 0
            clutch_bit = 1 if (state.clutch_pedal > 20.0) else 0
            data[5] = brake_bit | (clutch_bit << 3)

        elif can_id == 0x1F9:  # ENGINE_RPM_ALT
            raw_rpm = int(round(state.rpm * 8.0)) & 0xFFFF
            data[2] = (raw_rpm >> 8) & 0xFF
            data[3] = raw_rpm & 0xFF

        elif can_id == 0x215:  # GEAR_STATUS
            data[2] = (1 << 6) if state.selected_gear == -1 else 0

        elif can_id == 0x284:  # WHEEL_SPEED_FRONT
            raw_fl = int(round(state.wheel_fl_speed / 0.005)) & 0xFFFF
            data[0] = (raw_fl >> 8) & 0xFF
            data[1] = raw_fl & 0xFF
            raw_fr = int(round(state.wheel_fr_speed / 0.005)) & 0xFFFF
            data[2] = (raw_fr >> 8) & 0xFF
            data[3] = raw_fr & 0xFF
            data[4] = 0
            data[5] = 0

        elif can_id == 0x285:  # WHEEL_SPEED_REAR
            raw_rl = int(round(state.wheel_rl_speed / 0.005)) & 0xFFFF
            data[0] = (raw_rl >> 8) & 0xFF
            data[1] = raw_rl & 0xFF
            raw_rr = int(round(state.wheel_rr_speed / 0.005)) & 0xFFFF
            data[2] = (raw_rr >> 8) & 0xFF
            data[3] = raw_rr & 0xFF
            data[4] = 0
            data[5] = 0

        elif can_id == 0x354:  # VEHICLE_DYNAMICS
            raw_spd = int(round(state.speed_kmh / 0.01)) & 0xFFFF
            data[0] = (raw_spd >> 8) & 0xFF
            data[1] = raw_spd & 0xFF
            raw_dist = int(round(state.distance_trip_km / 0.1)) & 0xFFFF
            data[2] = (raw_dist >> 8) & 0xFF
            data[3] = raw_dist & 0xFF
            brake_pressed = 1 if (state.brake_pedal > 0.0 or state.handbrake) else 0
            data[6] = (brake_pressed << 4)

        elif can_id == 0x551:  # ENGINE_ENV
            data[0] = max(0, min(255, int(round(state.engine_temp_c + 40.0))))
            raw_fuel = int(round(state.fuel_used_total_l / 0.00008)) & 0xFF
            data[1] = raw_fuel
            data[2] = state.gear_raw
            data[3] = state.glow_plug_status
            data[4] = state.vitesse_regulateur_kmh
            data[5] = (state.regulateur_mode & 0x0F) | ((state.regulateur_statut & 0x0F) << 4)

        elif can_id == 0x5C5:  # VEHICLE_STATUS
            data[0] = (1 << 2) if state.handbrake else 0
            odo_int = int(state.odometer_km) & 0xFFFFFF
            data[1] = (odo_int >> 16) & 0xFF
            data[2] = (odo_int >> 8) & 0xFF
            data[3] = odo_int & 0xFF

        elif can_id == 0x5FD:  # VEHICLE_LIFETIME
            raw_odo = (int(state.odometer_km) << 4) & 0xFFFFF0
            data[0] = (raw_odo >> 16) & 0xFF
            data[1] = (raw_odo >> 8) & 0xFF
            data[2] = raw_odo & 0xFF
            age = state.vehicle_age_min & 0xFFFFFF
            data[3] = (age >> 16) & 0xFF
            data[4] = (age >> 8) & 0xFF
            data[5] = age & 0xFF

        elif can_id == 0x60D:  # BODY_STATUS
            combined_24 = (
                ((1 if state.trunk_open else 0) << 23)
                | ((1 if state.door_rr_open else 0) << 22)
                | ((1 if state.door_rl_open else 0) << 21)
                | ((1 if state.door_fr_open else 0) << 20)
                | ((1 if state.door_fl_open else 0) << 19)
                | ((1 if (state.pos_lights or state.low_beam or state.high_beam) else 0) << 18)
                | ((1 if state.low_beam else 0) << 17)
                | ((1 if (state.turn_right or state.hazard) else 0) << 14)
                | ((1 if (state.turn_left or state.hazard) else 0) << 13)
                | ((1 if state.high_beam else 0) << 11)
                | ((1 if state.key_run else 0) << 10)
                | ((1 if state.key_acc else 0) << 9)
                | ((1 if state.fog_front else 0) << 8)
                | ((1 if state.doors_locked else 0) << 5)
                | ((1 if state.trunk_locked else 0) << 4)
                | ((1 if state.fog_rear else 0) << 2)
            )
            data[0] = (combined_24 >> 16) & 0xFF
            data[1] = (combined_24 >> 8) & 0xFF
            data[2] = combined_24 & 0xFF
            data[4] = max(0, min(255, int(round(state.outside_temp_c + 40.0))))
            data[5] = max(0, min(255, int(round(state.fuel_level_l / 0.7))))
            data[6] = (1 << 4) if state.selected_gear == -1 else 0
            data[7] = (1 if state.comodo_up else 0) | ((1 if state.comodo_down else 0) << 1)

        elif can_id == 0x645:  # DASHBOARD
            data[1] = max(0, min(100, state.brightness_pct))
            raw_spd = int(round(state.speed_dashboard_kmh / 0.01)) & 0xFFFF
            data[3] = (raw_spd >> 8) & 0xFF
            data[4] = raw_spd & 0xFF

        elif can_id == 0x651:  # SAFETY
            data[0] = ((1 if state.ignition_on else 0) << 2) | ((1 if state.passenger_disabled else 0) << 1)
            data[1] = (1 if state.driver_unbelted else 0)

        elif can_id == 0x715:  # ODOMETER_ALT
            raw_odo = (int(state.odometer_km) & 0x0FFFFF) << 4
            data[0] = (raw_odo >> 16) & 0xFF
            data[1] = (raw_odo >> 8) & 0xFF
            data[2] = raw_odo & 0xFF
        else:
            return None

        return can.Message(arbitration_id=can_id, data=data, is_extended_id=False, timestamp=ts)

    def schedule_frames(self, state: SimulatedVehicleState, now: float | None = None) -> list[can.Message]:
        """Génère toutes les trames dont l'intervalle d'émission est échu."""
        current_time = now or time.time()
        ready_frames = []

        for can_id, info in self._schedules.items():
            if current_time - info["last_ts"] >= info["interval_s"]:
                frame = self.encode_frame(can_id, state, current_time)
                if frame:
                    ready_frames.append(frame)
                    info["last_ts"] = current_time

        for f in ready_frames:
            self.frame_queue.append(f)

        return ready_frames

    # =========================================================================
    # ÉMULATION CALCULATEUR OBD-II & PROTOCOLE ISO-TP (0x7E8)
    # =========================================================================

    def handle_obd_request(self, frame: can.Message, active_dtcs: list[str]) -> list[can.Message]:
        """Traite une requête envoyée à l'ECU (0x7DF ou 0x7E0) et retourne la réponse ISO-TP sur 0x7E8."""
        responses = []
        if frame.arbitration_id not in (0x7DF, 0x7E0, 0x7E8):
            return responses

        data = list(frame.data)
        if not data:
            return responses

        pci_type = data[0] >> 4

        # 1. Flow Control reçu du client (0x30 = Continue to Send)
        if pci_type == 3 or (data[0] == 0x30):
            # Débloque l'envoi des trames consécutives en attente
            while self._isotp_pending_consecutive:
                cf = self._isotp_pending_consecutive.pop(0)
                responses.append(cf)
                self.frame_queue.append(cf)
            return responses

        # 2. Requête Mode 01 PID 00 (Ping Keep-Alive)
        if len(data) >= 3 and data[1] == 0x01 and data[2] == 0x00:
            # Réponse : Mode 41 PID 00 - PIDs supportés
            resp_data = [0x06, 0x41, 0x00, 0xBE, 0x3E, 0xB8, 0x11, 0xAA]
            msg = can.Message(arbitration_id=0x7E8, data=bytearray(resp_data), is_extended_id=False, timestamp=time.time())
            responses.append(msg)
            self.frame_queue.append(msg)
            return responses

        # 3. Requête Mode 03 (Lecture des codes DTC)
        if len(data) >= 2 and data[1] == 0x03:
            encoded_dtcs = [self._encode_dtc(code) for code in active_dtcs if self._encode_dtc(code)]
            num_dtcs = len(encoded_dtcs)

            payload = bytearray([0x43, num_dtcs])
            for a, b in encoded_dtcs:
                payload.append(a)
                payload.append(b)

            payload_len = len(payload)

            if payload_len <= 7:
                # Single Frame (SF)
                sf_data = bytearray(8)
                sf_data[0] = payload_len
                sf_data[1: 1 + payload_len] = payload
                for i in range(1 + payload_len, 8):
                    sf_data[i] = 0xAA  # Padding standard
                msg = can.Message(arbitration_id=0x7E8, data=sf_data, is_extended_id=False, timestamp=time.time())
                responses.append(msg)
                self.frame_queue.append(msg)
            else:
                # Multi-Frame ISO-TP : First Frame (FF)
                ff_data = bytearray(8)
                ff_data[0] = 0x10 | ((payload_len >> 8) & 0x0F)
                ff_data[1] = payload_len & 0xFF
                ff_data[2:8] = payload[:6]

                msg_ff = can.Message(arbitration_id=0x7E8, data=ff_data, is_extended_id=False, timestamp=time.time())
                responses.append(msg_ff)
                self.frame_queue.append(msg_ff)

                # Préparation des Consecutive Frames (CF)
                remaining = payload[6:]
                seq = 1
                self._isotp_pending_consecutive.clear()
                while remaining:
                    chunk = remaining[:7]
                    remaining = remaining[7:]
                    cf_data = bytearray(8)
                    cf_data[0] = 0x20 | (seq & 0x0F)
                    cf_data[1: 1 + len(chunk)] = chunk
                    for i in range(1 + len(chunk), 8):
                        cf_data[i] = 0xAA
                    cf_msg = can.Message(arbitration_id=0x7E8, data=cf_data, is_extended_id=False, timestamp=time.time())
                    self._isotp_pending_consecutive.append(cf_msg)
                    seq = (seq + 1) & 0x0F

            return responses

        # 4. Requête Mode 04 (Effacement des DTCs)
        if len(data) >= 2 and data[1] == 0x04:
            active_dtcs.clear()
            resp_data = [0x01, 0x44, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            msg = can.Message(arbitration_id=0x7E8, data=bytearray(resp_data), is_extended_id=False, timestamp=time.time())
            responses.append(msg)
            self.frame_queue.append(msg)
            return responses

        return responses

    @staticmethod
    def _encode_dtc(code_str: str) -> tuple[int, int] | None:
        """Convertit un code texte standard (ex: 'P0300', 'C0123') en 2 octets ISO-15031-6."""
        code_str = code_str.strip().upper()
        if len(code_str) != 5:
            return None

        letter = code_str[0]
        letter_map = {"P": 0, "C": 1, "B": 2, "U": 3}
        if letter not in letter_map:
            return None

        try:
            d1 = letter_map[letter]
            d2 = int(code_str[1])
            d3 = int(code_str[2], 16)
            d4 = int(code_str[3], 16)
            d5 = int(code_str[4], 16)

            byte_a = (d1 << 6) | (d2 << 4) | d3
            byte_b = (d4 << 4) | d5
            return byte_a, byte_b
        except (ValueError, IndexError):
            return None
