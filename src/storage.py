import json
import os

class PersistentStorage:
    """Gestionnaire de persistance des données avec sécurisation des écritures."""

    def __init__(self, filename="save.json"):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.filepath = os.path.join(base_dir, "data", filename)
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self.data = self._load()

    def _load(self):
        # Définition du schéma de données nominal
        defaults = {
            "trip_a_marker": 0.0,
            "trip_b_marker": 0.0,
            "last_odometer": 0.0,
            "fuel_b_accumulated": 0.0,
            "last_revision_odo": 0.0,
            "last_fuel_price": 1.70
        }

        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    saved_data = json.load(f)
                    for key, default_value in defaults.items():
                        if key not in saved_data:
                            saved_data[key] = default_value
                    return saved_data
            except json.JSONDecodeError:
                pass
        return defaults

    def get(self, key, default=0.0):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self._save()

    def _save(self):
        tmp_path = self.filepath + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(self.data, f)
        os.replace(tmp_path, self.filepath)