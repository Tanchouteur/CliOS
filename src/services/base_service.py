import threading
from enum import Enum

class Color:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'

class ServiceStatus(Enum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"

class BaseService:
    """Classe parente (Interface) pour tous les services d'arrière-plan."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.status = ServiceStatus.OK
        self.status_msg = ""
        print(f"{Color.GREEN}[INIT]{Color.RESET} Service '{self.service_name}' initialisé avec succès.")

    def start(self, stop_event: threading.Event, implemented=False):
        """Doit être implémentée par l'enfant. Lance le thread."""
        print(f"{Color.GREEN}[START]{Color.RESET} Démarrage du service '{self.service_name}'...")

        if not implemented:
            raise NotImplementedError("La méthode start() doit être redéfinie !")

    def stop(self):
        """Méthode optionnelle pour un arrêt propre."""
        print(f"{Color.YELLOW}[STOP]{Color.RESET} Service '{self.service_name}' arrêté.")

    def set_ok(self, message: str = ""):
        """Remet le service en état nominal (Vert)."""
        # On évite de spammer la console si c'était déjà OK
        if self.status != ServiceStatus.OK:
            # On colore le [INFO] en bleu
            print(f"{Color.BLUE}[INFO]{Color.RESET} {self.service_name} : Rétablissement du service. {message}")
            self.status = ServiceStatus.OK
            self.status_msg = message

    def set_warning(self, message: str = ""):
        """Passe le service en avertissement (Jaune)."""
        if self.status != ServiceStatus.WARNING:
            # On colore le [WARNING] en jaune
            print(f"{Color.YELLOW}[WARNING]{Color.RESET} {self.service_name} : {message}")
            self.status = ServiceStatus.WARNING
            self.status_msg = message

    def set_error(self, message: str):
        """Passe le service en erreur et enregistre le pourquoi (Rouge)."""
        if self.status != ServiceStatus.ERROR:
            # On colore le [ERREUR] en rouge
            print(f"{Color.RED}[ERREUR]{Color.RESET} {self.service_name} : {message}")
            self.status = ServiceStatus.ERROR
            self.status_msg = message

    def get_health(self) -> dict:
        """Retourne l'état de santé du service pour le QML."""
        return {
            "status": self.status.value,
            "message": self.status_msg
        }