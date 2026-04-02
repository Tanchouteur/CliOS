import json
import os
import time
import threading
import sys
import argparse

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from src.dispatcher import CanDispatcher
from src.parser import DbcParser
from src.signal_processor import SignalProcessor
from src.vehicle import VehicleAPI
from src.driver import Slcan
from src.qt_bridge import DashboardBridge
from src.mock_driver import MockProvider


# --- Routines d'Exécution Asynchrones ---

def can_listener_loop(provider, dispatcher, api, stop_event):
    """Machine à états gérant l'acquisition, la reconnexion automatique et l'arrêt propre."""

    while not stop_event.is_set():
        # Etat 1 : Tentative de connexion matérielle
        if not provider.is_connected:
            api.set_connection_status(False)
            success = provider.connect()

            if not success:
                # Temporisation non-bloquante avant la prochaine tentative (2 secondes)
                stop_event.wait(2.0)
                continue
            else:
                api.set_connection_status(True)

        # Etat 2 : Acquisition des trames télémétriques
        try:
            frame = provider.read_frame(timeout=0.2)
            if frame:
                if getattr(api, 'is_starting_up', False):
                    continue
                dispatcher.dispatch(frame)
        except Exception:
            # Etat 3 : Rupture de la liaison détectée
            print("[ATTENTION] Rupture de la liaison serie. Reconnexion planifiee.")
            api.set_connection_status(False)
            provider.close()
            stop_event.wait(1.0)


def ui_loop(api, stop_event):
    """Interface de débogage en ligne de commande (CLI)."""
    while not stop_event.is_set():
        os.system('cls' if os.name == 'nt' else 'clear')

        print("\033[H\033[2J", end="")
        print("=" * 40)
        print("   CONSOLE DE DEBUG TELEMETRIQUE")
        print("=" * 40)

        data_dict = api._data
        if not data_dict:
            print("\nEn attente du flux de donnees CAN...")
        else:
            for key in sorted(data_dict.keys()):
                val = data_dict[key]
                if isinstance(val, bool):
                    status = "ON" if val else "OFF"
                    print(f" {key:<20} : {status}")
                elif isinstance(val, float):
                    print(f" {key:<20} : {val:.1f}")
                else:
                    print(f" {key:<20} : {val}")
        print("\n[Ctrl+C pour interrompre le processus]")
        stop_event.wait(0.1)


def main():
    # Déclaration de l'événement de signalisation inter-threads
    stop_event = threading.Event()

    # --- Traitement des Arguments d'Exécution ---
    cmd_parser = argparse.ArgumentParser(description="Serveur de Telemetrie et Tableau de Bord OBD")
    cmd_parser.add_argument('--ui', choices=['cli', 'gui'], default='gui')
    cmd_parser.add_argument('--mock', action='store_true')
    cmd_parser.add_argument('--conf', type=str, default='clio3diesel_config.json')

    args = cmd_parser.parse_args()

    # --- Configuration de l'Environnement ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CAN_DIR = os.path.join(BASE_DIR, "can")
    CONFIG_DIR = os.path.join(BASE_DIR, "config")

    config_path = os.path.join(CONFIG_DIR, args.conf)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            vehicle_config = json.load(f)
    except Exception as e:
        print(f"[ERREUR] Impossible de charger la configuration : {e}")
        return

    # --- Initialisation de l'Architecture Core ---
    dbc_parser = DbcParser(os.path.join(CAN_DIR, "can_clio3.json"))
    processor = SignalProcessor()
    api = VehicleAPI(vehicle_config)
    api.run_startup_sequence(duration_sec=1.5)
    dispatcher = CanDispatcher(dbc_parser, processor, api)

    # --- Configuration du Périphérique d'Acquisition ---
    if args.mock:
        provider = MockProvider(os.path.join(CAN_DIR, "can_clio3.json"))
    else:
        port_mac = "/dev/cu.usbmodem207B3949534B1"
        provider = Slcan(channel=port_mac, baudrate=500000)

    # Note : L'appel initial à connect() est supprimé ici car la machine à états
    # du can_listener_loop va s'en charger automatiquement.

    # --- Déploiement du Thread Télémétrique ---
    can_thread = threading.Thread(target=can_listener_loop, args=(provider, dispatcher, api, stop_event), daemon=True)
    can_thread.start()

    # --- Lancement du Moteur de Rendu (Frontend) ---
    try:
        if args.ui == 'cli':
            ui_loop(api, stop_event)
        elif args.ui == 'gui':
            app = QGuiApplication(sys.argv)
            engine = QQmlApplicationEngine()

            bridge = DashboardBridge(api, os.path.join(CONFIG_DIR, "clio3diesel_config.json"))
            engine.rootContext().setContextProperty("bridge", bridge)

            qml_file = os.path.join(BASE_DIR, "frontend", "main.qml")
            engine.load(qml_file)

            if not engine.rootObjects():
                sys.exit(-1)

            app.exec()
            del engine
            del bridge

    except KeyboardInterrupt:
        print("\n[INFO] Interruption manuelle detectee.")
    finally:
        # Séquence de nettoyage (Clean teardown)
        print("[INFO] Initiation de la sequence d'arret materiel...")
        stop_event.set()  # 1. Signale aux threads de s'arrêter
        provider.close()  # 2. Ferme le port série pour débloquer les lectures en attente
        can_thread.join(timeout=2)  # 3. Attend la fin confirmée du thread
        print("[INFO] Arret termine avec succes.")


if __name__ == "__main__":
    main()