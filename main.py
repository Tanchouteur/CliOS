import json
import os
import sys
import argparse
import threading

from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6 import __version__ as pyside_version

from src.profile_manager import ProfileManager
from src.driver import Slcan
from src.services.gear_calibration_service import GearCalibrationService
from src.services.power_management_service import PowerManagementService
from src.services.trip_session_manager import TripSessionManager
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
from src.storage import PersistentStorage
from src.api import VehicleAPI
from src.qt_bridge import DashboardBridge
from src.services.dynamics_service import DynamicsService
from src.logging_runtime import init_logging, set_global_context, shutdown_logging, get_logger
from src.crash_hooks import install_crash_hooks

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
    minimum_stable = (6, 8, 2, 1)

    if installed < minimum_stable and not allow_unsupported:
        print(
            f"[ERREUR] PySide6 {pyside_version} est instable pour cette UI (segfault/bool_dealloc connus)."
        )
        print("[ERREUR] Mettez à jour vers PySide6 6.8.2.1+ ou lancez avec --allow-unsupported-pyside.")
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


def setup_services(api, storage, orchestrator, can_provider, vehicle_config, profile_manager, engine_dir, storage_dir):
    """Initialise et enregistre tous les services via une boucle propre."""

    diag_service = DiagnosticService(api, can_provider)
    can_service = CanService(
        name="CAN_Moteur",
        api=api,
        storage=storage,
        dbc_path=profile_manager.get_can_path(),
        provider=can_provider,
        obd_callback=diag_service.receive_obd_frame
    )

    led_service = BleLedController(storage)
    stats_service = TripStatsService(api, vehicle_config, storage)
    dynamics_service = DynamicsService(api, vehicle_config, storage)
    gear_calib_service = GearCalibrationService(api, storage, profile_manager, dynamics_service)
    session_manager = TripSessionManager(api, storage, stats_service, storage_dir)

    services_to_register = [
        (can_service, "services.CAN_Moteur.enabled", True),
        (diag_service, "services.Diag.enabled", True),
        (stats_service, "services.TripStats.enabled", True),
        (dynamics_service, "services.Dynamics.enabled", True),
        (gear_calib_service, "services.GearCalibration.enabled", True),
        (SystemMonitorService(api, storage), "services.Monitor.enabled", True),
        (EngineSoundService(api, storage, engine_path=engine_dir), "services.EngineSound.enabled", False),
        (CabinNoiseService(api, storage), "services.Noise.enabled", True),
        (led_service, "services.Leds.enabled", True),
        (PowerManagementService(api, storage, orchestrator), "services.PowerManager.enabled", True),
        (session_manager, "services.SessionManager.enabled", True),
    ]

    # Rétrocompatibilité: anciennes sauvegardes utilisaient services.Can.enabled
    can_enabled = storage.get("services.CAN_Moteur.enabled", storage.get("services.Can.enabled", True))

    for service, storage_key, default_state in services_to_register:
        if service.service_name == "CAN_Moteur":
            orchestrator.add_service(service, enabled=can_enabled)
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
    STORAGE_DIR = os.path.join(BASE_DIR, "data")
    LOG_DIR = os.path.join(STORAGE_DIR, "logs")

    init_logging(LOG_DIR, level=args.log_level, console_level="WARNING")
    install_crash_hooks(LOG_DIR)
    set_global_context(ui=args.ui, mock=args.mock)
    logger = get_logger("Main")
    CAN_DIR = os.path.join(STORAGE_DIR, "can")
    CONFIG_DIR = os.path.join(STORAGE_DIR, "config")
    SAVE_DASH_DIR = os.path.join(STORAGE_DIR, "dash_save")
    ENGINE_DIR = os.path.join(BASE_DIR, "assets", "sounds", "engine")

    # --- 2. Initialisation Core (Fichiers, BDD, API) ---
    profile_manager = ProfileManager(CONFIG_DIR, CAN_DIR, SAVE_DASH_DIR, args.mock)

    with open(profile_manager.get_config_path(), 'r', encoding='utf-8') as f:
        vehicle_config = json.load(f)

    storage = PersistentStorage(profile_manager.get_save_path())
    api = VehicleAPI(storage)

    # Charge la version applicative et l'expose à l'interface.
    app_version = load_system_version(BASE_DIR)
    set_global_context(app_version=app_version)
    api.update({"system_version": app_version})
    logger.info("Demarrage de ClOS", extra={"error_code": "APP_START"})

    api.run_startup_sequence(duration_sec=1.5)

    orchestrator = SystemOrchestrator()

    # --- 3. Initialisation Hardware ---
    if args.mock:
        can_provider = PhysicsMockProvider(api)
    else:
        can_provider = Slcan()

    folder_name = "trips_mock" if profile_manager.is_mock else "trips"
    TRIPS_DIR = os.path.join(STORAGE_DIR, folder_name)

    # --- 4. Branchement des Services ---
    led_srv, stats_srv, diag_srv, gear_calib_srv, session_manager = setup_services(
        api, storage, orchestrator, can_provider, vehicle_config, profile_manager, ENGINE_DIR, TRIPS_DIR
    )

    # --- 5. Lancement de l'Application ---
    needs_restart = False
    try:
        if args.ui == 'cli':
            cli_stop_event = threading.Event()
            orchestrator.start_all()
            ui_loop(api, cli_stop_event)

        elif args.ui == 'gui':
            QQuickStyle.setStyle("Basic")
            app = QApplication(sys.argv)
            engine = QQmlApplicationEngine()

            # Connexion du Bridge
            bridge = DashboardBridge(
                api,
                profile_manager.get_config_path(),
                orchestrator=orchestrator,
                led_service=led_srv,
                stats_service=stats_srv,
                diag_service=diag_srv,
                profile_manager=profile_manager,
                gear_calib_service=gear_calib_srv,
                session_manager=session_manager
            )
            bridge.storage = storage
            engine.rootContext().setContextProperty("bridge", bridge)

            # Notifications Système
            notif_service = NotificationService(bridge, storage)
            orchestrator.add_service(notif_service, enabled=storage.get("services.Notification", True))

            orchestrator.start_all()

            # Outils de Mock
            mock_panel = None
            if args.mock:
                mock_panel = MockControlPanel(can_provider)
                mock_panel.show()

            # Lancement QML
            engine.load(os.path.join(BASE_DIR, "frontend", "main.qml"))
            if not engine.rootObjects():
                sys.exit(-1)

            app.exec()
            needs_restart = bridge.needs_restart

    except KeyboardInterrupt:
        logger.warning("Interruption manuelle detectee", extra={"error_code": "APP_KEYBOARD_INTERRUPT"})
    finally:
        # --- 6. Nettoyage et Arrêt ---
        logger.info("Extinction de l'orchestrateur", extra={"error_code": "APP_SHUTDOWN"})
        orchestrator.stop_all()
        if hasattr(storage, "close"):
            storage.close()
        shutdown_logging()

    # --- 7. Redémarrage Kiosk ---
    if needs_restart:
        logger.warning("Redemarrage demande", extra={"error_code": "APP_RESTART"})
        os.execv(sys.executable, ['python'] + sys.argv)


if __name__ == "__main__":
    main()