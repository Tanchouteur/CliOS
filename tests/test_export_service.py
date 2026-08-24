import json
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from src.services.export_service import ExportService
from src.services.trip_session_manager import TripSessionManager


class FakeStorage:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class ExportServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        self.data_dir = os.path.join(self.root, "internal", "trips")
        self.mountpoint = os.path.join(self.root, "media", "clios", "sda1")
        os.makedirs(self.data_dir)
        os.makedirs(os.path.join(self.mountpoint, "clios"))
        self.notifications = []
        self.service = ExportService(
            lambda *args: self.notifications.append(args),
            FakeStorage(),
            self.data_dir,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _partition(self):
        return SimpleNamespace(mountpoint=self.mountpoint, fstype="fuseblk", device="/dev/sda1")

    def test_fuse_export_key_with_automatic_clios_folder_is_processed(self):
        with open(os.path.join(self.data_dir, "trip_1.json"), "w", encoding="utf-8") as stream:
            json.dump({"distance": 12}, stream)
        with open(os.path.join(self.mountpoint, "clios_export.json"), "w", encoding="utf-8") as stream:
            json.dump({"target_folder": "CliOS_Exports"}, stream)

        with mock.patch("src.services.export_service.psutil.disk_partitions", return_value=[self._partition()]) as scan:
            self.service._check_usb_drives()

        scan.assert_called_once_with(all=True)
        self.assertTrue(os.path.isfile(os.path.join(self.mountpoint, "CliOS_Exports", "trip_1.json")))
        self.assertTrue(any(event[0] == "OK" for event in self.notifications))

    def test_legacy_config_name_remains_supported(self):
        with open(os.path.join(self.data_dir, "trip_2.json"), "w", encoding="utf-8") as stream:
            stream.write("{}")
        with open(os.path.join(self.mountpoint, "clos_export.json"), "w", encoding="utf-8") as stream:
            stream.write("{}")

        with mock.patch("src.services.export_service.psutil.disk_partitions", return_value=[self._partition()]):
            self.service._check_usb_drives()

        self.assertTrue(os.path.isfile(os.path.join(self.mountpoint, "CliOS_Exports", "trip_2.json")))

    def test_active_trip_checkpoint_is_never_exported(self):
        checkpoint_name = TripSessionManager.CHECKPOINT_FILENAME
        with open(os.path.join(self.data_dir, checkpoint_name), "w", encoding="utf-8") as stream:
            stream.write("{}")
        with open(os.path.join(self.data_dir, "trip_3.json"), "w", encoding="utf-8") as stream:
            stream.write("{}")
        with open(os.path.join(self.mountpoint, "clios_export.json"), "w", encoding="utf-8") as stream:
            stream.write("{}")

        with mock.patch("src.services.export_service.psutil.disk_partitions", return_value=[self._partition()]):
            self.service._check_usb_drives()

        export_dir = os.path.join(self.mountpoint, "CliOS_Exports")
        self.assertTrue(os.path.isfile(os.path.join(export_dir, "trip_3.json")))
        self.assertFalse(os.path.exists(os.path.join(export_dir, checkpoint_name)))

    def test_active_storage_key_is_not_exported_to_itself(self):
        active_data = os.path.join(self.mountpoint, "clios", "trips")
        os.makedirs(active_data)
        self.service.update_data_dir(active_data)
        with open(os.path.join(self.mountpoint, "clios_export.json"), "w", encoding="utf-8") as stream:
            stream.write("{}")

        with mock.patch("src.services.export_service.psutil.disk_partitions", return_value=[self._partition()]):
            with mock.patch.object(self.service, "_process_usb_export") as process:
                self.service._check_usb_drives()

        process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
