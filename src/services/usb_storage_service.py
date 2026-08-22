import threading

from src.services.base_service import BaseService


class UsbStorageService(BaseService):
    """Publie l'état du stockage résilient dans le domaine système."""

    def __init__(self, runtime, storage, storage_manager, *, development_mode: bool = False):
        super().__init__("USB_Storage", storage)
        self.runtime = runtime
        self._storage_manager = storage_manager
        self._development_mode = development_mode

    def start(self, stop_event: threading.Event, implemented=False):
        super().start(stop_event, implemented=True)
        self._thread = threading.Thread(
            target=self._run,
            args=(stop_event,),
            daemon=True,
            name=self.service_name,
        )
        self._thread.start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            status = self._storage_manager.get_status()
            free_mb = float(status.get("free_space_mb", 0.0))
            if status.get("usb_connected"):
                if free_mb < 100.0:
                    self.set_warning(f"Espace faible : {free_mb:.0f} MB restants")
                else:
                    self.set_ok(f"USB OK — {free_mb:.0f} MB libres")
            elif status.get("mode") == "INTERNAL":
                self.set_ok(f"Carte SD interne — {free_mb:.0f} MB libres")
            elif self._development_mode:
                self.set_ok(f"Stockage temporaire de développement — {free_mb:.0f} MB libres")
            else:
                diagnostic = str(status.get("usb_diagnostic", "Stockage USB indisponible"))
                self.set_warning(f"{status.get('mode', 'RAM')} — {diagnostic}")

            self.runtime.publish("system", {
                "storage_mode": status.get("mode", "RAM"),
                "storage_usb_connected": bool(status.get("usb_connected", False)),
                "storage_free_mb": free_mb,
                "storage_mount": status.get("mount_point", ""),
            }, source="usb-storage")
            stop_event.wait(2.0)
