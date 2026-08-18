import json
import os
import tempfile
import unittest

from src.storage import PersistentStorage


class PersistentStorageResilientTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_relocate_preserves_target_and_overlays_session_changes(self):
        volatile_path = os.path.join(self.temp_dir.name, "volatile", "save.json")
        storage = PersistentStorage(volatile_path)
        try:
            storage.set("trips.a.marker", 42.0)
            storage.flush()

            usb_path = os.path.join(self.temp_dir.name, "usb", "save.json")
            os.makedirs(os.path.dirname(usb_path))
            with open(usb_path, "w", encoding="utf-8") as stream:
                json.dump({"usb_only": {"kept": True}, "trips": {"a": {"marker": 3.0}}}, stream)

            self.assertTrue(storage.relocate(usb_path, merge_existing=True))
            self.assertEqual(storage.get("trips.a.marker"), 42.0)
            self.assertTrue(storage.get("usb_only.kept"))
        finally:
            storage.close()

    def test_failed_write_stays_dirty_and_does_not_raise(self):
        save_path = os.path.join(self.temp_dir.name, "save.json")
        storage = PersistentStorage(save_path)
        try:
            storage.set("settings.test", "pending")
            impossible_parent = os.path.join(self.temp_dir.name, "not_a_directory")
            with open(impossible_parent, "w", encoding="utf-8") as stream:
                stream.write("block")

            result = storage.relocate(os.path.join(impossible_parent, "save.json"), merge_existing=False)
            self.assertFalse(result)
            self.assertTrue(storage._dirty)
            self.assertEqual(storage.get("settings.test"), "pending")
        finally:
            # Retour sur une cible valide pour permettre le flush de fermeture.
            storage.relocate(save_path, merge_existing=False)
            storage.close()


if __name__ == "__main__":
    unittest.main()

