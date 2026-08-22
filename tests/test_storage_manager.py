import json
import os
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

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
            mount_table_provider=lambda: "overlay / overlay rw 0 0",
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
        shutil.rmtree(volume)
        self.assertTrue(self.manager.refresh())
        self.assertEqual(self.manager.mode, StorageMode.VOLATILE)
        self.assertEqual(transitions[-1], StorageMode.VOLATILE)

    def test_direct_media_root_mount_is_detected(self):
        usb_root = os.path.join(self.media_root, "clios")
        os.makedirs(usb_root)
        self.mounts.append(self.media_root)

        self.assertTrue(self.manager.refresh())
        self.assertEqual(self.manager.mode, StorageMode.USB)
        self.assertEqual(self.manager.get_writable_root(), os.path.realpath(usb_root))

    def test_managed_directory_fallback_when_mount_api_omits_usb(self):
        volume = os.path.join(self.media_root, "sda1")
        usb_root = os.path.join(volume, "clios")
        os.makedirs(usb_root)

        self.assertTrue(self.manager.refresh())
        self.assertEqual(self.manager.mode, StorageMode.USB)
        self.assertEqual(self.manager.get_status()["mount_point"], os.path.realpath(volume))

    def test_nonempty_sda1_usb_wins_even_if_legacy_migration_fails(self):
        pending = self.manager.resolve_path("logs/pending.log")
        with open(pending, "w", encoding="utf-8") as stream:
            stream.write("pending")
        volume = os.path.join(self.media_root, "sda1")
        usb_root = os.path.join(volume, "clios")
        os.makedirs(os.path.join(usb_root, "export"))
        with open(os.path.join(usb_root, "export", "ancien-export.zip"), "w", encoding="utf-8") as stream:
            stream.write("keep")

        with mock.patch("src.storage_manager.shutil.copy2", side_effect=PermissionError("metadata refused")):
            self.assertTrue(self.manager.refresh())

        self.assertEqual(self.manager.mode, StorageMode.USB)
        self.assertEqual(self.manager.get_writable_root(), os.path.realpath(usb_root))
        self.assertTrue(os.path.isfile(os.path.join(usb_root, "export", "ancien-export.zip")))
        self.assertIn("migration partielle", self.manager.get_status()["usb_diagnostic"])

    def test_metadata_error_after_successful_copy_does_not_fail_migration(self):
        source = self.manager.resolve_path("logs/pending.log")
        with open(source, "w", encoding="utf-8") as stream:
            stream.write("complete data")
        volume = os.path.join(self.media_root, "sda1")
        usb_root = os.path.join(volume, "clios")
        os.makedirs(usb_root)

        def copy_then_reject_metadata(copy_source, copy_target):
            shutil.copyfile(copy_source, copy_target)
            raise PermissionError("chmod refused")

        with mock.patch("src.storage_manager.shutil.copy2", side_effect=copy_then_reject_metadata):
            self.assertTrue(self.manager.refresh())

        self.assertEqual(self.manager.mode, StorageMode.USB)
        with open(os.path.join(usb_root, "logs", "pending.log"), encoding="utf-8") as stream:
            self.assertEqual(stream.read(), "complete data")
        self.assertNotIn("migration partielle", self.manager.get_status()["usb_diagnostic"])

    def test_missing_linux_media_root_is_normal_on_desktop(self):
        missing_root = os.path.join(self.root, "does-not-exist")
        with mock.patch("src.storage_manager.logging.Logger.warning") as warning:
            manager = StorageManager(
                self.root,
                media_root=missing_root,
                volatile_root=os.path.join(self.root, "desktop-volatile"),
                mount_provider=lambda: [],
                mount_table_provider=lambda: "",
            )
        try:
            warning.assert_not_called()
            self.assertEqual(manager.mode, StorageMode.VOLATILE)
        finally:
            manager.stop_monitoring()

    def test_fuse_mount_is_not_filtered_by_psutil(self):
        volume = os.path.join(self.media_root, "sda1")
        usb_root = os.path.join(volume, "clios")
        os.makedirs(usb_root)

        fake_psutil = mock.Mock()
        fake_psutil.disk_partitions.return_value = [
            SimpleNamespace(mountpoint=volume, fstype="fuseblk", device="/dev/sda1")
        ]
        with mock.patch("src.storage_manager.psutil", fake_psutil):
            manager = StorageManager(
                self.root,
                media_root=self.media_root,
                volatile_root=os.path.join(self.root, "fuse-volatile"),
                mount_table_provider=lambda: "overlay / overlay rw 0 0",
            )
        try:
            self.assertEqual(manager.mode, StorageMode.USB)
            self.assertEqual(manager.get_writable_root(), os.path.realpath(usb_root))
            fake_psutil.disk_partitions.assert_called_once_with(all=True)
        finally:
            manager.stop_monitoring()

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

    def test_internal_storage_is_used_when_root_is_persistent(self):
        internal = os.path.join(self.root, "internal")
        manager = StorageManager(
            self.root,
            media_root=self.media_root,
            volatile_root=os.path.join(self.root, "ram"),
            internal_root=internal,
            mount_provider=lambda: [],
            mount_table_provider=lambda: "/dev/root / ext4 rw 0 0",
        )
        try:
            self.assertEqual(manager.mode, StorageMode.INTERNAL)
            self.assertEqual(manager.get_writable_root(), internal)
        finally:
            manager.stop_monitoring()

    def test_overlay_forces_ram_even_when_internal_is_writable(self):
        internal = os.path.join(self.root, "writable_internal")
        manager = StorageManager(
            self.root,
            media_root=self.media_root,
            volatile_root=os.path.join(self.root, "overlay_ram"),
            internal_root=internal,
            mount_provider=lambda: [],
            mount_table_provider=lambda: "36 25 0:32 / / rw - overlay overlay rw",
        )
        try:
            self.assertEqual(manager.mode, StorageMode.VOLATILE)
            self.assertEqual(manager.get_status()["mode"], "RAM")
        finally:
            manager.stop_monitoring()

    def test_migration_preserves_target_and_reports_trip_conflict(self):
        source = os.path.join(self.root, "old")
        target = self.manager.get_writable_root()
        os.makedirs(os.path.join(source, "trips"))
        os.makedirs(os.path.join(target, "trips"), exist_ok=True)
        with open(os.path.join(source, "trips", "trip_1.json"), "w", encoding="utf-8") as stream:
            stream.write('{"source": true}')
        with open(os.path.join(target, "trips", "trip_1.json"), "w", encoding="utf-8") as stream:
            stream.write('{"target": true}')
        report_path = os.path.join(self.root, "migration.json")

        report = self.manager.migrate_existing_data(source, report_path)

        self.assertEqual(len(report["conflicts"]), 1)
        with open(os.path.join(target, "trips", "trip_1.json"), encoding="utf-8") as stream:
            self.assertEqual(json.load(stream), {"target": True})
        self.assertTrue(os.path.isfile(report_path))


if __name__ == "__main__":
    unittest.main()
