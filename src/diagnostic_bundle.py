import json
import os
import platform
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.logging_runtime import get_dropped_count, get_recent_events


def create_diagnostic_bundle(
    output_dir: str,
    log_dir: str,
    config_path: str,
    system_health: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> str:
    """Crée un bundle zip léger pour post-mortem sans bloquer longtemps l'UI."""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle_name = f"diag_bundle_{timestamp}.zip"
    bundle_path = os.path.join(output_dir, bundle_name)

    runtime_info = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "dropped_logs": get_dropped_count(),
        "system_health": system_health,
        "recent_events": get_recent_events(limit=200),
    }
    if extra:
        runtime_info["extra"] = extra

    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Snapshot runtime
        zf.writestr("runtime_snapshot.json", json.dumps(runtime_info, indent=2, ensure_ascii=True))

        # Config active
        cfg_path = Path(config_path)
        if cfg_path.exists():
            zf.write(str(cfg_path), arcname=f"config/{cfg_path.name}")

        # Logs rotation
        log_path = Path(log_dir)
        if log_path.exists():
            for p in sorted(log_path.glob("clios.log.jsonl*")):
                zf.write(str(p), arcname=f"logs/{p.name}")
            fatal = log_path / "fatal_tracebacks.log"
            if fatal.exists():
                zf.write(str(fatal), arcname="logs/fatal_tracebacks.log")

    return bundle_path


