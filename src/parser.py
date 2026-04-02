import json


class DbcParser:
    """Analyseur de base de données CAN (DBC formaté en JSON).
    Gère la mise en cache et la résolution des identifiants de trames vers leurs définitions de signaux.
    """

    def __init__(self, filepath: str):
        # Chargement statique du dictionnaire en mémoire vive lors de l'instanciation.
        # Cette approche prévient les opérations d'E/S (I/O) bloquantes sur le disque
        # lors du traitement à haute fréquence des trames entrantes.
        with open(filepath, 'r') as f:
            self.db = json.load(f)

    def get_definition(self, frame_id: int) -> dict | None:
        """Retourne la structure de définition associée à un identifiant de trame.

        Args:
            frame_id (int): L'identifiant brut de la trame CAN (base décimale).

        Returns:
            dict | None: Le dictionnaire de configuration du payload, ou None si non référencé.
        """
        # Conversion du format de l'identifiant pour la résolution de clé de hachage (ex: 385 -> "0x181")
        hex_id = hex(frame_id).lower()
        return self.db.get(hex_id)