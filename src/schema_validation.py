"""Authoritative JSON Schema validation and cross-file CliOS v1 contracts."""

from __future__ import annotations

import json
import os
import re
import shutil
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas" / "v1"
SCHEMA_FILES = {
    "theme": "theme-manifest.schema.json",
    "vehicle": "vehicle-config.schema.json",
    "can": "can-dictionary.schema.json",
    "profiles": "profile-catalog.schema.json",
    "release": "release-manifest.schema.json",
}
JSON_NAME = re.compile(r"^(?!.*\.\.)[A-Za-z0-9][A-Za-z0-9_.-]*\.json$")


@lru_cache(maxsize=None)
def _validator(kind: str) -> Draft202012Validator:
    with open(SCHEMA_DIR / SCHEMA_FILES[kind], encoding="utf-8") as stream:
        schema = json.load(stream)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _error_path(error) -> str:
    parts = [str(part) for part in error.absolute_path]
    if error.validator == "required":
        match = re.search(r"'([^']+)' is a required property", error.message)
        if match:
            parts.append(match.group(1))
    return ".".join(parts) or "$"


def _schema_errors(kind: str, payload: object) -> list[str]:
    errors = sorted(_validator(kind).iter_errors(payload), key=lambda item: list(item.absolute_path))
    return [f"{_error_path(error)}: {error.message}" for error in errors]


def validate_theme_manifest(payload: object, folder_name: str | None = None,
                            theme_dir: str | Path | None = None) -> list[str]:
    errors = _schema_errors("theme", payload)
    if not isinstance(payload, dict):
        return errors
    if folder_name and payload.get("id") != folder_name:
        errors.append(f"id: doit correspondre au dossier '{folder_name}'")
    dashboard = payload.get("dashboard")
    if theme_dir is not None and isinstance(dashboard, str):
        root = Path(theme_dir).resolve()
        candidate = (root / dashboard).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append("dashboard: doit rester dans le dossier du thème")
        else:
            if not candidate.is_file():
                errors.append(f"dashboard: fichier introuvable ({dashboard})")
    return errors


def validate_vehicle_config(payload: object, available_themes: set[str] | None = None) -> list[str]:
    errors = _schema_errors("vehicle", payload)
    if not isinstance(payload, dict):
        return errors

    tachometer = payload.get("tachometer")
    if isinstance(tachometer, dict):
        maximum = tachometer.get("max_rpm")
        redline = tachometer.get("redline_rpm")
        if _greater(redline, maximum):
            errors.append("tachometer.redline_rpm: doit être inférieur ou égal à tachometer.max_rpm")

    temperature = payload.get("engine_temp")
    if isinstance(temperature, dict):
        ordered = [(name, temperature.get(name)) for name in ("min_display", "optimal", "warning", "max_display")]
        present = [(name, value) for name, value in ordered if _numbers(value)]
        for (left_name, left), (right_name, right) in zip(present, present[1:]):
            if _greater(left, right):
                errors.append(f"engine_temp.{right_name}: doit être supérieur ou égal à engine_temp.{left_name}")

    revision = payload.get("maintenance", {}).get("revision") if isinstance(payload.get("maintenance"), dict) else None
    if isinstance(revision, dict):
        interval = revision.get("interval_km")
        warning = revision.get("warning_threshold_km")
        if _greater(warning, interval):
            errors.append("maintenance.revision.warning_threshold_km: doit être inférieur ou égal à interval_km")

    consumption = payload.get("instant_fuel_consumption")
    if isinstance(consumption, dict):
        minimum, maximum = consumption.get("min_display"), consumption.get("max_display")
        if _greater(minimum, maximum):
            errors.append("instant_fuel_consumption.max_display: doit être supérieur ou égal à min_display")

    style = payload.get("ui", {}).get("visual_style") if isinstance(payload.get("ui"), dict) else None
    if available_themes is not None and isinstance(style, str) and style not in available_themes:
        errors.append(f"ui.visual_style: thème introuvable dans le catalogue ({style})")
    return errors


def validate_can_dictionary(payload: object) -> list[str]:
    errors = _schema_errors("can", payload)
    if not isinstance(payload, dict):
        return errors

    frame_count = 0
    for frame_id, frame in payload.items():
        if frame_id == "schema_version" or not isinstance(frame_id, str):
            continue
        frame_count += 1
        try:
            numeric_id = int(frame_id, 16)
        except ValueError:
            continue
        if not 0 <= numeric_id <= 0x1FFFFFFF:
            errors.append(f"{frame_id}: identifiant hors plage CAN (0x0–0x1FFFFFFF)")
        if not isinstance(frame, dict) or not isinstance(frame.get("signals"), dict):
            continue
        for signal_name, signal in frame["signals"].items():
            if not isinstance(signal, dict):
                continue
            prefix = f"{frame_id}.signals.{signal_name}"
            start, size = signal.get("start_byte"), signal.get("size", 1)
            if isinstance(start, int) and not isinstance(start, bool) and isinstance(size, int) and not isinstance(size, bool):
                if start + size > 8:
                    errors.append(f"{prefix}.size: le signal dépasse les 8 octets de la trame")
                width = size * 8
                shift = signal.get("shift")
                if isinstance(shift, int) and not isinstance(shift, bool) and shift >= width:
                    errors.append(f"{prefix}.shift: doit être inférieur à la largeur du signal ({width})")
                mask = signal.get("mask")
                try:
                    mask_value = int(mask, 16) if isinstance(mask, str) else mask
                    if isinstance(mask_value, int) and not isinstance(mask_value, bool) and mask_value >= (1 << width):
                        errors.append(f"{prefix}.mask: dépasse la largeur du signal ({width} bits)")
                except ValueError:
                    pass
                bits = signal.get("bits")
                if isinstance(bits, dict):
                    positions = [value for value in bits.values() if isinstance(value, int) and not isinstance(value, bool)]
                    if len(positions) != len(set(positions)):
                        errors.append(f"{prefix}.bits: positions de bits dupliquées")
                    for bit_name, position in bits.items():
                        if isinstance(position, int) and not isinstance(position, bool) and position >= width:
                            errors.append(f"{prefix}.bits.{bit_name}: doit être inférieur à {width}")
    if frame_count == 0:
        errors.append("$: aucune trame CAN déclarée")
    return errors


def validate_profile_catalog(payload: object) -> list[str]:
    errors = _schema_errors("profiles", payload)
    if not isinstance(payload, dict):
        return errors
    profiles = payload.get("profiles")
    active = payload.get("active_profile")
    if isinstance(profiles, dict) and active not in profiles:
        errors.append(f"active_profile: profil introuvable ({active})")
    return errors


def validate_profile_references(payload: object, config_dir: str | Path, can_dir: str | Path,
                                styles_dir: str | Path) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), dict):
        return []
    errors = []
    config_root, can_root, style_root = Path(config_dir), Path(can_dir), Path(styles_dir)
    available_themes = {
        path.parent.name for path in style_root.glob("*/style.json")
        if not validate_theme_manifest(load_json(path), path.parent.name, path.parent)
    }
    for profile_id, profile in payload["profiles"].items():
        if not isinstance(profile, dict):
            continue
        for key, root in (("config_file", config_root), ("can_file", can_root)):
            filename = profile.get(key)
            if isinstance(filename, str) and JSON_NAME.fullmatch(filename) and not (root / filename).is_file():
                errors.append(f"profiles.{profile_id}.{key}: fichier introuvable ({filename})")
        config_name = profile.get("config_file")
        if isinstance(config_name, str) and JSON_NAME.fullmatch(config_name) and (config_root / config_name).is_file():
            try:
                config = load_json(config_root / config_name)
                errors.extend(f"profiles.{profile_id}.{error}" for error in validate_vehicle_config(config, available_themes))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"profiles.{profile_id}.config_file: {exc}")
        can_name = profile.get("can_file")
        if isinstance(can_name, str) and JSON_NAME.fullmatch(can_name) and (can_root / can_name).is_file():
            try:
                errors.extend(f"profiles.{profile_id}.{error}" for error in validate_can_dictionary(load_json(can_root / can_name)))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"profiles.{profile_id}.can_file: {exc}")
    return errors


def _numbers(*values) -> bool:
    return all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values)


def _greater(left, right) -> bool:
    return _numbers(left, right) and float(left) > float(right)


def load_json(path: str | Path) -> object:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def migrate_to_v1(path: str | Path, payload: dict) -> dict:
    """Additive v0 -> v1 migration with a recoverable backup."""
    if payload.get("schema_version") == 1:
        return payload
    target = Path(path)
    backup = target.with_suffix(target.suffix + ".v0.bak")
    if target.exists() and not backup.exists():
        shutil.copy2(target, backup)
    migrated = dict(payload)
    migrated["schema_version"] = 1
    if "dashboard" in migrated and "profiles" not in migrated:
        dashboard = migrated.get("dashboard", {})
        migrated.setdefault("theme", {"main": "#48B8FF"})
        migrated.setdefault("ui", {"visual_style": "gt_modern"})
        migrated.setdefault("tachometer", {"max_rpm": dashboard.get("max_rpm", 7000), "redline_rpm": dashboard.get("redline", 6500)})
        migrated.setdefault("speedometer", {"max_speed": dashboard.get("max_speed", 220)})
        migrated.setdefault("fuel", {"max_liters": 50, "reserve_percentage": 0.15})
        migrated.setdefault("engine_temp", {"warning": 105, "max_display": 120})
        migrated.setdefault("transmission", {"type": "manual", "gears_count": 5, "ratios": {}})
        migrated.setdefault("maintenance", {"revision": {"interval_km": 20000, "warning_threshold_km": 2000}})
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as stream:
        json.dump(migrated, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, target)
    return migrated
