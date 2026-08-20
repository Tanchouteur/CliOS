import threading

from src.logging_runtime import get_logger


class SystemOrchestrator:
    """Gestionnaire centralisé et dynamique du cycle de vie des services."""

    def __init__(self):
        # Structure : { objet_service: {"event": threading.Event() ou None, "enabled": bool} }
        self.services = {}
        self.is_running = False
        self.logger = get_logger("Orchestrator")
        self._lock = threading.RLock()

    def add_service(self, service, enabled=True):
        """Enregistre un service dans le tableau électrique."""
        with self._lock:
            self.services[service] = {"event": None, "enabled": enabled}
            running = self.is_running

        # Démarrage à chaud si l'orchestrateur tourne déjà et que le service est activé
        if running and enabled:
            self.start_service(service.service_name)

    def start_service(self, service_name: str):
        """Allume l'interrupteur d'un service spécifique."""
        with self._lock:
            services = list(self.services.items())
        for srv, data in services:
            if srv.service_name == service_name:
                with self._lock:
                    data["enabled"] = True
                    should_start = self.is_running and (data["event"] is None or data["event"].is_set())
                    if should_start:
                        data["event"] = threading.Event()
                        event = data["event"]
                if should_start:
                    try:
                        srv.start(event)
                    except Exception as e:
                        self.logger.error(f"Erreur au démarrage du service {service_name}: {e}", extra={"error_code": "SRV_START_ERR"})
                return
        self.logger.warning(f"Service introuvable au demarrage: {service_name}", extra={"error_code": "SERVICE_NOT_FOUND"})

    def stop_service(self, service_name: str):
        """Coupe le courant d'un service sans le supprimer de la mémoire."""
        with self._lock:
            services = list(self.services.items())
        for srv, data in services:
            if srv.service_name == service_name:
                with self._lock:
                    data["enabled"] = False
                    should_stop = bool(data["event"] and not data["event"].is_set())
                    if should_stop:
                        data["event"].set()
                if should_stop:
                    try:
                        srv.stop()
                    except Exception as e:
                        self.logger.error(f"Erreur à l'arrêt du service {service_name}: {e}", extra={"error_code": "SRV_STOP_ERR"})
                return

    def start_all(self):
        """Démarre UNIQUEMENT les services cochés 'enabled'."""
        with self._lock:
            if self.is_running:
                return
            self.is_running = True
            services = list(self.services.items())
        for srv, data in services:
            if data["enabled"]:
                with self._lock:
                    if data["event"] is not None and not data["event"].is_set():
                        continue
                    data["event"] = threading.Event()
                    event = data["event"]
                try:
                    srv.start(event)
                except Exception as e:
                    self.logger.error(f"Erreur démarrage service {srv.service_name}: {e}", extra={"error_code": "SRV_START_ERR"})

    def stop_all(self):
        """Coupe absolument tout."""
        #print("[INFO] Orchestrateur : Signal d'arrêt global envoyé.")
        with self._lock:
            self.is_running = False
            services = list(self.services.items())
        for srv, data in services:
            if data["event"] and not data["event"].is_set():
                data["event"].set()
                srv.stop()

    def get_system_health(self) -> dict:
        """Récupère l'état de tous les services actifs ou signale ceux désactivés."""
        health = {}
        with self._lock:
            services = list(self.services.items())
        for srv, data in services:
            if data["enabled"]:
                health[srv.service_name] = srv.get_health()
            else:
                health[srv.service_name] = {
                    "status": "DISABLED",
                    "message": "Désactivé dans les réglages"
                }
        return health
