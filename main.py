import os
import sys
import argparse
import threading

from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6 import __version__ as pyside_version

from src.services.export_service import ExportService
from src.profile_manager import ProfileManager
from src.driver import Slcan
from src.services.gear_calibration_service import GearCalibrationService
from src.services.power_management_service import PowerManagementService
from src.services.trip_session_manager import TripSessionManager
from src.services.usb_storage_service import UsbStorageService
from src.simulation.physique_mock import PhysicsMockProvider
from src.simulation.mock_ui import MockControlPanel

from src.services.cabin_noise_service import CabinNoiseService
from src.services.can_service import CanService
from src.services.diagnostic_service import DiagnosticService
from src.services.engine_sound_service import EngineSoundService
from src.services.led_service import BleLedController
from src.services.notification_service import NotificationService
from src.orchestrator import SystemOrchestrator
from src.services.system_monitor_service import SystemMonitorService
from src.services.trip_stats_service import TripStatsService
from src.services.vehicle_metrics_service import VehicleMetricsService
from src.storage import PersistentStorage
from src.runtime import VehicleRuntime
from src.qt_bridge import DashboardBridge
from src.services.dynamics_service import DynamicsService
from src.logging_runtime import init_logging, relocate_log_dir, set_global_context, shutdown_logging, get_logger
from src.crash_hooks import install_crash_hooks, relocate_crash_log
from src.storage_manager import StorageManager, StorageMode

# Import de notre outil de debug externalisé
from src.cli_debug import ui_loop


def ensure_supported_pyside(is_gui: bool, allow_unsupported: bool) -> None:
    """Bloque les versions PySide6 connues instables en mode GUI."""
    if not is_gui:
        return

    def parse_version(version_str: str):
        parts = []
        for token in str(version_str).split('.'):
            if token.isdigit():
                parts.append(int(token))
            else:
                break
        return tuple(parts)

    installed = parse_version(str(pyside_version))
    minimum_stable = (6, 8, 0)

    if installed < minimum_stable and not allow_unsupported:
        print(
            f"[ERREUR] PySide6 {pyside_version} est instable pour cette UI (segfault/bool_dealloc connus sur < 6.8.0)."
        )
        print("[ERREUR] Mettez à jour vers PySide6 6.8.0+ ou lancez avec --allow-unsupported-pyside.")
        sys.exit(2)


# ==========================================
# GESTION DE LA VERSION (SSOT)
# ==========================================
def load_system_version(root_dir: str) -> str:
    """Lit la version du système depuis le fichier maître 'VERSION'."""
    version_file = os.path.join(root_dir, 'VERSION')
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("[ATTENTION] Fichier VERSION introuvable. Version fixée sur 'unknown'.")
        return "unknown"


def setup_services(runtime, storage, orchestrator, can_provider, vehicle_config, profile_manager, engine_dir,
                   storage_dir, storage_manager):
    """Initialise et enregistre tous les services via une boucle propre."""

    diag_service = DiagnosticService(runtime, can_provider)
    can_service = CanService(
        name="CAN_Moteur",
        runtime=runtime,
        storage=storage,
        dbc_path=profile_manager.get_can_path(),
        provider=can_provider,
        obd_callback=diag_service.receive_obd_frame
    )

    led_service = BleLedController(storage)
    stats_service = TripStatsService(runtime, vehicle_config, storage)
    dynamics_service = DynamicsService(runtime, vehicle_config, storage)
    gear_calib_service = GearCalibrationService(runtime, storage, profile_manager, dynamics_service)
    session_manager = TripSessionManager(runtime, storage, stats_service, storage_dir)

    services_to_register = [
        (can_service, "services.CAN_Moteur.enabled", True),
        (diag_service, "services.Diag.enabled", True),
        (stats_service, "services.TripStats.enabled", True),
        (VehicleMetricsService(runtime, vehicle_config, storage), "services.VehicleMetrics.enabled", True),
        (dynamics_service, "services.Dynamics.enabled", True),
        (gear_calib_service, "services.GearCalibration.enabled", True),
        (SystemMonitorService(runtime, storage), "services.Monitor.enabled", True),
        (EngineSoundService(runtime, storage, engine_path=engine_dir), "services.EngineSound.enabled", False),
        (CabinNoiseService(runtime, storage), "services.Noise.enabled", True),
        (led_service, "services.Leds.enabled", True),
        (PowerManagementService(runtime, storage, orchestrator), "services.PowerManager.enabled", True),
        (session_manager, "services.SessionManager.enabled", True),
        (UsbStorageService(runtime, storage, storage_manager), None, True),
    ]

    # Rétrocompatibilité: anciennes sauvegardes utilisaient services.Can.enabled
    can_enabled = storage.get("services.CAN_Moteur.enabled", storage.get("services.Can.enabled", True))

    for service, storage_key, default_state in services_to_register:
        if service.service_name == "CAN_Moteur":
            orchestrator.add_service(service, enabled=can_enabled)
        elif storage_key is None:
            orchestrator.add_service(service, enabled=True)
        else:
            orchestrator.add_service(service, enabled=storage.get(storage_key, default_state))

    return led_service, stats_service, diag_service, gear_calib_service, session_manager


def main():
    # --- 1. Arguments & Environnement ---
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', choices=['cli', 'gui'], default='gui')
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--allow-unsupported-pyside', action='store_true')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    args = parser.parse_args()

    ensure_supported_pyside(is_gui=(args.ui == 'gui'), allow_unsupported=args.allow_unsupported_pyside)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DATA_DIR = os.path.join(BASE_DIR, "data")
    storage_mgr = StorageManager(BASE_DIR)
    storage_mgr.start_monitoring()

    LOG_DIR = storage_mgr.resolve_path("logs")

    init_logging(LOG_DIR, level=args.log_level, console_level="WARNING")
    install_crash_hooks(LOG_DIR)
    set_global_context(ui=args.ui, mock=args.mock)
    logger = get_logger("Main")
    CAN_DIR = os.path.join(STATIC_DATA_DIR, "can")
    STATIC_CONFIG_DIR = os.path.join(STATIC_DATA_DIR, "config")
    CONFIG_DIR = storage_mgr.prepare_config_dir(STATIC_CONFIG_DIR)
    SAVE_DASH_DIR = storage_mgr.resolve_path("dash_save")
    ENGINE_DIR = os.path.join(BASE_DIR, "assets", "sounds", "engine")

    # --- 2. Initialisation Core (Fichiers, BDD, Runtime) ---
    profile_manager = ProfileManager(
        CONFIG_DIR,
        CAN_DIR,
        SAVE_DASH_DIR,
        args.mock,
        fallback_config_dir=STATIC_CONFIG_DIR,
    )
    vehicle_config = profile_manager.load_active_config()

    storage = PersistentStorage(profile_manager.get_save_path())
    runtime = VehicleRuntime(storage)

    # Charge la version applicative et l'expose à l'interface.
    app_version = load_system_version(BASE_DIR)
    set_global_context(app_version=app_version)
    runtime.publish("system", {"system_version": app_version}, source="application")
    logger.info("Demarrage de ClOS", extra={"error_code": "APP_START"})

    runtime.run_startup_sequence(duration_sec=1.5)

    orchestrator = SystemOrchestrator()

    # --- 3. Initialisation Hardware ---
    if args.mock:
        can_provider = PhysicsMockProvider(
            runtime,
            config=vehicle_config,
            can_db_path=profile_manager.get_can_path(),
        )
    else:
        can_provider = Slcan()

    folder_name = "trips_mock" if profile_manager.is_mock else "trips"
    TRIPS_DIR = storage_mgr.resolve_path(folder_name)

    # --- 4. Branchement des Services ---
    led_srv, stats_srv, diag_srv, gear_calib_srv, session_manager = setup_services(
        runtime, storage, orchestrator, can_provider, vehicle_config, profile_manager, ENGINE_DIR, TRIPS_DIR,
        storage_mgr
    )

    runtime_targets = {"bridge": None, "export": None}

    def on_storage_mode_changed(new_mode):
        new_config_dir = storage_mgr.prepare_config_dir(STATIC_CONFIG_DIR)
        new_save_dir = storage_mgr.resolve_path("dash_save")
        profile_manager.relocate(new_config_dir, new_save_dir)
        storage.relocate(
            profile_manager.get_save_path(),
            merge_existing=(new_mode is StorageMode.USB),
        )
        new_trips_dir = storage_mgr.resolve_path(folder_name)
        session_manager.update_trips_dir(new_trips_dir)
        relocate_log_dir(storage_mgr.resolve_path("logs"))
        relocate_crash_log(storage_mgr.resolve_path("logs"))

        bridge = runtime_targets["bridge"]
        if bridge is not None:
            bridge.relocate_config(profile_manager.get_config_path())
        export_service = runtime_targets["export"]
        if export_service is not None:
            export_service.update_data_dir(new_trips_dir)

    storage_mgr.register_callback(on_storage_mode_changed)
    on_storage_mode_changed(storage_mgr.mode)

    # --- 5. Lancement de l'Application ---
    needs_restart = False
    try:
        if args.ui == 'cli':
            cli_stop_event = threading.Event()
            orchestrator.start_all()
            ui_loop(runtime, cli_stop_event)

        elif args.ui == 'gui':
            QQuickStyle.setStyle("Basic")
            app = QApplication(sys.argv)
            engine = QQmlApplicationEngine()

            # Connexion du Bridge
            bridge = DashboardBridge(
                runtime,
                profile_manager.get_config_path(),
                orchestrator=orchestrator,
                led_service=led_srv,
                stats_service=stats_srv,
                diag_service=diag_srv,
                profile_manager=profile_manager,
                gear_calib_service=gear_calib_srv,
                session_manager=session_manager,
                storage_manager=storage_mgr,
            )
            runtime_targets["bridge"] = bridge
            bridge.storage = storage
            engine.rootContext().setContextProperty("bridge", bridge)

            # Notifications Système
            notif_service = NotificationService(runtime, bridge.send_notification, storage)
            orchestrator.add_service(notif_service, enabled=storage.get("services.Notification", True))

            exp_service = ExportService(bridge.send_notification, storage, storage_mgr.resolve_path(folder_name))
            runtime_targets["export"] = exp_service
            orchestrator.add_service(exp_service, enabled=storage.get("services.Export.enabled", True))

            # Lancement QML immédiat (First-Frame First : affichage prioritaire)
            engine.load(os.path.join(BASE_DIR, "frontend", "main.qml"))
            if not engine.rootObjects():
                sys.exit(-1)

            # Démarrage des services d'arrière-plan dès le premier tick d'affichage
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, orchestrator.start_all)

            # Outils de Mock
            mock_panel = None
            if args.mock:
                mock_panel = MockControlPanel(can_provider)
                mock_panel.show()

            app.exec()
            needs_restart = bridge.needs_restart

    except KeyboardInterrupt:
        logger.warning("Interruption manuelle detectee", extra={"error_code": "APP_KEYBOARD_INTERRUPT"})
    finally:
        # --- 6. Nettoyage et Arrêt ---
        logger.info("Extinction de l'orchestrateur", extra={"error_code": "APP_SHUTDOWN"})
        storage_mgr.stop_monitoring()
        orchestrator.stop_all()
        bridge = runtime_targets.get("bridge")
        if bridge is not None:
            bridge.close()
        if hasattr(storage, "close"):
            storage.close()
        shutdown_logging()

    # --- 7. Redémarrage Kiosk ---
    if needs_restart:
        logger.warning("Redemarrage demande", extra={"error_code": "APP_RESTART"})
        executable = sys.executable
        args = [executable] + sys.argv
        os.execv(executable, args)


if __name__ == "__main__":
    main()
