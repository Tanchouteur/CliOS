import hashlib
import json
import tarfile
import tempfile
import threading
import time
import unittest
from pathlib import Path

from src.release_manager import ReleaseManager
from src.updater_service import UpdaterEngine, UpdaterProtocolError


class Catalog:
    def __init__(self, manifests):
        self.manifests = manifests

    def find(self, version):
        return self.manifests[version]


class UpdaterServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.install = self.root / "opt/clios"
        self.state = self.root / "var/lib/clios"
        self.archives = {}

    def tearDown(self):
        self.temp.cleanup()

    def make_manifest(self, version, channel):
        source = self.root / f"src-{version}"
        (source / "frontend").mkdir(parents=True)
        (source / "data/config").mkdir(parents=True)
        (source / "src").mkdir()
        (source / "tools").mkdir()
        files = {
            "main.py": "print('ok')\n", "VERSION": version,
            "frontend/main.qml": "import QtQuick\nItem {}\n",
            "data/config/profiles.json": "{}",
        }
        digests = {}
        for relative, content in files.items():
            path = source / relative
            path.write_text(content, encoding="utf-8")
            digests[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        archive = self.root / f"clios-{version}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(source, arcname=f"clios-{version}")
        url = f"https://fixtures/{archive.name}"
        self.archives[url] = archive
        return {
            "schema_version": 1, "version": version, "channel": channel,
            "platform": "raspberry-pi-os-bookworm-arm64", "archive_url": url,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(), "files": digests,
        }

    def engine(self, manifests, timeout=0.2):
        def download(url, destination):
            Path(destination).write_bytes(self.archives[url].read_bytes())
        manager = ReleaseManager(
            str(self.install), str(self.state), downloader=download,
            platform_id="raspberry-pi-os-bookworm-arm64",
        )
        manager._install_environment = lambda _root, _platform: None
        return UpdaterEngine(manager, Catalog(manifests), str(self.state / "updater-status.json"), restart=lambda: None, health_timeout=timeout)

    def test_protocol_rejects_urls_paths_and_extra_fields(self):
        engine = self.engine({})
        for request in (
            {"operation": "stage", "version": "2.0.1", "url": "https://evil"},
            {"operation": "activate", "version": "../../tmp"},
            {"operation": "shell", "command": "id"},
        ):
            with self.assertRaises(UpdaterProtocolError):
                engine.handle(request)

    def test_restart_failure_restores_current_immediately(self):
        stable = self.make_manifest("2.0.0", "stable")
        candidate = self.make_manifest("2.0.1-rc.1", "beta")
        engine = self.engine({"2.0.0": stable, "2.0.1-rc.1": candidate})
        engine.stage("2.0.0")
        engine.manager.activate("2.0.0")
        engine.manager.mark_healthy("2.0.0")
        engine.stage("2.0.1-rc.1")

        def fail_restart():
            raise OSError("systemd indisponible")

        engine.restart = fail_restart
        with self.assertRaises(OSError):
            engine.activate("2.0.1-rc.1")
        self.assertEqual(engine.manager.current_link.resolve().name, "2.0.0")

    def test_rc_stage_activate_health_and_failed_first_boot_rollback(self):
        stable = self.make_manifest("2.0.0", "stable")
        candidate = self.make_manifest("2.0.1-rc.1", "beta")
        engine = self.engine({"2.0.0": stable, "2.0.1-rc.1": candidate}, timeout=1.0)
        engine.stage("2.0.0")
        engine.manager.activate("2.0.0")
        engine.manager.mark_healthy("2.0.0")
        engine.stage("2.0.1-rc.1")

        def healthy():
            time.sleep(0.1)
            (self.state / "health-2.0.1-rc.1").write_text("healthy", encoding="utf-8")

        threading.Thread(target=healthy).start()
        engine.activate("2.0.1-rc.1")
        time.sleep(0.3)
        self.assertEqual(engine.manager._load_state().get("healthy"), "2.0.1-rc.1")

        # Un second essai sans marqueur restaure N-1.
        failed = self.make_manifest("2.0.1-rc.2", "beta")
        engine.catalog.manifests["2.0.1-rc.2"] = failed
        engine.stage("2.0.1-rc.2")
        engine.health_timeout = 0.1
        engine.activate("2.0.1-rc.2")
        deadline = time.monotonic() + 2.0
        while (engine.manager.current_link.resolve().name == "2.0.1-rc.2" or engine.status().get("error") is None) and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(engine.manager.current_link.resolve().name, "2.0.1-rc.1")
        self.assertIsNotNone(engine.status().get("error"))
        self.assertEqual(engine.status()["error"]["code"], "HEALTH_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
