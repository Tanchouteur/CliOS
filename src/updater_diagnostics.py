"""Read-only updater diagnostics suitable for Raspberry Pi support bundles."""

from __future__ import annotations

import json
import os
import platform
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path


MAX_COMMAND_OUTPUT = 32 * 1024


def _bounded(value: str, limit: int = MAX_COMMAND_OUTPUT) -> str:
    return value if len(value) <= limit else value[:limit] + "\n… output truncated …"


def _command(args: list[str], timeout: float = 8.0) -> dict:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "command": args,
            "returncode": result.returncode,
            "stdout": _bounded(result.stdout),
            "stderr": _bounded(result.stderr),
        }
    except FileNotFoundError as exc:
        return {"command": args, "error": "ENOENT", "errno": exc.errno, "message": str(exc)}
    except PermissionError as exc:
        return {"command": args, "error": "EACCES", "errno": exc.errno, "message": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {
            "command": args, "error": "TIMEOUT",
            "stdout": _bounded(str(exc.stdout or "")), "stderr": _bounded(str(exc.stderr or "")),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "command": args, "error": type(exc).__name__,
            "errno": getattr(exc, "errno", None), "message": str(exc),
        }


def _path_info(path: Path) -> dict:
    try:
        value = path.lstat()
        info = {
            "path": str(path),
            "exists": True,
            "mode": stat.filemode(value.st_mode),
            "uid": value.st_uid,
            "gid": value.st_gid,
            "size": value.st_size,
        }
        if path.is_symlink():
            info["symlink_target"] = os.readlink(path)
            try:
                info["resolved"] = str(path.resolve(strict=True))
            except OSError as exc:
                info["resolve_error"] = {"type": type(exc).__name__, "errno": exc.errno, "message": str(exc)}
        return info
    except OSError as exc:
        return {
            "path": str(path), "exists": False, "error": type(exc).__name__,
            "errno": exc.errno, "message": str(exc),
        }


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"error": type(exc).__name__, "errno": getattr(exc, "errno", None), "message": str(exc)}


def collect_updater_diagnostics(
    install_root: str = "/opt/clios",
    state_root: str = "/var/lib/clios",
    service_name: str = "clios-updater.service",
) -> dict:
    """Collect systemd, filesystem, OverlayFS, disk, Python and release state without mutation."""
    install = Path(install_root)
    state = Path(state_root)
    commands = {
        "systemd_properties": _command([
            "systemctl", "show", service_name,
            "--property=User,Group,NoNewPrivileges,ProtectSystem,ReadWritePaths,PrivateTmp,PrivateDevices,"
            "CapabilityBoundingSet,RestrictAddressFamilies,ActiveState,SubState,ExecMainStatus",
        ]),
        "systemd_unit": _command(["systemctl", "cat", service_name]),
        "journal": _command(["journalctl", "-u", service_name, "-n", "250", "--no-pager", "-o", "short-iso-precise"]),
        "mount": _command(["findmnt", "--target", str(install), "--output", "TARGET,SOURCE,FSTYPE,OPTIONS"]),
        "permissions": _command(["namei", "-l", str(install / "current")]),
        "python3": _command(["python3", "--version"]),
    }
    platform_pythons = {}
    for executable in ("python3.11", "python3.13"):
        platform_pythons[executable] = _command([executable, "--version"])
    try:
        disk = shutil.disk_usage(install if install.exists() else install.parent)
        disk_usage = {"total": disk.total, "used": disk.used, "free": disk.free}
    except OSError as exc:
        disk_usage = {"error": type(exc).__name__, "errno": exc.errno, "message": str(exc)}
    try:
        releases = sorted(path.name for path in (install / "releases").iterdir() if path.is_dir())
    except OSError:
        releases = []
    try:
        mountinfo = _bounded(Path("/proc/self/mountinfo").read_text(encoding="utf-8"))
    except OSError as exc:
        mountinfo = f"{type(exc).__name__}: {exc}"
    return {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "effective_ids": {"uid": os.geteuid(), "gid": os.getegid(), "groups": os.getgroups()},
        "paths": [
            _path_info(install), _path_info(install / "current"), _path_info(install / "releases"),
            _path_info(state), _path_info(state / "updater-status.json"),
            _path_info(state / "updater-operations.jsonl"),
        ],
        "disk_usage": disk_usage,
        "mountinfo": mountinfo,
        "python": {"runtime": platform.python_version(), "commands": platform_pythons},
        "releases": releases,
        "release_state": _read_json(state / "release-state.json"),
        "updater_status": _read_json(state / "updater-status.json"),
        "commands": commands,
    }
