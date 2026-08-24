import hashlib
import errno
import json
import tarfile
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path

from src.release_manager import ReleaseManager
from src.updater_service import UpdaterEngine, UpdaterProtocolError
from src.update_safety import UpdateSafety


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
        safety = UpdateSafety(
            str(self.state / "updater-status.json"), str(self.root / "missing-mountinfo"),
        )
        return UpdaterEngine(
            manager, Catalog(manifests), str(self.state / "updater-status.json"),
            restart=lambda: None, health_timeout=timeout, update_safety=safety,
        )

    def test_overlay_install_root_is_rejected_before_download(self):
        manifest = self.make_manifest("2.0.1-rc.10", "beta")
        engine = self.engine({"2.0.1-rc.10": manifest})
        mountinfo = self.root / "mountinfo"
        mountinfo.write_text("36 25 0:32 / / rw - overlay overlay rw\n", encoding="utf-8")
        engine.update_safety.mountinfo_path = mountinfo

        with self.assertRaisesRegex(RuntimeError, "protection SD active"):
            engine.stage("2.0.1-rc.10")
        self.assertFalse((self.install / "releases/2.0.1-rc.10").exists())

    def test_helper_restart_clears_stale_power_inhibitor(self):
        self.state.mkdir(parents=True)
        status = self.state / "updater-status.json"
        status.write_text(
            '{"state":"DOWNLOADING","version":"2.0.1-rc.10"}', encoding="utf-8",
        )

        engine = self.engine({})

        self.assertEqual(engine.status()["state"], "ERROR")
        self.assertEqual(engine.status()["error"]["code"], "UPDATE_INTERRUPTED")

    def test_permission_error_reports_phase_and_actionable_detail(self):
        engine = self.engine({})
        engine._write_status({
            "state": "DOWNLOADING", "operation": "stage", "phase": "self_check",
            "version": "2.0.1", "progress": 94, "message": "Self-check",
        })
        failure = OSError(errno.EPERM, "Operation not permitted")
        engine._record_error(failure)

        status = engine.status()
        self.assertEqual(status["error"]["code"], "PRIVILEGE")
        self.assertEqual(status["error"]["phase"], "self_check")
        self.assertIn("self-check", status["message"])
        self.assertIn("permission système", status["detail"])
        self.assertGreater(status["updated_at"], 0)

    def test_error_codes_distinguish_absence_permission_and_subprocess(self):
        engine = self.engine({})
        self.assertEqual(engine.error_code(FileNotFoundError(errno.ENOENT, "missing")), "NOT_FOUND")
        self.assertEqual(engine.error_code(PermissionError(errno.EACCES, "denied")), "PRIVILEGE")
        failure = engine.manager._run_checked
        with mock.patch("src.release_manager.subprocess.run") as run:
            run.return_value = mock.Mock(returncode=7, stderr="pip failed", stdout="")
            with self.assertRaises(Exception) as raised:
                failure(["pip", "install"], "installation")
        self.assertEqual(engine.error_code(raised.exception), "SUBPROCESS_FAILED")

    def test_trace_has_operation_sequence_and_bounded_exception_context(self):
        engine = self.engine({})
        engine._active_operation_id = "trace-operation-123"
        engine._write_status({
            "state": "DOWNLOADING", "operation": "stage", "operation_id": "trace-operation-123",
            "phase": "environment", "progress": 80, "indeterminate": True,
        })
        error = OSError(errno.EPERM, "Operation not permitted")
        engine._record_error(error)

        status = engine.status()
        events = [json.loads(line) for line in engine.trace_path.read_text().splitlines()]
        self.assertEqual(status["operation_id"], "trace-operation-123")
        self.assertGreater(status["sequence"], 1)
        self.assertEqual(events[-1]["exception_type"], "PermissionError")
        self.assertEqual(events[-1]["errno"], errno.EPERM)

    def test_operation_id_is_validated_by_closed_protocol(self):
        engine = self.engine({})
        with self.assertRaises(UpdaterProtocolError):
            engine.handle({"operation": "stage", "version": "2.0.1", "operation_id": "../bad"})

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

    def test_manual_rollback_restart_failure_restores_candidate(self):
        stable = self.make_manifest("2.0.0", "stable")
        candidate = self.make_manifest("2.0.1-rc.1", "beta")
        engine = self.engine({"2.0.0": stable, "2.0.1-rc.1": candidate})
        engine.stage("2.0.0")
        engine.manager.activate("2.0.0")
        engine.manager.mark_healthy("2.0.0")
        engine.stage("2.0.1-rc.1")
        engine.manager.activate("2.0.1-rc.1")
        engine.manager.mark_healthy("2.0.1-rc.1")

        engine.restart = mock.Mock(side_effect=OSError("systemd indisponible"))
        with self.assertRaises(OSError):
            engine.rollback(False)

        self.assertEqual(engine.manager.current_link.resolve().name, "2.0.1-rc.1")

    def test_rc_stage_activate_health_and_failed_first_boot_rollback(self):
        stable = self.make_manifest("2.0.0", "stable")
        candidate = self.make_manifest("2.0.1-rc.1", "beta")
        engine = self.engine({"2.0.0": stable, "2.0.1-rc.1": candidate}, timeout=1.0)
        engine.stage("2.0.0")
        engine.manager.activate("2.0.0")
        engine.manager.mark_healthy("2.0.0")
        engine.stage("2.0.1-rc.1")

        restart_requested = threading.Event()
        engine.restart = restart_requested.set

        def healthy():
            if restart_requested.wait(timeout=1.0):
                (self.state / "health-2.0.1-rc.1").write_text("healthy", encoding="utf-8")

        health_writer = threading.Thread(target=healthy)
        health_writer.start()
        engine.activate("2.0.1-rc.1")
        health_writer.join(timeout=1.0)
        deadline = time.monotonic() + 2.0
        while engine.manager._load_state().get("healthy") != "2.0.1-rc.1" and time.monotonic() < deadline:
            time.sleep(0.02)
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
