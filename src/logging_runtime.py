import atexit
import json
import logging
import logging.handlers
import os
import queue
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any


_LOCK = threading.RLock()
_INITIALIZED = False
_QUEUE: queue.Queue | None = None
_LISTENER: logging.handlers.QueueListener | None = None
_RECENT_EVENTS: deque[dict[str, Any]] = deque(maxlen=500)
_DROPPED_COUNT = 0
_GLOBAL_CONTEXT: dict[str, Any] = {}

_COLOR_RESET = "\033[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[96m",    # cyan
    logging.INFO: "\033[92m",     # vert
    logging.WARNING: "\033[93m",  # jaune
    logging.ERROR: "\033[91m",    # rouge
    logging.CRITICAL: "\033[95m", # magenta
}


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in _GLOBAL_CONTEXT.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        if not hasattr(record, "error_code"):
            record.error_code = ""
        return True


class RingBufferHandler(logging.Handler):
    """Conserve les derniers événements en mémoire pour debug UI/export."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            event = {
                "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "thread": record.threadName,
                "message": record.getMessage(),
                "error_code": getattr(record, "error_code", ""),
            }
            with _LOCK:
                _RECENT_EVENTS.append(event)
        except Exception:
            # On ne doit jamais casser l'app à cause du logging.
            pass


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "thread": record.threadName,
            "message": record.getMessage(),
            "error_code": getattr(record, "error_code", ""),
        }

        for key, value in _GLOBAL_CONTEXT.items():
            payload.setdefault(key, value)

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


class AnsiConsoleFormatter(logging.Formatter):
    """Formatter console coloré (ANSI), désactivable automatiquement."""

    def format(self, record: logging.LogRecord) -> str:
        base = f"[{record.levelname}] {record.name}: {record.getMessage()}"
        color = _LEVEL_COLORS.get(record.levelno)
        if not color:
            return base
        return f"{color}{base}{_COLOR_RESET}"


class NonBlockingQueueHandler(logging.handlers.QueueHandler):
    """QueueHandler borné: si plein, on drop pour protéger les threads métier."""

    def enqueue(self, record: logging.LogRecord) -> None:
        global _DROPPED_COUNT
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            with _LOCK:
                _DROPPED_COUNT += 1


def _supports_ansi_colors() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("CLIOS_NO_COLOR") in {"1", "true", "TRUE"}:
        return False

    term = os.environ.get("TERM", "")
    if term.lower() == "dumb":
        return False

    return hasattr(os.sys.stderr, "isatty") and os.sys.stderr.isatty()


def init_logging(log_dir: str, level: str = "INFO", console_level: str = "WARNING") -> None:
    global _INITIALIZED, _QUEUE, _LISTENER

    with _LOCK:
        if _INITIALIZED:
            return

        os.makedirs(log_dir, exist_ok=True)

        root = logging.getLogger()
        root.setLevel(getattr(logging, level.upper(), logging.INFO))
        root.handlers.clear()

        _QUEUE = queue.Queue(maxsize=2000)

        log_queue = _QUEUE
        queue_handler = NonBlockingQueueHandler(log_queue)
        queue_handler.addFilter(ContextFilter())
        root.addHandler(queue_handler)

        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "clios.log.jsonl"),
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonFormatter())

        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, console_level.upper(), logging.WARNING))
        if _supports_ansi_colors():
            console_handler.setFormatter(AnsiConsoleFormatter())
        else:
            console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))

        ring_handler = RingBufferHandler()
        ring_handler.setLevel(logging.INFO)

        _LISTENER = logging.handlers.QueueListener(
            log_queue,
            file_handler,
            console_handler,
            ring_handler,
            respect_handler_level=True,
        )
        _LISTENER.start()
        _INITIALIZED = True

    atexit.register(shutdown_logging)


def shutdown_logging() -> None:
    global _INITIALIZED, _LISTENER

    with _LOCK:
        if not _INITIALIZED:
            return

        if _LISTENER:
            _LISTENER.stop()

        logging.shutdown()
        _LISTENER = None
        _INITIALIZED = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def set_global_context(**kwargs: Any) -> None:
    with _LOCK:
        _GLOBAL_CONTEXT.update(kwargs)


def get_recent_events(limit: int = 100) -> list[dict[str, Any]]:
    with _LOCK:
        if limit <= 0:
            return []
        return list(_RECENT_EVENTS)[-limit:]


def get_dropped_count() -> int:
    with _LOCK:
        return _DROPPED_COUNT


def log_with_code(logger: logging.Logger, level: int, error_code: str, message: str, **kwargs: Any) -> None:
    extra = {"error_code": error_code}
    if kwargs:
        message = f"{message} | {kwargs}"
    logger.log(level, message, extra=extra)


