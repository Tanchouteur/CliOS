#!/usr/bin/env python3
"""Outil interactif de scan et de test des bandeaux LED Bluetooth (BLE).

Permet de scanner les appareils environnants, de détecter les contrôleurs
Lotus Lantern et LED Lamp, et d'envoyer des séquences de test de couleurs
pour identifier la bonne adresse MAC et le bon protocole.

Usage sur Raspberry Pi:
    python3 tools/scan_ble_leds.py
"""

import asyncio
import sys

try:
    from bleak import BleakScanner, BleakClient
    from bleak.exc import BleakError
except ImportError:
    print("\n[ERREUR] La bibliothèque 'bleak' n'est pas installée.")
    print("Installez-la avec : pip install bleak\n")
    sys.exit(1)


KNOWN_LED_NAMES = [
    "elk", "lotus", "led", "qhm", "melk", "sp110", "sp107", "banlan",
    "triones", "ble", "lamp", "dream", "slg", "hj", "zengge"
]

PROTOCOLS = {
    "1": ("LOTUS_9B (Lotus Lantern / ELK-BLEDOM 9-octets)", [
        bytearray([0x7E, 0x00, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]), # ON
        bytearray([0x7E, 0x00, 0x05, 0x03, 255, 0, 0, 0x00, 0xEF]),       # Rouge
    ]),
    "2": ("TRIONES_7B (LED BLE / Triones / Magic 7-octets)", [
        bytearray([0xCC, 0x23, 0x33]),                                      # ON
        bytearray([0x56, 255, 0, 0, 0x00, 0xF0, 0xAA]),                     # Rouge
    ]),
    "3": ("SP110E_4B (BanlanX / SP110E DreamColor 4-octets)", [
        bytearray([0xAA, 0x02, 0x01, 0xAD]),                               # ON
        bytearray([0x38, 255, 0, 0]),                                       # Rouge
    ]),
    "4": ("LED_LAMP_9B (HiLighting / LED Lamp 9-octets variant)", [
        bytearray([0x7E, 0x04, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]), # ON
        bytearray([0x7E, 0x04, 0x05, 0x03, 255, 0, 0, 0xFF, 0xEF]),       # Rouge
    ]),
}


async def scan_devices():
    print("\n🔍 Recherche des appareils Bluetooth BLE à proximité (5 secondes)...")
    discovered = await BleakScanner.discover(timeout=5.0, return_adv=True)
    entries = list(discovered.values())

    if not entries:
        print("❌ Aucun appareil Bluetooth détecté. Vérifiez que le Bluetooth est activé.")
        return []

    print(f"\n📡 {len(entries)} appareils détectés :\n")
    candidates = []

    for idx, (d, advertisement) in enumerate(entries, 1):
        name = d.name or "Inconnu"
        is_candidate = any(k in name.lower() for k in KNOWN_LED_NAMES)
        marker = "💡 [POTENTIEL CONTRÔLEUR LED]" if is_candidate else ""
        rssi = getattr(advertisement, "rssi", "?")
        print(f"  [{idx:02d}] {d.address} | Nom: {name:<24} | RSSI: {rssi} dBm {marker}")
        if is_candidate or name != "Inconnu":
            candidates.append(d)

    return [device for device, _advertisement in entries]


async def test_device(address: str, name: str):
    print(f"\n🔌 Connexion à {name} ({address})...")
    try:
        async with BleakClient(address, timeout=6.0) as client:
            print("✅ Connecté avec succès !")

            # Recherche des caractéristiques d'écriture
            write_chars = []
            print("\n📋 Caractéristiques GATT disponibles :")
            for service in client.services:
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    is_writable = "write" in char.properties or "write-without-response" in char.properties
                    marker = "✏️ [ÉCRITURE POSSIBLE]" if is_writable else ""
                    print(f"   Service: {service.uuid[:8]}... | Char: {char.uuid} ({props}) {marker}")
                    if is_writable:
                        write_chars.append(char.uuid)

            if not write_chars:
                print("❌ Aucune caractéristique d'écriture trouvée sur ce périphérique.")
                return

            target_char = write_chars[0]
            print(f"\n🎯 Caractéristique sélectionnée pour l'envoi : {target_char}")

            # Test de chaque protocole
            print("\n🧪 Test d'envoi de séquences de couleurs (ROUGE -> VERT -> BLEU)...")
            colors = [
                ("ROUGE", 255, 0, 0),
                ("VERT", 0, 255, 0),
                ("BLEU", 0, 0, 255),
            ]

            for proto_key, (proto_name, _) in PROTOCOLS.items():
                print(f"\n--- Test Protocole {proto_key} : {proto_name} ---")
                for cname, r, g, b in colors:
                    payloads = []
                    if proto_key == "1":
                        payloads = [
                            bytearray([0x7E, 0x00, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]),
                            bytearray([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF]),
                            bytearray([0x7E, 0x00, 0x01, 100, 0x00, 0x00, 0x00, 0x00, 0xEF]),
                        ]
                    elif proto_key == "2":
                        payloads = [
                            bytearray([0xCC, 0x23, 0x33]),
                            bytearray([0x56, r, g, b, 0x00, 0xF0, 0xAA]),
                        ]
                    elif proto_key == "3":
                        payloads = [
                            bytearray([0xAA, 0x02, 0x01, 0xAD]),
                            bytearray([0x38, r, g, b]),
                        ]
                    elif proto_key == "4":
                        payloads = [
                            bytearray([0x7E, 0x04, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]),
                            bytearray([0x7E, 0x04, 0x05, 0x03, r, g, b, 0xFF, 0xEF]),
                        ]

                    for p in payloads:
                        try:
                            await client.write_gatt_char(target_char, p, response=False)
                            await asyncio.sleep(0.05)
                        except Exception as e:
                            print(f"   ⚠️ Erreur envoi: {e}")

                    print(f"   -> Couleur envoyée : {cname} ({r},{g},{b})")
                    await asyncio.sleep(1.2)

            print("\n🏁 Test terminé ! Avez-vous vu le bandeau changer de couleur ?")

    except BleakError as e:
        print(f"❌ Échec de connexion : {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")


async def main():
    print("=" * 65)
    print("   🚗 CliOS - Diagnostic & Scanner Bandeaux LED Bluetooth")
    print("=" * 65)

    devices = await scan_devices()
    if not devices:
        return

    print("\nEntrez le numéro ou l'adresse MAC de l'appareil à tester (ou 'q' pour quitter) :")
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.lower() == 'q' or not choice:
        return

    target = None
    if choice.isdigit() and 1 <= int(choice) <= len(devices):
        target = devices[int(choice) - 1]
    else:
        for d in devices:
            if d.address.lower() == choice.lower():
                target = d
                break

    if target:
        await test_device(target.address, target.name or "Inconnu")
    else:
        print(f"❌ Appareil '{choice}' non trouvé dans la liste.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nArrêt.")
