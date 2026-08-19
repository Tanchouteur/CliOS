import can

class Slcan:
    """Interface de communication matérielle via SocketCAN (Linux Natif).
    Désormais 100% plug & play via le module noyau gs_usb (firmware candlelight).
    """

    def __init__(self, channel: str = "can0", baudrate: int = 500000):
        self.channel = channel
        self.bus = None
        self.is_connected = False

    def connect(self, can_filters: list = None) -> bool:
        """Se connecte directement à l'interface réseau SocketCAN."""
        if self.is_connected:
            return True

        try:
            self.bus = can.interface.Bus(
                bustype="socketcan",
                channel=self.channel,
                can_filters=can_filters,
            )
            self.is_connected = True
            return True

        except Exception as e:
            self.is_connected = False
            self.bus = None
            raise RuntimeError(f"Impossible de se connecter au réseau {self.channel}. L'interface est-elle UP sous Linux ? : {e}")

    def read_frame(self, timeout: float = 0.1) -> can.Message | None:
        """Extrait une trame matérielle du noyau Linux."""
        if not self.is_connected or not self.bus:
            return None

        try:
            msg = self.bus.recv(timeout)
            if msg is not None and msg.is_error_frame:
                return None
            return msg
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