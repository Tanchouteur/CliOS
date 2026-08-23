"""Registre central des protocoles BLE LED.

Source unique de verite pour les protocoles BLE, partagee entre le service
LED runtime et l'outil de scan CLI.
"""

from dataclasses import dataclass


PREFERRED_CHAR_UUIDS: list[str] = [
    "0000fff3-0000-1000-8000-00805f9b34fb",
    "0000ffe1-0000-1000-8000-00805f9b34fb",
    "0000ffd9-0000-1000-8000-00805f9b34fb",
    "0000ae01-0000-1000-8000-00805f9b34fb",
    "0000fa02-0000-1000-8000-00805f9b34fb",
]

KNOWN_LED_NAMES: list[str] = [
    "elk", "lotus", "led", "qhm", "melk", "sp110", "sp107", "banlan",
    "triones", "ble", "lamp", "dream", "slg", "hj", "zengge", "ledcar",
]


@dataclass(frozen=True)
class BleProtocol:
    """Definit un protocole de communication BLE pour un controleur LED."""

    identifier: str
    label: str
    witness_color: tuple[int, int, int]
    witness_name: str
    runtime_capable: bool = True


_PROTOCOLS: dict[str, BleProtocol] = {
    "LOTUS_9B": BleProtocol(
        identifier="LOTUS_9B",
        label="Lotus Lantern / ELK-BLEDOM 9 octets",
        witness_color=(255, 0, 0),
        witness_name="ROUGE",
    ),
    "LEDCAR_DMX_9B": BleProtocol(
        identifier="LEDCAR_DMX_9B",
        label="LEDCAR-01 barres RGBIC / LED DMX 9 octets",
        witness_color=(0, 255, 255),
        witness_name="CYAN",
    ),
    "LED_LAMP_9B": BleProtocol(
        identifier="LED_LAMP_9B",
        label="HiLighting / LED Lamp 9 octets",
        witness_color=(255, 0, 255),
        witness_name="MAGENTA",
    ),
    "TRIONES_7B": BleProtocol(
        identifier="TRIONES_7B",
        label="LED BLE / Triones / Magic Home 7 octets",
        witness_color=(0, 255, 0),
        witness_name="VERT",
    ),
    "SP110E_4B": BleProtocol(
        identifier="SP110E_4B",
        label="BanlanX / SP110E DreamColor 4 octets",
        witness_color=(0, 0, 255),
        witness_name="BLEU",
    ),
    # Protocoles de test scan uniquement (non utilises en runtime)
    "LEDCAR_A_9B": BleProtocol(
        identifier="LEDCAR_A_9B",
        label="LEDCAR-01 sortie analogique / LED BLE",
        witness_color=(255, 255, 0),
        witness_name="JAUNE",
        runtime_capable=False,
    ),
    "LEDCAR_ALL_9B": BleProtocol(
        identifier="LEDCAR_ALL_9B",
        label="LEDCAR-01 canal combine",
        witness_color=(255, 96, 0),
        witness_name="ORANGE",
        runtime_capable=False,
    ),
    "LEDCAR_B_CLASSIC_9B": BleProtocol(
        identifier="LEDCAR_B_CLASSIC_9B",
        label="LEDCAR / LEDDMX dialecte B classique",
        witness_color=(255, 255, 255),
        witness_name="BLANC",
        runtime_capable=False,
    ),
}

_SCAN_PROTOCOL_ORDER: list[str] = [
    "LOTUS_9B", "TRIONES_7B", "SP110E_4B", "LED_LAMP_9B",
    "LEDCAR_A_9B", "LEDCAR_DMX_9B", "LEDCAR_ALL_9B", "LEDCAR_B_CLASSIC_9B",
]


class ProtocolRegistry:
    """Registre central des protocoles BLE supportes."""

    def get(self, identifier: str) -> BleProtocol:
        """Retourne le protocole identifie, leve KeyError si inconnu."""
        return _PROTOCOLS[identifier]

    def all(self) -> list[BleProtocol]:
        """Retourne tous les protocoles dans l'ordre de scan."""
        return [_PROTOCOLS[k] for k in _SCAN_PROTOCOL_ORDER if k in _PROTOCOLS]

    def runtime_protocols(self) -> list[BleProtocol]:
        """Retourne uniquement les protocoles utilisables en runtime (LED service)."""
        return [p for p in self.all() if p.runtime_capable]

    def runtime_protocol_ids(self) -> list[str]:
        """Retourne les identifiants des protocoles runtime."""
        return [p.identifier for p in self.runtime_protocols()]

    def preferred_char_uuids(self) -> list[str]:
        """Retourne la liste ordonnee des UUIDs de caracteristiques GATT prioritaires."""
        return list(PREFERRED_CHAR_UUIDS)

    def guess_protocol_order(self, device_name: str) -> list[str]:
        """Retourne les identifiants de protocoles ordonnes par probabilite pour le nom d'appareil."""
        keys = list(_SCAN_PROTOCOL_ORDER)
        upper_name = device_name.strip().upper()
        if upper_name.startswith("LEDCAR-01"):
            priorities = ["LEDCAR_DMX_9B", "LEDCAR_ALL_9B", "LEDCAR_B_CLASSIC_9B", "LEDCAR_A_9B"]
            return priorities + [k for k in keys if k not in priorities]
        if upper_name.startswith("ELK-BLEDOM"):
            return ["LOTUS_9B"] + [k for k in keys if k != "LOTUS_9B"]
        return keys

    def build_payloads(
        self,
        identifier: str,
        r: int,
        g: int,
        b: int,
        brightness_pct: float,
        power_on: bool,
    ) -> list[bytearray]:
        """Genere les trames BLE correctes selon le protocole, la couleur et la luminosite."""
        brightness_val = max(0, min(100, int(brightness_pct)))
        r, g, b = (max(0, min(255, int(channel))) for channel in (r, g, b))
        sr, sg, sb = (
            (channel * brightness_val) // 100 for channel in (r, g, b)
        )

        if identifier == "LOTUS_9B":
            if not power_on or brightness_val <= 0:
                return [bytearray([0x7E, 0x00, 0x04, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xEF])]
            return [
                bytearray([0x7E, 0x00, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]),
                bytearray([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF]),
                bytearray([0x7E, 0x00, 0x01, brightness_val, 0x00, 0x00, 0x00, 0x00, 0xEF]),
            ]

        elif identifier == "LED_LAMP_9B":
            if not power_on or brightness_val <= 0:
                return [bytearray([0x7E, 0x04, 0x04, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xEF])]
            return [
                bytearray([0x7E, 0x04, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]),
                bytearray([0x7E, 0x04, 0x05, 0x03, sr, sg, sb, 0xFF, 0xEF]),
            ]

        elif identifier == "LEDCAR_DMX_9B":
            if not power_on or brightness_val <= 0:
                return [bytearray([0x7B, 0xFF, 0x04, 0x02, 0xFF, 0xFF, 0xFF, 0xFF, 0xBF])]
            adjusted_brightness = (brightness_val * 32) // 100
            return [
                bytearray([0x7B, 0xFF, 0x04, 0x03, 0xFF, 0xFF, 0xFF, 0xFF, 0xBF]),
                bytearray([
                    0x7B, 0xFF, 0x01, adjusted_brightness, brightness_val,
                    0x00, 0xFF, 0xFF, 0xBF,
                ]),
                bytearray([0x7B, 0x00, 0x07, r, g, b, 0x00, 0xFF, 0xBF]),
            ]

        elif identifier == "TRIONES_7B":
            if not power_on or brightness_val <= 0:
                return [bytearray([0xCC, 0x24, 0x33])]
            return [
                bytearray([0xCC, 0x23, 0x33]),
                bytearray([0x56, sr, sg, sb, 0x00, 0xF0, 0xAA]),
            ]

        elif identifier == "SP110E_4B":
            if not power_on or brightness_val <= 0:
                return [bytearray([0xAA, 0x02, 0x00, 0xAC])]
            return [
                bytearray([0xAA, 0x02, 0x01, 0xAD]),
                bytearray([0x38, sr, sg, sb]),
            ]

        # Protocoles scan-only (pas de brightness dans les trames de test)
        elif identifier == "LEDCAR_A_9B":
            return [
                bytearray([0x7E, 0xFF, 0x04, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xEF]),
                bytearray([0x7E, 0xFF, 0x01, 32, 100, 0xFF, 0xFF, 0xFF, 0xEF]),
                bytearray([0x7E, 0xFF, 0x05, 0x03, r, g, b, 0xFF, 0xEF]),
            ]

        elif identifier == "LEDCAR_ALL_9B":
            return [
                bytearray([0x7B, 0x01, 0x04, 0x03, 0xFF, 0xFF, 0xFF, 0xFF, 0xBF]),
                bytearray([0x7B, 0xFF, 0x01, 32, 100, 0x02, 0xFF, 0xFF, 0xBF]),
                bytearray([0x7B, 0x01, 0x07, r, g, b, 0x00, 0xFF, 0xBF]),
            ]

        elif identifier == "LEDCAR_B_CLASSIC_9B":
            return [
                bytearray([0x7B, 0xFF, 0x04, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xBF]),
                bytearray([0x7B, 0xFF, 0x01, 32, 100, 0x01, 0xFF, 0xFF, 0xBF]),
                bytearray([0x7B, 0xFF, 0x07, r, g, b, 0x00, 0xFF, 0xBF]),
            ]

        # Fallback Lotus 9B
        return [bytearray([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF])]

    def build_power_off(self, identifier: str) -> list[bytearray]:
        """Genere uniquement la trame d'extinction pour le protocole."""
        return self.build_payloads(identifier, 0, 0, 0, 0.0, power_on=False)


registry = ProtocolRegistry()
