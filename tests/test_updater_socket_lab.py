import hashlib
import errno
import os
import tarfile
import tempfile
import threading
import time
import unittest
from pathlib import Path

from src.release_manager import ReleaseManager
from src.update_safety import UpdateSafety
from src.updater_client import UpdaterClient
from src.updater_service import UpdaterEngine, UpdaterServer


class Catalog:
    def __init__(self, manifest):
        self.manifest = manifest

    def find(self, _version):
        return self.manifest


class UpdaterSocketLabTest(unittest.TestCase):
    def test_real_socket_exposes_monotone_progress_during_slow_stage(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            source = root / "source"
            for path in (source / "frontend", source / "data/config", source / "src", source / "tools"):
                path.mkdir(parents=True)
            files = {
                "main.py": "print('ok')\n", "VERSION": "2.0.1-rc.4\n",
                "frontend/main.qml": "import QtQuick\nItem {}\n",
                "data/config/profiles.json": "{}\n",
            }
            for relative, content in files.items():
                (source / relative).write_text(content, encoding="utf-8")
            archive = root / "release.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                bundle.add(source, arcname="clios-2.0.1-rc.4")
            manifest = {
                "schema_version": 1, "version": "2.0.1-rc.4", "channel": "beta",
                "platform": "raspberry-pi-os-bookworm-arm64",
                "archive_url": "https://fixtures.invalid/release.tar.gz",
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "files": {
                    name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in files
                },
            }

            def slow_download(_url, destination):
                with archive.open("rb") as incoming, open(destination, "wb") as outgoing:
                    while block := incoming.read(64):
                        outgoing.write(block)
                        outgoing.flush()
                        time.sleep(0.012)

            install = root / "opt/clios"
            state = root / "var/lib/clios"
            manager = ReleaseManager(
                str(install), str(state), downloader=slow_download,
                platform_id="raspberry-pi-os-bookworm-arm64",
            )
            manager._install_environment = lambda _root, _platform: None
            engine = UpdaterEngine(
                manager, Catalog(manifest), str(state / "updater-status.json"), restart=lambda: None,
                update_safety=UpdateSafety(str(state / "updater-status.json"), str(root / "mountinfo")),
            )
            socket_path = root / "updater.sock"
            try:
                server_context = UpdaterServer(str(socket_path), engine)
            except PermissionError as exc:
                if exc.errno == errno.EPERM:
                    self.skipTest("Unix sockets interdits par le bac à sable local")
                raise
            with server_context as server:
                server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                server_thread.start()
                operation_id = "socketlab-12345678"
                result = {}

                def stage():
                    result.update(UpdaterClient(str(socket_path), timeout=10).stage("2.0.1-rc.4", operation_id))

                worker = threading.Thread(target=stage)
                worker.start()
                samples = []
                while worker.is_alive():
                    status = UpdaterClient(str(socket_path), timeout=2).status()["result"]
                    if status.get("operation_id") == operation_id:
                        samples.append(status)
                    time.sleep(0.01)
                worker.join(timeout=2)
                server.shutdown()
                server_thread.join(timeout=2)

            progress = [int(item.get("progress", 0)) for item in samples]
            sequences = [int(item.get("sequence", 0)) for item in samples]
            self.assertEqual(result["state"], "STAGED")
            self.assertGreater(len(samples), 3)
            self.assertEqual(progress, sorted(progress))
            self.assertEqual(sequences, sorted(sequences))
            self.assertTrue(any(item.get("indeterminate") for item in samples))
            self.assertTrue(any(0 < value < 100 for value in progress))
            self.assertFalse(os.path.lexists(install / "current"))


if __name__ == "__main__":
    unittest.main()
