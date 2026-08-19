import json
import os
import threading

from PySide6.QtCore import QObject, Signal, Property, QTimer, Slot, QCoreApplication
from src.logging_runtime import get_logger, get_recent_events
from src.diagnostic_bundle import create_diagnostic_bundle
from src.state_store import VEHICLE_DOMAINS


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

    def __init__(self, runtime, config_path, orchestrator, led_service=None, stats_service=None, diag_service=None,
                 profile_manager=None, gear_calib_service=None, session_manager=None, storage_manager=None):
        super().__init__()
        self.logger = get_logger("DashboardBridge")
        self.session_manager = session_manager
        self.runtime = runtime
        self.storage = getattr(runtime, "storage", None)
        self.led_service = led_service
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

        self._config_path = config_path
        self._vehicle_state = {}
        self._trip_state = {}
        self._diagnostics_state = {}
        self._system_state = {}
        self._session_state = {}
        self._calibration_state = {}
        self._presentation_state = {}
        self._data_quality = {}

        with open(config_path, 'r') as f:
            self._config = json.load(f)

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

        self.needs_restart = False

    # Boucles de rafraîchissement.
    def _update_fast_data(self):
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
        system = self.runtime.snapshot().domain("system")
        version = system.get("system_version", "unknown")
        telemetry = {key: value for key, value in system.items() if key != "system_version"}
        new_system = self._sanitize_for_qml({
            "version": version,
            "telemetry": telemetry,
            "health": self.orchestrator.get_system_health(),
            "storage": self._read_storage_status(),
        })
        if new_system != self._system_state:
            self._system_state = new_system
            self.systemStateChanged.emit()
        new_quality = self._sanitize_for_qml(self.runtime.metadata_snapshot())
        if new_quality != self._data_quality:
            self._data_quality = new_quality
            self.dataQualityChanged.emit()

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
            except Exception:
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
        """Découvre les paquets UI placés dans frontend/styles/<id>/style.json."""
        required_colors = {
            "background", "surface", "surfaceRaised", "surfaceSoft",
            "text", "textSecondary", "outline", "gaugeTrack",
        }
        styles = []
        try:
            entries = sorted(os.scandir(self._ui_styles_dir), key=lambda entry: entry.name)
        except OSError as exc:
            self.logger.error(f"Catalogue de styles illisible: {exc}", extra={"error_code": "UI_STYLE_CATALOG_ERROR"})
            return []

        for entry in entries:
            if not entry.is_dir() or entry.name.startswith("_") or not entry.name.replace("_", "").isalnum():
                continue
            manifest_path = os.path.join(entry.path, "style.json")
            try:
                with open(manifest_path, "r", encoding="utf-8") as manifest_file:
                    manifest = json.load(manifest_file)
            except (OSError, json.JSONDecodeError, TypeError):
                continue

            style_id = str(manifest.get("id", ""))
            dashboard_file = os.path.basename(str(manifest.get("dashboard", "Dashboard.qml")))
            palette = manifest.get("palette", {})
            if style_id != entry.name or not dashboard_file.endswith(".qml"):
                continue
            if not isinstance(palette, dict) or not required_colors.issubset(palette):
                continue
            if not os.path.isfile(os.path.join(entry.path, dashboard_file)):
                continue

            styles.append({
                "id": style_id,
                "label": str(manifest.get("label", style_id)),
                "description": str(manifest.get("description", "")),
                "order": int(manifest.get("order", 100)),
                "dashboard": f"styles/{style_id}/{dashboard_file}",
                "palette": {key: str(palette[key]) for key in required_colors},
                "metrics": self._sanitize_for_qml(manifest.get("metrics", {})),
            })

        styles.sort(key=lambda item: (item["order"], item["label"].lower()))
        return styles

    @Slot()
    def requestDiagnosticScan(self):
        if self.diag_service:
            self.diag_service.request_scan()

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
        if key_path == "theme.main" and self.led_service:
            self.led_service.set_color(value)

        keys = key_path.split('.')
        with self._config_lock:
            current_dict = self._config
            for k in keys[:-1]:
                if k not in current_dict:
                    current_dict[k] = {}
                current_dict = current_dict[k]
            current_dict[keys[-1]] = value
        self.configChanged.emit()

        self._config_write_requested.set()

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
        if not self.profile_manager.add_profile(profile_id, name, can_file, config_file, save_file):
            return False
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
            if self._storage_manager:
                log_dir = self._storage_manager.resolve_path("logs")
                output_dir = self._storage_manager.resolve_path("diagnostics")
            else:
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


    @Slot()
    def triggerGitUpdate(self):
        """Déclenche la mise à jour Git de CliOS en arrière-plan."""
        self.logger.info("Déclenchement mise à jour Git", extra={"error_code": "MAINT_GIT_UPDATE"})
        self.send_notification("INFO", "Mise à jour Git en cours...", 4000)

        def _update_task():
            import subprocess
            try:
                script_candidates = [
                    os.path.expanduser("~/update_clios.sh"),
                    os.path.expanduser("~/Desktop/update.sh"),
                    os.path.expanduser("~/Desktop/git_pull.sh"),
                    os.path.expanduser("~/git_pull.sh"),
                ]
                custom_script = next((s for s in script_candidates if os.path.isfile(s)), None)

                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if custom_script:
                    res = subprocess.run(["bash", custom_script], capture_output=True, text=True, timeout=120)
                else:
                    res = subprocess.run(["git", "pull", "--rebase"], cwd=project_root, capture_output=True, text=True, timeout=60)

                if res.returncode == 0:
                    self.logger.info(f"Mise à jour Git réussie: {res.stdout.strip()}", extra={"error_code": "GIT_PULL_SUCCESS"})
                    self.send_notification("SUCCESS", "Mise à jour terminée ! Veuillez redémarrer CliOS.", 5000)
                else:
                    err_msg = res.stderr.strip() or res.stdout.strip() or "Code erreur non nul"
                    self.logger.error(f"Échec mise à jour Git: {err_msg}", extra={"error_code": "GIT_PULL_ERROR"})
                    self.send_notification("ERROR", f"Échec mise à jour : {err_msg[:60]}", 6000)
            except subprocess.TimeoutExpired:
                self.logger.error("Timeout lors de la mise à jour Git", extra={"error_code": "GIT_PULL_TIMEOUT"})
                self.send_notification("ERROR", "Délai dépassé lors du git pull (pas d'accès Internet ?)", 5000)
            except Exception as e:
                self.logger.error(f"Erreur inattendue git pull: {e}", extra={"error_code": "GIT_PULL_EXCEPTION"})
                self.send_notification("ERROR", f"Erreur màj: {str(e)[:50]}", 5000)

        threading.Thread(target=_update_task, daemon=True, name="GitUpdateThread").start()

    @Slot(result=str)
    def getSystemMaintenanceStatus(self) -> str:
        """Retourne les infos système pour le menu de maintenance (JSON)."""
        import socket
        import subprocess

        ip_addr = "Hors-ligne"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_addr = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                ip_addr = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip_addr = "127.0.0.1"

        overlay_status = "READ_WRITE"
        try:
            with open("/proc/mounts", "r") as f:
                mounts = f.read()
                if "overlay on / " in mounts or ("/dev/root" not in mounts and "overlay" in mounts):
                    overlay_status = "READ_ONLY"
        except Exception:
            overlay_status = "READ_WRITE"

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        git_info = "main"
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=project_root, stderr=subprocess.DEVNULL, text=True, timeout=2
            ).strip()
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=project_root, stderr=subprocess.DEVNULL, text=True, timeout=2
            ).strip()
            git_info = f"{branch} ({commit})"
        except Exception:
            pass

        cpu_temp = ""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                t = float(f.read().strip()) / 1000.0
                cpu_temp = f"{t:.1f}°C"
        except Exception:
            pass

        system = self.runtime.snapshot().domain("system")
        version = system.get("system_version", "unknown")

        return json.dumps({
            "version": version,
            "ip_address": ip_addr,
            "overlay_status": overlay_status,
            "git_info": git_info,
            "cpu_temp": cpu_temp,
        })

    @Slot()
    def toggleOverlayFs(self):
        """Bascule la protection SD (OverlayFS)."""
        self.logger.info("Bascule protection SD demandée", extra={"error_code": "MAINT_SD_TOGGLE"})

        def _toggle_task():
            import subprocess
            script_candidates = [
                os.path.expanduser("~/Desktop/protected.sh"),
                os.path.expanduser("~/Desktop/toggle_readonly.sh"),
                os.path.expanduser("~/toggle_overlay.sh"),
                os.path.expanduser("~/protect_sd.sh"),
            ]
            custom_script = next((s for s in script_candidates if os.path.isfile(s)), None)

            try:
                if custom_script:
                    res = subprocess.run(["bash", custom_script], capture_output=True, text=True, timeout=30)
                    self.send_notification("WARNING", "Protection SD basculée ! Redémarrez le système.", 5000)
                else:
                    check = subprocess.run(["sudo", "raspi-config", "nonint", "get_overlay_now"], capture_output=True, text=True)
                    is_enabled = check.stdout.strip() == "0"
                    if is_enabled:
                        subprocess.run(["sudo", "raspi-config", "nonint", "disable_overlayfs"], timeout=30)
                        self.send_notification("WARNING", "Protection SD désactivée (Mode RW). Redémarrez pour valider.", 5000)
                    else:
                        subprocess.run(["sudo", "raspi-config", "nonint", "enable_overlayfs"], timeout=30)
                        self.send_notification("SUCCESS", "Protection SD activée (Lecture Seule). Redémarrez pour valider.", 5000)
            except Exception as e:
                self.logger.error(f"Erreur bascule SD: {e}", extra={"error_code": "SD_TOGGLE_ERROR"})
                self.send_notification("ERROR", f"Erreur SD: {str(e)[:50]}", 4000)

        threading.Thread(target=_toggle_task, daemon=True, name="SdToggleThread").start()

    @Slot()
    def rebootSystem(self):
        """Arrête proprement les services et redémarre le Raspberry Pi."""
        self.logger.warning("Redémarrage matériel demandé", extra={"error_code": "SYS_REBOOT"})
        self.send_notification("WARNING", "Redémarrage du système...", 3000)
        threading.Thread(target=self._handle_exit, args=(False, True), daemon=True).start()

    # Pas super propre. A re faire
    @Slot()
    def quitApplication(self):
        """Arrête proprement les services et ferme l'application."""
        self.logger.info("Fermeture manuelle de l'application", extra={"error_code": "APP_QUIT"})
        self.send_notification("INFO", "Fermeture de l'application...", 2000)
        threading.Thread(target=self._handle_exit, args=(False, False), daemon=True).start()

    @Slot()
    def shutdownSystem(self):
        """Arrête proprement les services et éteint le Raspberry Pi."""
        self.logger.warning("Extinction système demandée", extra={"error_code": "SYS_SHUTDOWN"})
        self.send_notification("WARNING", "Extinction du système...", 3000)
        threading.Thread(target=self._handle_exit, args=(True, False), daemon=True).start()

    def _handle_exit(self, poweroff=False, reboot=False):
        import time
        import os
        import platform

        # Temps pour laisser l'UI afficher la notification
        time.sleep(1.0)

        # Arrêt de l'orchestrateur (déclenche le .stop() de chaque service pour sauvegarder)
        self.close()
        self.orchestrator.stop_all()
        time.sleep(0.8)

        if reboot and platform.system() not in ["Darwin", "Windows"]:
            os.system("sudo reboot")
        elif poweroff and platform.system() not in ["Darwin", "Windows"]:
            os.system("sudo poweroff")
        else:
            # os._exit(0) est plus radical que quit() pour s'assurer que le thread principal s'arrête
            os._exit(0)
