import json
import os
import sys
import argparse

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from src.services.can_service import CanService
from src.services.led_service import BleLedController
from src.services.notification_service import NotificationService
from src.services.orchestrator import SystemOrchestrator
from src.services.trip_stats_service import TripStatsService
from src.vehicle import VehicleAPI
from src.qt_bridge import DashboardBridge

# --- Console de Débogage ---
def ui_loop(api, stop_event):
    """Interface de débogage en ligne de commande (CLI)."""
    while not stop_event.is_set():
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\033[H\033[2J", end="")
        print("=" * 45)
        print("   CONSOLE DE DEBUG TELEMETRIQUE (CLIOS)")
        print("=" * 45)

        # On utilise .copy() pour éviter une erreur si un service modifie la donnée pendant l'affichage
        data_dict = api._data.copy()

        if not data_dict:
            print("\nEn attente du flux de donnees...")
        else:
            for key in sorted(data_dict.keys()):
                val = data_dict[key]
                if isinstance(val, bool):
                    status = "\033[92mON\033[0m" if val else "\033[91mOFF\033[0m"  # Vert pour ON, Rouge pour OFF
                    print(f" {key:<25} : {status}")
                elif isinstance(val, float):
                    print(f" {key:<25} : {val:.1f}")
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
    BASE_DIR =  os.path.dirname(os.path.abspath(__file__))
    CAN_DIR = os.path.join(BASE_DIR, "can")
    CONFIG_DIR = os.path.join(BASE_DIR, "config")

    with open(os.path.join(CONFIG_DIR, args.conf), 'r', encoding='utf-8') as f:
        vehicle_config = json.load(f)

    # --- 1. Initialisation du Disque Dur Central ---
    api = VehicleAPI()
    api.run_startup_sequence(duration_sec=1.5)

    # --- 2. Initialisation de l'Orchestrateur ---
    orchestrator = SystemOrchestrator()

    # --- 3. Branchement des Périphériques ---
    # Service CAN Moteur (Haute Vitesse)
    orchestrator.add_service(CanService(
        name="CAN_Moteur",
        api=api,
        dbc_path=os.path.join(CAN_DIR, "can_moteur_clio3.json"),
        port="/dev/cu.usbmodem207B3949534B1", # Remplacer par le bon port sur le Pi
        baudrate=500000,
        is_mock=args.mock,
        status_key="connexion_obd_moteur"
    ))

    # Service CAN Habitacle (Basse Vitesse)
    #orchestrator.add_service(CanService(
     #   name="CAN_Habitacle",
      #  api=api,
       # dbc_path=os.path.join(CAN_DIR, "can_habitacle_clio3.json"),
        #port="/dev/ttyUSB1", # Remplacer par le deuxième port
        #baudrate=250000,
        #is_mock=args.mock,
        #status_key="connexion_obd_habitacle"
    #))

    led_service = BleLedController()
    stats_service = TripStatsService(api, vehicle_config)

    # --- 5. Lancement de l'IHM ---
    try:
        if args.ui == 'cli':
            ui_loop(api, orchestrator.stop_event)
            pass
        elif args.ui == 'gui':
            app = QGuiApplication(sys.argv)
            engine = QQmlApplicationEngine()

            bridge = DashboardBridge(
                api,
                os.path.join(CONFIG_DIR, args.conf),
                led_service=led_service,
                stats_service=stats_service
            )
            engine.rootContext().setContextProperty("bridge", bridge)

            notif_service = NotificationService(bridge)
            orchestrator.add_service(notif_service)

            orchestrator.add_service(stats_service)
            orchestrator.add_service(led_service)

            # ---Démarrage de tous les threads ---
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