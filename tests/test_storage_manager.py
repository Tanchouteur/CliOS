import os
import tempfile
import unittest

from src.storage_manager import StorageManager, StorageMode


class StorageManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        self.media_root = os.path.join(self.root, "media", "clios")
        self.volatile_root = os.path.join(self.root, "volatile")
        os.makedirs(self.media_root)
        self.mounts = []
        self.manager = StorageManager(
            self.root,
            media_root=self.media_root,
            volatile_root=self.volatile_root,
            mount_provider=lambda: list(self.mounts),
        )

    def tearDown(self):
        self.manager.stop_monitoring()
        self.temp_dir.cleanup()

    def test_volatile_usb_and_unplug_transition(self):
        self.assertEqual(self.manager.mode, StorageMode.VOLATILE)
        volatile_trip = self.manager.resolve_path("trips/trip_pending.json")
        with open(volatile_trip, "w", encoding="utf-8") as stream:
            stream.write("{}")

        volume = os.path.join(self.media_root, "MY_USB")
        usb_root = os.path.join(volume, "clios")
        os.makedirs(usb_root)
        self.mounts.append(volume)
        transitions = []
        self.manager.register_callback(transitions.append)

        self.assertTrue(self.manager.refresh())
        self.assertEqual(self.manager.mode, StorageMode.USB)
        self.assertEqual(self.manager.get_writable_root(), os.path.realpath(usb_root))
        self.assertTrue(os.path.isfile(os.path.join(usb_root, "trips", "trip_pending.json")))
        self.assertEqual(transitions, [StorageMode.USB])

        self.mounts.clear()
        self.assertTrue(self.manager.refresh())
        self.assertEqual(self.manager.mode, StorageMode.VOLATILE)
        self.assertEqual(transitions[-1], StorageMode.VOLATILE)

    def test_path_traversal_is_rejected(self):
        for invalid in ("../secret", "/absolute", "trips/../../secret", ""):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    self.manager.resolve_path(invalid)

    def test_config_seed_does_not_overwrite_existing_file(self):
        static_dir = os.path.join(self.root, "static_config")
        os.makedirs(static_dir)
        source = os.path.join(static_dir, "profile.json")
        with open(source, "w", encoding="utf-8") as stream:
            stream.write("source")

        target_dir = self.manager.prepare_config_dir(static_dir)
        target = os.path.join(target_dir, "profile.json")
        with open(target, "w", encoding="utf-8") as stream:
            stream.write("runtime")
        self.manager.prepare_config_dir(static_dir)

        with open(target, "r", encoding="utf-8") as stream:
            self.assertEqual(stream.read(), "runtime")


if __name__ == "__main__":
    unittest.main()

