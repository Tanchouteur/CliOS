"""Contrats de version et de manifeste pour les releases CliOS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering
from urllib.parse import urlparse

from src.release_platform import SUPPORTED_PLATFORMS


class ReleaseContractError(ValueError):
    """Une version ou un manifeste ne respecte pas le contrat public."""


_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@total_ordering
@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        match = _SEMVER_RE.fullmatch(str(value).strip())
        if not match:
            raise ReleaseContractError(f"version SemVer invalide: {value}")
        prerelease = tuple((match.group(4) or "").split(".")) if match.group(4) else ()
        for identifier in prerelease:
            if identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0"):
                raise ReleaseContractError(f"version SemVer invalide: {value}")
        build = tuple((match.group(5) or "").split(".")) if match.group(5) else ()
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)), prerelease, build)

    @property
    def channel(self) -> str:
        return "beta" if self.prerelease else "stable"

    def __str__(self) -> str:
        value = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            value += "-" + ".".join(self.prerelease)
        if self.build:
            value += "+" + ".".join(self.build)
        return value

    def _precedence(self) -> tuple:
        # Les métadonnées de build ne participent pas à l'ordre SemVer.
        if not self.prerelease:
            pre = ((2, ""),)
        else:
            pre = tuple((0, int(item)) if item.isdigit() else (1, item) for item in self.prerelease)
        return self.major, self.minor, self.patch, bool(not self.prerelease), pre

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        if not self.prerelease:
            return False
        if not other.prerelease:
            return True
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            if left.isdigit() and right.isdigit():
                return int(left) < int(right)
            if left.isdigit() != right.isdigit():
                return left.isdigit()
            return left < right
        return len(self.prerelease) < len(other.prerelease)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return False
        return (
            self.major, self.minor, self.patch, self.prerelease
        ) == (
            other.major, other.minor, other.patch, other.prerelease
        )


def channel_for_version(version: str) -> str:
    return SemVer.parse(version).channel


def validate_manifest(manifest: object, *, require_https: bool = True) -> dict:
    """Valide et normalise un manifeste v1 sans conserver de champs ambigus."""
    if not isinstance(manifest, dict):
        raise ReleaseContractError("le manifeste doit être un objet JSON")
    required = {"schema_version", "version", "channel", "platform", "archive_url", "archive_sha256", "files"}
    extra = sorted(set(manifest) - required)
    if extra:
        raise ReleaseContractError("champs de manifeste interdits: " + ", ".join(extra))
    missing = sorted(required - manifest.keys())
    if missing:
        raise ReleaseContractError("manifeste incomplet: " + ", ".join(missing))
    if manifest["schema_version"] != 1:
        raise ReleaseContractError("version de schéma de release non prise en charge")
    version = str(manifest["version"])
    expected_channel = channel_for_version(version)
    channel = str(manifest["channel"])
    if channel != expected_channel:
        raise ReleaseContractError(
            f"canal {channel!r} contradictoire avec la version {version} ({expected_channel})"
        )
    if manifest["platform"] not in SUPPORTED_PLATFORMS:
        raise ReleaseContractError("plateforme de release non prise en charge")
    archive_url = str(manifest["archive_url"])
    parsed = urlparse(archive_url)
    if require_https and parsed.scheme != "https":
        raise ReleaseContractError("l'archive doit utiliser HTTPS")
    digest = str(manifest["archive_sha256"]).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ReleaseContractError("SHA-256 de l'archive invalide")
    raw_files = manifest["files"]
    if not isinstance(raw_files, dict) or not raw_files:
        raise ReleaseContractError("liste de fichiers vide ou invalide")
    files: dict[str, str] = {}
    for raw_path, raw_digest in raw_files.items():
        path = str(raw_path)
        if not path or path.startswith("/") or ".." in path.split("/") or "\\" in path:
            raise ReleaseContractError(f"chemin manifesté non sûr: {path}")
        file_digest = str(raw_digest).lower()
        if not re.fullmatch(r"[0-9a-f]{64}", file_digest):
            raise ReleaseContractError(f"SHA-256 invalide: {path}")
        files[path] = file_digest
    return {
        "schema_version": 1,
        "version": version,
        "channel": channel,
        "platform": manifest["platform"],
        "archive_url": archive_url,
        "archive_sha256": digest,
        "files": files,
    }
