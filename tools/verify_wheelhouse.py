#!/usr/bin/env python3
"""Vérifie qu'un wheelhouse couvre entièrement un lock ARM64."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def canonical(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def locked_names(path: Path) -> set[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "--")):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)==", stripped)
        if match:
            names.add(canonical(match.group(1)))
    return names


def wheel_names(directory: Path) -> set[str]:
    return {canonical(path.name.split("-", 1)[0]) for path in directory.glob("*.whl")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("lock", type=Path)
    parser.add_argument("wheelhouse", type=Path)
    args = parser.parse_args()
    locked = locked_names(args.lock)
    wheels = wheel_names(args.wheelhouse)
    missing = sorted(locked - wheels)
    if missing:
        raise SystemExit("wheels absentes: " + ", ".join(missing))
    extra = sorted(wheels - locked)
    if extra:
        raise SystemExit("wheels non verrouillées: " + ", ".join(extra))
    print(f"wheelhouse complet: {len(wheels)} wheels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
