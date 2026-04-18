import faulthandler
import os
import signal
import sys
import threading
from datetime import datetime
from datetime import timezone

from src.logging_runtime import get_logger


_FAULT_FILE = None


def install_crash_hooks(log_dir: str) -> None:
    """Installe des hooks globaux pour capturer les crashes Python et natifs."""
    global _FAULT_FILE

    os.makedirs(log_dir, exist_ok=True)
    fault_path = os.path.join(log_dir, "fatal_tracebacks.log")
    _FAULT_FILE = open(fault_path, "a", buffering=1, encoding="utf-8")
    _FAULT_FILE.write(f"\n=== Crash hook active: {datetime.now(timezone.utc).isoformat()} ===\n")

    faulthandler.enable(file=_FAULT_FILE, all_threads=True)

    if hasattr(signal, "SIGUSR1"):
        try:
            faulthandler.register(signal.SIGUSR1, file=_FAULT_FILE, all_threads=True)
        except Exception:
            pass

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


