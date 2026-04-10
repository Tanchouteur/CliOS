import json
import threading

from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot


class DashboardBridge(QObject):
    """Pont de communication optimisé par Polling Asymétrique."""

    dataChanged = Signal(dict)
    configChanged = Signal(dict)
    notificationEvent = Signal(str, str, int, arguments=['level', 'message', 'duration'])
    statsChanged = Signal(dict)
    systemHealthChanged = Signal()

    def __init__(self, api, config_path, orchestrator, led_service=None, stats_service=None, diag_service=None):
        super().__init__()
        self.api = api
        self.led_service = led_service
        self.stats_service = stats_service
        self.diag_service = diag_service
        self.orchestrator = orchestrator

        self._config_path = config_path
        self._data = {}
        self._stats = {}
        self._system_health = {}

        with open(config_path, 'r') as f:
            self._config = json.load(f)

        # 1. Voie Ultra-Rapide (60 Hz / 16ms) : Uniquement la télémétrie (Vitesse, RPM)
        self.timer_fast = QTimer()
        self.timer_fast.timeout.connect(self._update_fast_data)
        self.timer_fast.start(16)

        # 2. Voie Moyenne (2 Hz / 500ms) : Les calculs de l'ordinateur de bord
        self.timer_medium = QTimer()
        self.timer_medium.timeout.connect(self._update_stats)
        self.timer_medium.start(500)

        # 3. Voie Lente (1 Hz / 1000ms) : La santé du système et les logs
        self.timer_slow = QTimer()
        self.timer_slow.timeout.connect(self._update_health)
        self.timer_slow.start(1000)

    # --- LES SOUS-ROUTINES (Plus courtes, plus rapides) ---

    def _update_fast_data(self):
        new_data = self.api._data.copy()
        if new_data != self._data:
            self._data = new_data
            self.dataChanged.emit(self._data)

    def _update_stats(self):
        if self.stats_service:
            new_stats = self.stats_service.stats.copy()
            if new_stats != self._stats:
                self._stats = new_stats
                self.statsChanged.emit(self._stats)

    def _update_health(self):
        new_health = self.orchestrator.get_system_health()
        if new_health != self._system_health:
            self._system_health = new_health
            self.systemHealthChanged.emit()

    @Property('QVariant', notify=dataChanged)
    def data(self):
        """Accesseur de la structure de données télémétriques exposé au moteur QML."""
        return self._data

    @Property('QVariant', notify=configChanged)
    def config(self):
        """Accesseur de la configuration statique exposé au moteur QML."""
        return self._config

    @Property('QVariant', notify=statsChanged)
    def stats(self):
        """Accesseur des statistiques exposé au moteur QML."""
        return self._stats

    @Property('QVariant', notify=systemHealthChanged)
    def systemHealth(self):
        return self._system_health

    @Slot()
    def requestDiagnosticScan(self):
        if self.diag_service:
            self.diag_service.request_scan()

    @Property(bool, notify=dataChanged)
    def isScanning(self):
        return self.api._data.get("diag_scanning", False)

    @Property(bool, notify=dataChanged)
    def hasScanned(self):
        return self.api._data.get("diag_has_scanned", False)

    @Property('QVariantList', notify=dataChanged)
    def diagnosticCodes(self):
        return self.api._data.get("diag_codes", [])

    @Slot()
    def resetTripB(self):
        """
        Point d'entrée QML (Slot) permettant à l'IHM d'invoquer une méthode métier.
        Déclenche la réinitialisation matérielle de l'odomètre partiel B et des accumulateurs associés.
        """
        print("[INFO] Signal IHM reçu : Réinitialisation du Trip B.")
        if self.stats_service:
            self.stats_service.reset_trip_b()

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

    @Slot(float)
    def updateFuelPrice(self, new_price: float):
        """Reçoit le prix depuis l'UI et met à jour le service."""
        if self.stats_service:
            self.stats_service.set_fuel_price(new_price)
            print(f"[BRIDGE] Prix du carburant mis à jour : {new_price} €/L")

    @Slot(str, bool)
    def toggleService(self, service_name: str, enable: bool):
        """
        Point d'entrée QML : Active ou désactive un service à la volée
        et sauvegarde ce choix pour le prochain démarrage.
        """
        print(f"[INFO] IHM : Bascule du service {service_name} -> {'ON' if enable else 'OFF'}")

        # 1. Mémoire : Sauvegarde sur le disque dur (ex: "service_EngineSound")
        storage_key = f"services.{service_name}"
        if hasattr(self, 'storage'):
            self.storage.set(storage_key, enable)

        # 2. Action : Ordre direct à l'électricien (Orchestrateur)
        if enable:
            self.orchestrator.start_service(service_name)
        else:
            self.orchestrator.stop_service(service_name)

        # 3. Rafraîchissement visuel : Force la mise à jour immédiate de la barre de statut
        self._system_health = self.orchestrator.get_system_health()
        self.systemHealthChanged.emit()

    def send_notification(self, level: str, message: str, duration: int = 3000):
        """Méthode appelée par l'orchestrateur quand une alerte se déclenche"""
        self.notificationEvent.emit(level, message, duration)