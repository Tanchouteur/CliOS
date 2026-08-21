#!/usr/bin/env python3
"""Valide les thèmes et données communautaires CliOS v1."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.schema_validation import (  # noqa: E402
    validate_can_dictionary,
    validate_profile_catalog,
    validate_theme_manifest,
    validate_vehicle_config,
)


def validate(path: Path, kind: str) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [str(exc)]
    if kind == "theme":
        return validate_theme_manifest(payload, path.parent.name)
    if kind == "vehicle":
        return validate_vehicle_config(payload)
    if kind == "can":
        return validate_can_dictionary(payload)
    return validate_profile_catalog(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="valider toutes les données officielles")
    parser.add_argument("--theme", type=Path)
    parser.add_argument("--vehicle", type=Path)
    parser.add_argument("--can", dest="can_path", type=Path)
    parser.add_argument("--profiles", type=Path)
    args = parser.parse_args()
    jobs = []
    if args.all:
        jobs.extend((path, "theme") for path in sorted((ROOT / "frontend/styles").glob("*/style.json")) if path.parent.name != "_template")
        jobs.extend((path, "vehicle") for path in sorted((ROOT / "data/config").glob("*.json")) if path.name != "profiles.json")
        jobs.extend((path, "can") for path in sorted((ROOT / "data/can").glob("*.json")))
        jobs.append((ROOT / "data/config/profiles.json", "profiles"))
    for path, kind in ((args.theme, "theme"), (args.vehicle, "vehicle"), (args.can_path, "can"), (args.profiles, "profiles")):
        if path:
            jobs.append((path, kind))
    if not jobs:
        parser.error("utilisez --all ou indiquez un fichier")
    failed = False
    for path, kind in jobs:
        errors = validate(path, kind)
        if errors:
            failed = True
            print(f"ERREUR {path}: " + " | ".join(errors))
        else:
            print(f"OK {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
