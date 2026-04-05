import threading

class SystemOrchestrator:
    """Gestionnaire centralisé du cycle de vie des services d'arrière-plan."""

    def __init__(self):
        # Pourquoi : L'Event agit comme un interrupteur global.
        # S'il est activé, tous les threads qui le surveillent s'arrêtent.
        self.stop_event = threading.Event()
        self.services = []

    def add_service(self, service):
        """Ajoute un service à la liste d'exécution."""
        self.services.append(service)

    def start_all(self):
        """Démarre tous les services enregistrés dans des threads séparés."""
        print("[INFO] Orchestrateur : Démarrage des services...")
        for service in self.services:
            # On passe le stop_event à chaque service pour qu'ils sachent quand s'arrêter
            service.start(self.stop_event)

    def stop_all(self):
        """Déclenche l'arrêt propre de tous les threads et ferme les connexions."""
        print("[INFO] Orchestrateur : Signal d'arrêt envoyé à tous les services.")
        self.stop_event.set()

        for service in self.services:
            service.stop()