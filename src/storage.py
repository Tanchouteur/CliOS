import json
import os


class PersistentStorage:
    """Gestionnaire de persistance des données avec sécurisation des écritures."""

    def __init__(self, filename="save.json"):
        # Résolution du chemin absolu vers le répertoire cible
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.filepath = os.path.join(base_dir, "data", filename)

        # Vérification et création de l'arborescence
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

        # Chargement de l'état persistant en mémoire vive
        self.data = self._load()

    def _load(self):
        """Charge le fichier local et assure l'intégrité du schéma de données."""

        # Définition du schéma de données nominal
        defaults = {
            "trip_a_marker": 0.0,
            "trip_b_marker": 0.0,
            "last_odometer": 0.0,
            "fuel_b_accumulated": 0.0,
            "last_revision_odo": 0.0
        }

        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    saved_data = json.load(f)

                    # Rétrocompatibilité : Fusion des clés manquantes dans la structure existante
                    for key, default_value in defaults.items():
                        if key not in saved_data:
                            saved_data[key] = default_value

                    return saved_data
            except json.JSONDecodeError:
                # Interception des corruptions de fichier système
                pass

                # Allocation du schéma par défaut si le fichier est inexistant ou corrompu
        return defaults

    def get(self, key, default=0.0):
        """Accesseur (Getter) avec valeur de repli."""
        return self.data.get(key, default)

    def set(self, key, value):
        """Mutateur (Setter) avec déclenchement automatique de la persistance."""
        self.data[key] = value
        self._save()

    def _save(self):
        """Exécute une transaction d'écriture atomique sur le support de stockage."""
        tmp_path = self.filepath + ".tmp"

        # Écriture séquentielle dans un fichier tampon
        with open(tmp_path, 'w') as f:
            json.dump(self.data, f)

        # Substitution atomique déléguée au système d'exploitation
        # (Prévient la corruption des données en cas de coupure d'alimentation)
        os.replace(tmp_path, self.filepath)