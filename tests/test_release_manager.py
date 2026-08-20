import hashlib
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from src.release_manager import ReleaseError, ReleaseManager


class ReleaseManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.install = self.root / "opt/clios"
        self.state = self.root / "var/lib/clios"
        self.manager = ReleaseManager(str(self.install), str(self.state), downloader=self._copy_download)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _copy_download(source, destination):
        Path(destination).write_bytes(Path(source).read_bytes())
        return destination, None

    def make_release(self, version):
        source = self.root / f"src-{version}"
        (source / "frontend").mkdir(parents=True)
        (source / "data/config").mkdir(parents=True)
        (source / "src").mkdir()
        (source / "tools").mkdir()
        (source / "main.py").write_text("print('ok')\n", encoding="utf-8")
        (source / "VERSION").write_text(version, encoding="utf-8")
        (source / "frontend/main.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")
        (source / "data/config/profiles.json").write_text("{}", encoding="utf-8")
        archive = self.root / f"clios-{version}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(source, arcname=f"clios-{version}")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        manifest = self.root / f"manifest-{version}.json"
        manifest.write_text(json.dumps({
            "version": version, "channel": "stable",
            "archive_url": str(archive), "archive_sha256": digest,
        }), encoding="utf-8")
        return manifest

    def test_corrupt_archive_never_changes_current(self):
        active = self.install / "releases/1.9.0"
        active.mkdir(parents=True)
        self.manager._atomic_symlink(active, self.manager.current_link)
        manifest = self.make_release("2.0.0")
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["archive_sha256"] = "0" * 64
        manifest.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaises(ReleaseError):
            self.manager.stage(str(manifest))

        self.assertEqual(self.manager.current_link.resolve(), active.resolve())
        self.assertFalse((self.install / "releases/2.0.0").exists())

    def test_activate_and_rollback_switch_symlink_atomically(self):
        first = self.manager.stage(str(self.make_release("1.9.0")))
        second = self.manager.stage(str(self.make_release("2.0.0")))
        self.manager.activate("1.9.0")
        self.manager.activate("2.0.0")
        self.assertEqual(self.manager.current_link.resolve(), second.resolve())
        restored = self.manager.rollback()
        self.assertEqual(restored.resolve(), first.resolve())
        self.assertEqual(self.manager.current_link.resolve(), first.resolve())

    def test_interrupted_download_leaves_no_release(self):
        def interrupted(_source, destination):
            Path(destination).write_bytes(b"partial")
            raise OSError("network lost")

        manager = ReleaseManager(str(self.install), str(self.state), downloader=interrupted)
        with self.assertRaises(OSError):
            manager.stage(str(self.make_release("2.1.0")))
        self.assertFalse((self.install / "releases/2.1.0").exists())


if __name__ == "__main__":
    unittest.main()
