from src.signal_processor import RawFrame
import time


class CanDispatcher:
    """
    Orchestrateur de traitement des flux telemetriques.
    Integre un filtrage preemptif et un sous-echantillonnage (rate limiting)
    pour eviter la saturation du processeur (CPU overhead).
    """

    def __init__(self, parser, processor, api):
        self.parser = parser
        self.processor = processor
        self.api = api

        # Configuration de la limite de frequence (Rate Limiting)
        # 70 Hz = 1 trame traitée toutes les ~0.0142 secondes
        self._rate_limit_sec = 1.0 / 70.0
        self._last_seen_time = {}

    def dispatch(self, can_message):
        """
        Traite une trame materielle avec filtrage et limitation de frequence.

        Args:
            can_message: Objet trame issu de python-can.
        """
        msg_id = can_message.arbitration_id

        # 1. Filtrage preemptif (O(1))
        # Rejet silencieux avant toute allocation memoire.
        definition = self.parser.get_definition(msg_id)
        if not definition:
            return

        # 2. Sous-echantillonnage temporel (Rate Limiting)
        # Empeche le traitement redondant si la frequence depasse 70Hz pour un meme ID.
        current_time = time.time()
        last_time = self._last_seen_time.get(msg_id, 0.0)

        if (current_time - last_time) < self._rate_limit_sec:
            return

        self._last_seen_time[msg_id] = current_time

        # 3. Encapsulation tardive (Lazy Instantiation)
        # L'objet RawFrame n'est instancie que si la trame est valide et utile.
        frame = RawFrame(
            id=msg_id,
            data=can_message.data,
            timestamp=can_message.timestamp
        )

        # 4. Decodage et mise a jour du modele de donnees
        decoded_data = self.processor.decode(frame, definition)

        if decoded_data:
            self.api.update(decoded_data)