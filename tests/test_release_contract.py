import unittest

from src.release_contract import ReleaseContractError, SemVer, channel_for_version, validate_manifest


class ReleaseContractTest(unittest.TestCase):
    def test_semver_prerelease_precedence(self):
        ordered = [
            "2.0.1-alpha", "2.0.1-alpha.1", "2.0.1-beta.2",
            "2.0.1-beta.11", "2.0.1-rc.1", "2.0.1",
        ]
        self.assertEqual(sorted(ordered, key=SemVer.parse), ordered)
        self.assertEqual(SemVer.parse("2.0.1+build.7"), SemVer.parse("2.0.1+other"))

    def test_version_determines_channel(self):
        self.assertEqual(channel_for_version("2.0.1"), "stable")
        self.assertEqual(channel_for_version("2.1.0-beta.1"), "beta")
        self.assertEqual(channel_for_version("2.0.1-rc.1"), "beta")

    def test_manifest_rejects_channel_contradiction_and_unsafe_path(self):
        manifest = {
            "schema_version": 1, "version": "2.0.1-rc.1", "channel": "stable",
            "platform": "raspberry-pi-os-bookworm-arm64",
            "archive_url": "https://github.com/Tanchouteur/CliOS/releases/download/v2.0.1-rc.1/archive.tar.gz",
            "archive_sha256": "a" * 64, "files": {"main.py": "b" * 64},
        }
        with self.assertRaises(ReleaseContractError):
            validate_manifest(manifest)
        manifest["channel"] = "beta"
        manifest["files"] = {"../main.py": "b" * 64}
        with self.assertRaises(ReleaseContractError):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()
