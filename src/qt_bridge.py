import json
import os
import re
import threading
import time

from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot, QCoreApplication
try:
    from PySide6.QtNetwork import QNetworkInformation
except ImportError:  # Qt < 6.4 ou backend réseau non fourni
    QNetworkInformation = None
from src.logging_runtime import get_logger
from src.state_store import VEHICLE_DOMAINS
from src.bridge.profile_theme_controller import ProfileThemeController
from src.bridge.system_controller import SystemController
from src.bridge.updater_controller import UpdaterController
from src.bridge.ui_command_router import UiCommandRouter
from src.ble.device_catalog import BleDevice, MAX_DEVICES, PREDEFINED_NAMES


class DashboardBridge(QObject):
    """Pont de communication sécurisé (Thread-Safe)."""

    vehicleStateChanged = Signal()
    tripStateChanged = Signal()
    diagnosticsStateChanged = Signal()
    systemStateChanged = Signal()
    sessionStateChanged = Signal()
    calibrationStateChanged = Signal()
    presentationStateChanged = Signal()
    dataQualityChanged = Signal()
    configChanged = Signal()
    notificationEvent = Signal(str, str, int, arguments=['level', 'message', 'duration'])
    openMaintenanceRequested = Signal()
    exitRequested = Signal()

    def __init__(self, runtime, config_path, orchestrator, led_service=None, led_catalog=None,
                 stats_service=None, diag_service=None,
                 profile_manager=None, gear_calib_service=None, session_manager=None, storage_manager=None):
        super().__init__()
        self.logger = get_logger("DashboardBridge")
        self.session_manager = session_manager
        self.runtime = runtime
        self.storage = getattr(runtime, "storage", None)
        self.led_service = led_service
        self.led_catalog = led_catalog
        self.stats_service = stats_service
        self.diag_service = diag_service
        self.orchestrator = orchestrator
        self.profile_manager = profile_manager
        self.gear_calib_service = gear_calib_service
        self._storage_manager = storage_manager

        self._config_lock = threading.RLock()
        self._config_write_lock = threading.Lock()
        self._config_write_requested = threading.Event()
        self._config_writer_stop = threading.Event()
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._ui_styles_dir = os.path.join(project_root, "frontend", "styles")
        self._dev_styles_dir = os.path.join(project_root, "frontend", "dev_styles")
        self._theme_diagnostics = []
        try:
            with open(os.path.join(project_root, "VERSION"), encoding="utf-8") as stream:
                self._clios_version_text = stream.read().strip()
                core = self._clios_version_text.split("-", 1)[0].split("+", 1)[0]
                self._clios_version = tuple(int(part) for part in core.split("."))
        except (OSError, ValueError):
            self._clios_version_text = "0.0.0"
            self._clios_version = (0, 0, 0)

        self._config_path = config_path
        self._vehicle_state = {}
        self._trip_state = {}
        self._diagnostics_state = {}
        self._system_state = {}
        self._session_state = {}
        self._calibration_state = {}
        self._presentation_state = {}
        self._data_quality = {}
        self._updater_state = {
            "state": "IDLE", "installed_version": self._clios_version_text,
            "available_version": "", "channel": "stable", "progress": 0,
            "message": "", "can_activate": False, "last_manifest": {}, "error": {},
        }
        self._updater_poll_running = False
        self._network_was_online = False
        self._network_information = None

        with open(config_path, 'r') as f:
            self._config = json.load(f)

        self._profile_theme_controller = ProfileThemeController(self)
        self._system_controller = SystemController(self)
        self._updater_controller = UpdaterController(self)
        self._command_router = UiCommandRouter(self, self.logger)

        self._config_writer_thread = threading.Thread(
            target=self._config_writer_loop, daemon=True, name="ConfigWriter"
        )
        self._config_writer_thread.start()

        # --- Configuration des frequences de rafraichissement ---

        # 1. Voie Ultra-Rapide (60 Hz / 16ms) - Vitesse, RPM, etats critiques
        self.timer_fast = QTimer()
        self.timer_fast.timeout.connect(self._update_fast_data)
        self.timer_fast.start(16)

        # 2. Voie Lente (1 Hz / 1000ms) - Sante du systeme et qualité
        self.timer_slow = QTimer()
        self.timer_slow.timeout.connect(self._update_health)
        self.timer_slow.start(1000)

        # Le téléchargement est effectué par le helper root dans un autre
        # processus. Son statut doit être relu à intervalle fixe.
        self.timer_updater = QTimer()
        self.timer_updater.timeout.connect(self._poll_updater_status)
        self.timer_updater.start(1000)

        self._setup_network_information()

        self.needs_restart = False
        self.requested_power_action = ""
        self._closed = False
        self.exitRequested.connect(self._quit_qt)
        self._update_health()

    # Boucles de rafraîchissement.
    def _update_fast_data(self):
        if self._closed:
            return
        snapshot = self.runtime.snapshot()
        new_vehicle_state = self._sanitize_for_qml(snapshot.as_dict(VEHICLE_DOMAINS))
        if new_vehicle_state != self._vehicle_state:
            self._vehicle_state = new_vehicle_state
            self.vehicleStateChanged.emit()

        new_trip = self._sanitize_for_qml(snapshot.domain("trip"))
        if new_trip != self._trip_state:
            self._trip_state = new_trip
            self.tripStateChanged.emit()

        new_diagnostics = self._sanitize_for_qml(snapshot.domain("diagnostics"))
        if new_diagnostics != self._diagnostics_state:
            self._diagnostics_state = new_diagnostics
            self.diagnosticsStateChanged.emit()

        new_session = self._sanitize_for_qml(snapshot.domain("session"))
        if new_session != self._session_state:
            self._session_state = new_session
            self.sessionStateChanged.emit()

        new_calibration = self._sanitize_for_qml(snapshot.domain("calibration"))
        if new_calibration != self._calibration_state:
            self._calibration_state = new_calibration
            self.calibrationStateChanged.emit()

        new_presentation = self._sanitize_for_qml(self.runtime.presentation_snapshot())
        if new_presentation != self._presentation_state:
            self._presentation_state = new_presentation
            self.presentationStateChanged.emit()

    def _update_health(self):
        if self._closed:
            return
        system = self.runtime.snapshot().domain("system")
        version = system.get("system_version", "unknown")
        telemetry = {key: value for key, value in system.items() if key != "system_version"}
        led_scan = self.led_service.scan_state if self.led_service else {}
        new_system = self._sanitize_for_qml({
            "version": version,
            "telemetry": telemetry,
            "health": self.orchestrator.get_system_health(),
            "storage": self._read_storage_status(),
            "theme_diagnostics": self._theme_diagnostics,
            "recovery": {
                "active": bool(self.profile_manager and self.profile_manager.recovery_mode),
                "message": self.profile_manager.error_message if self.profile_manager else "",
            },
            "updater": self._updater_state,
            "led_devices": self.led_catalog.devices_to_json() if self.led_catalog else [],
            "led_groups": self.led_catalog.groups_to_json() if self.led_catalog else [],
            "led_max_devices": MAX_DEVICES,
            "ble_scanning": bool(led_scan.get("scanning", False)),
            "ble_scan_results": led_scan.get("results", []),
            "ble_characteristics": led_scan.get("characteristics", []),
            "ble_test_state": led_scan.get("test_state", {}),
        })
        if new_system != self._system_state:
            self._system_state = new_system
            self.systemStateChanged.emit()
        new_quality = self._sanitize_for_qml(self.runtime.metadata_snapshot())
        if new_quality != self._data_quality:
            self._data_quality = new_quality
            self.dataQualityChanged.emit()

    def _setup_network_information(self):
        if QNetworkInformation is None:
            return
        try:
            QNetworkInformation.loadDefaultBackend()
            self._network_information = QNetworkInformation.instance()
            if self._network_information is None:
                return
            self._network_information.reachabilityChanged.connect(self._on_reachability_changed)
            QTimer.singleShot(0, lambda: self._on_reachability_changed(self._network_information.reachability()))
        except (RuntimeError, TypeError, AttributeError) as exc:
            self.logger.warning(f"Détection réseau indisponible: {exc}", extra={"error_code": "NETWORK_INFO_UNAVAILABLE"})

    def _on_reachability_changed(self, reachability):
        try:
            online = reachability == QNetworkInformation.Reachability.Online
        except (AttributeError, TypeError):
            online = str(reachability).lower().endswith("online")
        became_online = online and not self._network_was_online
        self._network_was_online = online
        if became_online:
            last_success = int(self._config.get("updates", {}).get("last_success_epoch", 0) or 0)
            if time.time() - last_success >= 24 * 60 * 60:
                self._check_for_updates(force=False)

    def _set_updater_state(self, **changes):
        updated = dict(self._updater_state)
        updated.update(changes)
        updated["installed_version"] = self._clios_version_text
        updated["channel"] = self.getUpdateChannel()
        self._updater_state = self._sanitize_for_qml(updated)

    def _poll_updater_status(self):
        self._updater_controller.poll_status()

    def _read_storage_status(self):
        if not self._storage_manager:
            return {"mode": "UNKNOWN", "usb_connected": False, "free_space_mb": 0.0}
        return self._sanitize_for_qml(self._storage_manager.get_status())

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
            except (TypeError, ValueError, OverflowError):
                pass

        if isinstance(value, (bytes, bytearray)):
            return list(value)

        return str(value)

    @Property('QVariant', notify=vehicleStateChanged)
    def vehicleState(self):
        return self._vehicle_state

    @Property('QVariant', notify=tripStateChanged)
    def tripState(self):
        return self._trip_state

    @Property('QVariant', notify=diagnosticsStateChanged)
    def diagnosticsState(self):
        return self._diagnostics_state

    @Property('QVariant', notify=systemStateChanged)
    def systemState(self):
        return self._system_state

    @Property('QVariant', notify=sessionStateChanged)
    def sessionState(self):
        return self._session_state

    @Property('QVariant', notify=calibrationStateChanged)
    def calibrationState(self):
        return self._calibration_state

    @Property('QVariant', notify=presentationStateChanged)
    def presentationState(self):
        return self._presentation_state

    @Property('QVariant', notify=dataQualityChanged)
    def dataQuality(self):
        return self._data_quality

    @Property('QVariant', notify=configChanged)
    def config(self):
        return self._config

    @Slot(result='QVariantList')
    def getAvailableUiStyles(self):
        """Découvre uniquement les thèmes conformes à Theme API v1."""
        if not hasattr(self, "_profile_theme_controller"):
            self._profile_theme_controller = ProfileThemeController(self)
        return self._profile_theme_controller.available_ui_styles()

    @Slot()
    def requestDiagnosticScan(self):
        if self.diag_service:
            self.diag_service.request_scan()

    # Gestionnaire d'eclairages BLE -----------------------------------------

    @Slot()
    def requestBleScan(self):
        if self.led_service:
            self.led_service.request_scan()

    @Slot()
    def stopBleScan(self):
        if self.led_service:
            self.led_service.stop_scan()

    @Slot(str)
    def requestBleCharacteristics(self, address):
        if self.led_service and address:
            self.led_service.request_characteristics(address)

    @Slot(result=str)
    def getLedDevices(self):
        return json.dumps(self.led_catalog.devices_to_json() if self.led_catalog else [])

    @Slot(result=str)
    def getLedGroups(self):
        return json.dumps(self.led_catalog.groups_to_json() if self.led_catalog else [])

    @Slot(result=str)
    def getBleScanResults(self):
        state = self.led_service.scan_state if self.led_service else {}
        return json.dumps(state.get("results", []))

    @Slot(result='QVariantList')
    def getBleProtocols(self):
        if not self.led_service:
            return []
        return [
            {
                "identifier": protocol.identifier,
                "label": protocol.label,
                "witness_color": "#%02X%02X%02X" % protocol.witness_color,
                "witness_name": protocol.witness_name,
            }
            for protocol in self.led_service._registry.all()
        ]

    @Slot(result='QVariantList')
    def getLedPredefinedNames(self):
        return list(PREDEFINED_NAMES)

    @Slot(str, str, str, bool)
    def testBleProtocol(self, address, char_uuid, protocol, write_response):
        if self.led_service:
            self.led_service.start_protocol_test(
                address, char_uuid, protocol, bool(write_response),
            )

    @Slot()
    def stopBleTest(self):
        if self.led_service:
            self.led_service.stop_protocol_test()

    @Slot(str, str, str, str, bool, str, result=bool)
    def addLedDevice(self, address, name, protocol, char_uuid, write_response, advertised_name):
        if not self.led_catalog or not self.led_service:
            return False
        try:
            self.led_service._registry.get(protocol)
            if not address.strip() or not char_uuid.strip():
                raise ValueError("Adresse ou caracteristique GATT manquante")
            self.led_catalog.add_device(BleDevice(
                id="", name=name.strip() or "Eclairage", ble_address=address.strip(),
                protocol=protocol, gatt_char_uuid=char_uuid.strip(),
                write_with_response=bool(write_response), advertised_name=advertised_name.strip(),
            ))
        except (KeyError, ValueError) as exc:
            self.send_notification("WARNING", str(exc), 4000)
            return False
        self.led_service.refresh_devices()
        self._update_health()
        return True

    @Slot(str, result=bool)
    def removeLedDevice(self, device_id):
        if not self.led_catalog:
            return False
        removed = self.led_catalog.remove_device(device_id)
        if removed and self.led_service:
            self.led_service.refresh_devices()
        self._update_health()
        return removed

    @Slot(str, str, str, result=bool)
    def updateLedDevice(self, device_id, key, value):
        if not self.led_catalog:
            return False
        try:
            if key == "enabled":
                parsed = value.strip().lower() in {"1", "true", "yes", "on"}
            elif key == "brightness":
                parsed = max(0.0, min(100.0, float(value)))
            elif key == "color_override":
                parsed = value.upper() or None
                if parsed and not re.fullmatch(r"#[0-9A-F]{6}", parsed):
                    raise ValueError("Couleur invalide")
            elif key == "name":
                parsed = value.strip()[:64] or "Eclairage"
            else:
                return False
        except ValueError:
            return False
        updated = self.led_catalog.update_device(device_id, **{key: parsed})
        if updated and self.led_service:
            self.led_service.refresh_devices()
        self._update_health()
        return updated

    @Slot(str, result=str)
    def addLedGroup(self, name):
        if not self.led_catalog or not name.strip():
            return ""
        group_id = self.led_catalog.add_group(name.strip()[:64])
        self._update_health()
        return group_id

    @Slot(str, result=bool)
    def removeLedGroup(self, group_id):
        if not self.led_catalog:
            return False
        removed = self.led_catalog.remove_group(group_id)
        if removed and self.led_service:
            self.led_service.refresh_devices()
        self._update_health()
        return removed

    @Slot(str, str, str, result=bool)
    def updateLedGroup(self, group_id, key, value):
        if not self.led_catalog or key not in {"name", "enabled", "brightness", "color_override"}:
            return False
        try:
            if key == "enabled":
                parsed = value.strip().lower() in {"1", "true", "yes", "on"}
            elif key == "brightness":
                parsed = max(0.0, min(100.0, float(value)))
            elif key == "color_override":
                parsed = value.upper() or None
                if parsed and not re.fullmatch(r"#[0-9A-F]{6}", parsed):
                    raise ValueError("Couleur invalide")
            else:
                parsed = value.strip()[:64] or "Groupe"
        except ValueError:
            return False
        updated = self.led_catalog.update_group(group_id, **{key: parsed})
        if updated and self.led_service:
            self.led_service.refresh_devices()
        self._update_health()
        return updated

    @Slot(str, str, bool, result=bool)
    def setLedDeviceGroup(self, device_id, group_id, member):
        if not self.led_catalog:
            return False
        if member:
            self.led_catalog.add_device_to_group(device_id, group_id)
        else:
            self.led_catalog.remove_device_from_group(device_id, group_id)
        if self.led_service:
            self.led_service.refresh_devices()
        self._update_health()
        return True

    @Slot(str)
    def setSessionState(self, state: str):
        allowed = {"IDLE", "RUNNING", "PAUSED", "WAITING_IGNITION", "ENDING", "ENDED"}
        if state in allowed:
            self.runtime.publish("session", {"state": state}, source="dashboard")

    @Slot()
    def resetTripB(self):
        self.logger.info("Reset Trip B demande", extra={"error_code": "UI_RESET_TRIP_B"})
        if self.stats_service:
            self.stats_service.reset_trip_b()

    @Slot()
    def resetTripA(self):
        self.logger.info("Reset Trip A demande", extra={"error_code": "UI_RESET_TRIP_A"})
        if self.stats_service:
            self.stats_service.reset_trip_a()

    @Slot()
    def resetMaintenance(self):
        self.logger.info("Reset maintenance demande", extra={"error_code": "UI_RESET_MAINTENANCE"})
        if self.stats_service:
            self.stats_service.reset_maintenance()

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
        self._profile_theme_controller.save_setting(key_path, value)

    def _config_writer_loop(self):
        """Écrivain unique avec debounce : aucun fichier .tmp partagé entre threads."""
        while not self._config_writer_stop.is_set():
            if not self._config_write_requested.wait(0.5):
                continue
            self._config_write_requested.clear()
            # Regroupe les glissements tactiles successifs d'un même réglage.
            self._config_writer_stop.wait(0.08)
            if self._config_write_requested.is_set():
                continue
            if self._write_current_config():
                self.logger.info("Configuration sauvegardee", extra={"error_code": "CONFIG_SAVED"})
            else:
                self.logger.error("Echec sauvegarde configuration", extra={"error_code": "CONFIG_SAVE_ERROR"})
                self.send_notification("WARNING", "Réglage conservé en mémoire uniquement", 4000)

    def relocate_config(self, new_config_path: str) -> bool:
        with self._config_lock:
            self._config_path = new_config_path
        return self._write_current_config()

    def _write_current_config(self) -> bool:
        with self._config_write_lock:
            with self._config_lock:
                target = self._config_path
                snapshot = json.loads(json.dumps(self._config))
            tmp_path = target + ".tmp"
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, target)
                return True
            except OSError:
                try:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except OSError:
                    pass
                return False

    def close(self):
        """Vide la dernière configuration et arrête l'écrivain sérialisé."""
        if self._closed:
            return True
        self._closed = True
        self.timer_fast.stop()
        self.timer_slow.stop()
        self.timer_updater.stop()
        saved = self._write_current_config()
        self._config_writer_stop.set()
        self._config_write_requested.set()
        if self._config_writer_thread is not threading.current_thread():
            self._config_writer_thread.join(timeout=1.0)
        return saved

    @Slot(float)
    def updateFuelPrice(self, new_price: float):
        if self.stats_service:
            self.stats_service.set_fuel_price(new_price)
            self.logger.info(f"Prix carburant mis a jour: {new_price}", extra={"error_code": "FUEL_PRICE_UPDATE"})

    @Slot(str, bool)
    def toggleService(self, service_name: str, enable: bool):
        storage_key = f"services.{service_name}.enabled"
        if self.storage is not None:
            self.storage.set(storage_key, enable)

        if enable:
            self.orchestrator.start_service(service_name)
        else:
            self.orchestrator.stop_service(service_name)

        self._update_health()

    def send_notification(self, level: str, message: str, duration: int = 3000):
        self.notificationEvent.emit(level, message, duration)

    @Slot(str, float, result=bool)
    def executeUiCommand(self, command: str, speed_kmh: float = 0.0) -> bool:
        """Point d'entrée unique des commandes émises par l'AppShell."""
        return self._command_router.execute(command, speed_kmh)

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
        return self._profile_theme_controller.available_profiles()

    @Slot(result=str)
    def getActiveProfile(self):
        return self._profile_theme_controller.active_profile()

    @Slot(result='QVariantList')
    def getAvailableCanFiles(self):
        return self._profile_theme_controller.available_can_files()

    @Slot(result='QVariantList')
    def getAvailableConfigFiles(self):
        return self._profile_theme_controller.available_config_files()

    @Slot(str, str, str, str, str, result=bool)
    def createNewProfile(self, profile_id: str, name: str, can_file: str, config_file: str, save_file: str):
        return self._profile_theme_controller.create_profile(profile_id, name, can_file, config_file, save_file)

    @Slot(str, result=bool)
    def setActiveProfile(self, profile_id: str):
        return self._profile_theme_controller.set_active_profile(profile_id)

    @Slot()
    def restartApplication(self):
        self.logger.warning("Ordre de redemarrage recu", extra={"error_code": "APP_RESTART_REQUEST"})
        self.send_notification("INFO", "Redémarrage de CliOS en cours...", 2000)
        self.needs_restart = True
        QTimer.singleShot(400, self.exitRequested.emit)

    @Slot()
    def _quit_qt(self):
        app = QCoreApplication.instance()
        if app is not None:
            app.quit()

    @Slot(int, result=str)
    def getRecentLogs(self, limit: int = 100) -> str:
        return self._system_controller.recent_logs(limit)

    @Slot(result=str)
    def exportDiagnosticBundle(self) -> str:
        return self._system_controller.export_diagnostic_bundle()

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

    @Slot()
    def triggerGitUpdate(self):
        """Compatibilité dev uniquement; aucune mise à jour Git n'est lancée."""
        self.logger.warning("triggerGitUpdate obsolète", extra={"error_code": "GIT_UPDATE_DISABLED"})
        self.send_notification("WARNING", "Mise à jour Git désactivée en production", 4000)

    @Slot(result=str)
    def getUpdateChannel(self) -> str:
        return self._updater_controller.channel()

    @Slot(str, result=bool)
    def setUpdateChannel(self, channel: str) -> bool:
        return self._updater_controller.set_channel(channel)

    @Slot()
    def checkForUpdates(self):
        self._check_for_updates(force=True)

    def _check_for_updates(self, force: bool):
        self._updater_controller.check(force)

    @Slot(float)
    def stageUpdate(self, speed_kmh: float = 0.0):
        self._updater_controller.stage(speed_kmh)

    @Slot(float)
    def activateUpdate(self, speed_kmh: float = 0.0):
        self._updater_controller.activate(speed_kmh)

    @Slot(float, bool)
    def rollbackUpdate(self, speed_kmh: float = 0.0, stable_only: bool = False):
        self._updater_controller.rollback(speed_kmh, stable_only)

    @Slot(result=str)
    def getSystemMaintenanceStatus(self) -> str:
        """Retourne les infos système pour le menu de maintenance (JSON)."""
        return self._system_controller.maintenance_status()

    @Slot()
    def toggleOverlayFs(self):
        """Bascule la protection SD (OverlayFS)."""
        self._system_controller.toggle_overlay()

    @Slot()
    def rebootSystem(self):
        """Arrête proprement les services et redémarre le Raspberry Pi."""
        self._system_controller.request_exit("reboot")

    @Slot()
    def quitApplication(self):
        """Arrête proprement les services et ferme l'application."""
        self._system_controller.request_exit("quit")

    @Slot()
    def shutdownSystem(self):
        """Arrête proprement les services et éteint le Raspberry Pi."""
        self._system_controller.request_exit("poweroff")

    @Slot()
    def openMaintenanceMenu(self):
        """Ouvre le menu de maintenance système."""
        self.openMaintenanceRequested.emit()
