import json
import os
import tempfile
import unittest

from src.schema_validation import migrate_to_v1, validate_vehicle_config


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


if __name__ == "__main__":
    unittest.main()
