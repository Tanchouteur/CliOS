import logging
import os
import shutil
import tempfile
import threading
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable

try:
    import psutil
except ImportError:
    psutil = None

try:
    import pyudev
except ImportError:  # pyudev n'est disponible que sur Linux en production.
    pyudev = None


class StorageMode(Enum):
    USB = "USB"
    VOLATILE = "VOLATILE"


class StorageManager:
    """Résout les écritures vers la clé CliOS ou vers un fallback volatil."""

    _DYNAMIC_DIRS = ("dash_save", "logs", "trips", "trips_mock", "config", "diagnostics")

    def __init__(
        self,
        base_dir: str,
        usb_folder_name: str = "clios",
        media_root: str = "/media/clios",
        volatile_root: str | None = None,
        scan_interval: float = 1.0,
        mount_provider: Callable[[], Iterable[str]] | None = None,
    ):
        self._base_dir = os.path.abspath(base_dir)
        self._logger = logging.getLogger("StorageManager")
        self._usb_folder_name = usb_folder_name
        self._media_root = os.path.abspath(media_root)
        self._volatile_root = os.path.abspath(volatile_root or self._default_volatile_root())
        self._scan_interval = max(0.2, float(scan_interval))
        self._mount_provider = mount_provider or self._mounted_volumes

        self._mode = StorageMode.VOLATILE
        self._usb_root: str | None = None
        self._lock = threading.RLock()
        self._callbacks: list[Callable[[StorageMode], None]] = []
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._udev_observer = None

        self._ensure_tree(self._volatile_root)
        self.refresh()

    @staticmethod
    def _default_volatile_root() -> str:
        # /dev/shm est un tmpfs sur Linux. /tmp reste le fallback de développement.
        shm = "/dev/shm"
        if os.name == "posix" and os.path.isdir(shm) and os.access(shm, os.W_OK):
            return os.path.join(shm, "clios_volatile")
        return os.path.join(tempfile.gettempdir(), "clios_volatile")

    def get_writable_root(self) -> str:
        with self._lock:
            return self._usb_root if self._mode is StorageMode.USB and self._usb_root else self._volatile_root

    def resolve_path(self, relative_path: str) -> str:
        relative = self._validate_relative_path(relative_path)
        return os.path.join(self.get_writable_root(), relative)

    def resolve_static_path(self, relative_path: str) -> str:
        relative = self._validate_relative_path(relative_path)
        return os.path.join(self._base_dir, relative)

    def prepare_config_dir(self, static_config_dir: str) -> str:
        """Amorce la config modifiable avec les fichiers statiques absents."""
        target = self.resolve_path("config")
        os.makedirs(target, exist_ok=True)
        if not os.path.isdir(static_config_dir):
            return target

        for entry in os.scandir(static_config_dir):
            if not entry.is_file(follow_symlinks=False) or not entry.name.endswith(".json"):
                continue
            destination = os.path.join(target, entry.name)
            if not os.path.exists(destination):
                shutil.copy2(entry.path, destination)
        return target

    def start_monitoring(self) -> None:
        with self._lock:
            if self._monitor_thread and self._monitor_thread.is_alive():
                return
            self._stop_event.clear()
            self._start_udev_observer()
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True,
                name="StorageMonitor",
            )
            self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        observer = self._udev_observer
        if observer is not None:
            try:
                observer.stop()
            except Exception:
                pass
        thread = self._monitor_thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, self._scan_interval * 2))
        self._monitor_thread = None
        self._udev_observer = None

    def refresh(self) -> bool:
        """Rescan synchrone. Retourne True si le mode ou la clé a changé."""
        candidate = self._find_usb_root()
        with self._lock:
            current = self._usb_root
            current_mode = self._mode

        if candidate and (current_mode is not StorageMode.USB or candidate != current):
            self._switch_to_usb(candidate)
            return True
        if not candidate and current_mode is StorageMode.USB:
            self._switch_to_volatile()
            return True
        return False

    @property
    def mode(self) -> StorageMode:
        with self._lock:
            return self._mode

    @property
    def is_usb_available(self) -> bool:
        return self.mode is StorageMode.USB

    @property
    def usb_free_space_mb(self) -> float:
        with self._lock:
            usb_root = self._usb_root
        if not usb_root:
            return 0.0
        try:
            return shutil.disk_usage(usb_root).free / (1024 * 1024)
        except OSError:
            return 0.0

    def get_status(self) -> dict:
        with self._lock:
            mode = self._mode
            usb_root = self._usb_root

        free_mb = 0.0
        total_mb = 0.0
        if usb_root:
            try:
                usage = shutil.disk_usage(usb_root)
                free_mb = usage.free / (1024 * 1024)
                total_mb = usage.total / (1024 * 1024)
            except OSError:
                pass

        trip_count = 0
        for folder in ("trips", "trips_mock"):
            try:
                trip_count += sum(
                    1 for item in os.scandir(self.resolve_path(folder))
                    if item.is_file(follow_symlinks=False)
                    and item.name.startswith("trip_")
                    and item.name.endswith(".json")
                )
            except OSError:
                pass

        return {
            "mode": mode.value,
            "usb_connected": mode is StorageMode.USB,
            "mount_point": os.path.dirname(usb_root) if usb_root else "",
            "storage_root": usb_root or self._volatile_root,
            "free_space_mb": round(free_mb, 1),
            "total_space_mb": round(total_mb, 1),
            "trip_count": trip_count,
        }

    def register_callback(self, callback: Callable[[StorageMode], None]) -> None:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[StorageMode], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            self.refresh()
            self._wake_event.wait(self._scan_interval)
            self._wake_event.clear()

    def _start_udev_observer(self) -> None:
        if pyudev is None or os.name != "posix":
            return
        try:
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem="block")
            self._udev_observer = pyudev.MonitorObserver(
                monitor,
                callback=lambda _action, _device: self._wake_event.set(),
                name="StorageUdev",
            )
            self._udev_observer.start()
        except Exception:
            # Le rescan périodique reste fonctionnel si udev est indisponible.
            self._udev_observer = None

    def _mounted_volumes(self) -> Iterable[str]:
        if psutil is not None:
            for partition in psutil.disk_partitions(all=False):
                yield partition.mountpoint
            return
        try:
            with open("/proc/self/mounts", "r", encoding="utf-8") as mounts:
                for line in mounts:
                    fields = line.split()
                    if len(fields) >= 2:
                        yield fields[1].replace("\\040", " ")
        except OSError:
            return

    def _find_usb_root(self) -> str | None:
        candidates = []
        try:
            mountpoints = self._mount_provider()
        except Exception:
            return None

        media_prefix = self._media_root + os.sep
        for mountpoint in mountpoints:
            mount_abs = os.path.abspath(str(mountpoint))
            if mount_abs != self._media_root and not mount_abs.startswith(media_prefix):
                continue
            candidate = os.path.join(mount_abs, self._usb_folder_name)
            try:
                real_candidate = os.path.realpath(candidate)
                if (
                    not os.path.islink(candidate)
                    and real_candidate.startswith(os.path.realpath(mount_abs) + os.sep)
                    and os.path.isdir(real_candidate)
                    and os.access(real_candidate, os.W_OK)
                ):
                    candidates.append(real_candidate)
            except OSError:
                continue

        if not candidates:
            return None
        return sorted(candidates)[0]

    def _switch_to_usb(self, usb_root: str) -> None:
        try:
            self._ensure_tree(usb_root)
            self._migrate_volatile_to_usb(usb_root)
        except OSError:
            return

        with self._lock:
            self._usb_root = usb_root
            self._mode = StorageMode.USB
        self._notify_callbacks(StorageMode.USB)

    def _switch_to_volatile(self) -> None:
        try:
            self._ensure_tree(self._volatile_root)
        except OSError:
            return
        with self._lock:
            self._usb_root = None
            self._mode = StorageMode.VOLATILE
        self._notify_callbacks(StorageMode.VOLATILE)

    def _migrate_volatile_to_usb(self, usb_root: str) -> None:
        """Copie les fichiers volatils sans écraser silencieusement l'USB."""
        if not os.path.isdir(self._volatile_root):
            return
        for source_dir, dirnames, filenames in os.walk(self._volatile_root, followlinks=False):
            dirnames[:] = [name for name in dirnames if not os.path.islink(os.path.join(source_dir, name))]
            relative_dir = os.path.relpath(source_dir, self._volatile_root)
            target_dir = usb_root if relative_dir == "." else os.path.join(usb_root, relative_dir)
            os.makedirs(target_dir, exist_ok=True)
            for filename in filenames:
                if filename.endswith(".tmp"):
                    continue
                source = os.path.join(source_dir, filename)
                if os.path.islink(source):
                    continue
                target = os.path.join(target_dir, filename)
                if not os.path.exists(target):
                    shutil.copy2(source, target)
                    continue
                if self._same_file_contents(source, target):
                    continue
                if relative_dir in {"trips", "trips_mock", "diagnostics", "logs"}:
                    conflict = self._conflict_path(target)
                    shutil.copy2(source, conflict)

    @staticmethod
    def _same_file_contents(left: str, right: str) -> bool:
        try:
            if os.path.getsize(left) != os.path.getsize(right):
                return False
            with open(left, "rb") as first, open(right, "rb") as second:
                while True:
                    a = first.read(64 * 1024)
                    b = second.read(64 * 1024)
                    if a != b:
                        return False
                    if not a:
                        return True
        except OSError:
            return False

    @staticmethod
    def _conflict_path(path: str) -> str:
        stem, suffix = os.path.splitext(path)
        index = 1
        while True:
            candidate = f"{stem}.volatile-{index}{suffix}"
            if not os.path.exists(candidate):
                return candidate
            index += 1

    def _notify_callbacks(self, mode: StorageMode) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for callback in callbacks:
            try:
                callback(mode)
            except Exception:
                # Une intégration ne doit jamais tuer le moniteur de stockage.
                self._logger.exception(
                    "Callback de transition stockage en échec",
                    extra={"error_code": "STORAGE_CALLBACK_FAILED"},
                )

    @classmethod
    def _ensure_tree(cls, root: str) -> None:
        os.makedirs(root, exist_ok=True)
        for folder in cls._DYNAMIC_DIRS:
            os.makedirs(os.path.join(root, folder), exist_ok=True)

    @staticmethod
    def _validate_relative_path(relative_path: str) -> str:
        raw = os.fspath(relative_path)
        candidate = os.path.normpath(raw)
        parts = Path(candidate).parts
        if not raw or os.path.isabs(raw) or candidate == ".." or ".." in parts:
            raise ValueError("Le chemin de stockage doit rester relatif à la racine CliOS")
        return candidate
