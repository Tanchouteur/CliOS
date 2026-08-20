import threading
from enum import Enum
from typing import Any, cast

from src.logging_runtime import get_logger
from src.services.param_types import (
    ServiceParamType,
    coerce_param_value,
    normalize_param_type,
)

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
    """Service API v1 : identité, paramètres typés, santé et cycle de vie."""

    API_VERSION = 1

    def __init__(self, service_name: str, storage=None, *, service_id: str | None = None,
                 description: str = "", version: str = "1.0.0"):
        self.service_name = service_name
        self.service_id = service_id or service_name
        if not self.service_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for char in self.service_id):
            raise ValueError("service_id doit être stable et ne contenir que lettres, chiffres, _, . ou -")
        self.metadata = {
            "api_version": self.API_VERSION,
            "id": self.service_id,
            "name": service_name,
            "description": description,
            "version": version,
        }
        self.lifecycle_state = "CREATED"
        self.status = ServiceStatus.OK
        self.status_msg = ""
        self._params = {}
        self.storage = storage
        self.logger = get_logger(f"Service.{self.service_name}")
        self._state_lock = threading.RLock()
        self._stop_event = None
        #print(f"{Color.GREEN}[INIT]{Color.RESET} Service '{self.service_name}' initialisé avec succès.")

    def start(self, stop_event: threading.Event, implemented=False):
        """Doit être implémentée par l'enfant. Lance le thread."""
        self.logger.info("Demarrage du service", extra={"error_code": "SERVICE_START"})

        if not implemented:
            raise NotImplementedError("La méthode start() doit être redéfinie !")
        self._stop_event = stop_event
        self.lifecycle_state = "RUNNING"

    def stop(self):
        """Arrêt commun : signale puis rejoint les workers connus."""
        if self._stop_event is not None:
            self._stop_event.set()
        current = threading.current_thread()
        seen = set()
        for attr in ("_thread", "thread"):
            worker = getattr(self, attr, None)
            if worker and worker not in seen and worker is not current and worker.is_alive():
                seen.add(worker)
                worker.join(timeout=2.0)
        self.logger.info("Arret du service", extra={"error_code": "SERVICE_STOP"})
        self.lifecycle_state = "STOPPED"

    def register_param(self, key: str, label: str, param_type: str | ServiceParamType, default_val, persistent=True, **kwargs):
        """Enregistre un paramètre. Si persistent=True, le service gère sa propre sauvegarde."""

        normalized_type = normalize_param_type(param_type)

        val = default_val
        if persistent and self.storage:
            val = self.storage.get(f"services.{self.service_name}.params.{key}", default_val)

        schema = {
            "key": key,
            "label": label,
            "type": normalized_type.value,
            "persistent": persistent,
            "default": default_val,
        }
        schema.update(kwargs)
        coerced = coerce_param_value(normalized_type, val, default_val, schema)

        self._params[key] = {
            "key": key,
            "label": label,
            "type": normalized_type.value,
            "value": coerced,
            "persistent": persistent
        }
        self._params[key].update(kwargs)

    def update_param(self, key: str, value):
        """Met à jour la valeur et gère la sauvegarde de manière autonome."""
        with self._state_lock:
            if key not in self._params:
                return
            param = self._params[key]
            param_type = normalize_param_type(param.get("type"))
            default_val = param.get("default", param.get("value"))

            schema = cast(dict[str, Any], dict(param))
            schema["default"] = default_val
            coerced = coerce_param_value(param_type, value, default_val, schema)
            param["value"] = coerced
            persistent = bool(param["persistent"])

        if persistent and self.storage:
            self.storage.set(f"services.{self.service_name}.params.{key}", coerced)
            self.logger.info(
                "Parametre persiste",
                extra={"error_code": "SERVICE_PARAM_SAVED"}
            )

        self.on_param_changed(key, coerced)

    def get_params_schema(self) -> list:
        """Retourne la liste des paramètres pour le QML."""
        with self._state_lock:
            return [dict(param) for param in self._params.values()]

    @staticmethod
    def get_supported_param_types() -> list[str]:
        """Expose la liste des types connus pour aide dev/autocomplétion."""
        return [p.value for p in ServiceParamType]

    def on_param_changed(self, key: str, value):
        """Méthode à écraser dans l'enfant si le service doit réagir en direct."""
        pass

    def set_ok(self, message: str = ""):
        """Remet le service en état nominal (Vert)."""
        with self._state_lock:
            changed = self.status != ServiceStatus.OK or self.status_msg != message
            if changed:
                self.status = ServiceStatus.OK
                self.status_msg = message
        if changed:
            self.logger.info(f"Retablissement du service. {message}", extra={"error_code": "SERVICE_OK"})

    def set_warning(self, message: str = ""):
        """Passe le service en avertissement (Jaune)."""
        with self._state_lock:
            changed = self.status != ServiceStatus.WARNING or self.status_msg != message
            if changed:
                self.status = ServiceStatus.WARNING
                self.status_msg = message
        if changed:
            self.logger.warning(message, extra={"error_code": "SERVICE_WARNING"})

    def set_error(self, message: str):
        """Passe le service en erreur et enregistre le pourquoi (Rouge)."""
        with self._state_lock:
            changed = self.status != ServiceStatus.ERROR or self.status_msg != message
            if changed:
                self.status = ServiceStatus.ERROR
                self.status_msg = message
        if changed:
            self.logger.error(message, extra={"error_code": "SERVICE_ERROR"})

    def get_health(self) -> dict:
        """Retourne l'état de santé du service pour le QML."""
        with self._state_lock:
            return {
                "status": self.status.value,
                "message": self.status_msg,
                "service_id": self.service_id,
                "api_version": self.API_VERSION,
                "lifecycle": self.lifecycle_state,
            }

    def get_metadata(self) -> dict:
        return dict(self.metadata)

    def print_message(self, message: str):
        self.logger.info(message)
