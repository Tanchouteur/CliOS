import json
import os
import sys
import argparse
import threading

from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

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

# Import de notre outil de debug externalisé
from src.cli_debug import ui_loop


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


def setup_services(api, storage, orchestrator, can_provider, vehicle_config, profile_manager, engine_dir, storage_dir,
                   diag_cfg=None):
    """Initialise et enregistre tous les services via une boucle propre."""

    diag_service = DiagnosticService(api, can_provider)
    can_service = CanService(
        name="CAN_Moteur",
        api=api,
        storage=storage,
        dbc_path=profile_manager.get_can_path(),
        provider=can_provider,
        obd_callback=diag_service.receive_obd_frame,
        diag=diag_cfg
    )

    led_service = BleLedController(storage)
    stats_service = TripStatsService(api, vehicle_config, storage)
    dynamics_service = DynamicsService(api, vehicle_config, storage)
    gear_calib_service = GearCalibrationService(api, storage, profile_manager, dynamics_service)
    session_manager = TripSessionManager(api, storage, stats_service, storage_dir)

    services_to_register = [
        (can_service, "services.Can.enabled", True),
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

    for service, storage_key, default_state in services_to_register:
        orchestrator.add_service(service, enabled=storage.get(storage_key, default_state))

    return led_service, stats_service, diag_service, gear_calib_service, session_manager


def main():
    # --- 1. Arguments & Environnement ---
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', choices=['cli', 'gui'], default='gui')
    parser.add_argument('--mock', action='store_true')
    parser.add_argument('--diag', action='store_true', help="Active les options de diagnostic crash GUI/CAN.")
    parser.add_argument('--diag-no-can-api', action='store_true',
                        help="Le CAN décode mais n'écrit plus dans l'API (isole CAN->API).")
    parser.add_argument('--diag-no-fast-emit', action='store_true',
                        help="Le bridge met à jour son cache mais n'émet plus dataChanged (isole Bridge->QML).")
    parser.add_argument('--diag-fast-ms', type=int, default=16,
                        help="Période du timer fast du bridge en ms (défaut: 16).")
    parser.add_argument('--diag-keys', default="",
                        help="Liste CSV de clés autorisées vers QML et API (ex: speed,rpm,clutch).")
    parser.add_argument('--diag-log-types', action='store_true',
                        help="Log les changements de type des clés CAN.")
    parser.add_argument('--diag-log-bridge', action='store_true',
                        help="Log le rythme d'émission du bridge.")
    parser.add_argument('--diag-log-api', action='store_true',
                        help="Log la fréquence des update() API et les changements de type par clé.")
    args = parser.parse_args()

    include_keys = [k.strip() for k in args.diag_keys.split(',') if k.strip()]
    diag_cfg = {
        "enabled": args.diag,
        "disable_can_api_update": args.diag_no_can_api,
        "disable_fast_emit": args.diag_no_fast_emit,
        "fast_timer_ms": max(5, int(args.diag_fast_ms)),
        "include_keys": include_keys,
        "log_type_changes": args.diag_log_types,
        "log_bridge": args.diag_log_bridge,
        "log_api": args.diag_log_api,
    }

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STORAGE_DIR = os.path.join(BASE_DIR, "data")
    CAN_DIR = os.path.join(STORAGE_DIR, "can")
    CONFIG_DIR = os.path.join(STORAGE_DIR, "config")
    SAVE_DASH_DIR = os.path.join(STORAGE_DIR, "dash_save")
    ENGINE_DIR = os.path.join(BASE_DIR, "assets", "sounds", "engine")

    # --- 2. Initialisation Core (Fichiers, BDD, API) ---
    profile_manager = ProfileManager(CONFIG_DIR, CAN_DIR, SAVE_DASH_DIR, args.mock)

    with open(profile_manager.get_config_path(), 'r', encoding='utf-8') as f:
        vehicle_config = json.load(f)

    storage = PersistentStorage(profile_manager.get_save_path())
    api = VehicleAPI(storage, diag_cfg)

    # --- NOUVEAU : Chargement et injection de la version système ---
    app_version = load_system_version(BASE_DIR)
    api.update({"system_version": app_version})
    print(f"\n[INFO] 🚀 Démarrage de ClOS (Version : {app_version})")

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
        api, storage, orchestrator, can_provider, vehicle_config, profile_manager, ENGINE_DIR, TRIPS_DIR, diag_cfg
    )

    # --- 5. Lancement de l'Application ---
    needs_restart = False
    try:
        if args.ui == 'cli':
            orchestrator.start_all()
            cli_stop_event = threading.Event()
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
                session_manager=session_manager,
                diag=diag_cfg
            )
            bridge.storage = storage
            engine.rootContext().setContextProperty("bridge", bridge)

            # Notifications Système
            notif_service = NotificationService(bridge, storage)
            orchestrator.add_service(notif_service, enabled=storage.get("services.Notification", True))

            orchestrator.start_all()

            if diag_cfg["enabled"]:
                print("[DIAG] Mode diagnostic actif")
                print(f"[DIAG] fast_timer_ms={diag_cfg['fast_timer_ms']} disable_fast_emit={diag_cfg['disable_fast_emit']}")
                print(f"[DIAG] disable_can_api_update={diag_cfg['disable_can_api_update']} include_keys={diag_cfg['include_keys']}")

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
        print("\n[INFO] Interruption manuelle détectée.")
    finally:
        # --- 6. Nettoyage et Arrêt ---
        print("[INFO] Extinction de l'orchestrateur et libération des ports...")
        orchestrator.stop_all()

    # --- 7. Redémarrage Kiosk ---
    if needs_restart:
        print("[INFO] >>> REDÉMARRAGE DU SYSTÈME <<<")
        os.execv(sys.executable, ['python'] + sys.argv)


if __name__ == "__main__":
    main()