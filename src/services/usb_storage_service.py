import threading

from src.services.base_service import BaseService


class UsbStorageService(BaseService):
    """Expose le stockage résilient dans la santé système et l'API."""

    def __init__(self, api, storage, storage_manager):
        super().__init__("USB_Storage", storage)
        self.api = api
        self._storage_manager = storage_manager

    def start(self, stop_event: threading.Event):
        super().start(stop_event, implemented=True)
        threading.Thread(
            target=self._run,
            args=(stop_event,),
            daemon=True,
            name=self.service_name,
        ).start()

    def _run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            status = self._storage_manager.get_status()
            free_mb = float(status.get("free_space_mb", 0.0))
            if status.get("usb_connected"):
                if free_mb < 100.0:
                    self.set_warning(f"Espace faible : {free_mb:.0f} MB restants")
                else:
                    self.set_ok(f"USB OK — {free_mb:.0f} MB libres")
            else:
                self.set_warning("Mode dégradé — données temporaires en RAM")

            self.api.update({
                "storage_mode": status.get("mode", "VOLATILE"),
                "storage_usb_connected": bool(status.get("usb_connected", False)),
                "storage_free_mb": free_mb,
                "storage_mount": status.get("mount_point", ""),
            })
            stop_event.wait(2.0)

