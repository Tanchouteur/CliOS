from src.parser import DbcParser
from src.signal_processor import RawFrame, SignalProcessor
from src.api import VehicleAPI


class CanDispatcher:
    """Orchestrateur de traitement des flux télémétriques.
    Assure le routage des trames brutes matérielles vers les modules de décodage
    et synchronise la mise à jour du modèle de données (API).
    """

    def __init__(self, parser: DbcParser, processor: SignalProcessor, api: VehicleAPI):
        self.parser = parser
        self.processor = processor
        self.api = api

    def dispatch(self, can_message):
        """Point d'entrée de la chaîne de traitement asynchrone pour chaque trame acquise."""

        # Encapsulation de la trame matérielle (python-can) dans une structure de données interne agnostique
        frame = RawFrame(id=can_message.arbitration_id, data=can_message.data, timestamp=can_message.timestamp)

        # Résolution du schéma de décodage via l'identifiant d'arbitration CAN
        definition = self.parser.get_definition(frame.id)

        if not definition:
            # Filtrage préemptif : Rejet silencieux des trames non référencées
            # afin de limiter la charge d'interruption du processeur (CPU overhead).
            return

        # Extraction et conversion du payload binaire en structure de données exploitables
        decoded_data = self.processor.decode(frame, definition)

        # Propagation des nouvelles occurrences de signaux vers le moteur d'état du véhicule
        if decoded_data:
            self.api.update(decoded_data)