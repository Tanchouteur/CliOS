import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.release_manager import ReleaseError, ReleaseManager


class ReleaseSignatureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.private = self.root / "private.pem"
        self.public = self.root / "public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(self.private)], check=True)
        subprocess.run(
            ["openssl", "pkey", "-in", str(self.private), "-pubout", "-out", str(self.public)], check=True,
        )
        self.keyring = self.root / "keys.json"
        self.keyring.write_text(json.dumps({
            "schema_version": 1,
            "keys": [{"id": "test", "public_key": self.public.read_text(encoding="utf-8")}],
        }), encoding="utf-8")
        self.manager = ReleaseManager(
            str(self.root / "install"), str(self.root / "state"),
            downloader=lambda source, destination: Path(destination).write_bytes(Path(source).read_bytes()),
            platform_id="raspberry-pi-os-bookworm-arm64", trusted_keys_path=str(self.keyring),
        )

    def tearDown(self):
        self.temp.cleanup()

    def make_signed_release(self):
        archive = self.root / "clios-2.0.1-bookworm-arm64.tar.gz"
        archive.write_bytes(b"archive")
        manifest = {
            "schema_version": 1, "version": "2.0.1", "channel": "stable",
            "platform": "raspberry-pi-os-bookworm-arm64",
            "archive_url": f"https://example.invalid/{archive.name}",
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": {"main.py": "a" * 64},
        }
        manifest_path = self.root / "clios-2.0.1-bookworm-arm64-stable.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        sums = self.root / "SHA256SUMS"
        sums.write_text(
            f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n"
            f"{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}  {manifest_path.name}\n",
            encoding="utf-8",
        )
        subprocess.run([
            "openssl", "pkeyutl", "-sign", "-inkey", str(self.private), "-rawin",
            "-in", str(sums), "-out", str(self.root / "SHA256SUMS.sig"),
        ], check=True)
        return manifest, manifest_path, archive

    def test_valid_signed_manifest_and_archive_are_accepted(self):
        manifest, manifest_path, _ = self.make_signed_release()
        signed = self.manager._verify_signed_metadata(manifest, str(manifest_path))
        self.assertEqual(signed[manifest_path.name], hashlib.sha256(manifest_path.read_bytes()).hexdigest())

    def test_altered_manifest_is_refused(self):
        manifest, manifest_path, _ = self.make_signed_release()
        manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "hash signé du manifeste"):
            self.manager._verify_signed_metadata(manifest, str(manifest_path))

    def test_altered_signature_is_refused(self):
        manifest, manifest_path, _ = self.make_signed_release()
        signature = self.root / "SHA256SUMS.sig"
        signature.write_bytes(signature.read_bytes()[:-1] + bytes([signature.read_bytes()[-1] ^ 1]))
        with self.assertRaisesRegex(ReleaseError, "signature Ed25519"):
            self.manager._verify_signed_metadata(manifest, str(manifest_path))

    def test_wrong_key_is_refused(self):
        manifest, manifest_path, _ = self.make_signed_release()
        wrong_private = self.root / "wrong-private.pem"
        wrong_public = self.root / "wrong-public.pem"
        subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(wrong_private)], check=True)
        subprocess.run(["openssl", "pkey", "-in", str(wrong_private), "-pubout", "-out", str(wrong_public)], check=True)
        self.keyring.write_text(json.dumps({
            "schema_version": 1,
            "keys": [{"id": "wrong", "public_key": wrong_public.read_text(encoding="utf-8")}],
        }), encoding="utf-8")
        with self.assertRaisesRegex(ReleaseError, "signature Ed25519"):
            self.manager._verify_signed_metadata(manifest, str(manifest_path))

    def test_archive_hash_not_matching_signed_sums_is_refused(self):
        manifest, manifest_path, archive = self.make_signed_release()
        archive.write_bytes(b"altered")
        def download(source, destination):
            actual = archive if str(source).startswith("https://") else Path(source)
            Path(destination).write_bytes(actual.read_bytes())
        self.manager.downloader = download
        manifest["_manifest_url"] = str(manifest_path)
        with self.assertRaisesRegex(ReleaseError, "SHA-256 de l'archive"):
            self.manager.stage(manifest, strict=True)


if __name__ == "__main__":
    unittest.main()
