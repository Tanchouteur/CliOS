#!/usr/bin/env python3
"""Supervise le premier démarrage d'une release et restaure N-1 sans santé."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.release_manager import ReleaseManager  # noqa: E402
from src.updater_client import UpdaterClient, UpdaterClientError  # noqa: E402


def application_args(arguments: list[str]) -> list[str]:
    """Retire le séparateur argparse avant de transmettre les options à main."""
    return arguments[1:] if arguments[:1] == ["--"] else list(arguments)


def last_startup_phase(status_path: Path) -> str:
    """Retourne une description bornée de la dernière phase applicative."""
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        phase = str(payload.get("phase", "inconnue"))[:80]
        elapsed_ms = int(payload.get("elapsed_ms", 0))
        return f"{phase} ({elapsed_ms} ms)"
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return "inconnue"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-root", default="/opt/clios")
    parser.add_argument("--state-root", default="/var/lib/clios")
    parser.add_argument("--health-timeout", type=float, default=30.0)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    opts = parser.parse_args()
    manager = ReleaseManager(opts.install_root, opts.state_root)
    current = manager.current_link.resolve()
    version = (current / "VERSION").read_text(encoding="utf-8").strip()
    marker = manager.state_root / f"health-{version}"
    startup_status = manager.state_root / f"startup-{version}.json"
    marker.unlink(missing_ok=True)
    startup_status.unlink(missing_ok=True)
    env = dict(
        os.environ,
        CLIOS_HEALTH_MARKER=str(marker),
        CLIOS_RELEASE_VERSION=version,
        CLIOS_STARTUP_STATUS=str(startup_status),
    )
    python = current / ".venv/bin/python3"
    if not python.exists():
        python = Path(sys.executable)
    process = subprocess.Popen(
        [str(python), "-u", str(current / "main.py"), *application_args(opts.args)],
        cwd=current,
        env=env,
    )
    deadline = time.monotonic() + opts.health_timeout
    while time.monotonic() < deadline and process.poll() is None:
        if marker.exists():
            manager.mark_healthy(version)
            return process.wait()
        time.sleep(0.25)
    if marker.exists():
        manager.mark_healthy(version)
        return process.wait()
    print(
        f"CliOS non sain après {opts.health_timeout:.1f} s; "
        f"dernière phase: {last_startup_phase(startup_status)}",
        file=sys.stderr,
    )
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    try:
        UpdaterClient(timeout=10).rollback()
    except UpdaterClientError as exc:
        print(f"Rollback privilégié impossible: {exc}", file=sys.stderr)
        return 1
    # Le helper redémarre clios.service après avoir restauré N-1.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
