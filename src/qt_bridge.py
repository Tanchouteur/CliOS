import json
import threading

from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot


class DashboardBridge(QObject):
    """Pont de communication (Context Property) entre le moteur logique (Python) et le moteur de rendu (QML)."""

    # Signaux d'état pour la notification asynchrone de l'interface graphique
    dataChanged = Signal(dict)
    configChanged = Signal(dict)
    notificationEvent = Signal(str, str, int, arguments=['level', 'message', 'duration'])

    def __init__(self, api, config_path, led_service=None):
        super().__init__()
        self.api = api
        self.led_service = led_service
        self._data = {}
        self._config_path = config_path
        # Chargement et mise en cache des paramètres de configuration de l'interface
        with open(config_path, 'r') as f:
            self._config = json.load(f)

        # Initialisation du temporisateur de rafraîchissement (Polling à ~60Hz / 16ms)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(16)

    def update_data(self):
        """Routine de vérification d'état. Émet un signal uniquement si une mutation de données est détectée."""
        new_data = self.api._data.copy()
        if new_data != self._data:
            self._data = new_data
            self.dataChanged.emit(self._data)

    @Property('QVariant', notify=dataChanged)
    def data(self):
        """Accesseur de la structure de données télémétriques exposé au moteur QML."""
        return self._data

    @Property('QVariant', notify=configChanged)
    def config(self):
        """Accesseur de la configuration statique exposé au moteur QML."""
        return self._config

    @Slot()
    def resetTripB(self):
        """
        Point d'entrée QML (Slot) permettant à l'IHM d'invoquer une méthode métier.
        Déclenche la réinitialisation matérielle de l'odomètre partiel B et des accumulateurs associés.
        """
        print("[INFO] Signal IHM reçu : Réinitialisation du Trip B et des accumulateurs de consommation.")
        self.api.reset_trip_b()

    @Slot(str, str)
    def save_setting(self, key_path, value):
        """
        Met à jour la configuration en RAM (supporte les clés imbriquées ex: 'theme.main')
        et l'écrit sur le disque en arrière-plan.
        """
        if key_path == "theme.main" and self.led_service:
            self.led_service.set_color(value)

        keys = key_path.split('.')
        current_dict = self._config

        for k in keys[:-1]:
            if k not in current_dict:
                current_dict[k] = {}
            current_dict = current_dict[k]

        current_dict[keys[-1]] = value

        self.configChanged.emit(self._config)

        def write_worker():
            try:
                with open(self._config_path, "w") as f:
                    json.dump(self._config, f, indent=4)
                print(f"[INFO] Paramètre sauvegardé : {key_path} = {value}")
            except Exception as e:
                print(f"[ERREUR] Échec de la sauvegarde de {key_path} : {e}")

        threading.Thread(target=write_worker, daemon=True).start()

    def send_notification(self, level: str, message: str, duration: int = 3000):
        """Méthode appelée par l'orchestrateur quand une alerte se déclenche"""
        self.notificationEvent.emit(level, message, duration)