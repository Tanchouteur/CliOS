import json

class DbcParser:
    def __init__(self, filepath: str):
        with open(filepath, 'r') as f:
            raw_db = json.load(f)

        self.optimized_db = {}

        for hex_id, definition in raw_db.items():
            int_id = int(hex_id, 16)

            if "signals" in definition:
                for sig_name, sig_def in definition["signals"].items():
                    sig_def.setdefault("factor", 1.0)
                    sig_def.setdefault("offset", 0.0)
                    sig_def.setdefault("shift", 0)
                    sig_def.setdefault("size", 1)
                    sig_def.setdefault("start_byte", 0)
                    sig_def.setdefault("endian", "big")
                    sig_def.setdefault("signed", False)
                    sig_def.setdefault("unit", None)
                    sig_def.setdefault("min_value", None)
                    sig_def.setdefault("max_value", None)
                    sig_def.setdefault("bit_length", sig_def["size"] * 8)

                    if sig_def["endian"] not in {"big", "little"}:
                        raise ValueError(f"Endianness invalide pour {sig_name}: {sig_def['endian']}")
                    if int(sig_def["size"]) <= 0 or int(sig_def["start_byte"]) < 0:
                        raise ValueError(f"Position/taille invalide pour {sig_name}")

                    if "mask" in sig_def:
                        sig_def["mask_val"] = int(sig_def["mask"], 16)
                    else:
                        sig_def["mask_val"] = None

                    sig_def["is_bits"] = "bits" in sig_def

            self.optimized_db[int_id] = definition

    def get_definition(self, frame_id: int) -> dict | None:
        return self.optimized_db.get(frame_id)
