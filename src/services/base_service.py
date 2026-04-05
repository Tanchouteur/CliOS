import threading
from enum import Enum

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

    def start(self, stop_event: threading.Event):
        """Doit être implémentée par l'enfant. Lance le thread."""
        raise NotImplementedError("La méthode start() doit être redéfinie !")

    def stop(self):
        """Méthode optionnelle pour un arrêt propre."""
        pass

    def set_ok(self, message: str = ""):
        """Remet le service en état nominal (Vert)."""
        # On évite de spammer la console si c'était déjà OK
        if self.status != ServiceStatus.OK:
            print(f"[INFO] {self.service_name} : Rétablissement du service. {message}")
            self.status = ServiceStatus.OK
            self.status_msg = message

    def set_warning(self, message: str = ""):
        """Remet le service en état nominal (Vert)."""
        if self.status != ServiceStatus.WARNING:
            print(f"[WARNING] {self.service_name} : WARNING du service. {message}")
            self.status = ServiceStatus.OK
            self.status_msg = message

    def set_error(self, message: str):
        """Passe le service en erreur et enregistre le pourquoi."""
        if self.status != ServiceStatus.ERROR:
            self.status = ServiceStatus.ERROR
            self.status_msg = message
            print(f"[ERREUR] {self.service_name} : {message}")

    def get_health(self) -> dict:
        """Retourne l'état de santé du service pour le QML."""
        return {
            "status": self.status.value,
            "message": self.status_msg
        }