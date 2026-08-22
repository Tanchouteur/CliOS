import logging
import os
import shutil
import tempfile
import threading
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, TypedDict

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
    INTERNAL = "INTERNAL"
    VOLATILE = "RAM"


class MigrationReport(TypedDict):
    source: str
    target: str
    copied: list[str]
    conflicts: list[str]


class StorageManager:
    """Résout les écritures vers la clé CliOS ou vers un fallback volatil."""

    _DYNAMIC_DIRS = ("dash_save", "logs", "trips", "trips_mock", "config", "diagnostics")

    def __init__(
        self,
        base_dir: str,
        usb_folder_name: str = "clios",
        media_root: str = "/media/clios",
        volatile_root: str | None = None,
        internal_root: str = "/var/lib/clios",
        scan_interval: float = 1.0,
        mount_provider: Callable[[], Iterable[str]] | None = None,
        mount_table_provider: Callable[[], str] | None = None,
    ):
        self._base_dir = os.path.abspath(base_dir)
        self._logger = logging.getLogger("StorageManager")
        self._usb_folder_name = usb_folder_name
        self._media_root = os.path.abspath(media_root)
        self._volatile_root = os.path.abspath(volatile_root or self._default_volatile_root())
        self._internal_root = os.path.abspath(internal_root)
        self._scan_interval = max(0.2, float(scan_interval))
        self._mount_provider = mount_provider or self._mounted_volumes
        self._mount_table_provider = mount_table_provider or self._read_mount_table

        self._mode = StorageMode.VOLATILE
        self._usb_root: str | None = None
        self._usb_diagnostic = "Aucun stockage USB CliOS détecté"
        self._last_logged_usb_diagnostic = ""
        self._lock = threading.RLock()
        self._callbacks: list[Callable[[StorageMode], None]] = []
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._udev_observer = None

        self._ensure_tree(self._volatile_root)
        if not self._root_is_overlay() and self._prepare_root(self._internal_root):
            self._mode = StorageMode.INTERNAL
        self.refresh()

    @staticmethod
    def _default_volatile_root() -> str:
        # /run est un tmpfs sur Raspberry Pi OS. /tmp reste le repli développement.
        run_root = "/run"
        if os.name == "posix" and os.path.isdir(run_root) and os.access(run_root, os.W_OK):
            return os.path.join(run_root, "clios")
        return os.path.join(tempfile.gettempdir(), "clios_volatile")

    def get_writable_root(self) -> str:
        with self._lock:
            if self._mode is StorageMode.USB and self._usb_root:
                return self._usb_root
            if self._mode is StorageMode.INTERNAL:
                return self._internal_root
            return self._volatile_root

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
            self._switch_to_base_storage()
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
        active_root = self.get_writable_root()
        if active_root:
            try:
                usage = shutil.disk_usage(active_root)
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
            "storage_root": active_root,
            "free_space_mb": round(free_mb, 1),
            "total_space_mb": round(total_mb, 1),
            "trip_count": trip_count,
            "usb_diagnostic": self._usb_diagnostic,
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
            observer = pyudev.MonitorObserver(
                monitor,
                callback=lambda _action, _device: self._wake_event.set(),
                name="StorageUdev",
            )
            observer.start()
            self._udev_observer = observer
        except Exception:
            # Le rescan périodique reste fonctionnel si udev est indisponible.
            self._udev_observer = None

    def _mounted_volumes(self) -> Iterable[str]:
        """Énumère tous les montages, y compris NTFS/FUSE, sans doublon."""
        seen: set[str] = set()
        if psutil is not None:
            try:
                # all=False élimine les types marqués nodev dans
                # /proc/filesystems. Cela exclut notamment fuseblk/ntfs-3g.
                for partition in psutil.disk_partitions(all=True):
                    mountpoint = os.path.abspath(str(partition.mountpoint))
                    if mountpoint not in seen:
                        seen.add(mountpoint)
                        yield mountpoint
            except (OSError, RuntimeError) as exc:
                self._logger.warning(
                    "Énumération psutil des montages impossible: %s",
                    exc,
                    extra={"error_code": "USB_PSUTIL_SCAN_FAILED"},
                )
        try:
            with open("/proc/self/mounts", "r", encoding="utf-8") as mounts:
                for line in mounts:
                    fields = line.split()
                    if len(fields) >= 2:
                        mountpoint = os.path.abspath(self._decode_mount_path(fields[1]))
                        if mountpoint not in seen:
                            seen.add(mountpoint)
                            yield mountpoint
        except OSError as exc:
            log = self._logger.warning if os.path.isdir("/proc") else self._logger.debug
            log(
                "Lecture de /proc/self/mounts impossible: %s",
                exc,
                extra={"error_code": "USB_MOUNT_TABLE_FAILED"},
            )

    @staticmethod
    def _decode_mount_path(value: str) -> str:
        return (
            value.replace("\\040", " ")
            .replace("\\011", "\t")
            .replace("\\012", "\n")
            .replace("\\134", "\\")
        )

    def _find_usb_root(self) -> str | None:
        candidates = []
        try:
            mountpoints = list(self._mount_provider())
        except (OSError, RuntimeError, TypeError) as exc:
            self._set_usb_diagnostic(f"Énumération des montages impossible: {exc}", "USB_MOUNT_SCAN_FAILED")
            mountpoints = []

        # Le montage systemd peut précéder Cage et ne pas être remonté par
        # psutil sur certains systèmes de fichiers FUSE. /media/clios est
        # détenu par root : inspecter ses enfants directs reste borné et sûr.
        managed_paths = []
        if os.path.isdir(self._media_root):
            try:
                if os.path.isdir(os.path.join(self._media_root, self._usb_folder_name)):
                    managed_paths.append(self._media_root)
                for entry in os.scandir(self._media_root):
                    if (
                        entry.is_dir(follow_symlinks=False)
                        and os.path.isdir(os.path.join(entry.path, self._usb_folder_name))
                    ):
                        managed_paths.append(entry.path)
            except OSError as exc:
                self._set_usb_diagnostic(
                    f"Inspection de {self._media_root} impossible: {exc}",
                    "USB_MEDIA_ROOT_SCAN_FAILED",
                )
        for managed_path in managed_paths:
            if managed_path not in mountpoints:
                mountpoints.append(managed_path)

        media_prefix = self._media_root + os.sep
        managed_mounts = 0
        for mountpoint in mountpoints:
            mount_abs = os.path.abspath(str(mountpoint))
            if mount_abs != self._media_root and not mount_abs.startswith(media_prefix):
                continue
            managed_mounts += 1
            candidate = os.path.join(mount_abs, self._usb_folder_name)
            try:
                real_candidate = os.path.realpath(candidate)
                if os.path.islink(candidate):
                    self._set_usb_diagnostic(f"Lien symbolique USB refusé: {candidate}", "USB_ROOT_SYMLINK")
                    continue
                if not real_candidate.startswith(os.path.realpath(mount_abs) + os.sep):
                    self._set_usb_diagnostic(f"Racine USB hors du montage: {candidate}", "USB_ROOT_ESCAPE")
                    continue
                if not os.path.isdir(real_candidate):
                    self._set_usb_diagnostic(f"Dossier CliOS absent: {candidate}", "USB_ROOT_MISSING")
                    continue
                if not os.access(real_candidate, os.W_OK):
                    self._set_usb_diagnostic(f"Dossier CliOS non inscriptible: {candidate}", "USB_ROOT_NOT_WRITABLE")
                    continue
                candidates.append(real_candidate)
            except OSError as exc:
                self._set_usb_diagnostic(f"Inspection USB impossible pour {candidate}: {exc}", "USB_ROOT_SCAN_FAILED")
                continue

        if not candidates:
            if not managed_mounts:
                self._set_usb_diagnostic("Aucun montage sous /media/clios", "USB_MOUNT_NOT_FOUND", warning=False)
            return None
        selected = sorted(candidates)[0]
        self._usb_diagnostic = f"Stockage USB actif: {selected}"
        self._last_logged_usb_diagnostic = ""
        return selected

    def _set_usb_diagnostic(self, message: str, error_code: str, *, warning: bool = True) -> None:
        self._usb_diagnostic = message
        if message == self._last_logged_usb_diagnostic:
            return
        self._last_logged_usb_diagnostic = message
        if warning:
            self._logger.warning(message, extra={"error_code": error_code})
        else:
            self._logger.debug(message, extra={"error_code": error_code})

    def _switch_to_usb(self, usb_root: str) -> None:
        try:
            self._ensure_tree(usb_root)
            self._migrate_without_overwrite(self.get_writable_root(), usb_root)
        except OSError:
            return

        with self._lock:
            self._usb_root = usb_root
            self._mode = StorageMode.USB
        self._notify_callbacks(StorageMode.USB)

    def _switch_to_base_storage(self) -> None:
        mode = StorageMode.VOLATILE
        target = self._volatile_root
        if not self._root_is_overlay() and self._prepare_root(self._internal_root):
            mode = StorageMode.INTERNAL
            target = self._internal_root
        self._ensure_tree(target)
        with self._lock:
            self._usb_root = None
            self._mode = mode
        self._notify_callbacks(mode)

    def _migrate_volatile_to_usb(self, usb_root: str) -> None:
        """Copie les fichiers volatils sans écraser silencieusement l'USB."""
        self._migrate_without_overwrite(self._volatile_root, usb_root)

    def _migrate_without_overwrite(self, source_root: str, target_root: str) -> MigrationReport:
        report: MigrationReport = {"source": source_root, "target": target_root, "copied": [], "conflicts": []}
        if not os.path.isdir(source_root) or os.path.realpath(source_root) == os.path.realpath(target_root):
            return report
        for source_dir, dirnames, filenames in os.walk(source_root, followlinks=False):
            dirnames[:] = [name for name in dirnames if not os.path.islink(os.path.join(source_dir, name))]
            relative_dir = os.path.relpath(source_dir, source_root)
            target_dir = target_root if relative_dir == "." else os.path.join(target_root, relative_dir)
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
                    report["copied"].append(os.path.relpath(target, target_root))
                    continue
                if self._same_file_contents(source, target):
                    continue
                conflict = self._conflict_path(target)
                shutil.copy2(source, conflict)
                report["conflicts"].append(os.path.relpath(conflict, target_root))
        return report

    def migrate_existing_data(self, source_root: str, report_path: str | None = None) -> MigrationReport:
        """Copie une ancienne installation vers le stockage actif sans supprimer la source."""
        import json
        report = self._migrate_without_overwrite(os.path.abspath(source_root), self.get_writable_root())
        if report_path:
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False)
        return report

    @classmethod
    def _prepare_root(cls, root: str) -> bool:
        try:
            cls._ensure_tree(root)
            probe = os.path.join(root, ".write-probe")
            with open(probe, "w", encoding="utf-8") as stream:
                stream.write("ok")
            os.remove(probe)
            return True
        except OSError:
            return False

    @staticmethod
    def _read_mount_table() -> str:
        for path in ("/proc/self/mountinfo", "/proc/mounts"):
            try:
                with open(path, encoding="utf-8") as stream:
                    return stream.read()
            except OSError:
                continue
        return ""

    def _root_is_overlay(self) -> bool:
        """Détecte le type du montage racine, pas sa simple inscriptibilité."""
        try:
            table = self._mount_table_provider()
        except Exception:
            return False
        for line in table.splitlines():
            fields = line.split()
            if " - " in line:
                before, after = line.split(" - ", 1)
                mount_fields = before.split()
                after_fields = after.split()
                if len(mount_fields) >= 5 and mount_fields[4] == "/" and after_fields:
                    return after_fields[0] == "overlay"
            elif len(fields) >= 3 and fields[1] == "/":
                return fields[2] == "overlay"
        return False

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
            candidate = f"{stem}.migration-{index}{suffix}"
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
