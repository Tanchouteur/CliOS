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

    def __init__(self, service_name: str, storage=None):
        self.service_name = service_name
        self.status = ServiceStatus.OK
        self.status_msg = ""
        self._params = {}
        self.storage = storage
        #print(f"{Color.GREEN}[INIT]{Color.RESET} Service '{self.service_name}' initialisé avec succès.")

    def start(self, stop_event: threading.Event, implemented=False):
        """Doit être implémentée par l'enfant. Lance le thread."""
        print(f"{Color.GREEN}[START]{Color.RESET} Démarrage du service '{self.service_name}'...")

        if not implemented:
            raise NotImplementedError("La méthode start() doit être redéfinie !")

    def stop(self):
        """Méthode optionnelle pour un arrêt propre."""
        print(f"{Color.YELLOW}[STOP]{Color.RESET} Service '{self.service_name}' arrêté.")

    def register_param(self, key: str, label: str, param_type: str, default_val, persistent=True, **kwargs):
        """Enregistre un paramètre. Si persistent=True, le service gère sa propre sauvegarde."""

        val = default_val
        if persistent and self.storage:
            val = self.storage.get(f"services.{self.service_name}.params.{key}", default_val)

        self._params[key] = {
            "key": key,
            "label": label,
            "type": param_type,
            "value": val,
            "persistent": persistent
        }
        self._params[key].update(kwargs)

    def update_param(self, key: str, value):
        """Met à jour la valeur et gère la sauvegarde de manière autonome."""
        if key in self._params:
            self._params[key]["value"] = value

            if self._params[key]["persistent"] and self.storage:
                self.storage.set(f"services.{self.service_name}.params.{key}", value)
                print(
                    f"{Color.BLUE}[INFO]{Color.RESET} {self.service_name} : Paramètre '{key}' sauvegardé sur le disque.")

            self.on_param_changed(key, value)

    def get_params_schema(self) -> list:
        """Retourne la liste des paramètres pour le QML."""
        return list(self._params.values())

    def on_param_changed(self, key: str, value):
        """Méthode à écraser dans l'enfant si le service doit réagir en direct."""
        pass

    def set_ok(self, message: str = ""):
        """Remet le service en état nominal (Vert)."""
        if self.status != ServiceStatus.OK or self.status_msg != message:
            # On colore le [INFO] en bleu
            print(f"{Color.BLUE}[INFO]{Color.RESET} {self.service_name} : Rétablissement du service. {message}")
            self.status = ServiceStatus.OK
            self.status_msg = message

    def set_warning(self, message: str = ""):
        """Passe le service en avertissement (Jaune)."""
        if self.status != ServiceStatus.WARNING or self.status_msg != message:
            # On colore le [WARNING] en jaune
            print(f"{Color.YELLOW}[WARNING]{Color.RESET} {self.service_name} : {message}")
            self.status = ServiceStatus.WARNING
            self.status_msg = message

    def set_error(self, message: str):
        """Passe le service en erreur et enregistre le pourquoi (Rouge)."""
        if self.status != ServiceStatus.ERROR or self.status_msg != message:
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

    def print_message(self, message: str):
        print(f"{Color.BLUE}[INFO]{Color.RESET} {self.service_name} : {message}")