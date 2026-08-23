#!/usr/bin/env python3
"""Outil interactif de scan et de test des bandeaux LED Bluetooth (BLE).

Permet de scanner les appareils environnants, de détecter les contrôleurs
Lotus Lantern et LED Lamp, et d'envoyer des séquences de test de couleurs
pour identifier le bon appareil BLE et le bon protocole.

Usage sur Raspberry Pi:
    python3 tools/scan_ble_leds.py
"""

import asyncio
import pathlib
import sys
from typing import NamedTuple

# Permet de conserver l'usage documente `python3 tools/scan_ble_leds.py`.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ble.protocol_registry import (  # noqa: E402
    KNOWN_LED_NAMES,
    PREFERRED_CHAR_UUIDS,
    registry,
)

try:
    from bleak import BleakScanner, BleakClient
    from bleak.exc import BleakError
    BLEAK_IMPORT_ERROR = None
except ImportError as exc:
    BleakScanner = None
    BleakClient = None
    BLEAK_IMPORT_ERROR = exc

    class BleakError(Exception):
        """Type de repli utilisé uniquement lorsque Bleak est absent."""


def require_bleak():
    if BLEAK_IMPORT_ERROR is not None or BleakScanner is None or BleakClient is None:
        raise RuntimeError(
            "La bibliothèque 'bleak' n'est pas installée. "
            "Installez-la avec : pip install bleak"
        ) from BLEAK_IMPORT_ERROR


class ProtocolTest(NamedTuple):
    identifier: str
    label: str
    color_name: str
    color: tuple[int, int, int]


_PROTOCOL_KEYS = {
    "1": "LOTUS_9B", "2": "TRIONES_7B", "3": "SP110E_4B",
    "4": "LED_LAMP_9B", "5": "LEDCAR_A_9B", "6": "LEDCAR_DMX_9B",
    "7": "LEDCAR_ALL_9B", "8": "LEDCAR_B_CLASSIC_9B",
}
PROTOCOLS = {
    key: ProtocolTest(proto.identifier, proto.label, proto.witness_name, proto.witness_color)
    for key, identifier in _PROTOCOL_KEYS.items()
    for proto in [registry.get(identifier)]
}


def build_protocol_payloads(protocol_key: str, r: int, g: int, b: int) -> list[bytearray]:
    """Construit la commande d'allumage et la couleur d'un protocole de test."""
    try:
        identifier = _PROTOCOL_KEYS[protocol_key]
    except KeyError as exc:
        raise ValueError(f"Protocole de test inconnu: {protocol_key}") from exc
    return registry.build_payloads(identifier, r, g, b, 100.0, power_on=True)


def protocol_order(device_name: str) -> list[str]:
    """Teste d'abord les dialectes correspondant au nom annoncé."""
    by_identifier = {identifier: key for key, identifier in _PROTOCOL_KEYS.items()}
    return [by_identifier[identifier] for identifier in registry.guess_protocol_order(device_name)]


def preferred_characteristic_index(characteristics) -> int:
    for preferred_uuid in PREFERRED_CHAR_UUIDS:
        for index, characteristic in enumerate(characteristics):
            if characteristic.uuid.lower() == preferred_uuid:
                return index
    return 0


def select_write_characteristic(characteristics):
    """Laisse choisir la cible GATT au lieu d'utiliser arbitrairement la première."""
    default_index = preferred_characteristic_index(characteristics)
    if len(characteristics) == 1:
        return characteristics[0]

    print("\nPlusieurs caractéristiques acceptent une écriture.")
    print("Choisissez celle à tester ; Entrée conserve la cible recommandée.")
    try:
        choice = input(f"> [défaut {default_index + 1}] ").strip()
    except (EOFError, KeyboardInterrupt):
        return characteristics[default_index]
    if choice.isdigit() and 1 <= int(choice) <= len(characteristics):
        return characteristics[int(choice) - 1]
    return characteristics[default_index]


def write_requires_response(characteristic) -> bool:
    properties = set(characteristic.properties)
    return "write-without-response" not in properties and "write" in properties


def ask_protocol_result(color_name: str) -> str:
    """Attend explicitement l'observation humaine avant le protocole suivant."""
    prompt = (
        f"La couleur {color_name} est-elle apparue ? "
        "[o] oui  [r] réessayer  [Entrée] protocole suivant  [q] arrêter\n> "
    )
    while True:
        try:
            answer = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit"
        if answer in {"", "n", "non"}:
            return "next"
        if answer in {"o", "oui", "y", "yes"}:
            return "success"
        if answer in {"r", "retry", "réessayer"}:
            return "retry"
        if answer in {"q", "quit", "quitter"}:
            return "quit"
        print("Réponse inconnue.")


async def scan_devices():
    require_bleak()
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
    require_bleak()
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
                    if is_writable:
                        write_chars.append(char)
                        marker = f"✏️ [ÉCRITURE {len(write_chars)}]"
                    print(f"   Service: {service.uuid[:8]}... | Char: {char.uuid} ({props}) {marker}")

            if not write_chars:
                print("❌ Aucune caractéristique d'écriture trouvée sur ce périphérique.")
                return

            target_char = select_write_characteristic(write_chars)
            response = write_requires_response(target_char)
            write_mode = "avec réponse" if response else "sans réponse"
            print(f"\n🎯 Caractéristique sélectionnée : {target_char.uuid}")
            print(f"   Mode d'écriture : {write_mode}")

            print("\n🧪 Chaque protocole utilise une couleur distincte.")
            print("Le script attend votre validation avant de poursuivre.")

            for proto_key in protocol_order(name):
                protocol = PROTOCOLS[proto_key]
                print(f"\n--- Protocole {proto_key}: {protocol.identifier} ---")
                print(f"    Famille : {protocol.label}")
                print(f"    Couleur témoin : {protocol.color_name} {protocol.color}")
                while True:
                    payloads = build_protocol_payloads(proto_key, *protocol.color)
                    sent = True
                    for payload in payloads:
                        try:
                            print(f"    TX {payload.hex(' ')}")
                            await client.write_gatt_char(target_char.uuid, payload, response=response)
                            await asyncio.sleep(0.05)
                        except Exception as exc:
                            sent = False
                            print(f"    ⚠️ Erreur d'envoi : {exc}")
                            break

                    if sent:
                        print(f"    Couleur {protocol.color_name} envoyée. Observez le bandeau.")
                    action = ask_protocol_result(protocol.color_name)
                    if action == "retry":
                        continue
                    if action == "success":
                        print("\n✅ Protocole confirmé :")
                        print(f"   Appareil : {name} ({address})")
                        print(f"   Protocole : {protocol.identifier}")
                        print(f"   Caractéristique : {target_char.uuid}")
                        print(f"   Écriture : {write_mode}")
                        return
                    if action == "quit":
                        print("\nTest interrompu par l'utilisateur.")
                        return
                    break

            print("\n❌ Aucun protocole n'a été confirmé sur cette caractéristique.")
            if len(write_chars) > 1:
                print("Relancez le test et sélectionnez une autre caractéristique d'écriture.")
            print("Conservez la liste GATT et les lignes TX pour identifier un protocole supplémentaire.")

    except BleakError as e:
        print(f"❌ Échec de connexion : {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")


async def main():
    print("=" * 65)
    print("   🚗 CliOS - Diagnostic & Scanner Bandeaux LED Bluetooth")
    print("=" * 65)

    try:
        devices = await scan_devices()
    except RuntimeError as exc:
        print(f"\n[ERREUR] {exc}\n")
        return 1
    if not devices:
        return 0

    print("\nEntrez le numéro, l'identifiant BLE ou l'adresse MAC de l'appareil à tester")
    print("(ou 'q' pour quitter) :")
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return 0

    if choice.lower() == 'q' or not choice:
        return 0

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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\nArrêt.")
