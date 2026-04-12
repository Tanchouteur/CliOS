import json
import os
import shutil


class ProfileManager:
    """Gère les profils de véhicules, la validation des fichiers et l'exposition pour l'UI."""

    def __init__(self, config_dir: str, can_dir: str, storage_dir: str, is_mock: bool = False):
        self.config_dir = config_dir
        self.can_dir = can_dir
        self.storage_dir = storage_dir
        self.is_mock = is_mock

        self.profiles_path = os.path.join(self.config_dir, "profiles.json")

        # --- ÉTAT DU PROFIL ---
        self.has_error = False
        self.error_message = ""

        self.data = self._load()
        self._validate_and_fallback()

    def _load(self) -> dict:
        """Charge le fichier JSON en mémoire ou crée une structure de base."""
        if not os.path.exists(self.profiles_path):
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
        with open(self.profiles_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save(self):
        """Sauvegarde les modifications sur le disque."""
        with open(self.profiles_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def _validate_and_fallback(self):
        """Vérifie si les fichiers du profil actif existent. Sinon, force le fallback."""
        active_id = self.data.get("active_profile", "default")

        # Si l'ID n'existe même pas dans le dictionnaire
        if active_id not in self.data.get("profiles", {}):
            self.has_error = True
            self.error_message = f"Le profil '{active_id}' n'existe pas. Chargement du profil par défaut."
            self.data["active_profile"] = "default"
            self.save()
            return

        # Vérification physique des fichiers
        info = self.data["profiles"][active_id]
        can_path = os.path.join(self.can_dir, info.get("can_file", ""))
        config_path = os.path.join(self.config_dir, info.get("config_file", ""))

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

    # --- RÉSOLUTION DES CHEMINS (Utilisés par main.py) ---
    @property
    def active_profile_id(self) -> str:
        return self.data.get("active_profile", "default")

    @property
    def active_info(self) -> dict:
        return self.data.get("profiles", {}).get(self.active_profile_id, {})

    def get_config_path(self) -> str:
        return os.path.join(self.config_dir, self.active_info.get("config_file", "default_config.json"))

    def get_can_path(self) -> str:
        return os.path.join(self.can_dir, self.active_info.get("can_file", "default_can.json"))

    def get_save_path(self) -> str:
        if self.is_mock:
            return os.path.join(self.storage_dir, "save_mock.json")
        return os.path.join(self.storage_dir, self.active_info.get("save_file", "save.json"))

    # --- MÉTHODES POUR L'INTERFACE (QML / Bridge) ---
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
        target_path = os.path.join(self.config_dir, new_filename)
        if os.path.exists(target_path):
            return False  # Le fichier existe déjà

        # On crée une config standard de base (tu la remplaceras par tes vraies valeurs)
        base_config = {
            "dashboard": {
                "max_rpm": 7000,
                "redline": 6000,
                "max_speed": 220
            }
        }
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(base_config, f, indent=4)
        return True

    def add_profile(self, profile_id: str, name: str, can_file: str, config_file: str, save_file: str):
        """Ajoute un nouveau profil au trousseau."""
        if "profiles" not in self.data:
            self.data["profiles"] = {}

        self.data["profiles"][profile_id] = {
            "name": name,
            "can_file": can_file,
            "config_file": config_file,
            "save_file": save_file
        }
        self.save()