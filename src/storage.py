import json
import os
import threading

from src.logging_runtime import get_logger


class PersistentStorage:
    """Gestionnaire de persistance des données avec support des chemins imbriqués."""

    def __init__(self, filepath):
        self.filepath = filepath
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        self._lock = threading.RLock()
        self._dirty = False
        self._modified_paths = set()
        self._write_healthy = True
        self._stop_event = threading.Event()
        self.logger = get_logger("PersistentStorage")
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
            except (OSError, json.JSONDecodeError, TypeError):
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
            self._modified_paths.add(key_path)
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
                self._modified_paths.add(key_path)
            self._dirty = True

    def flush(self):
        """Force une écriture disque immédiate des changements en attente."""
        with self._lock:
            if self._dirty:
                if self._save_locked():
                    self._dirty = False

    def close(self):
        self._stop_event.set()
        self._flush_thread.join(timeout=1.0)
        self.flush()

    def _flush_loop(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(0.5)
            self.flush()

    def _save_locked(self):
        tmp_path = self.filepath + ".tmp"
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.filepath)
            self._write_healthy = True
            return True
        except OSError as exc:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            if self._write_healthy:
                self.logger.error(
                    "Ecriture du stockage impossible: %s",
                    exc,
                    extra={"error_code": "STORAGE_WRITE_FAILED"},
                )
                self._write_healthy = False
            return False

    def relocate(self, new_filepath: str, merge_existing: bool = True) -> bool:
        """Bascule de cible en conservant les mutations de la session en cours.

        Lors d'un retour vers une clé existante, seules les clés réellement modifiées
        par ce processus écrasent les valeurs déjà persistées sur la clé.
        """
        new_filepath = os.path.abspath(new_filepath)
        with self._lock:
            if new_filepath == os.path.abspath(self.filepath):
                self._dirty = True
                return self._save_locked()

            current_data = self.data
            target_data = self._read_dict(new_filepath) if merge_existing else None
            if target_data is not None:
                merged = target_data
                self._merge_missing(merged, current_data)
                for key_path in self._modified_paths:
                    self._set_nested(merged, key_path, self._get_nested(current_data, key_path))
                self.data = merged

            self.filepath = new_filepath
            self._dirty = True
            if self._save_locked():
                self._dirty = False
                return True
            return False

    @staticmethod
    def _read_dict(filepath):
        if not os.path.isfile(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            return payload if isinstance(payload, dict) else None
        except (OSError, json.JSONDecodeError, TypeError):
            return None

    @staticmethod
    def _get_nested(data, key_path):
        value = data
        for key in key_path.split('.'):
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value

    @staticmethod
    def _set_nested(data, key_path, value):
        keys = key_path.split('.')
        cursor = data
        for key in keys[:-1]:
            if key not in cursor or not isinstance(cursor[key], dict):
                cursor[key] = {}
            cursor = cursor[key]
        cursor[keys[-1]] = value

    @classmethod
    def _merge_missing(cls, destination, source):
        for key, value in source.items():
            if key not in destination:
                destination[key] = value
            elif isinstance(destination[key], dict) and isinstance(value, dict):
                cls._merge_missing(destination[key], value)
