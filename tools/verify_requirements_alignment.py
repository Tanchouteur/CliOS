#!/usr/bin/env python3
"""Ensure direct requirements remain compatible with both qualified ARM64 locks."""

from __future__ import annotations

import re
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version


ROOT = Path(__file__).resolve().parent.parent


def direct_requirements() -> list[Requirement]:
    result = []
    for raw in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            result.append(Requirement(line))
    return result


def locked_versions(path: Path) -> dict[str, Version]:
    versions = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)==([^ \\]+)", line)
        if match:
            versions[canonicalize_name(match.group(1))] = Version(match.group(2))
    return versions


def verify() -> list[str]:
    errors = []
    for target, python_version in (("bookworm-arm64", "3.11"), ("trixie-arm64", "3.13")):
        locked = locked_versions(ROOT / f"requirements-{target}.lock")
        environment = default_environment()
        environment.update({"python_version": python_version, "python_full_version": python_version + ".0", "sys_platform": "linux"})
        for requirement in direct_requirements():
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            name = canonicalize_name(requirement.name)
            version = locked.get(name)
            if version is None:
                errors.append(f"{target}: dépendance directe absente du lock: {requirement.name}")
            elif requirement.specifier and version not in requirement.specifier:
                errors.append(f"{target}: {requirement} exclut la version verrouillée {version}")
    return errors


def main() -> int:
    errors = verify()
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
