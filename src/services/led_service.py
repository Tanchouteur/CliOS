import asyncio
import threading
from typing import Dict, List, Optional, Tuple

try:
    from bleak import BleakClient
    from bleak.exc import BleakError
except ImportError:
    BleakClient = None
    BleakError = Exception

from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType

DEFAULT_MAC_DASHBOARD = "A060C742-6A5E-53EB-4196-099CF978EB2E"
DEFAULT_MAC_FOOTWELL = "1ED496B4-A08D-40AD-5D1F-01C1DEC86072"
DEFAULT_DASH_PROTOCOL = "LEDCAR_DMX_9B"
DEFAULT_FOOT_PROTOCOL = "LOTUS_9B"

SUPPORTED_PROTOCOLS = [
    "LOTUS_9B",
    "LEDCAR_DMX_9B",
    "LED_LAMP_9B",
    "TRIONES_7B",
    "SP110E_4B",
]

PREFERRED_CHAR_UUIDS = [
    "0000fff3-0000-1000-8000-00805f9b34fb",
    "0000ffe1-0000-1000-8000-00805f9b34fb",
    "0000ffd9-0000-1000-8000-00805f9b34fb",
    "0000ae01-0000-1000-8000-00805f9b34fb",
    "0000fa02-0000-1000-8000-00805f9b34fb",
]


class BleLedController(BaseService):
    """Gestionnaire BLE pour les contrôleurs Lotus et LEDCAR validés."""

    def __init__(self, storage=None):
        super().__init__("Leds", storage)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._queue: Optional[asyncio.Queue] = None
        self._running = False
        self._clients: Dict[str, BleakClient] = {}
        self._char_cache: Dict[str, str] = {}
        self._current_color = "#48B8FF"

        # Paramètres exposés
        self.register_param("dash_on", "Activer Habitacle", ServiceParamType.TOGGLE, True)
        self.register_param("foot_on", "Activer Plancher", ServiceParamType.TOGGLE, True)
        self.register_param("brightness", "Luminosité (%)", ServiceParamType.SLIDER, 100.0, min_val=0.0, max_val=100.0)
        self.register_param(
            "dash_proto", "Protocole Habitacle", ServiceParamType.LIST, DEFAULT_DASH_PROTOCOL,
            options=SUPPORTED_PROTOCOLS,
        )
        self.register_param(
            "foot_proto", "Protocole Plancher", ServiceParamType.LIST, DEFAULT_FOOT_PROTOCOL,
            options=SUPPORTED_PROTOCOLS,
        )
        self.register_param("dash_mac", "Adresse Habitacle", ServiceParamType.TEXT, DEFAULT_MAC_DASHBOARD)
        self.register_param("foot_mac", "Adresse Plancher", ServiceParamType.TEXT, DEFAULT_MAC_FOOTWELL)
        self._migrate_validated_protocols()

    def _migrate_validated_protocols(self):
        """Corrige l'ancien protocole par défaut du contrôleur LEDCAR connu."""
        dash_mac = str(self._params["dash_mac"]["value"]).strip().upper()
        dash_proto = str(self._params["dash_proto"]["value"])
        if dash_mac != DEFAULT_MAC_DASHBOARD.upper():
            return
        if dash_proto not in {"LOTUS_9B", "LED_LAMP_9B"}:
            return
        self._params["dash_proto"]["value"] = DEFAULT_DASH_PROTOCOL
        if self.storage:
            self.storage.set(
                f"services.{self.service_name}.params.dash_proto",
                DEFAULT_DASH_PROTOCOL,
            )

    def start(self, stop_event=None):
        if self._running:
            return
        self._running = True
        self.stop_event = stop_event

        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name=self.service_name)
        self._thread.start()
        super().start(stop_event, implemented=True)

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running() and self._queue:
            asyncio.run_coroutine_threadsafe(self._queue.put(None), self._loop)
        if self._thread:
            self._thread.join(timeout=2.0)
        super().stop()

    def set_color(self, hex_color: str):
        """Met à jour la couleur active et envoie l'ordre en arrière-plan."""
        self._current_color = hex_color
        if self._loop and self._queue and self._running:
            asyncio.run_coroutine_threadsafe(self._queue.put(hex_color), self._loop)

    def update_param(self, key: str, value):
        """Réagit immédiatement aux changements de paramètres (luminosité, on/off)."""
        super().update_param(key, value)
        if key in (
            "brightness", "dash_on", "foot_on", "dash_proto", "foot_proto",
            "dash_mac", "foot_mac",
        ):
            self.set_color(self._current_color)

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue = asyncio.Queue()
        self._queue.put_nowait(self._current_color)
        try:
            self._loop.run_until_complete(self._ble_worker())
        finally:
            self._loop.close()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return (255, 255, 255)

        bright_factor = max(0.0, min(100.0, float(self._params["brightness"]["value"]))) / 100.0
        r = int(int(hex_color[0:2], 16) * bright_factor)
        g = int(int(hex_color[2:4], 16) * bright_factor)
        b = int(int(hex_color[4:6], 16) * bright_factor)
        return (r, g, b)

    def _build_payloads(self, proto: str, r: int, g: int, b: int, power_on: bool) -> List[bytearray]:
        """Génère les trames BLE correctes selon le protocole de l'appareil."""
        brightness_val = max(0, min(100, int(self._params["brightness"]["value"])))

        if proto == "LOTUS_9B":
            # Protocole Lotus Lantern / ELK-BLEDOM officiel
            if not power_on or brightness_val <= 0:
                return [bytearray([0x7E, 0x00, 0x04, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xEF])]
            return [
                bytearray([0x7E, 0x00, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]), # Power ON
                bytearray([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF]),         # Set RGB Color
                bytearray([0x7E, 0x00, 0x01, brightness_val, 0x00, 0x00, 0x00, 0x00, 0xEF]), # Set Brightness
            ]

        elif proto == "LED_LAMP_9B":
            # Protocole LED Lamp / HiLighting 9 octets
            if not power_on or brightness_val <= 0:
                return [bytearray([0x7E, 0x04, 0x04, 0x00, 0x00, 0x00, 0xFF, 0x00, 0xEF])]
            return [
                bytearray([0x7E, 0x04, 0x04, 0xF0, 0x00, 0x01, 0xFF, 0x00, 0xEF]),
                bytearray([0x7E, 0x04, 0x05, 0x03, r, g, b, 0xFF, 0xEF]),
            ]

        elif proto == "LEDCAR_DMX_9B":
            # LEDCAR-01 / LED LAMP, sortie barres RGBIC confirmée sur FFE1.
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

        elif proto == "TRIONES_7B":
            # Protocole Triones / Magic Home 7 octets
            if not power_on or brightness_val <= 0:
                return [bytearray([0xCC, 0x24, 0x33])]
            return [
                bytearray([0xCC, 0x23, 0x33]),
                bytearray([0x56, r, g, b, 0x00, 0xF0, 0xAA]),
            ]

        elif proto == "SP110E_4B":
            # Protocole BanlanX / SP110E Addressable 4 octets
            if not power_on or brightness_val <= 0:
                return [bytearray([0xAA, 0x02, 0x00, 0xAC])]
            return [
                bytearray([0xAA, 0x02, 0x01, 0xAD]),
                bytearray([0x38, r, g, b]),
            ]

        # Fallback par défaut (Lotus 9B)
        return [bytearray([0x7E, 0x00, 0x05, 0x03, r, g, b, 0x00, 0xEF])]

    async def _resolve_write_char(self, client: BleakClient, mac: str) -> Optional[str]:
        """Découvre dynamiquement la caractéristique d'écriture GATT sur le périphérique."""
        if mac in self._char_cache:
            return self._char_cache[mac]

        # 1. Vérifier les UUIDs connus prioritaires
        for service in client.services:
            for char in service.characteristics:
                if char.uuid.lower() in PREFERRED_CHAR_UUIDS:
                    self._char_cache[mac] = char.uuid
                    return char.uuid

        # 2. Fallback: premier char writable
        for service in client.services:
            for char in service.characteristics:
                if "write-without-response" in char.properties or "write" in char.properties:
                    self._char_cache[mac] = char.uuid
                    return char.uuid

        return None

    async def _send_to_device(self, mac: str, proto: str, r: int, g: int, b: int, power_on: bool):
        if not BleakClient:
            self.set_warning("Bleak non installé")
            return

        if not mac or mac.strip() == "":
            return

        client = self._clients.get(mac)

        if not client or not client.is_connected:
            try:
                client = BleakClient(mac)
                await client.connect(timeout=4.0)
                self._clients[mac] = client
                self.set_ok(f"Connecté à {mac}")
            except Exception:
                self.set_warning(f"Connexion échouée: {mac[:8]}")
                return

        write_char = await self._resolve_write_char(client, mac)
        if not write_char:
            self.set_error(f"GATT introuvable sur {mac[:8]}")
            return

        payloads = self._build_payloads(proto, r, g, b, power_on)

        for payload in payloads:
            try:
                await client.write_gatt_char(write_char, payload, response=False)
                await asyncio.sleep(0.04)
            except Exception:
                self.set_error(f"Échec envoi sur {mac[:8]}")
                self._clients.pop(mac, None)
                self._char_cache.pop(mac, None)
                break

    async def _ble_worker(self):
        while self._running:
            hex_color = await self._queue.get()
            if hex_color is None:
                break

            # Conserve la dernière commande pour éviter l'accumulation de retard
            while not self._queue.empty():
                try:
                    hex_color = self._queue.get_nowait()
                    self._queue.task_done()
                except asyncio.QueueEmpty:
                    break

            if hex_color is None:
                break

            r, g, b = self._hex_to_rgb(hex_color)

            tasks = []
            dash_mac = str(self._params["dash_mac"]["value"]).strip()
            foot_mac = str(self._params["foot_mac"]["value"]).strip()
            dash_proto = str(self._params["dash_proto"]["value"])
            foot_proto = str(self._params["foot_proto"]["value"])
            dash_on = bool(self._params["dash_on"]["value"])
            foot_on = bool(self._params["foot_on"]["value"])

            if dash_mac:
                tasks.append(self._send_to_device(dash_mac, dash_proto, r, g, b, dash_on))
            if foot_mac:
                tasks.append(self._send_to_device(foot_mac, foot_proto, r, g, b, foot_on))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self._queue.task_done()

        # Déconnexion propre
        for mac, client in list(self._clients.items()):
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except Exception:
                    pass
