import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

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

    def make_release(self, version, channel="stable"):
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
            "version": version, "channel": channel,
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

    def test_staging_is_traversable_by_the_self_check_group(self):
        observed_modes = []

        def inspect_environment(release_root, _platform):
            observed_modes.append(os.stat(release_root.parent.parent).st_mode & 0o777)

        manager = ReleaseManager(str(self.install), str(self.state), downloader=self._copy_download)
        manager._install_environment = inspect_environment
        manager.stage(str(self.make_release("2.0.0")))

        self.assertEqual(observed_modes, [0o750])

    def test_privilege_drop_does_not_request_setgroups(self):
        account = SimpleNamespace(pw_uid=123, pw_gid=456)
        with mock.patch("src.release_manager.os.geteuid", return_value=0), \
                mock.patch("pwd.getpwnam", return_value=account):
            options = self.manager._run_as_options("clios")
        self.assertEqual(set(options), {"user", "group"})

    def test_privilege_drop_keeps_the_existing_service_group(self):
        account = SimpleNamespace(pw_uid=123, pw_gid=456)
        with mock.patch("src.release_manager.os.geteuid", return_value=0), \
                mock.patch("src.release_manager.os.getgid", return_value=456), \
                mock.patch("pwd.getpwnam", return_value=account):
            options = self.manager._run_as_options("clios")
        self.assertEqual(options, {"user": 123})

    def test_runtime_precompile_uses_the_release_python(self):
        release = self.root / "release"
        python = release / ".venv/bin/python3"
        python.parent.mkdir(parents=True)
        python.touch()
        completed = subprocess.CompletedProcess([], 0, "", "")
        with mock.patch("src.release_manager.subprocess.run", return_value=completed) as run:
            self.manager._precompile_runtime(release)

        self.assertEqual(run.call_args.args[0][:4], [str(python), "-m", "compileall", "-q"])
        self.assertEqual(run.call_args.kwargs["cwd"], release)

    def test_channel_is_stable_by_default_and_persists(self):
        self.assertEqual(self.manager.get_channel(), "stable")
        self.assertEqual(self.manager.set_channel("beta"), "beta")

        reloaded = ReleaseManager(str(self.install), str(self.state))
        self.assertEqual(reloaded.get_channel(), "beta")
        with self.assertRaises(ReleaseError):
            self.manager.set_channel("nightly")

    def test_check_uses_persisted_channel_unless_overridden(self):
        feed = self.root / "feed.json"
        feed.write_text(json.dumps({"releases": [
            {"version": "2.0.1", "channel": "stable"},
            {"version": "2.1.0", "channel": "beta"},
        ]}), encoding="utf-8")
        self.manager.set_channel("beta")

        self.assertEqual(self.manager.check(str(feed))["version"], "2.1.0")
        self.assertEqual(self.manager.check(str(feed), "stable")["version"], "2.0.1")

    def test_beta_can_rollback_directly_to_last_stable(self):
        stable = self.manager.stage(str(self.make_release("2.0.0")))
        # Simule l'installation initiale, créée avant release-state.json.
        self.manager._atomic_symlink(stable, self.manager.current_link)
        self.manager.stage(str(self.make_release("2.1.0", channel="beta")))
        self.manager.activate("2.1.0")

        restored = self.manager.rollback(stable_only=True)

        self.assertEqual(restored.resolve(), stable.resolve())
        self.assertEqual(self.manager.current_link.resolve(), stable.resolve())

    def test_strict_manifest_rejects_another_platform(self):
        manager = ReleaseManager(
            str(self.install), str(self.state), downloader=self._copy_download,
            platform_id="raspberry-pi-os-bookworm-arm64",
        )
        with self.assertRaisesRegex(ReleaseError, "incompatible"):
            manager._validate_manifest({
                "schema_version": 1,
                "version": "2.0.1-rc.2",
                "channel": "beta",
                "platform": "raspberry-pi-os-trixie-arm64",
                "archive_url": "https://github.com/Tanchouteur/CliOS/releases/download/v2.0.1-rc.2/archive.tar.gz",
                "archive_sha256": "a" * 64,
                "files": {"main.py": "b" * 64},
            }, strict=True)


if __name__ == "__main__":
    unittest.main()
