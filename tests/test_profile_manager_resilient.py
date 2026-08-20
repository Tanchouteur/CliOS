import json
import os
import tempfile
import unittest

from src.profile_manager import ProfileManager


class ProfileManagerResilientTest(unittest.TestCase):
    def test_corrupted_dynamic_config_is_repaired_from_static_copy(self):
        with tempfile.TemporaryDirectory() as root:
            dynamic = os.path.join(root, "dynamic")
            static = os.path.join(root, "static")
            can_dir = os.path.join(root, "can")
            saves = os.path.join(root, "saves")
            for directory in (dynamic, static, can_dir, saves):
                os.makedirs(directory)

            profiles = {
                "active_profile": "default",
                "profiles": {
                    "default": {
                        "name": "Default",
                        "can_file": "default_can.json",
                        "config_file": "default_config.json",
                        "save_file": "save.json",
                    }
                },
            }
            with open(os.path.join(dynamic, "profiles.json"), "w", encoding="utf-8") as stream:
                json.dump(profiles, stream)
            with open(os.path.join(static, "default_config.json"), "w", encoding="utf-8") as stream:
                json.dump({"dashboard": {"max_speed": 220}}, stream)
            with open(os.path.join(dynamic, "default_config.json"), "w", encoding="utf-8") as stream:
                stream.write("{broken")

            manager = ProfileManager(
                dynamic,
                can_dir,
                saves,
                is_mock=True,
                fallback_config_dir=static,
            )
            config = manager.load_active_config()
            self.assertEqual(config["dashboard"]["max_speed"], 220)
            with open(manager.get_config_path(), "r", encoding="utf-8") as stream:
                self.assertEqual(json.load(stream), config)

    def test_profile_paths_cannot_escape_managed_directories(self):
        with tempfile.TemporaryDirectory() as root:
            config_dir = os.path.join(root, "config")
            can_dir = os.path.join(root, "can")
            saves = os.path.join(root, "saves")
            for directory in (config_dir, can_dir, saves):
                os.makedirs(directory)
            manager = ProfileManager(config_dir, can_dir, saves, is_mock=True)
            manager.is_mock = False
            manager.data["profiles"]["default"]["config_file"] = "../../outside.json"
            manager.data["profiles"]["default"]["save_file"] = "../../outside.json"

            self.assertEqual(manager.get_config_path(), os.path.join(config_dir, "default_config.json"))
            self.assertEqual(manager.get_save_path(), os.path.join(saves, "save.json"))

    def test_invalid_active_profile_enters_recovery_without_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            config_dir = os.path.join(root, "config")
            can_dir = os.path.join(root, "can")
            saves = os.path.join(root, "saves")
            for directory in (config_dir, can_dir, saves):
                os.makedirs(directory)
            with open(os.path.join(config_dir, "profiles.json"), "w", encoding="utf-8") as stream:
                json.dump({"schema_version": 1, "active_profile": "missing", "profiles": {
                    "valid": {"name": "Valid", "can_file": "valid.json", "config_file": "valid.json", "save_file": "save.json"}
                }}, stream)

            manager = ProfileManager(config_dir, can_dir, saves, is_mock=True)

            self.assertTrue(manager.recovery_mode)
            self.assertEqual(manager.active_profile_id, "missing")
            self.assertIn("introuvable", manager.error_message)


if __name__ == "__main__":
    unittest.main()
