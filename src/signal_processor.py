from dataclasses import dataclass


@dataclass
class RawFrame:
    id: int
    data: bytearray
    timestamp: float


class SignalProcessor:
    def decode(self, frame: RawFrame, definition: dict) -> dict:
        results = {}
        frame_data = frame.data
        data_len = len(frame_data)

        for sig_name, sig_def in definition["signals"].items():
            start = sig_def["start_byte"]
            size = sig_def["size"]

            if start + size > data_len:
                continue

            endian = sig_def["endian"]

            # Décodage des signaux bit-à-bit.
            if sig_def["is_bits"]:
                # Construit le champ binaire sur la taille déclarée.
                raw_bytes = frame_data[start: start + size]
                combined_bits = int.from_bytes(raw_bytes, byteorder=endian)

                for bit_name, bit_pos in sig_def["bits"].items():
                    results[bit_name] = bool((combined_bits >> bit_pos) & 1)

            # Décodage des signaux numériques.
            else:
                raw_bytes = frame_data[start: start + size]
                raw_int = int.from_bytes(raw_bytes, byteorder=endian)

                if sig_def["mask_val"] is not None:
                    raw_int &= sig_def["mask_val"]

                if sig_def["shift"] > 0:
                    raw_int >>= sig_def["shift"]

                if sig_def.get("signed", False):
                    bit_length = int(sig_def.get("bit_length", size * 8))
                    sign_bit = 1 << (bit_length - 1)
                    if raw_int & sign_bit:
                        raw_int -= 1 << bit_length

                physical = (raw_int * sig_def["factor"]) + sig_def["offset"]
                min_value = sig_def.get("min_value")
                max_value = sig_def.get("max_value")
                if min_value is not None and physical < min_value:
                    continue
                if max_value is not None and physical > max_value:
                    continue
                results[sig_name] = physical

        return results
