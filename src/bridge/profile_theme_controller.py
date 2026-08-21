"""Profiles, themes and persisted dashboard settings for the QML facade."""

from __future__ import annotations

import json
import os


class ProfileThemeController:
    def __init__(self, target):
        self.target = target

    def available_ui_styles(self) -> list[dict]:
        target = self.target
        required_colors = {
            "background", "surface", "surfaceRaised", "surfaceSoft",
            "text", "textSecondary", "outline", "gaugeTrack",
        }
        styles: list[dict] = []
        diagnostics: list[str] = []
        official_ids: set[str] = set()
        developer_enabled = bool(target._config.get("developer", {}).get("enabled", False))
        roots = [(target._ui_styles_dir, "styles", False)]
        if developer_enabled:
            roots.append((target._dev_styles_dir, "dev_styles", True))

        for styles_root, qml_prefix, is_local in roots:
            try:
                entries = sorted(os.scandir(styles_root), key=lambda entry: entry.name)
            except OSError as exc:
                if not is_local:
                    diagnostics.append(f"Catalogue officiel illisible: {exc}")
                continue
            for entry in entries:
                if not entry.is_dir() or entry.name.startswith("_") or not entry.name.replace("_", "").isalnum():
                    continue
                manifest_path = os.path.join(entry.path, "style.json")
                try:
                    with open(manifest_path, encoding="utf-8") as manifest_file:
                        manifest = json.load(manifest_file)
                    style_id = str(manifest.get("id", ""))
                    dashboard_file = os.path.basename(str(manifest.get("dashboard", "Dashboard.qml")))
                    palette = manifest.get("palette", {})
                    problems: list[str] = []
                    if style_id != entry.name:
                        problems.append("id différent du dossier")
                    if manifest.get("apiVersion") != 1:
                        problems.append("apiVersion doit valoir 1")
                    try:
                        minimum = tuple(int(part) for part in str(manifest.get("minCliOSVersion", "")).split("."))
                        if len(minimum) != 3 or minimum > target._clios_version:
                            problems.append(f"requiert CliOS {manifest.get('minCliOSVersion')}")
                    except ValueError:
                        problems.append("minCliOSVersion invalide")
                    if "1920x720" not in manifest.get("supportedResolutions", []):
                        problems.append("résolution 1920x720 non déclarée")
                    if not isinstance(manifest.get("capabilities"), list):
                        problems.append("capabilities manquant")
                    if not dashboard_file.endswith(".qml") or not os.path.isfile(os.path.join(entry.path, dashboard_file)):
                        problems.append("dashboard QML manquant")
                    if not isinstance(palette, dict) or not required_colors.issubset(palette):
                        problems.append("palette incomplète")
                    if is_local and style_id in official_ids:
                        problems.append("un thème local ne peut pas remplacer un thème officiel")
                    if problems:
                        diagnostics.append(f"{entry.name}: " + "; ".join(problems))
                        continue
                except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                    diagnostics.append(f"{entry.name}: manifeste invalide ({exc})")
                    continue

                if not is_local:
                    official_ids.add(style_id)
                styles.append({
                    "id": style_id,
                    "label": str(manifest.get("label", style_id)),
                    "description": str(manifest.get("description", "")),
                    "order": int(manifest.get("order", 100)),
                    "dashboard": f"{qml_prefix}/{style_id}/{dashboard_file}",
                    "palette": {key: str(palette[key]) for key in required_colors},
                    "metrics": target._sanitize_for_qml(manifest.get("metrics", {})),
                    "apiVersion": 1,
                    "capabilities": target._sanitize_for_qml(manifest.get("capabilities", [])),
                    "local": is_local,
                    "trustedCodeWarning": "Code QML local de confiance, non sandboxé" if is_local else "",
                })

        target._theme_diagnostics = diagnostics
        for message in diagnostics:
            target.logger.error(message, extra={"error_code": "UI_THEME_INVALID"})
        styles.sort(key=lambda item: (item["order"], item["label"].lower()))
        return styles

    def save_setting(self, key_path: str, value: str) -> None:
        target = self.target
        if key_path == "theme.main" and target.led_service:
            target.led_service.set_color(value)
        keys = key_path.split(".")
        with target._config_lock:
            current = target._config
            for key in keys[:-1]:
                current = current.setdefault(key, {})
            current[keys[-1]] = value
        target.configChanged.emit()
        target._config_write_requested.set()

    def available_profiles(self) -> list:
        manager = self.target.profile_manager
        return manager.get_available_profiles() if manager else []

    def active_profile(self) -> str:
        manager = self.target.profile_manager
        return manager.active_profile_id if manager else ""

    def available_can_files(self) -> list:
        manager = self.target.profile_manager
        return manager.get_available_can_files() if manager else []

    def available_config_files(self) -> list:
        manager = self.target.profile_manager
        return manager.get_available_config_files() if manager else []

    def create_profile(self, profile_id: str, name: str, can_file: str, config_file: str, save_file: str) -> bool:
        manager = self.target.profile_manager
        if not manager:
            return False
        manager.create_new_config(config_file)
        if not manager.add_profile(profile_id, name, can_file, config_file, save_file):
            return False
        self.target.logger.info("Nouveau profil cree: %s", profile_id, extra={"error_code": "PROFILE_CREATED"})
        return True

    def set_active_profile(self, profile_id: str) -> bool:
        manager = self.target.profile_manager
        if not manager:
            return False
        success = manager.set_active_profile(profile_id)
        if success:
            self.target.logger.info(
                "Changement profil programme: %s", profile_id,
                extra={"error_code": "PROFILE_CHANGED"},
            )
            self.target.send_notification(
                "info", f"Profil '{profile_id}' sélectionné. Veuillez redémarrer l'application.", 4000,
            )
        return success
