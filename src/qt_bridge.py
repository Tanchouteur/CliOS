import json
import threading
import time

from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot, QCoreApplication


class DashboardBridge(QObject):
    """Pont de communication sécurisé (Thread-Safe)."""

    dataChanged = Signal()
    diagDataChanged = Signal()
    configChanged = Signal()
    notificationEvent = Signal(str, str, int, arguments=['level', 'message', 'duration'])
    statsChanged = Signal()
    systemHealthChanged = Signal()

    def __init__(self, api, config_path, orchestrator, led_service=None, stats_service=None, diag_service=None,
                 profile_manager=None, gear_calib_service=None, session_manager=None, diag=None):
        super().__init__()
        self.session_manager = session_manager
        self.api = api
        self.led_service = led_service
        self.stats_service = stats_service
        self.diag_service = diag_service
        self.orchestrator = orchestrator
        self.profile_manager = profile_manager
        self.gear_calib_service = gear_calib_service

        self._config_path = config_path
        self._data = {}
        self._stats = {}
        self._system_health = {}
        self.diag = diag or {}
        self._diag_disable_fast_emit = bool(self.diag.get("disable_fast_emit", False))
        self._diag_include_keys = set(self.diag.get("include_keys", []))
        self._diag_log_bridge = bool(self.diag.get("log_bridge", False))
        self._diag_last_print = time.time()
        self._diag_emit_count = 0

        with open(config_path, 'r') as f:
            self._config = json.load(f)

        # 1. Voie Ultra-Rapide (60 Hz / 16ms)
        self.timer_fast = QTimer()
        self.timer_fast.timeout.connect(self._update_fast_data)
        self.timer_fast.start(max(5, int(self.diag.get("fast_timer_ms", 16))))

        # 2. Voie Moyenne (2 Hz / 500ms)
        self.timer_medium = QTimer()
        self.timer_medium.timeout.connect(self._update_stats)
        self.timer_medium.start(500)

        # 3. Voie Lente (1 Hz / 1000ms)
        self.timer_slow = QTimer()
        self.timer_slow.timeout.connect(self._update_health)
        self.timer_slow.start(1000)

        self.needs_restart = False

    # --- LES SOUS-ROUTINES ---
    def _update_fast_data(self):
        # 1. On récupère la copie sécurisée de l'API
        new_data = self.api.get_display_data()

        if self._diag_include_keys:
            new_data = {k: v for k, v in new_data.items() if k in self._diag_include_keys}

        safe_qml_data = self._to_qml_safe(new_data)

        # 2. On vérifie s'il y a un changement par rapport à la dernière émission
        if safe_qml_data != getattr(self, '_last_raw_data', {}):
            self._last_raw_data = safe_qml_data

            self._data = safe_qml_data

            if not self._diag_disable_fast_emit:
                self.dataChanged.emit()
                self.diagDataChanged.emit()
                self._diag_emit_count += 1

        if self._diag_log_bridge:
            now = time.time()
            if now - self._diag_last_print >= 2.0:
                print(f"[DIAG][BRIDGE] emits={self._diag_emit_count} fast_emit={'OFF' if self._diag_disable_fast_emit else 'ON'} "
                      f"keys={len(self._data)}")
                self._diag_last_print = now

    def _update_stats(self):
        if self.stats_service:
            # On utilise la propriété .stats qui est déjà thread-safe
            new_stats = self._to_qml_safe(self.stats_service.stats)

            if new_stats != getattr(self, '_last_raw_stats', {}):
                self._last_raw_stats = new_stats
                self._stats = new_stats
                self.statsChanged.emit()

    def _to_qml_safe(self, value):
        """Normalise les types pour éviter les conversions fragiles côté Shiboken/Qt."""
        if isinstance(value, bool):
            return 1 if value else 0

        if value is None or isinstance(value, (int, float, str)):
            return value

        if isinstance(value, dict):
            return {str(k): self._to_qml_safe(v) for k, v in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [self._to_qml_safe(v) for v in value]

        # Support défensif pour numpy scalars et objets avec .item().
        if hasattr(value, "item"):
            try:
                return self._to_qml_safe(value.item())
            except Exception:
                pass

        if isinstance(value, (bytes, bytearray)):
            return list(value)

        return str(value)

    def _update_health(self):
        new_health = self.orchestrator.get_system_health()
        if new_health != self._system_health:
            self._system_health = new_health
            self.systemHealthChanged.emit()

    @Property('QVariant', notify=dataChanged)
    def data(self):
        return self._data

    @Property('QVariant', notify=configChanged)
    def config(self):
        return self._config

    @Property('QVariant', notify=statsChanged)
    def stats(self):
        return self._stats

    @Property('QVariant', notify=systemHealthChanged)
    def systemHealth(self):
        return self._system_health

    @Slot()
    def requestDiagnosticScan(self):
        if self.diag_service:
            self.diag_service.request_scan()

    # --- CORRECTION DE FUITE : On lit self._data (local) et non self.api._data (risqué) ---
    @Property(bool, notify=diagDataChanged)
    def isScanning(self):
        return bool(self._data.get("diag_scanning", False))

    @Property(bool, notify=diagDataChanged)
    def hasScanned(self):
        return bool(self._data.get("diag_has_scanned", False))

    @Property('QVariantList', notify=diagDataChanged)
    def diagnosticCodes(self):
        return list(self._data.get("diag_codes", []))

    @Slot()
    def resetTripB(self):
        print("[INFO] Signal IHM reçu : Réinitialisation du Trip B.")
        if self.stats_service:
            self.stats_service.reset_trip_b()

    @Slot(str, str)
    def save_setting(self, key_path, value):
        if key_path == "theme.main" and self.led_service:
            self.led_service.set_color(value)

        keys = key_path.split('.')
        current_dict = self._config

        for k in keys[:-1]:
            if k not in current_dict:
                current_dict[k] = {}
            current_dict = current_dict[k]

        current_dict[keys[-1]] = value
        self.configChanged.emit()

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
        if self.stats_service:
            self.stats_service.set_fuel_price(new_price)
            print(f"[BRIDGE] Prix du carburant mis à jour : {new_price} €/L")

    @Slot(str, bool)
    def toggleService(self, service_name: str, enable: bool):
        storage_key = f"services.{service_name}.enabled"
        if hasattr(self, 'storage'):
            self.storage.set(storage_key, enable)

        if enable:
            self.orchestrator.start_service(service_name)
        else:
            self.orchestrator.stop_service(service_name)

        self._system_health = self.orchestrator.get_system_health()
        self.systemHealthChanged.emit()

    def send_notification(self, level: str, message: str, duration: int = 3000):
        self.notificationEvent.emit(level, message, duration)

    def _get_service_obj(self, service_name: str):
        for srv in self.orchestrator.services.keys():
            if srv.service_name == service_name:
                return srv
        return None

    @Slot(str, result=str)
    def getServiceParameters(self, service_name: str) -> str:
        srv = self._get_service_obj(service_name)
        if srv:
            return json.dumps(srv.get_params_schema())
        return "[]"

    @Slot(str, str, 'QVariant')
    def setServiceParameter(self, service_name: str, param_key: str, value):
        srv = self._get_service_obj(service_name)
        if srv:
            srv.update_param(param_key, value)

    @Slot(result='QVariantList')
    def getAvailableProfiles(self):
        if self.profile_manager:
            return self.profile_manager.get_available_profiles()
        return []

    @Slot(result=str)
    def getActiveProfile(self):
        if self.profile_manager:
            return self.profile_manager.active_profile_id
        return ""

    @Slot(result='QVariantList')
    def getAvailableCanFiles(self):
        if self.profile_manager:
            return self.profile_manager.get_available_can_files()
        return []

    @Slot(result='QVariantList')
    def getAvailableConfigFiles(self):
        if self.profile_manager:
            return self.profile_manager.get_available_config_files()
        return []

    @Slot(str, str, str, str, str, result=bool)
    def createNewProfile(self, profile_id: str, name: str, can_file: str, config_file: str, save_file: str):
        if not self.profile_manager:
            return False
        self.profile_manager.create_new_config(config_file)
        self.profile_manager.add_profile(profile_id, name, can_file, config_file, save_file)
        print(f"[INFO] Nouveau profil créé : {name} ({profile_id})")
        return True

    @Slot(str, result=bool)
    def setActiveProfile(self, profile_id: str):
        if not self.profile_manager:
            return False
        success = self.profile_manager.set_active_profile(profile_id)
        if success:
            print(f"[INFO] Changement de profil programmé : {profile_id}. Redémarrage nécessaire.")
            self.send_notification("info", f"Profil '{profile_id}' sélectionné. Veuillez redémarrer l'application.",
                                   4000)
        return success

    @Slot()
    def restartApplication(self):
        print("[INFO] Ordre de redémarrage reçu depuis l'IHM.")
        self.needs_restart = True
        QCoreApplication.instance().quit()

    @Slot()
    def startGearCalibration(self):
        if self.gear_calib_service:
            self.gear_calib_service.start_calibration()

    @Slot(result=bool)
    def stopGearCalibration(self):
        if self.gear_calib_service:
            return self.gear_calib_service.stop_and_save_calibration()
        return False

    @Slot()
    def resumeTripSession(self):
        if self.session_manager:
            self.session_manager.resume_trip()

    @Slot()
    def endTripSession(self):
        if self.session_manager:
            self.session_manager.end_trip()