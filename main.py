import json
import os
import sys
import argparse

from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

from src.driver import Slcan
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


# --- Console de Débogage ---
def ui_loop(api, stop_event):
    """Interface de débogage en ligne de commande (CLI)."""
    while not stop_event.is_set():
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\033[H\033[2J", end="")
        print("=" * 45)
        print("   CONSOLE DE DEBUG TELEMETRIQUE (CLIOS)")
        print("=" * 45)

        data_dict = api._data.copy()

        if not data_dict:
            print("\nEn attente du flux de donnees...")
        else:
            for key in sorted(data_dict.keys()):
                val = data_dict[key]
                if isinstance(val, bool):
                    status = "\033[92mON\033[0m" if val else "\033[91mOFF\033[0m"
                    print(f" {key:<25} : {status}")
                elif isinstance(val, float):
                    print(f" {key:<25} : {val:.3f}")
                else:
                    print(f" {key:<25} : {val}")

        print("\n[Ctrl+C pour interrompre le processus]")
        stop_event.wait(0.1)


def main():
    # --- Traitement des Arguments ---
    cmd_parser = argparse.ArgumentParser()
    cmd_parser.add_argument('--ui', choices=['cli', 'gui'], default='gui')
    cmd_parser.add_argument('--mock', action='store_true')
    cmd_parser.add_argument('--conf', type=str, default='config_clio3diesel.json')
    args = cmd_parser.parse_args()

    # --- Environnement ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CAN_DIR = os.path.join(BASE_DIR, "can")
    CONFIG_DIR = os.path.join(BASE_DIR, "config")
    STORAGE_DIR = os.path.join(BASE_DIR, "data")
    SOUNDS_DIR = os.path.join(BASE_DIR, "assets", "sounds")
    ENGINE_DIR = os.path.join(SOUNDS_DIR, "engine")

    with open(os.path.join(CONFIG_DIR, args.conf), 'r', encoding='utf-8') as f:
        vehicle_config = json.load(f)

    # --- 1. Initialisation du Disque Dur Central ---
    if args.mock:
        storage_file_name = "save_mock.json"
    else:
        storage_file_name = "save.json"

    storage_file_path = os.path.join(STORAGE_DIR, storage_file_name)

    storage = PersistentStorage(storage_file_path)

    api = VehicleAPI(storage)
    api.run_startup_sequence(duration_sec=1.5)

    # --- 2. Initialisation de l'Orchestrateur ---
    orchestrator = SystemOrchestrator()

    # --- 3. Branchement des Périphériques ---
    if args.mock:
        can_provider = PhysicsMockProvider(api)
    else:
        can_provider = Slcan(channel="/dev/cu.usbmodem207B3949534B1", baudrate=500000)

    # --- 4. Création et Ajout de TOUS les services de base ---
    diag_service = DiagnosticService(api, can_provider)
    led_service = BleLedController(storage)
    stats_service = TripStatsService(api, vehicle_config, storage)
    dynamics_service = DynamicsService(api, storage)
    engine_sound_service = EngineSoundService(api, storage,engine_path=ENGINE_DIR)
    cabin_sound_service = CabinNoiseService(api, storage)
    monitor_service = SystemMonitorService(api, storage)

    can_service = CanService(
        name="CAN_Moteur",
        api=api,
        storage=storage,
        dbc_path=os.path.join(CAN_DIR, "can_moteur_clio3.json"),
        provider=can_provider,
        obd_callback=diag_service.receive_obd_frame
    )

    orchestrator.add_service(can_service, enabled=storage.get("services.Can.enabled", True))
    orchestrator.add_service(diag_service, enabled=storage.get("services.Diag.enabled", True))
    orchestrator.add_service(stats_service, enabled=storage.get("services.TripStats.enabled", True))
    orchestrator.add_service(dynamics_service, enabled=storage.get("services.Dynamics.enabled", True))
    orchestrator.add_service(monitor_service, enabled=storage.get("services.Monitor.enabled", True))
    orchestrator.add_service(engine_sound_service, enabled=storage.get("services.EngineSound.enabled", False))
    orchestrator.add_service(cabin_sound_service, enabled=storage.get("services.Noise.enabled", True))
    orchestrator.add_service(led_service, enabled=storage.get("services.Leds.enabled", True))

    # --- 5. Lancement de l'IHM ---
    try:
        if args.ui == 'cli':
            orchestrator.start_all()
            ui_loop(api, orchestrator.stop_event)

        elif args.ui == 'gui':
            QQuickStyle.setStyle("Basic")

            app = QApplication(sys.argv)
            engine = QQmlApplicationEngine()

            bridge = DashboardBridge(
                api,
                os.path.join(CONFIG_DIR, args.conf),
                orchestrator=orchestrator,
                led_service=led_service,
                stats_service=stats_service,
                diag_service=diag_service
            )
            # Ajout du storage au pont si on en a besoin plus tard (Optionnel mais pratique)
            bridge.storage = storage

            engine.rootContext().setContextProperty("bridge", bridge)

            notif_service = NotificationService(bridge, storage)
            orchestrator.add_service(notif_service, enabled=storage.get("services.Notification", True))

            orchestrator.start_all()

            control_panel = None
            if args.mock:
                control_panel = MockControlPanel(can_provider)
                control_panel.show()

            engine.load(os.path.join(BASE_DIR, "frontend", "main.qml"))

            if not engine.rootObjects():
                sys.exit(-1)

            app.exec()
            del engine
            del bridge

    except KeyboardInterrupt:
        print("\n[INFO] Interruption manuelle détectée.")
    finally:
        # --- 6. Arrêt propre ---
        orchestrator.stop_all()


if __name__ == "__main__":
    main()