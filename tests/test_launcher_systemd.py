import pathlib
import unittest

from tools.clios_launcher import application_args
from tools.generate_systemd import render_service


ROOT = pathlib.Path(__file__).parents[1]


class LauncherSystemdTest(unittest.TestCase):
    def test_launcher_removes_only_argparse_separator(self):
        self.assertEqual(application_args(["--", "--ui", "gui"]), ["--ui", "gui"])
        self.assertEqual(application_args(["--ui", "gui"]), ["--ui", "gui"])

    def test_headless_service_starts_from_multi_user_target(self):
        service = render_service("clios", 1000)
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("WantedBy=multi-user.target", service)
        for payload in (service, installer):
            self.assertNotIn("WantedBy=graphical.target", payload)
            self.assertNotIn("After=graphical.target", payload)

    def test_installer_and_tests_use_the_authoritative_unit_generator(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        template = (ROOT / "installation/systemd/clios.service.in").read_text(encoding="utf-8")
        rendered = render_service("dashboard", 1234)
        self.assertIn('tools/generate_systemd.py', installer)
        self.assertIn("User=dashboard", rendered)
        self.assertIn("SupplementaryGroups=clios", rendered)
        self.assertIn("XDG_RUNTIME_DIR=/run/user/1234", rendered)
        self.assertIn("@USER@", template)
        self.assertFalse((ROOT / "installation/etc/systemd/system/clios.service").exists())

    def test_installer_has_offline_targets_for_both_supported_distributions(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn('RELEASE_TARGET="bookworm-arm64"', installer)
        self.assertIn('RELEASE_TARGET="trixie-arm64"', installer)
        self.assertIn("--no-index --require-hashes", installer)

    def test_installer_stages_release_without_copying_local_venv(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("install_release_tree", installer)
        self.assertIn("--exclude='./.venv'", installer)
        self.assertIn('mv "$VENV_DIR" "${staging_dir}/.venv"', installer)
        self.assertIn("Self-check QML de la release", installer)
        self.assertNotIn('cp -a "${PROJECT_DIR}/." "${RELEASE_DIR}/"', installer)
        self.assertLess(
            installer.index('install_release_tree "$RELEASE_DIR"'),
            installer.index('ln -sfn "${RELEASE_DIR}" /opt/clios/current'),
        )


if __name__ == "__main__":
    unittest.main()
