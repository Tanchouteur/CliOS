import time
from driver import Slcan

# --- LE DICTIONNAIRE UNIVERSEL OBD2 (Mode 1) ---
# Il contient tous les PIDs standard les plus courants traduits en français.
OBD2_PIDS_DICT = {
    0x01: "Statut des moniteurs depuis effacement DTC",
    0x03: "Statut du système d'alimentation en carburant",
    0x04: "Charge moteur calculée (%)",
    0x05: "Température du liquide de refroidissement (°C)",
    0x06: "Ajustement carburant à court terme (Bank 1) (%)",
    0x07: "Ajustement carburant à long terme (Bank 1) (%)",
    0x0A: "Pression de carburant (kPa)",
    0x0B: "Pression d'admission / Pression Turbo (MAP) (kPa)",
    0x0C: "Régime Moteur (RPM)",
    0x0D: "Vitesse du véhicule (km/h)",
    0x0E: "Avance à l'allumage (°)",
    0x0F: "Température de l'air d'admission (°C)",
    0x10: "Débit d'air au débitmètre (MAF) (g/s)",
    0x11: "Position de la pédale/papillon des gaz (%)",
    0x13: "Présence des capteurs d'oxygène (O2)",
    0x14: "Tension Sonde Lambda 1 (V)",
    0x15: "Tension Sonde Lambda 2 (V)",
    0x1C: "Norme OBD supportée",
    0x1F: "Temps depuis le démarrage du moteur (sec)",
    0x21: "Distance parcourue avec voyant moteur allumé (km)",
    0x22: "Pression de la rampe d'injection (kPa)",
    0x23: "Pression de la rampe d'injection / Diesel (kPa)",
    0x2C: "Commande de la vanne EGR (%)",
    0x2D: "Erreur de la vanne EGR (%)",
    0x2F: "Niveau de carburant (%)",
    0x31: "Distance parcourue depuis effacement des défauts (km)",
    0x33: "Pression barométrique atmosphérique (kPa)",
    0x34: "Sonde Lambda O2 (Ratio Air/Carburant)",
    0x3C: "Température du Catalyseur (Bank 1, Capteur 1) (°C)",
    0x42: "Tension du calculateur / Batterie (V)",
    0x43: "Charge absolue du moteur (%)",
    0x44: "Ratio d'équivalence commandé (Lambda)",
    0x45: "Position relative du papillon des gaz (%)",
    0x46: "Température de l'air ambiant extérieur (°C)",
    0x4A: "Position de la pédale d'accélérateur B (%)",
    0x4C: "Commande de l'actuateur du papillon (%)",
    0x51: "Type de carburant utilisé par le véhicule",
    0x52: "Pourcentage d'éthanol dans le carburant (%)",
    0x5C: "Température de l'huile moteur (°C)",
    0x5D: "Calage de l'injection de carburant (°)",
    0x5E: "Consommation de carburant moteur (L/h)",
    0x61: "Pourcentage de couple demandé par le conducteur (%)",
    0x62: "Pourcentage de couple réel du moteur (%)",
    0x63: "Couple de référence du moteur (Nm)"
}


def discover_car_capabilities(port="/dev/cu.usbmodem207B3949534B1", baudrate=500000):
    driver = Slcan(channel=port, baudrate=baudrate)

    print(f"Connexion à l'adaptateur sur {port}...")
    if not driver.connect():
        print("❌Échec de la connexion matérielle.")
        return

    current_menu_pid = 0x00
    supported_pids = []

    print("\n==================================================")
    print(" DÉBUT DE L'EXPLORATION DU CALCULATEUR (OBD2) 🚀")
    print("==================================================")

    # Boucle de pagination (Tant que l'ECU dit qu'il y a une page suivante)
    while current_menu_pid is not None:
        print(f"\n📂 Envoi de la requête pour la page [0x{current_menu_pid:02X}]...")

        # On demande la liste des capteurs de cette page
        req_data = [0x01, current_menu_pid, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        driver.send_frame(0x7DF, req_data)

        timeout = time.time() + 2.0
        page_found = False

        while time.time() < timeout:
            frame = driver.read_frame(timeout=0.2)

            # On écoute la réponse de l'ECU Moteur
            if frame and 0x7E8 <= frame.arbitration_id <= 0x7EF:
                # On vérifie que c'est la réponse à notre requête (0x41 = 0x01 + 0x40)
                if frame.data[1] == 0x41 and frame.data[2] == current_menu_pid:
                    page_found = True

                    # Extraction des 4 octets de données utiles (32 bits)
                    binary_bits = "".join([format(b, '08b') for b in frame.data[3:7]])

                    has_next_page = False

                    # Analyse des 32 bits un par un
                    for index, bit in enumerate(binary_bits):
                        if bit == '1':
                            # Calcul de l'adresse du PID trouvé
                            actual_pid = current_menu_pid + index + 1

                            # Si c'est un PID de pagination (0x20, 0x40, 0x60...)
                            if actual_pid % 0x20 == 0:
                                has_next_page = True
                            else:
                                supported_pids.append(actual_pid)
                                # On cherche le nom dans notre dictionnaire géant
                                pid_name = OBD2_PIDS_DICT.get(actual_pid, "Capteur Inconnu ou Spécifique Constructeur")
                                print(f"  ✅ [0x{actual_pid:02X}] -> {pid_name}")

                    # On passe à la page suivante si le dernier bit disait '1', sinon on s'arrête (None)
                    if has_next_page:
                        current_menu_pid += 0x20
                        print(f"  ➡️ L'ECU annonce qu'une suite existe (Page 0x{current_menu_pid:02X}).")
                    else:
                        current_menu_pid = None
                        print("  🏁 Fin de la pagination atteinte.")

                    break  # On sort de la boucle d'écoute puisqu'on a eu notre réponse

        if not page_found:
            print(f"⚠️ Aucune réponse pour la page 0x{current_menu_pid:02X}. L'ECU ne va pas plus loin.")
            break

    print("\n==================================================")
    print(f"BILAN : Ton véhicule supporte {len(supported_pids)} capteurs OBD2 standard en direct.")
    print("==================================================")

    driver.close()


if __name__ == "__main__":
    # N'oublie pas de vérifier le nom de ton port !
    discover_car_capabilities()