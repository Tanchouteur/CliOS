"""Plateformes Raspberry Pi OS prises en charge par les releases ARM64."""

from __future__ import annotations

import platform as host_platform
from dataclasses import dataclass
from pathlib import Path


class ReleasePlatformError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleasePlatform:
    identifier: str
    target: str
    codename: str
    python_minor: str


SUPPORTED_PLATFORMS = {
    "raspberry-pi-os-bookworm-arm64": ReleasePlatform(
        "raspberry-pi-os-bookworm-arm64", "bookworm-arm64", "bookworm", "3.11",
    ),
    "raspberry-pi-os-trixie-arm64": ReleasePlatform(
        "raspberry-pi-os-trixie-arm64", "trixie-arm64", "trixie", "3.13",
    ),
}
PLATFORMS_BY_TARGET = {value.target: value for value in SUPPORTED_PLATFORMS.values()}
PLATFORMS_BY_CODENAME = {value.codename: value for value in SUPPORTED_PLATFORMS.values()}


def get_release_platform(identifier: str) -> ReleasePlatform:
    try:
        return SUPPORTED_PLATFORMS[identifier]
    except KeyError as exc:
        raise ReleasePlatformError(f"plateforme de release non prise en charge: {identifier}") from exc


def get_target_platform(target: str) -> ReleasePlatform:
    try:
        return PLATFORMS_BY_TARGET[target]
    except KeyError as exc:
        raise ReleasePlatformError(f"cible de release non prise en charge: {target}") from exc


def detect_release_platform(
    os_release_path: str | Path = "/etc/os-release",
    *,
    machine: str | None = None,
) -> ReleasePlatform:
    architecture = (machine or host_platform.machine()).lower()
    if architecture not in {"aarch64", "arm64"}:
        raise ReleasePlatformError(f"architecture non prise en charge: {architecture or 'inconnue'}")
    values: dict[str, str] = {}
    try:
        for line in Path(os_release_path).read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value.strip().strip("\"'")
    except OSError as exc:
        raise ReleasePlatformError(f"/etc/os-release illisible: {exc}") from exc
    codename = values.get("VERSION_CODENAME", "").lower()
    try:
        return PLATFORMS_BY_CODENAME[codename]
    except KeyError as exc:
        raise ReleasePlatformError(
            f"distribution non prise en charge: {codename or values.get('PRETTY_NAME', 'inconnue')}"
        ) from exc
