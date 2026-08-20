"""Validation légère des contrats communautaires CliOS v1, sans dépendance runtime."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path


JSON_NAME = re.compile(r"^[^/\\]+\.json$")
STYLE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


def _missing(payload: dict, required: tuple[str, ...]) -> list[str]:
    return [f"champ requis manquant: {key}" for key in required if key not in payload]


def validate_theme_manifest(payload: object, folder_name: str | None = None) -> list[str]:
    if not isinstance(payload, dict):
        return ["le manifeste doit être un objet JSON"]
    errors = _missing(payload, ("apiVersion", "id", "label", "dashboard", "minCliOSVersion", "supportedResolutions", "capabilities", "palette"))
    if payload.get("apiVersion") != 1:
        errors.append("apiVersion doit valoir 1")
    style_id = payload.get("id")
    if not isinstance(style_id, str) or not STYLE_ID.fullmatch(style_id):
        errors.append("id de thème invalide")
    if folder_name and style_id != folder_name:
        errors.append("id différent du dossier")
    if "1920x720" not in (payload.get("supportedResolutions") or []):
        errors.append("1920x720 doit être supporté")
    if not isinstance(payload.get("capabilities"), list):
        errors.append("capabilities doit être une liste")
    palette = payload.get("palette")
    colors = {"background", "surface", "surfaceRaised", "surfaceSoft", "text", "textSecondary", "outline", "gaugeTrack"}
    if not isinstance(palette, dict) or not colors.issubset(palette):
        errors.append("palette incomplète")
    return errors


def validate_vehicle_config(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["la configuration véhicule doit être un objet JSON"]
    errors = _missing(payload, ("schema_version", "theme", "ui", "tachometer", "speedometer", "fuel", "engine_temp", "transmission", "maintenance"))
    if payload.get("schema_version") != 1:
        errors.append("schema_version doit valoir 1")
    for section in ("theme", "ui", "tachometer", "speedometer", "fuel", "engine_temp", "transmission", "maintenance"):
        if section in payload and not isinstance(payload[section], dict):
            errors.append(f"{section} doit être un objet")
    return errors


def validate_can_dictionary(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["le dictionnaire CAN doit être un objet JSON"]
    errors = []
    if payload.get("schema_version") != 1:
        errors.append("schema_version doit valoir 1")
    frames = 0
    for frame_id, frame in payload.items():
        if frame_id == "schema_version":
            continue
        frames += 1
        try:
            int(frame_id, 16)
        except (TypeError, ValueError):
            errors.append(f"identifiant CAN invalide: {frame_id}")
            continue
        if not isinstance(frame, dict) or not isinstance(frame.get("signals"), dict) or not frame["signals"]:
            errors.append(f"{frame_id}: signals manquant ou vide")
    if not frames:
        errors.append("aucune trame CAN déclarée")
    return errors


def validate_profile_catalog(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["le catalogue de profils doit être un objet JSON"]
    errors = _missing(payload, ("schema_version", "active_profile", "profiles"))
    if payload.get("schema_version") != 1:
        errors.append("schema_version doit valoir 1")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append("profiles doit contenir au moins un profil")
        return errors
    active = payload.get("active_profile")
    if active not in profiles:
        errors.append(f"profil actif introuvable: {active}")
    for profile_id, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"{profile_id}: profil invalide")
            continue
        for key in ("name", "can_file", "config_file", "save_file"):
            value = profile.get(key)
            if not isinstance(value, str) or not value:
                errors.append(f"{profile_id}: {key} manquant")
            elif key.endswith("_file") and not JSON_NAME.fullmatch(value):
                errors.append(f"{profile_id}: {key} doit être un nom JSON simple")
    return errors


def load_json(path: str | Path) -> object:
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def migrate_to_v1(path: str | Path, payload: dict) -> dict:
    """Migration additive v0 -> v1 avec sauvegarde préalable."""
    if payload.get("schema_version") == 1:
        return payload
    target = Path(path)
    backup = target.with_suffix(target.suffix + ".v0.bak")
    if target.exists() and not backup.exists():
        shutil.copy2(target, backup)
    migrated = dict(payload)
    migrated["schema_version"] = 1
    # Ancien générateur de profil (<=1.x) : conserve les clés historiques tout
    # en ajoutant les sections v1 pour permettre un retour à N-1.
    if "dashboard" in migrated and "profiles" not in migrated:
        dashboard = migrated.get("dashboard", {})
        migrated.setdefault("theme", {"main": "#48B8FF"})
        migrated.setdefault("ui", {"visual_style": "gt_modern"})
        migrated.setdefault("tachometer", {
            "max_rpm": dashboard.get("max_rpm", 7000),
            "redline_rpm": dashboard.get("redline", 6500),
        })
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
