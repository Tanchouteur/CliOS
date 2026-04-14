import time
import random
import json
import can


class MockProvider:
    """Émulateur d'interface matérielle CAN avec architecture de maintien d'état."""

    def __init__(self, json_path):
        with open(json_path, 'r') as f:
            self.db = json.load(f)

        self.ids = [int(k, 16) for k in self.db.keys()]
        self.rpm = 800
        self.protected_ids = [0x5C5, 0x715, 0x5FD, 0x354]
        self.is_connected = False

    def connect(self) -> bool:
        """Initialisation immédiate de l'interface virtuelle."""
        self.is_connected = True
        print("[INFO] Simulateur materiel (MockProvider) synchronise.")
        return True

    def read_frame(self, timeout=0.1):
        if not self.is_connected:
            return None

        time.sleep(0.02)

        random_id = random.choice(self.ids)
        while random_id in self.protected_ids:
            random_id = random.choice(self.ids)

        data = bytearray(8)

        if random_id == 0x181:
            self.rpm += random.randint(-100, 200)
            if self.rpm < 800: self.rpm = 800
            if self.rpm > 5000: self.rpm = 4500

            raw_val = int(self.rpm * 8)
            data[0] = (raw_val >> 8) & 0xFF
            data[1] = raw_val & 0xFF

        elif random_id == 0x551:
            cycle = int(time.time() / 4) % 2
            if cycle == 0:
                data[4] = 110
                data[5] = 0x52
            elif cycle == 1:
                data[4] = 110
                data[5] = 0x42
        else:
            data = bytearray(random.getrandbits(8) for _ in range(8))

        return can.Message(arbitration_id=random_id, data=data, timestamp=time.time())

    def close(self):
        """Clôture du processus de simulation."""
        self.is_connected = False