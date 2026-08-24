import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.release_manager import ReleaseError, ReleaseManager


ROOT = Path(__file__).parents[1]


@unittest.skipUnless(shutil.which("openssl"), "openssl requis pour les fixtures signées")
class UpdaterSignedFixturesTest(unittest.TestCase):
    def test_signed_a_b_and_intentionally_broken_c(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = root / "fixtures"
            subprocess.run(
                [sys.executable, str(ROOT / "tools/updater_lab/create_fixtures.py"), str(fixtures)],
                check=True, capture_output=True, text=True,
            )

            def download(source, destination):
                Path(destination).write_bytes((fixtures / Path(source).name).read_bytes())

            manager = ReleaseManager(
                str(root / "opt/clios"), str(root / "var/lib/clios"), downloader=download,
                platform_id="raspberry-pi-os-bookworm-arm64",
                trusted_keys_path=str(fixtures / "release-keys.json"),
            )
            manager._install_environment = lambda _root, _platform: None

            manifests = {}
            for label, filename in {
                "A": "clios-2.0.0-bookworm-arm64-stable.json",
                "B": "clios-2.0.1-rc.13-bookworm-arm64-beta.json",
                "C": "clios-2.0.1-rc.14-bookworm-arm64-beta.json",
            }.items():
                path = fixtures / filename
                manifests[label] = json.loads(path.read_text(encoding="utf-8"))
                manifests[label]["_manifest_url"] = "https://fixtures.invalid/" + filename

            prepared_a = manager.stage(manifests["A"], strict=True)
            prepared_b = manager.stage(manifests["B"], strict=True)
            with self.assertRaisesRegex(ReleaseError, "self-check"):
                manager.stage(manifests["C"], strict=True)

            self.assertEqual(prepared_a.name, "2.0.0")
            self.assertEqual(prepared_b.name, "2.0.1-rc.13")
            self.assertFalse((manager.releases_dir / "2.0.1-rc.14").exists())
            self.assertFalse(manager.current_link.exists())


if __name__ == "__main__":
    unittest.main()
