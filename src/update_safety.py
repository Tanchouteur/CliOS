"""Shared safety checks for release updates and host power actions."""

from __future__ import annotations

import json
import os
from pathlib import Path


ACTIVE_UPDATE_STATES = frozenset({"DOWNLOADING", "ACTIVATING"})


class UpdateSafety:
    def __init__(self, status_path: str = "/var/lib/clios/updater-status.json",
                 mountinfo_path: str = "/proc/self/mountinfo"):
        self.status_path = Path(status_path)
        self.mountinfo_path = Path(mountinfo_path)

    def state(self) -> str:
        try:
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "IDLE"
        return str(payload.get("state", "IDLE")) if isinstance(payload, dict) else "IDLE"

    def update_in_progress(self) -> bool:
        return self.state() in ACTIVE_UPDATE_STATES

    def path_is_overlay(self, path: str | os.PathLike[str]) -> bool:
        """Return whether the longest mount containing path is an OverlayFS."""
        try:
            lines = self.mountinfo_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        target = os.path.abspath(os.fspath(path))
        selected_mount = ""
        selected_type = ""
        for line in lines:
            fields = line.split()
            try:
                separator = fields.index("-")
                mount_point = fields[4].replace("\\040", " ")
                filesystem = fields[separator + 1]
            except (ValueError, IndexError):
                continue
            normalized = mount_point.rstrip("/") or "/"
            contains = normalized == "/" or target == normalized or target.startswith(normalized + "/")
            if contains and len(normalized) >= len(selected_mount):
                selected_mount = normalized
                selected_type = filesystem
        return selected_type == "overlay"
