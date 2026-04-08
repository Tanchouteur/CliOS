import threading


class SystemOrchestrator:
    """Gestionnaire centralisé et dynamique du cycle de vie des services."""

    def __init__(self):
        # Le dictionnaire lie chaque service à SON propre interrupteur
        # Structure : { objet_service: threading.Event() }
        self.services = {}

        # Permet de savoir si on doit démarrer un nouveau service immédiatement
        self.is_running = False

    def add_service(self, service):
        """Ajoute un service et le démarre à chaud si le système tourne déjà."""
        service_event = threading.Event()
        self.services[service] = service_event

        if self.is_running:
            print(f"[INFO] Orchestrateur : Démarrage à chaud de {service.service_name}")
            service.start(service_event)

    def remove_service(self, service_name: str):
        """Trouve un service par son nom, l'arrête proprement et le retire."""
        target_service = None
        for srv in self.services.keys():
            if srv.service_name == service_name:
                target_service = srv
                break

        if target_service:
            print(f"[INFO] Orchestrateur : Arrêt dynamique de {service_name}...")

            self.services[target_service].set()

            target_service.stop()

            del self.services[target_service]
            print(f"[INFO] Orchestrateur : {service_name} retiré avec succès.")
        else:
            print(f"[ATTENTION] Orchestrateur : Impossible de retirer {service_name}, service introuvable.")

    def start_all(self):
        """Démarre tous les services enregistrés initialement."""
        print("[INFO] Orchestrateur : Démarrage global des services...")
        self.is_running = True

        # On donne à chaque service son event personnel
        for service, event in self.services.items():
            service.start(event)

    def stop_all(self):
        """Arrête la totalité du système proprement."""
        print("[INFO] Orchestrateur : Signal d'arrêt global envoyé.")
        self.is_running = False

        for service, event in self.services.items():
            event.set()  # On coupe l'interrupteur du service
            service.stop()  # On lance son nettoyage

    def get_system_health(self) -> dict:
        """Récupère l'état de tous les services actifs."""
        # On utilise une compréhension de dictionnaire pour faire ça en 1 ligne
        return {srv.service_name: srv.get_health() for srv in self.services.keys()}