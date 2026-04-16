import can

class Slcan:
    """Interface de communication matérielle via SocketCAN (Linux Natif).
    Gère l'initialisation non-bloquante sur la carte réseau virtuelle (ex: can0).
    """

    def __init__(self, channel: str = "can0", baudrate: int = 500000):
        # On garde baudrate dans le constructeur pour ne pas casser le reste du code s'il est appelé,
        # mais il ne sera plus utilisé pour initialiser le bus.
        self.channel = channel
        self.baudrate = baudrate
        self.bus = None
        self.is_connected = False

    def connect(self, can_filters: list = None) -> bool:
        """Tente d'établir la liaison sur l'interface réseau SocketCAN."""
        if self.is_connected:
            return True

        try:
            self.bus = can.interface.Bus(
                bustype="socketcan",  # <--- LE CHANGEMENT MAGIQUE EST ICI
                channel=self.channel,
                can_filters=can_filters
            )
            self.is_connected = True
            return True

        except Exception as e:
            self.is_connected = False
            self.bus = None
            raise RuntimeError(f"Impossible de se connecter à l'interface réseau {self.channel} : {e}")

    def read_frame(self, timeout: float = 0.1) -> can.Message | None:
        """Extrait une trame matérielle du noyau Linux."""
        if not self.is_connected or not self.bus:
            return None

        try:
            return self.bus.recv(timeout)
        except Exception:
            self.close()
            raise RuntimeError("Perte de communication avec la carte réseau CAN.")

    def close(self) -> None:
        """Ferme la socket réseau."""
        if self.bus:
            try:
                self.bus.shutdown()
            except Exception:
                pass

        self.bus = None
        self.is_connected = False

    def send_frame(self, can_id: int, data: list) -> bool:
        """Envoie une trame CAN active sur le réseau."""
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