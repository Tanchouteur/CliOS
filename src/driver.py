import can

class Slcan:
    """Interface de communication matérielle pour adaptateurs CAN basés sur le protocole SLCAN.
    Gère l'initialisation non-bloquante et la détection de perte de liaison matérielle.
    """

    def __init__(self, channel: str = "/dev/cu.usbmodem207B3949534B1", baudrate: int = 500000):
        self.channel = channel
        self.baudrate = baudrate
        self.bus = None
        self.is_connected = False

    # --- MODIFICATION : Ajout de can_filters ---
    def connect(self, can_filters: list = None) -> bool:
        """Tente d'établir la liaison série avec filtres matériels optionnels."""
        if self.is_connected:
            return True

        try:
            self.bus = can.interface.Bus(
                bustype="slcan",
                channel=self.channel,
                bitrate=self.baudrate,
                can_filters=can_filters # Le module hardware recevra la liste ici
            )
            self.is_connected = True
            return True

        except Exception as e:
            self.is_connected = False
            self.bus = None
            raise RuntimeError(f"Impossible de se connecter à l'adaptateur CAN sur {self.channel} : {e}")

    def read_frame(self, timeout: float = 0.1) -> can.Message | None:
        """Extrait une trame matérielle. Lève une exception si le périphérique est déconnecté physiquement."""
        if not self.is_connected or not self.bus:
            return None

        try:
            return self.bus.recv(timeout)
        except Exception:
            self.close()
            raise RuntimeError("Perte de communication avec le périphérique série.")

    def close(self) -> None:
        """Libère le descripteur de fichier série et réinitialise l'état interne."""
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass

        self.bus = None
        self.is_connected = False

    def send_frame(self, can_id: int, data: list) -> bool:
        """Envoie une trame CAN active (Ex: Requête OBD2)."""
        if not self.is_connected or not self.bus:
            return False

        try:
            msg = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=False
            )
            self.bus.send(msg)
            return True
        except Exception as e:
            self.close()
            raise RuntimeError(f"Échec de l'envoi CAN : {e}")