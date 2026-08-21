import tempfile
import unittest
from pathlib import Path

from src.release_platform import ReleasePlatformError, detect_release_platform, get_target_platform


class ReleasePlatformTest(unittest.TestCase):
    def os_release(self, codename: str) -> Path:
        root = Path(self.addCleanupPath.name)
        path = root / f"os-release-{codename}"
        path.write_text(f'PRETTY_NAME="Debian {codename}"\nVERSION_CODENAME={codename}\n', encoding="utf-8")
        return path

    def setUp(self):
        self.addCleanupPath = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.addCleanupPath.cleanup()

    def test_detects_bookworm_and_trixie_arm64(self):
        self.assertEqual(detect_release_platform(self.os_release("bookworm"), machine="aarch64").python_minor, "3.11")
        self.assertEqual(detect_release_platform(self.os_release("trixie"), machine="arm64").python_minor, "3.13")
        self.assertEqual(get_target_platform("trixie-arm64").identifier, "raspberry-pi-os-trixie-arm64")

    def test_rejects_unsupported_distribution_or_architecture(self):
        with self.assertRaises(ReleasePlatformError):
            detect_release_platform(self.os_release("forky"), machine="aarch64")
        with self.assertRaises(ReleasePlatformError):
            detect_release_platform(self.os_release("trixie"), machine="x86_64")


if __name__ == "__main__":
    unittest.main()
