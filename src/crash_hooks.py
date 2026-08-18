import faulthandler
import os
import signal
import sys
import threading
from datetime import datetime
from datetime import timezone

from src.logging_runtime import get_logger


_FAULT_FILE = None
_FAULT_FILE_OWNED = False


def install_crash_hooks(log_dir: str) -> None:
    """Installe des hooks globaux pour capturer les crashes Python et natifs."""
    _configure_fault_file(log_dir)

    logger = get_logger("CrashHooks")

    def _sys_hook(exc_type, exc_value, exc_tb):
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb), extra={"error_code": "UNHANDLED_EXCEPTION"})

    def _thread_hook(args: threading.ExceptHookArgs):
        if args.exc_value is None:
            return
        logger.critical(
            "Unhandled thread exception in %s",
            args.thread.name if args.thread else "<unknown>",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            extra={"error_code": "UNHANDLED_THREAD_EXCEPTION"},
        )

    sys.excepthook = _sys_hook
    threading.excepthook = _thread_hook


def relocate_crash_log(log_dir: str) -> bool:
    """Rebranche faulthandler vers le support de stockage actif."""
    return _configure_fault_file(log_dir)


def _configure_fault_file(log_dir: str) -> bool:
    global _FAULT_FILE, _FAULT_FILE_OWNED

    new_file = None
    owned = False
    try:
        os.makedirs(log_dir, exist_ok=True)
        fault_path = os.path.join(log_dir, "fatal_tracebacks.log")
        new_file = open(fault_path, "a", buffering=1, encoding="utf-8")
        new_file.write(f"\n=== Crash hook active: {datetime.now(timezone.utc).isoformat()} ===\n")
        owned = True
    except OSError:
        new_file = sys.stderr

    try:
        if hasattr(signal, "SIGUSR1"):
            try:
                faulthandler.unregister(signal.SIGUSR1)
            except Exception:
                pass
        faulthandler.disable()
        faulthandler.enable(file=new_file, all_threads=True)
        if hasattr(signal, "SIGUSR1"):
            try:
                faulthandler.register(signal.SIGUSR1, file=new_file, all_threads=True)
            except Exception:
                pass
    except (OSError, RuntimeError):
        if owned:
            new_file.close()
        return False

    previous = _FAULT_FILE
    previous_owned = _FAULT_FILE_OWNED
    _FAULT_FILE = new_file
    _FAULT_FILE_OWNED = owned
    if previous_owned and previous is not None and previous is not new_file:
        try:
            previous.close()
        except OSError:
            pass
    return owned
