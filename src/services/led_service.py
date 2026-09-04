"""Gestionnaire BLE des controleurs LED.

Pilote un catalogue variable d'appareils BLE confirmes via le DeviceCatalog.
Les couleurs, luminosites et groupes sont geres dynamiquement.
"""

import asyncio
import threading
from typing import Dict, List, Optional, Tuple

try:
    from bleak import BleakClient
    from bleak.exc import BleakError
except ImportError:
    BleakClient = None  # type: ignore
    BleakError = Exception

from src.services.base_service import BaseService
from src.services.param_types import ServiceParamType
from src.ble.protocol_registry import ProtocolRegistry, registry as _default_registry
from src.ble.device_catalog import DeviceCatalog, BleDevice
from src.ble.scanner import BleScanner, scanner as _ble_scanner

# Conserves pour la retrocompatibilite (imports externes eventuels)
SUPPORTED_PROTOCOLS: List[str] = [p.identifier for p in _default_registry.runtime_protocols()]


class BleLedController(BaseService):
    """Gestionnaire BLE pour les controleurs LED confirmes du catalogue."""

    STARTUP_RETRY_DELAYS = (1.0, 2.0)

    def __init__(self, storage=None, catalog: Optional[DeviceCatalog] = None,
                 registry: Optional[ProtocolRegistry] = None,
                 initial_color: str = "#48B8FF"):
        super().__init__("Leds", storage)
        self._catalog: DeviceCatalog = catalog or DeviceCatalog(storage)
        self._registry: ProtocolRegistry = registry or _default_registry
        self._scanner: BleScanner = _ble_scanner

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._queue: Optional[asyncio.Queue] = None
        self._running = False

        # Connexions BLE persistantes indexees par device_id
        self._clients: Dict[str, BleakClient] = {}
        # Cache de caracteristiques GATT indexe par device_id
        self._char_cache: Dict[str, Tuple[str, bool]] = {}  # device_id -> (char_uuid, write_response)

        self._current_color = initial_color

        # Etat du scan BLE (expose au bridge via scan_state)
        self._scan_lock = threading.Lock()
        self._scan_state: dict = {
            "scanning": False, "results": [], "characteristics": [], "test_state": {},
        }
        self._scan_task: Optional[asyncio.Task] = None
        self._test_task: Optional[asyncio.Task] = None

        # Parametre de luminosite globale (reste visible dans ServicesPage)
        self.register_param(
            "global_brightness", "Luminosite globale (%)",
            ServiceParamType.SLIDER, 100.0, min_val=0.0, max_val=100.0,
        )

    # -------------------------------------------------------------------------
    # Cycle de vie
    # -------------------------------------------------------------------------

    def start(self, stop_event=None):
        if self._running:
            return
        self._running = True
        self.stop_event = stop_event
        self._thread = threading.Thread(
            target=self._run_event_loop, daemon=True, name=self.service_name,
        )
        self._thread.start()
        super().start(stop_event, implemented=True)

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running() and self._queue:
            asyncio.run_coroutine_threadsafe(self._queue.put(None), self._loop)
        if self._thread:
            self._thread.join(timeout=2.0)
        super().stop()

    # -------------------------------------------------------------------------
    # API publique (thread-safe)
    # -------------------------------------------------------------------------

    def set_color(self, hex_color: str) -> None:
        """Met a jour la couleur d'accent et propage aux appareils."""
        self._current_color = hex_color
        if self._loop and self._queue and self._running:
            asyncio.run_coroutine_threadsafe(self._queue.put(hex_color), self._loop)

    def update_param(self, key: str, value) -> None:
        """Reagit aux changements de parametres (luminosite globale)."""
        super().update_param(key, value)
        if key == "global_brightness":
            self.set_color(self._current_color)

    def refresh_devices(self) -> None:
        """Rejoue la couleur courante apres une modification du catalogue."""
        self.set_color(self._current_color)

    @property
    def scan_state(self) -> dict:
        """Retourne l'etat courant du scan BLE (thread-safe)."""
        with self._scan_lock:
            return dict(self._scan_state)

    def request_scan(self) -> None:
        """Lance un scan BLE asynchrone (delegue a la boucle asyncio du service)."""
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(self._async_scan(), self._loop)

    def stop_scan(self) -> None:
        """Interrompt un scan en cours."""
        if self._loop and self._running and self._scan_task:
            self._loop.call_soon_threadsafe(self._scan_task.cancel)

    def request_characteristics(self, address: str) -> None:
        """Decouvre les caracteristiques GATT writables d'un appareil."""
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(
                self._async_discover_characteristics(address), self._loop,
            )

    def start_protocol_test(
        self, address: str, char_uuid: str, protocol_id: str, write_with_response: bool,
    ) -> None:
        """Lance le test d'un protocole BLE (delegue a la boucle asyncio du service)."""
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(
                self._async_test_protocol(address, char_uuid, protocol_id, write_with_response),
                self._loop,
            )

    def stop_protocol_test(self) -> None:
        """Interrompt un test de protocole en cours."""
        if self._loop and self._running and self._test_task:
            self._loop.call_soon_threadsafe(self._test_task.cancel)

    # -------------------------------------------------------------------------
    # Boucle asyncio interne
    # -------------------------------------------------------------------------

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue = asyncio.Queue()
        self._queue.put_nowait(self._current_color)
        try:
            self._loop.run_until_complete(self._ble_worker())
        finally:
            self._loop.close()

    async def _ble_worker(self) -> None:
        """Consomme la file des mises a jour de couleur et les envoie aux appareils."""
        initial_dispatch = True
        while self._running:
            hex_color = await self._queue.get()
            if hex_color is None:
                break

            # Coalescing: conserve la derniere commande uniquement
            while not self._queue.empty():
                try:
                    next_color = self._queue.get_nowait()
                    self._queue.task_done()
                    if next_color is None:
                        self._queue.task_done()
                        # Arret demande
                        await self._disconnect_all()
                        return
                    hex_color = next_color
                except asyncio.QueueEmpty:
                    break

            if hex_color is None:
                break

            global_brightness = float(self._params["global_brightness"]["value"])
            # Inclut les appareils desactives pour leur envoyer une commande
            # d'extinction avant de conserver leur configuration.
            devices = self._catalog.list_devices()

            tasks = []
            attempts = 1 + len(self.STARTUP_RETRY_DELAYS) if initial_dispatch else 1
            for device in devices:
                effective_color = self._catalog.get_effective_color(device, hex_color)
                device_brightness = self._catalog.get_effective_brightness(device)
                effective_brightness = (global_brightness * device_brightness) / 100.0
                # Le registre applique la luminosite selon les capacites du
                # protocole (commande dediee ou attenuation RGB).
                r, g, b = self._hex_to_rgb(effective_color, 100.0)
                tasks.append(self._send_to_device(
                    device, r, g, b, effective_brightness,
                    power_on=self._catalog.is_effectively_enabled(device),
                    attempts=attempts,
                ))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            initial_dispatch = False
            self._queue.task_done()

        await self._disconnect_all()

    async def _disconnect_all(self) -> None:
        """Deconnexion propre de tous les clients BLE."""
        for device_id, client in list(self._clients.items()):
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except Exception:
                    pass
        self._clients.clear()
        self._char_cache.clear()

    # -------------------------------------------------------------------------
    # Envoi BLE par appareil
    # -------------------------------------------------------------------------

    @staticmethod
    def _hex_to_rgb(hex_color: str, brightness_pct: float) -> Tuple[int, int, int]:
        """Convertit une couleur hex en RGB avec application de la luminosite."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return (255, 255, 255)
        factor = max(0.0, min(100.0, brightness_pct)) / 100.0
        r = int(int(hex_color[0:2], 16) * factor)
        g = int(int(hex_color[2:4], 16) * factor)
        b = int(int(hex_color[4:6], 16) * factor)
        return (r, g, b)

    async def _resolve_write_char(
        self, client: "BleakClient", device_id: str
    ) -> Optional[Tuple[str, bool]]:
        """Decouvre la caracteristique GATT writable et le mode d'ecriture."""
        if device_id in self._char_cache:
            return self._char_cache[device_id]

        preferred = set(self._registry.preferred_char_uuids())
        # 1. Chercher un UUID prefere
        for service in client.services:
            for char in service.characteristics:
                if char.uuid.lower() in preferred:
                    write_response = "write" in char.properties and "write-without-response" not in char.properties
                    self._char_cache[device_id] = (char.uuid, write_response)
                    return self._char_cache[device_id]
        # 2. Fallback: premier char writable
        for service in client.services:
            for char in service.characteristics:
                if "write-without-response" in char.properties or "write" in char.properties:
                    write_response = "write" in char.properties and "write-without-response" not in char.properties
                    self._char_cache[device_id] = (char.uuid, write_response)
                    return self._char_cache[device_id]
        return None

    async def _send_to_device(
        self, device: BleDevice, r: int, g: int, b: int,
        brightness_pct: float, power_on: bool, attempts: int = 1,
    ) -> bool:
        """Envoie une couleur avec des nouvelles tentatives bornees."""
        attempt_count = max(1, int(attempts))
        for attempt_index in range(attempt_count):
            if attempt_index and (
                not self._running
                or (self._queue is not None and not self._queue.empty())
            ):
                break
            if await self._send_to_device_once(
                device, r, g, b, brightness_pct, power_on,
            ):
                return True
            if attempt_index >= attempt_count - 1 or not self._running:
                break
            if self._queue is not None and not self._queue.empty():
                break
            delay_index = min(attempt_index, len(self.STARTUP_RETRY_DELAYS) - 1)
            await asyncio.sleep(self.STARTUP_RETRY_DELAYS[delay_index])
        return False

    async def _send_to_device_once(
        self, device: BleDevice, r: int, g: int, b: int,
        brightness_pct: float, power_on: bool,
    ) -> bool:
        """Envoie les trames de couleur a un appareil BLE."""
        if not BleakClient:
            self.set_warning("Bleak non installe")
            return False
        if not device.ble_address or not device.ble_address.strip():
            return False

        client = self._clients.get(device.id)
        if not client or not client.is_connected:
            try:
                client = BleakClient(device.ble_address)
                await client.connect(timeout=4.0)
                self._clients[device.id] = client
                self._catalog.update_device_health(device.id, "connected")
                self.set_ok(f"Connecte: {device.name}")
            except Exception:
                self._catalog.update_device_health(device.id, "disconnected")
                self.set_warning(f"Connexion echouee: {device.name}")
                return False

        # Determine la caracteristique GATT a utiliser
        char_info = None
        if device.gatt_char_uuid:
            # Utilise la char confirmee lors du wizard
            char_info = (device.gatt_char_uuid, device.write_with_response)
            self._char_cache[device.id] = char_info
        else:
            char_info = await self._resolve_write_char(client, device.id)

        if not char_info:
            self._catalog.update_device_health(device.id, "error")
            self.set_error(f"GATT introuvable: {device.name}")
            return False

        char_uuid, write_response = char_info
        payloads = self._registry.build_payloads(
            device.protocol, r, g, b, brightness_pct, power_on,
        )
        for payload in payloads:
            try:
                await client.write_gatt_char(char_uuid, payload, response=write_response)
                await asyncio.sleep(0.04)
            except Exception:
                self._catalog.update_device_health(device.id, "error")
                self.set_error(f"Echec envoi: {device.name}")
                self._clients.pop(device.id, None)
                self._char_cache.pop(device.id, None)
                return False
        return True

    # -------------------------------------------------------------------------
    # Scan et test de protocoles (async, appeles depuis le worker asyncio)
    # -------------------------------------------------------------------------

    async def _async_scan(self) -> None:
        """Execute un scan BLE et met a jour scan_state."""
        with self._scan_lock:
            self._scan_state.update({"scanning": True, "results": [], "characteristics": []})
        try:
            self._scan_task = asyncio.current_task()
            results = await self._scanner.scan()
            with self._scan_lock:
                self._scan_state = {
                    "scanning": False,
                    "results": [r.to_dict() for r in results],
                    "characteristics": [], "test_state": {},
                }
        except asyncio.CancelledError:
            with self._scan_lock:
                self._scan_state["scanning"] = False
        except Exception as exc:
            self.set_warning(f"Erreur scan BLE: {exc}")
            with self._scan_lock:
                self._scan_state["scanning"] = False
        finally:
            self._scan_task = None

    async def _async_discover_characteristics(self, address: str) -> None:
        with self._scan_lock:
            self._scan_state["test_state"] = {
                "running": True, "stage": "connecting", "address": address,
            }
            self._scan_state["characteristics"] = []
        chars = await self._scanner.discover_characteristics(address)
        with self._scan_lock:
            self._scan_state["characteristics"] = [char.to_dict() for char in chars]
            self._scan_state["test_state"] = {
                "running": False,
                "stage": "characteristics" if chars else "error",
                "address": address,
                "message": "" if chars else "Aucune caracteristique GATT writable trouvee",
            }

    async def _async_test_protocol(
        self, address: str, char_uuid: str, protocol_id: str, write_with_response: bool,
    ) -> None:
        """Execute le test d'un protocole et met a jour scan_state.test_state."""
        try:
            self._test_task = asyncio.current_task()
            with self._scan_lock:
                self._scan_state["test_state"] = {
                    "running": True, "protocol": protocol_id, "success": None,
                }
            success = await self._scanner.test_protocol(
                address, char_uuid, write_with_response, protocol_id,
            )
            with self._scan_lock:
                self._scan_state["test_state"] = {
                    "running": False, "protocol": protocol_id, "success": success,
                }
        except asyncio.CancelledError:
            with self._scan_lock:
                self._scan_state["test_state"]["running"] = False
        except Exception:
            with self._scan_lock:
                self._scan_state["test_state"] = {
                    "running": False, "protocol": protocol_id, "success": False,
                }
        finally:
            self._test_task = None
