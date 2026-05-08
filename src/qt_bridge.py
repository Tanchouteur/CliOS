import json
import os
import threading

from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot, QCoreApplication
from src.logging_runtime import get_logger, get_recent_events
from src.diagnostic_bundle import create_diagnostic_bundle


class DashboardBridge(QObject):
    """Pont de communication sécurisé (Thread-Safe)."""

    dataChanged = Signal()
    diagDataChanged = Signal()
    configChanged = Signal()
    notificationEvent = Signal(str, str, int, arguments=['level', 'message', 'duration'])
    statsChanged = Signal()
    systemHealthChanged = Signal()

    def __init__(self, api, config_path, orchestrator, led_service=None, stats_service=None, diag_service=None,
                 profile_manager=None, gear_calib_service=None, session_manager=None):
        super().__init__()
        self.logger = get_logger("DashboardBridge")
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
        self._diag_state = (False, False, ())

        with open(config_path, 'r') as f:
            self._config = json.load(f)

        # 1. Voie Ultra-Rapide (60 Hz / 16ms)
        self.timer_fast = QTimer()
        self.timer_fast.timeout.connect(self._update_fast_data)
        self.timer_fast.start(16)

        # 2. Voie Moyenne (2 Hz / 500ms)
        self.timer_medium = QTimer()
        self.timer_medium.timeout.connect(self._update_stats)
        self.timer_medium.start(500)

        # 3. Voie Lente (1 Hz / 1000ms)
        self.timer_slow = QTimer()
        self.timer_slow.timeout.connect(self._update_health)
        self.timer_slow.start(1000)

        self.needs_restart = False

    # Boucles de rafraîchissement.
    def _update_fast_data(self):
        new_data = self._sanitize_for_qml(self.api.get_display_data())

        if new_data != self._data:
            self._data = new_data
            self.dataChanged.emit()

            new_diag_state = self._extract_diag_state(new_data)
            if new_diag_state != self._diag_state:
                self._diag_state = new_diag_state
                self.diagDataChanged.emit()

    def _extract_diag_state(self, data: dict) -> tuple:
        scanning = bool(data.get("diag_scanning", False))
        has_scanned = bool(data.get("diag_has_scanned", False))
        codes = tuple(data.get("diag_codes", []))
        return scanning, has_scanned, codes

    def _update_stats(self):
        if self.stats_service:
            new_stats = self._sanitize_for_qml(self.stats_service.stats.copy())
            if new_stats != self._stats:
                self._stats = new_stats
                self.statsChanged.emit()

    def _update_health(self):
        new_health = self._sanitize_for_qml(self.orchestrator.get_system_health())
        if new_health != self._system_health:
            self._system_health = new_health
            self.systemHealthChanged.emit()

    def _sanitize_for_qml(self, value):
        # Types primitifs compatibles QML.
        if value is None or isinstance(value, (bool, int, float, str)):
            return value

        if isinstance(value, dict):
            return {str(k): self._sanitize_for_qml(v) for k, v in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [self._sanitize_for_qml(v) for v in value]

        if hasattr(value, "item"):
            try:
                return self._sanitize_for_qml(value.item())
            except Exception:
                pass

        if isinstance(value, (bytes, bytearray)):
            return list(value)

        return str(value)

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

    @Slot(str)
    def setSessionState(self, state: str):
        allowed = {"IDLE", "RUNNING", "PAUSED", "WAITING_IGNITION", "ENDED"}
        if state in allowed:
            self.api.update({"session_state": state})

    # Lit l'état local déjà sérialisé pour éviter les accès concurrents à l'API.
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
        self.logger.info("Reset Trip B demande", extra={"error_code": "UI_RESET_TRIP_B"})
        if self.stats_service:
            self.stats_service.reset_trip_b()

    @Slot(float)
    def updateTripBFuel(self, new_fuel: float):
        if self.stats_service:
            self.stats_service.set_trip_b_fuel(new_fuel)
            self.logger.info(f"Carburant Trip B mis a jour: {new_fuel}", extra={"error_code": "FUEL_TRIP_B_UPDATE"})

    @Slot(float)
    def updateTripBDistance(self, new_distance: float):
        if self.stats_service:
            self.stats_service.set_trip_b_distance(new_distance)
            self.logger.info(f"Distance Trip B mise a jour: {new_distance}",
                             extra={"error_code": "DISTANCE_TRIP_B_UPDATE"})

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
                self.logger.info(f"Parametre sauvegarde: {key_path}", extra={"error_code": "CONFIG_SAVED"})
            except Exception as e:
                self.logger.error(f"Echec sauvegarde config {key_path}: {e}", extra={"error_code": "CONFIG_SAVE_ERROR"})

        threading.Thread(target=write_worker, daemon=True).start()

    @Slot(float)
    def updateFuelPrice(self, new_price: float):
        if self.stats_service:
            self.stats_service.set_fuel_price(new_price)
            self.logger.info(f"Prix carburant mis a jour: {new_price}", extra={"error_code": "FUEL_PRICE_UPDATE"})

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
        self.logger.info(f"Nouveau profil cree: {profile_id}", extra={"error_code": "PROFILE_CREATED"})
        return True

    @Slot(str, result=bool)
    def setActiveProfile(self, profile_id: str):
        if not self.profile_manager:
            return False
        success = self.profile_manager.set_active_profile(profile_id)
        if success:
            self.logger.info(f"Changement profil programme: {profile_id}", extra={"error_code": "PROFILE_CHANGED"})
            self.send_notification("info", f"Profil '{profile_id}' sélectionné. Veuillez redémarrer l'application.",
                                   4000)
        return success

    @Slot()
    def restartApplication(self):
        self.logger.warning("Ordre de redemarrage recu", extra={"error_code": "APP_RESTART_REQUEST"})
        self.needs_restart = True
        QCoreApplication.instance().quit()

    @Slot(int, result=str)
    def getRecentLogs(self, limit: int = 100) -> str:
        limit = max(1, min(limit, 300))
        return json.dumps(get_recent_events(limit=limit))

    @Slot(result=str)
    def exportDiagnosticBundle(self) -> str:
        try:
            data_dir = os.path.dirname(os.path.dirname(self._config_path))
            log_dir = os.path.join(data_dir, "logs")
            output_dir = os.path.join(data_dir, "diagnostics")
            bundle_path = create_diagnostic_bundle(
                output_dir=output_dir,
                log_dir=log_dir,
                config_path=self._config_path,
                system_health=self.orchestrator.get_system_health(),
                extra={"active_profile": self.getActiveProfile()},
            )
            self.logger.info(f"Bundle diagnostic exporte: {bundle_path}", extra={"error_code": "DIAG_BUNDLE_EXPORTED"})
            return bundle_path
        except Exception as e:
            self.logger.error(f"Echec export bundle: {e}", extra={"error_code": "DIAG_BUNDLE_ERROR"})
            return ""

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