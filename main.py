import json
import os
import sys
import argparse

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from src.driver import Slcan
from src.mock_driver import MockProvider
from src.services.cabin_noise_service import CabinNoiseService
from src.services.can_service import CanService
from src.services.diagnostic_service import DiagnosticService
from src.services.engine_sound_service import EngineSoundService
from src.services.led_service import BleLedController
from src.services.notification_service import NotificationService
from src.services.orchestrator import SystemOrchestrator
from src.services.trip_stats_service import TripStatsService
from src.vehicle import VehicleAPI
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
    SOUNDS_DIR = os.path.join(BASE_DIR, "assets", "sounds")

    with open(os.path.join(CONFIG_DIR, args.conf), 'r', encoding='utf-8') as f:
        vehicle_config = json.load(f)

    # --- 1. Initialisation du Disque Dur Central ---
    api = VehicleAPI()
    api.run_startup_sequence(duration_sec=1.5)

    # --- 2. Initialisation de l'Orchestrateur ---
    orchestrator = SystemOrchestrator()

    # --- 3. Branchement des Périphériques ---
    if args.mock:
        can_provider = MockProvider(os.path.join(CAN_DIR, "can_moteur_clio3.json"))
    else:
        can_provider = Slcan(channel="/dev/cu.usbmodem207B3949534B1", baudrate=500000)

    # --- 4. Création et Ajout de TOUS les services de base ---
    diag_service = DiagnosticService(api, can_provider)
    led_service = BleLedController()
    stats_service = TripStatsService(api, vehicle_config)
    dynamics_service = DynamicsService(api)
    sound_file_path = os.path.join(SOUNDS_DIR, "gtr.wav")
    engine_sound_service = EngineSoundService(api, audio_path=sound_file_path)
    cabin_sound_service = CabinNoiseService(api)

    can_service = CanService(
        name="CAN_Moteur",
        api=api,
        dbc_path=os.path.join(CAN_DIR, "can_moteur_clio3.json"),
        provider=can_provider,
        obd_callback=diag_service.receive_obd_frame
    )

    orchestrator.add_service(can_service)
    orchestrator.add_service(diag_service)
    orchestrator.add_service(led_service)
    orchestrator.add_service(stats_service)
    orchestrator.add_service(dynamics_service)
    #orchestrator.add_service(engine_sound_service)
    orchestrator.add_service(cabin_sound_service)

    # --- 5. Lancement de l'IHM ---
    try:
        if args.ui == 'cli':
            orchestrator.start_all()
            ui_loop(api, orchestrator.stop_event)

        elif args.ui == 'gui':
            app = QGuiApplication(sys.argv)
            engine = QQmlApplicationEngine()

            bridge = DashboardBridge(
                api,
                os.path.join(CONFIG_DIR, args.conf),
                orchestrator=orchestrator,
                led_service=led_service,
                stats_service=stats_service,
                diag_service=diag_service
            )
            engine.rootContext().setContextProperty("bridge", bridge)

            notif_service = NotificationService(bridge)
            orchestrator.add_service(notif_service)

            orchestrator.start_all()

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