import threading


class SystemOrchestrator:
    """Gestionnaire centralisé et dynamique du cycle de vie des services."""

    def __init__(self):
        # Structure : { objet_service: {"event": threading.Event() ou None, "enabled": bool} }
        self.services = {}
        self.is_running = False

    def add_service(self, service, enabled=True):
        """Enregistre un service dans le tableau électrique."""
        self.services[service] = {"event": None, "enabled": enabled}

        # Démarrage à chaud si l'orchestrateur tourne déjà et que le service est activé
        if self.is_running and enabled:
            self.start_service(service.service_name)

    def start_service(self, service_name: str):
        """Allume l'interrupteur d'un service spécifique."""
        for srv, data in self.services.items():
            if srv.service_name == service_name:
                data["enabled"] = True
                if self.is_running and (data["event"] is None or data["event"].is_set()):
                    data["event"] = threading.Event()
                    srv.start(data["event"])
                    print(f"[INFO] Orchestrateur : {service_name} ALLUMÉ.")
                return
        print(f"[ATTENTION] Orchestrateur : Impossible d'allumer {service_name} (Introuvable).")

    def stop_service(self, service_name: str):
        """Coupe le courant d'un service sans le supprimer de la mémoire."""
        for srv, data in self.services.items():
            if srv.service_name == service_name:
                data["enabled"] = False
                if data["event"] and not data["event"].is_set():
                    data["event"].set()  # Coupe la boucle while du thread
                    srv.stop()  # Nettoyage du service
                    #print(f"[INFO] Orchestrateur : {service_name} ÉTEINT.")
                return

    def start_all(self):
        """Démarre UNIQUEMENT les services cochés 'enabled'."""
        #print("[INFO] Orchestrateur : Démarrage global selon la configuration...")
        self.is_running = True

        for srv, data in self.services.items():
            if data["enabled"]:
                data["event"] = threading.Event()
                srv.start(data["event"])

    def stop_all(self):
        """Coupe absolument tout."""
        #print("[INFO] Orchestrateur : Signal d'arrêt global envoyé.")
        self.is_running = False

        for srv, data in self.services.items():
            if data["event"] and not data["event"].is_set():
                data["event"].set()
                srv.stop()

    def get_system_health(self) -> dict:
        """Récupère l'état de tous les services actifs ou signale ceux désactivés."""
        health = {}
        for srv, data in self.services.items():
            if data["enabled"]:
                health[srv.service_name] = srv.get_health()
            else:
                health[srv.service_name] = {
                    "status": "DISABLED",
                    "message": "Désactivé dans les réglages"
                }
        return health