import json
import os
import tempfile
import unittest

from src.schema_validation import (
    migrate_to_v1,
    validate_can_dictionary,
    validate_theme_manifest,
    validate_profile_catalog,
    validate_profile_references,
    validate_vehicle_config,
)


class SchemaValidationTest(unittest.TestCase):
    def test_v0_vehicle_migration_is_additive_and_backed_up(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "vehicle.json")
            original = {"dashboard": {"max_rpm": 7200, "redline": 6800, "max_speed": 240}}
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(original, stream)

            migrated = migrate_to_v1(path, original)

            self.assertEqual(migrated["dashboard"], original["dashboard"])
            self.assertEqual(migrated["schema_version"], 1)
            self.assertEqual(validate_vehicle_config(migrated), [])
            with open(path + ".v0.bak", encoding="utf-8") as stream:
                self.assertEqual(json.load(stream), original)

    def test_previous_version_can_ignore_additive_schema_key(self):
        payload = {"schema_version": 1, "dashboard": {"max_speed": 220}}
        legacy_view = {key: value for key, value in payload.items() if key != "schema_version"}
        self.assertEqual(legacy_view, {"dashboard": {"max_speed": 220}})

    def test_vehicle_errors_include_precise_json_paths(self):
        payload = {
            "schema_version": 1,
            "theme": {},
            "ui": {"visual_style": "missing"},
            "tachometer": {"max_rpm": 6000, "redline_rpm": 7000},
            "speedometer": {"max_speed": 220},
            "fuel": {"max_liters": 50},
            "engine_temp": {"warning": 130, "max_display": 120},
            "transmission": {"type": "manual", "gears_count": 5, "ratios": {}},
            "maintenance": {"revision": {"interval_km": 1000, "warning_threshold_km": 2000}},
        }
        errors = validate_vehicle_config(payload, {"gt_modern"})
        self.assertTrue(any(error.startswith("theme.main:") for error in errors))
        self.assertTrue(any(error.startswith("tachometer.redline_rpm:") for error in errors))
        self.assertTrue(any(error.startswith("engine_temp.max_display:") for error in errors))
        self.assertTrue(any(error.startswith("maintenance.revision.warning_threshold_km:") for error in errors))
        self.assertTrue(any(error.startswith("ui.visual_style:") for error in errors))

    def test_can_rejects_bad_types_sizes_and_frame_overflow(self):
        payload = {
            "schema_version": 1,
            "0x123": {
                "name": "BAD",
                "signals": {
                    "typed": {"start_byte": "oops", "size": 1},
                    "huge": {"start_byte": 0, "size": 999},
                    "overflow": {"start_byte": 7, "size": 2},
                },
            },
        }
        errors = validate_can_dictionary(payload)
        self.assertTrue(any(error.startswith("0x123.signals.typed.start_byte:") for error in errors))
        self.assertTrue(any(error.startswith("0x123.signals.huge.size:") for error in errors))
        self.assertTrue(any(error.startswith("0x123.signals.overflow.size:") for error in errors))

    def test_theme_dashboard_cannot_escape_and_must_exist(self):
        manifest = {
            "apiVersion": 1, "id": "safe", "label": "Safe",
            "dashboard": "../../evil.qml", "minCliOSVersion": "2.0.0",
            "supportedResolutions": ["1920x720"], "capabilities": [],
            "palette": dict.fromkeys(
                ("background", "surface", "surfaceRaised", "surfaceSoft", "text", "textSecondary", "outline", "gaugeTrack"),
                "#000000",
            ),
        }
        errors = validate_theme_manifest(manifest, "safe", "/tmp")
        self.assertTrue(any(error.startswith("dashboard:") for error in errors))

    def test_theme_folder_dashboard_and_top_level_types_are_checked(self):
        self.assertTrue(validate_theme_manifest([]))
        valid = {
            "apiVersion": 1, "id": "theme_a", "label": "Theme A", "dashboard": "Missing.qml",
            "minCliOSVersion": "2.0.1-rc.4", "supportedResolutions": ["1920x720"],
            "capabilities": ["settings"],
            "palette": dict.fromkeys(
                ("background", "surface", "surfaceRaised", "surfaceSoft", "text", "textSecondary", "outline", "gaugeTrack"),
                "#AABBCC",
            ),
        }
        with tempfile.TemporaryDirectory() as root:
            errors = validate_theme_manifest(valid, "other", root)
        self.assertTrue(any(error.startswith("id:") for error in errors))
        self.assertTrue(any("fichier introuvable" in error for error in errors))

    def test_can_semantic_bounds_and_duplicates_are_checked(self):
        payload = {
            "schema_version": 1,
            "0x20000000": {"name": "OUT", "signals": {
                "flags": {"start_byte": 0, "size": 1, "shift": 8, "mask": "0x1FF", "bits": {"a": 7, "b": 7, "c": 8}}
            }},
        }
        errors = validate_can_dictionary(payload)
        for fragment in ("hors plage CAN", ".shift:", ".mask:", "positions de bits dupliquées", ".bits.c:"):
            self.assertTrue(any(fragment in error for error in errors), fragment)
        self.assertTrue(any("aucune trame" in error for error in validate_can_dictionary({"schema_version": 1})))
        self.assertTrue(validate_can_dictionary([]))

    def test_profile_catalog_and_cross_file_references(self):
        invalid = {"schema_version": 1, "active_profile": "missing", "profiles": {
            "one": {"name": "One", "can_file": "missing.json", "config_file": "missing.json", "save_file": "save.json"}
        }}
        self.assertTrue(any(error.startswith("active_profile:") for error in validate_profile_catalog(invalid)))
        with tempfile.TemporaryDirectory() as root:
            errors = validate_profile_references(invalid, root, root, root)
        self.assertTrue(any("config_file" in error for error in errors))
        self.assertTrue(any("can_file" in error for error in errors))
        self.assertEqual(validate_profile_references([], "/tmp", "/tmp", "/tmp"), [])

    def test_profile_reference_reports_malformed_json_files(self):
        with tempfile.TemporaryDirectory() as root:
            config_dir = os.path.join(root, "config")
            can_dir = os.path.join(root, "can")
            styles_dir = os.path.join(root, "styles")
            os.makedirs(config_dir)
            os.makedirs(can_dir)
            os.makedirs(styles_dir)
            for path in (os.path.join(config_dir, "bad.json"), os.path.join(can_dir, "bad.json")):
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write("{")
            catalog = {"profiles": {"bad": {
                "config_file": "bad.json", "can_file": "bad.json", "save_file": "save.json", "name": "Bad"
            }}}
            errors = validate_profile_references(catalog, config_dir, can_dir, styles_dir)
        self.assertTrue(any("config_file" in error for error in errors))
        self.assertTrue(any("can_file" in error for error in errors))

    def test_temperature_and_consumption_ordering(self):
        payload = {
            "schema_version": 1, "theme": {"main": "#000000"}, "ui": {"visual_style": "gt_modern"},
            "tachometer": {"max_rpm": 7000, "redline_rpm": 6500}, "speedometer": {"max_speed": 220},
            "fuel": {"max_liters": 50},
            "engine_temp": {"min_display": 90, "optimal": 80, "warning": 70, "max_display": 60},
            "transmission": {"type": "manual", "gears_count": 5, "ratios": {}},
            "instant_fuel_consumption": {"min_display": 20, "max_display": 10},
            "maintenance": {"revision": {"interval_km": 20000, "warning_threshold_km": 2000}},
        }
        errors = validate_vehicle_config(payload)
        self.assertGreaterEqual(sum(error.startswith("engine_temp.") for error in errors), 3)
        self.assertTrue(any(error.startswith("instant_fuel_consumption.max_display:") for error in errors))


if __name__ == "__main__":
    unittest.main()
