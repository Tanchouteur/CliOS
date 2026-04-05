import asyncio
import threading
from bleak import BleakClient
from bleak.exc import BleakError

# Adresses MAC de tes bandeaux LEDs
MAC_DASHBOARD = "A060C742-6A5E-53EB-4196-099CF978EB2E" # Fonctionne en GRB
MAC_FOOTWELL = "1ED496B4-A08D-40AD-5D1F-01C1DEC86072"

# UUID standard pour les bandeaux Lotus Lantern / Triones
CHAR_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"


class BleLedController:
    """Gestionnaire BLE asynchrone isolé dans un Thread pour ne pas bloquer PySide6."""

    def __init__(self):
        self._loop = None
        self._thread = None
        self._queue = None
        self._running = False

        # Cache pour maintenir les connexions actives
        self._clients = {}

    def start(self, stop_event=None):
        """Lance le thread dédié au Bluetooth."""
        if self._running:
            return
        self._running = True

        # On sauvegarde le stop_event fourni par l'orchestrateur
        self.stop_event = stop_event

        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="BLE_Worker")
        self._thread.start()

    def stop(self):
        """Arrête proprement le thread et ferme les connexions."""
        self._running = False

        if self._loop and self._loop.is_running():
            # Injecte un poison pill (None) pour débloquer le await queue.get()
            asyncio.run_coroutine_threadsafe(self._queue.put(None), self._loop)

        if self._thread:
            self._thread.join(timeout=2.0)
            print("[BLE] Thread Bluetooth arrêté proprement.")

    def set_color(self, hex_color: str):
        """
        Point d'entrée pour l'orchestrateur (Thread Principal).
        Glisse la couleur de manière sécurisée dans la queue asynchrone.
        """
        if self._loop and self._queue and self._running:
            # Transfert sécurisé entre le thread PySide6 et le thread asyncio
            asyncio.run_coroutine_threadsafe(self._queue.put(hex_color), self._loop)

    def _run_event_loop(self):
        """Méthode exécutée par le Thread. Crée et gère la boucle asyncio."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue = asyncio.Queue()

        try:
            self._loop.run_until_complete(self._ble_worker())
        finally:
            self._loop.close()

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Convertit un code HEX (#FF0000) en tuple RGB (255, 0, 0)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return (0, 0, 0)
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    def _build_payload(self, hex_color: str, mac: str) -> bytearray:
        """Construit la trame BLE. Inverse le Rouge et le Vert pour le Dashboard (GRB)."""
        r, g, b = self._hex_to_rgb(hex_color)

        if mac == MAC_DASHBOARD:
            # Ordre GRB
            return bytearray([0x7E, 0x00, 0x04, g, r, b, 0xFF, 0x00, 0xEF])

        # Ordre RGB par défaut (Footwell)
        return bytearray([0x7E, 0x00, 0x04, r, g, b, 0xFF, 0x00, 0xEF])

    async def _send_to_device(self, mac: str, payload: bytearray):
        """Gère la connexion et l'écriture pour un appareil spécifique."""
        client = self._clients.get(mac)

        # Si non connecté, on tente de se connecter
        if not client or not client.is_connected:
            try:
                client = BleakClient(mac)
                await client.connect(timeout=5.0)
                self._clients[mac] = client
                print(f"[BLE] Connecté au bandeau {mac}")
            except BleakError as e:
                print(f"[BLE] Erreur connexion à {mac} : {e}")
                return

        # Écriture du payload (sans réponse pour plus de rapidité)
        try:
            await client.write_gatt_char(CHAR_UUID, payload, response=False)
        except Exception as e:
            print(f"[BLE] Erreur d'écriture sur {mac} : {e}")
            # En cas d'erreur fatale, on purge le cache pour forcer une reconnexion
            self._clients.pop(mac, None)

    async def _ble_worker(self):
        """Boucle principale : génère les bons payloads et les expédie en parallèle."""
        print("[BLE] Worker asynchrone démarré.")
        while self._running:
            hex_color = await self._queue.get()
            if hex_color is None:
                break

            # 1. Génération de deux payloads distincts
            payload_dash = self._build_payload(hex_color, MAC_DASHBOARD)
            payload_foot = self._build_payload(hex_color, MAC_FOOTWELL)

            # 2. Envoi asynchrone
            await asyncio.gather(
                self._send_to_device(MAC_DASHBOARD, payload_dash),
                self._send_to_device(MAC_FOOTWELL, payload_foot),
                return_exceptions=True
            )
            self._queue.task_done()

        # Nettoyage à l'arrêt
        for mac, client in self._clients.items():
            if client and client.is_connected:
                await client.disconnect()
        print("[BLE] Worker asynchrone arrêté.")