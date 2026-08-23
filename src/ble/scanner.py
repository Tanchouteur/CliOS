"""Moteur de scan BLE asynchrone et testeur de protocoles.

Fournit les primitives de decouverte d'appareils, d'inspection GATT
et de test de protocoles utilisees par le LED service et la page QML.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

try:
    from bleak import BleakScanner, BleakClient
    from bleak.exc import BleakError
    BLEAK_AVAILABLE = True
except ImportError:
    BleakScanner = None  # type: ignore
    BleakClient = None   # type: ignore
    BleakError = Exception
    BLEAK_AVAILABLE = False

from src.ble.protocol_registry import registry, PREFERRED_CHAR_UUIDS, KNOWN_LED_NAMES
from src.logging_runtime import get_logger

logger = get_logger("BLE.Scanner")

SCAN_TIMEOUT: float = 5.0
CONNECT_TIMEOUT: float = 6.0


@dataclass
class ScanResult:
    """Resultat de la decouverte d'un appareil BLE."""

    address: str
    name: str
    rssi: int
    is_candidate: bool

    def short_address(self) -> str:
        """Retourne les 11 derniers caracteres de l'adresse pour l'affichage."""
        return self.address[-11:] if len(self.address) > 11 else self.address

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "name": self.name,
            "rssi": self.rssi,
            "is_candidate": self.is_candidate,
            "short_address": self.short_address(),
        }


@dataclass
class GattCharInfo:
    """Caracteristique GATT writable d'un peripherique BLE."""

    uuid: str
    properties: list[str] = field(default_factory=list)
    write_with_response: bool = False
    is_preferred: bool = False

    def to_dict(self) -> dict:
        return {
            "uuid": self.uuid,
            "properties": self.properties,
            "write_with_response": self.write_with_response,
            "is_preferred": self.is_preferred,
        }


class BleScanner:
    """Moteur de scan BLE et testeur de protocoles (sans etat, thread-safe).

    Toutes les methodes sont async et doivent etre appelees depuis une
    boucle asyncio.
    """

    async def scan(self, timeout: float = SCAN_TIMEOUT) -> list[ScanResult]:
        """Scanne les appareils BLE environnants et retourne les resultats.

        Filtre les candidats LED selon KNOWN_LED_NAMES.
        Leve RuntimeError si bleak n'est pas installe.
        """
        if not BLEAK_AVAILABLE or BleakScanner is None:
            raise RuntimeError(
                "La bibliotheque 'bleak' n'est pas installee. "
                "Installez-la avec : pip install bleak"
            )

        results: list[ScanResult] = []
        try:
            discovered = await BleakScanner.discover(timeout=timeout, return_adv=True)
        except Exception as exc:
            logger.warning("Erreur de scan BLE: %s", exc,
                           extra={"error_code": "BLE_SCAN_ERROR"})
            return results

        for address, (device, adv_data) in discovered.items():
            name = device.name or ""
            rssi = getattr(adv_data, "rssi", -99)
            lower_name = name.lower()
            is_candidate = any(kw in lower_name for kw in KNOWN_LED_NAMES)
            results.append(ScanResult(
                address=str(address),
                name=name,
                rssi=int(rssi),
                is_candidate=is_candidate,
            ))

        # Trie: candidats en premier, puis par force du signal
        results.sort(key=lambda r: (not r.is_candidate, -r.rssi))
        return results

    async def discover_characteristics(self, address: str) -> list[GattCharInfo]:
        """Se connecte a un peripherique et retourne ses caracteristiques GATT writables.

        Leve RuntimeError si bleak n'est pas installe.
        Retourne une liste vide si la connexion echoue.
        """
        if not BLEAK_AVAILABLE or BleakClient is None:
            raise RuntimeError("La bibliotheque 'bleak' n'est pas installee.")

        chars: list[GattCharInfo] = []
        try:
            async with BleakClient(address, timeout=CONNECT_TIMEOUT) as client:
                preferred_uuids = set(PREFERRED_CHAR_UUIDS)
                seen_uuids: set[str] = set()
                for service in client.services:
                    for char in service.characteristics:
                        props = list(char.properties)
                        is_writable = (
                            "write-without-response" in props or "write" in props
                        )
                        if not is_writable:
                            continue
                        lower_uuid = char.uuid.lower()
                        if lower_uuid in seen_uuids:
                            continue
                        seen_uuids.add(lower_uuid)
                        write_with_response = "write" in props and "write-without-response" not in props
                        is_preferred = lower_uuid in preferred_uuids
                        chars.append(GattCharInfo(
                            uuid=char.uuid,
                            properties=props,
                            write_with_response=write_with_response,
                            is_preferred=is_preferred,
                        ))
                # Trie: preferees en premier
                chars.sort(key=lambda c: not c.is_preferred)
        except Exception as exc:
            logger.warning("Echec connexion GATT sur %s: %s", address, exc,
                           extra={"error_code": "BLE_GATT_ERROR"})

        return chars

    async def select_best_characteristic(
        self, chars: list[GattCharInfo]
    ) -> Optional[GattCharInfo]:
        """Retourne la meilleure caracteristique writable.

        Priorite: premiere UUID preferee, sinon premiere writable.
        """
        for char in chars:
            if char.is_preferred:
                return char
        return chars[0] if chars else None

    async def test_protocol(
        self,
        address: str,
        char_uuid: str,
        write_with_response: bool,
        protocol_id: str,
    ) -> bool:
        """Envoie la couleur temoin d'un protocole sur un appareil.

        Connexion + envoi + deconnexion. Retourne True si l'envoi n'a pas produit d'erreur.
        """
        if not BLEAK_AVAILABLE or BleakClient is None:
            return False

        proto = registry.get(protocol_id)
        r, g, b = proto.witness_color

        try:
            async with BleakClient(address, timeout=CONNECT_TIMEOUT) as client:
                payloads = registry.build_payloads(protocol_id, r, g, b, 100.0, power_on=True)
                for payload in payloads:
                    await client.write_gatt_char(
                        char_uuid, payload, response=write_with_response
                    )
                    await asyncio.sleep(0.04)
            return True
        except Exception as exc:
            logger.debug("Test protocole %s echec sur %s: %s", protocol_id, address, exc,
                         extra={"error_code": "BLE_PROTO_TEST_FAIL"})
            return False

    async def send_color(
        self,
        client: "BleakClient",
        char_uuid: str,
        protocol_id: str,
        r: int,
        g: int,
        b: int,
        brightness_pct: float,
        write_with_response: bool,
    ) -> bool:
        """Envoie des trames de couleur sur un client BLE deja connecte.

        Retourne True si tous les envois ont reussi.
        """
        if not BLEAK_AVAILABLE:
            return False

        try:
            payloads = registry.build_payloads(protocol_id, r, g, b, brightness_pct, power_on=True)
            for payload in payloads:
                await client.write_gatt_char(char_uuid, payload, response=write_with_response)
                await asyncio.sleep(0.04)
            return True
        except Exception as exc:
            logger.debug("Erreur envoi couleur %s: %s", protocol_id, exc,
                         extra={"error_code": "BLE_SEND_ERROR"})
            return False


scanner = BleScanner()
