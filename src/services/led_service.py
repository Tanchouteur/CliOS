import asyncio
import threading
from bleak import BleakClient
from bleak.exc import BleakError

from src.services.base_service import BaseService

MAC_DASHBOARD = "A060C742-6A5E-53EB-4196-099CF978EB2E"
MAC_FOOTWELL = "1ED496B4-A08D-40AD-5D1F-01C1DEC86072"
CHAR_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"


class BleLedController(BaseService):
    """Gestionnaire BLE asynchrone isolé dans un Thread."""

    def __init__(self, storage=None):
        super().__init__("Leds", storage)
        self._loop = None
        self._thread = None
        self._queue = None
        self._running = False
        self._clients = {}

        # --- DÉCLARATION DES PARAMÈTRES ---
        self.register_param("dash_on", "Activer Dashboard", "toggle", True)
        self.register_param("foot_on", "Activer Plancher", "toggle", True)
        self.register_param("brightness", "Luminosité (%)", "slider", 100.0, min_val=0.0, max_val=100.0)

    def start(self, stop_event=None):
        if self._running:
            return
        self._running = True
        self.stop_event = stop_event

        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="Leds_Worker")
        self._thread.start()
        super().start(stop_event, implemented=True)

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._queue.put(None), self._loop)
        if self._thread:
            self._thread.join(timeout=2.0)
        super().stop()

    def set_color(self, hex_color: str):
        if self._loop and self._queue and self._running:
            asyncio.run_coroutine_threadsafe(self._queue.put(hex_color), self._loop)

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue = asyncio.Queue()
        try:
            self._loop.run_until_complete(self._ble_worker())
        finally:
            self._loop.close()

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convertit HEX en RGB et applique le paramètre de luminosité."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return (0, 0, 0)

        # On lit le paramètre de luminosité (ex: 50% = 0.5)
        bright_factor = self._params["brightness"]["value"] / 100.0

        r = int(int(hex_color[0:2], 16) * bright_factor)
        g = int(int(hex_color[2:4], 16) * bright_factor)
        b = int(int(hex_color[4:6], 16) * bright_factor)
        return (r, g, b)

    def _build_payload(self, hex_color: str, mac: str) -> bytearray:
        r, g, b = self._hex_to_rgb(hex_color)
        if mac == MAC_DASHBOARD:
            return bytearray([0x7E, 0x00, 0x04, g, r, b, 0xFF, 0x00, 0xEF])
        return bytearray([0x7E, 0x00, 0x04, r, g, b, 0xFF, 0x00, 0xEF])

    async def _send_to_device(self, mac: str, payload: bytearray):
        client = self._clients.get(mac)

        if not client or not client.is_connected:
            try:
                client = BleakClient(mac)
                await client.connect(timeout=3.0)  # Timeout réduit pour ne pas tout geler
                self._clients[mac] = client
                self.set_ok(f"Connecté au bandeau {mac}")
            except BleakError as e:
                self.set_warning(f"Impossible de joindre {mac}")
                return

        try:
            await client.write_gatt_char(CHAR_UUID, payload, response=False)
        except Exception as e:
            self.set_error(f"Écriture échouée sur {mac}")
            self._clients.pop(mac, None)

    async def _ble_worker(self):
        while self._running:
            hex_color = await self._queue.get()
            if hex_color is None:
                break

            # --- CORRECTION CRUCIALE : LA PURGE ---
            # Si 20 couleurs sont en attente (à cause d'un glissement de slider), on jette
            # les 19 premières et on ne garde que la toute dernière pour soulager le Bluetooth.
            while not self._queue.empty():
                try:
                    hex_color = self._queue.get_nowait()
                    self._queue.task_done()
                except asyncio.QueueEmpty:
                    break

            if hex_color is None:
                break

            tasks = []
            if self._params["dash_on"]["value"]:
                tasks.append(self._send_to_device(MAC_DASHBOARD, self._build_payload(hex_color, MAC_DASHBOARD)))

            if self._params["foot_on"]["value"]:
                tasks.append(self._send_to_device(MAC_FOOTWELL, self._build_payload(hex_color, MAC_FOOTWELL)))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self._queue.task_done()

        # Nettoyage
        for mac, client in list(self._clients.items()):
            if client and client.is_connected:
                await client.disconnect()