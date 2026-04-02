import json
from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot


class DashboardBridge(QObject):
    """Pont de communication (Context Property) entre le moteur logique (Python) et le moteur de rendu (QML)."""

    # Signaux d'état pour la notification asynchrone de l'interface graphique
    dataChanged = Signal(dict)
    configChanged = Signal(dict)

    def __init__(self, api, config_path):
        super().__init__()
        self.api = api
        self._data = {}

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