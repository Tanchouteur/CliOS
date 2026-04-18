import json
import os
import threading
import time


class PersistentStorage:
    """Gestionnaire de persistance des données avec support des chemins imbriqués."""

    def __init__(self, filepath):
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._lock = threading.RLock()
        self._dirty = False
        self._stop_event = threading.Event()
        self.data = self._load()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True, name="StorageFlush")
        self._flush_thread.start()

    def _load(self):
        defaults = {
            "trips": {
                "a": {"marker": 0.0},
                "b": {"marker": 0.0, "fuel": 0.0}
            },
            "vehicle": {
                "last_odometer": 0.0,
                "last_revision_odo": 0.0
            },
            "settings": {
                "last_fuel_price": 1.70
            },
            "services": {}
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

    def get(self, key_path, default=0.0):
        """Récupère une valeur via un chemin. Ex: get('trips.b.fuel')"""
        with self._lock:
            keys = key_path.split('.')
            val = self.data
            for k in keys:
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    return default
            return val

    def set(self, key_path, value):
        """Sauvegarde une valeur via un chemin. Ex: set('services.EngineSound', True)"""
        with self._lock:
            keys = key_path.split('.')
            d = self.data

            # On navigue jusqu'à l'avant-dernier dossier, en le créant si besoin
            for k in keys[:-1]:
                if k not in d or not isinstance(d[k], dict):
                    d[k] = {}
                d = d[k]

            # On assigne la valeur à la dernière clé
            d[keys[-1]] = value
            self._dirty = True

    def set_many(self, entries: dict):
        """Applique plusieurs clés atomiquement en mémoire puis déclenche un flush différé."""
        with self._lock:
            for key_path, value in entries.items():
                keys = key_path.split('.')
                d = self.data
                for k in keys[:-1]:
                    if k not in d or not isinstance(d[k], dict):
                        d[k] = {}
                    d = d[k]
                d[keys[-1]] = value
            self._dirty = True

    def flush(self):
        """Force une écriture disque immédiate des changements en attente."""
        with self._lock:
            if self._dirty:
                self._save_locked()
                self._dirty = False

    def close(self):
        self._stop_event.set()
        self._flush_thread.join(timeout=1.0)
        self.flush()

    def _flush_loop(self):
        while not self._stop_event.is_set():
            time.sleep(0.5)
            self.flush()

    def _save_locked(self):
        tmp_path = self.filepath + ".tmp"
        with open(tmp_path, 'w') as f:
            json.dump(self.data, f, indent=4)
        os.replace(tmp_path, self.filepath)