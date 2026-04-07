import time
import os
from driver import Slcan


def chasse_au_tresor(port="/dev/cu.usbmodem207B3949534B1", baudrate=500000):
    driver = Slcan(channel=port, baudrate=baudrate)

    if not driver.connect():
        print("❌ Port fermé.")
        return

    print("✅ En écoute... Appuie doucement sur l'accélérateur pour faire varier le Turbo/Régime.")

    # On va mémoriser l'état précédent de chaque trame
    memoire_trames = {}

    try:
        while True:
            frame = driver.read_frame(timeout=0.1)
            if frame:
                id_trame = frame.arbitration_id
                # On convertit les octets en tableau pour comparer facilement
                data_actuelle = list(frame.data)

                # Si on a déjà vu cette trame
                if id_trame in memoire_trames:
                    data_precedente = memoire_trames[id_trame]

                    # On compare octet par octet
                    changements = []
                    for i in range(len(data_actuelle)):
                        if data_actuelle[i] != data_precedente[i]:
                            changements.append(i)

                    # S'il y a un changement, on l'affiche avec des couleurs (si ton terminal le supporte)
                    if changements:
                        hex_data = " ".join([f"{b:02X}" for b in data_actuelle])
                        print(f"Trame [0x{id_trame:03X}] a changé ! -> {hex_data} (Octets modifiés : {changements})")

                # On met à jour la mémoire
                memoire_trames[id_trame] = data_actuelle

    except KeyboardInterrupt:
        print("\n🏁 Arrêt du chasseur.")
        driver.close()


if __name__ == "__main__":
    chasse_au_tresor()