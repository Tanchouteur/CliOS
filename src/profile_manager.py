import json
import os
import threading

from src.logging_runtime import get_logger


class ProfileManager:
    """Gère les profils de véhicules, la validation des fichiers et l'exposition pour l'UI."""

    def __init__(self, config_dir: str, can_dir: str, save_dash_dir: str, is_mock: bool = False,
                 fallback_config_dir: str | None = None):
        self.config_dir = config_dir
        self.can_dir = can_dir
        self.save_dash_dir = save_dash_dir
        self.is_mock = is_mock
        self.fallback_config_dir = fallback_config_dir
        self._lock = threading.RLock()
        self.logger = get_logger("ProfileManager")

        self.profiles_path = os.path.join(self.config_dir, "profiles.json")

        # État de validation du profil actif.
        self.has_error = False
        self.error_message = ""

        self.data = self._load()
        self._validate_and_fallback()

    def _load(self) -> dict:
        """Charge le fichier JSON en mémoire ou crée une structure de base."""
        if os.path.exists(self.profiles_path):
            try:
                with open(self.profiles_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    return payload
            except (OSError, json.JSONDecodeError, TypeError):
                pass

        if self.fallback_config_dir:
            fallback_path = os.path.join(self.fallback_config_dir, "profiles.json")
            try:
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    self._write_json_atomic(self.profiles_path, payload)
                    return payload
            except (OSError, json.JSONDecodeError, TypeError):
                pass

        return {
            "active_profile": "default",
            "profiles": {
                "default": {
                    "name": "Profil par défaut",
                    "can_file": "default_can.json",
                    "config_file": "default_config.json",
                    "save_file": "save.json"
                }
            }
        }

    def save(self):
        """Sauvegarde les modifications sur le disque."""
        tmp_path = self.profiles_path + ".tmp"
        with self._lock:
            try:
                os.makedirs(self.config_dir, exist_ok=True)
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, self.profiles_path)
                return True
            except OSError as exc:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass
                self.logger.error(
                    "Sauvegarde des profils impossible: %s",
                    exc,
                    extra={"error_code": "PROFILE_SAVE_FAILED"},
                )
                return False

    def relocate(self, config_dir: str, save_dash_dir: str) -> bool:
        """Bascule les chemins modifiables lors d'un hot-plug/unplug."""
        with self._lock:
            self.config_dir = config_dir
            self.save_dash_dir = save_dash_dir
            self.profiles_path = os.path.join(self.config_dir, "profiles.json")
            return self.save()

    def _validate_and_fallback(self):
        """Vérifie si les fichiers du profil actif existent. Sinon, force le fallback."""
        active_id = self.data.get("active_profile", "default")

        # Vérifie que le profil actif existe dans la configuration.
        if active_id not in self.data.get("profiles", {}):
            self.has_error = True
            self.error_message = f"Le profil '{active_id}' n'existe pas. Chargement du profil par défaut."
            self.data["active_profile"] = "default"
            self.save()
            return

        # Vérifie l'existence des fichiers associés au profil.
        info = self.data["profiles"][active_id]
        can_path = self.get_can_path()
        config_path = self.get_config_path()

        errors = []
        if not os.path.exists(can_path) and not self.is_mock:
            errors.append(f"CAN manquant ({info.get('can_file')})")
        if not os.path.exists(config_path):
            errors.append(f"Config manquante ({info.get('config_file')})")

        if errors:
            self.has_error = True
            self.error_message = f"Erreur Profil '{info.get('name')}' : " + " | ".join(
                errors) + ". Retour aux paramètres par défaut."
            self.data["active_profile"] = "default"
            self.save()

    def get_available_profiles(self) -> list:
        """Retourne la liste des identifiants (clés) des profils disponibles."""
        return list(self.data.get("profiles", {}).keys())

    def set_active_profile(self, profile_id: str) -> bool:
        """Change le profil actif pour le prochain redémarrage et sauvegarde sur le disque."""
        if profile_id in self.data.get("profiles", {}):
            self.data["active_profile"] = profile_id
            self.save()
            return True
        return False

    # Résolution des chemins utilisés par l'application.
    @property
    def active_profile_id(self) -> str:
        return self.data.get("active_profile", "default")

    @property
    def active_info(self) -> dict:
        return self.data.get("profiles", {}).get(self.active_profile_id, {})

    def get_config_path(self) -> str:
        filename = self._safe_json_filename(self.active_info.get("config_file"), "default_config.json")
        return os.path.join(self.config_dir, filename)

    def load_active_config(self) -> dict:
        """Charge la config active, avec réparation depuis la copie statique."""
        target_path = self.get_config_path()
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                return payload
        except (OSError, json.JSONDecodeError, TypeError):
            pass

        filename = os.path.basename(target_path)
        if self.fallback_config_dir:
            fallback_path = os.path.join(self.fallback_config_dir, filename)
            try:
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    self._write_json_atomic(target_path, payload)
                    return payload
            except (OSError, json.JSONDecodeError, TypeError):
                pass
        raise RuntimeError(f"Configuration véhicule illisible: {filename}")

    def get_can_path(self) -> str:
        filename = self._safe_json_filename(self.active_info.get("can_file"), "default_can.json")
        return os.path.join(self.can_dir, filename)

    def get_save_path(self) -> str:
        if self.is_mock:
            return os.path.join(self.save_dash_dir, "save_mock.json")
        filename = self._safe_json_filename(self.active_info.get("save_file"), "save.json")
        return os.path.join(self.save_dash_dir, filename)

    # Méthodes exposées à l'interface.
    def get_available_can_files(self) -> list:
        """Retourne la liste des fichiers CAN disponibles."""
        if not os.path.exists(self.can_dir): return []
        return [f for f in os.listdir(self.can_dir) if f.endswith('.json')]

    def get_available_config_files(self) -> list:
        """Retourne la liste des fichiers de configuration (en ignorant profiles.json)."""
        if not os.path.exists(self.config_dir): return []
        return [f for f in os.listdir(self.config_dir) if f.endswith('.json') and f != "profiles.json"]

    def create_new_config(self, new_filename: str) -> bool:
        """Crée une nouvelle configuration vierge (copie d'un modèle)."""
        if os.path.basename(new_filename) != new_filename or not new_filename.endswith(".json"):
            return False
        target_path = os.path.join(self.config_dir, new_filename)
        if os.path.exists(target_path):
            return False

        # Crée une configuration minimale.
        base_config = {
            "dashboard": {
                "max_rpm": 7000,
                "redline": 6000,
                "max_speed": 220
            }
        }
        tmp_path = target_path + ".tmp"
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(base_config, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target_path)
            return True
        except OSError:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            return False

    def add_profile(self, profile_id: str, name: str, can_file: str, config_file: str, save_file: str):
        """Ajoute un nouveau profil au trousseau."""
        if not profile_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in profile_id):
            return False
        if any(self._safe_json_filename(value, "") != value for value in (can_file, config_file, save_file)):
            return False
        if "profiles" not in self.data:
            self.data["profiles"] = {}

        self.data["profiles"][profile_id] = {
            "name": name,
            "can_file": can_file,
            "config_file": config_file,
            "save_file": save_file
        }
        return self.save()

    @staticmethod
    def _safe_json_filename(value, default: str) -> str:
        filename = str(value or "")
        if filename and os.path.basename(filename) == filename and filename.endswith(".json"):
            return filename
        return default

    @staticmethod
    def _write_json_atomic(path: str, payload: dict) -> bool:
        tmp_path = path + ".tmp"
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            return True
        except OSError:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            return False
