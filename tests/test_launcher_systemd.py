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
        self.assertIn("Environment=CLIOS_HIDE_CURSOR=1", rendered)
        self.assertIn("@USER@", template)
        self.assertFalse((ROOT / "installation/etc/systemd/system/clios.service").exists())
        self.assertNotIn("can0.service", rendered)
        self.assertNotIn("sound.target", rendered)

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
        self.assertIn("Précompilation Python pour le premier démarrage", installer)
        self.assertIn("-m compileall -q", installer)
        self.assertNotIn('cp -a "${PROJECT_DIR}/." "${RELEASE_DIR}/"', installer)
        self.assertLess(
            installer.index('install_release_tree "$RELEASE_DIR"'),
            installer.index('ln -sfn "${RELEASE_DIR}" /opt/clios/current'),
        )

    def test_source_launcher_falls_back_to_system_install_after_venv_move(self):
        launcher = (ROOT / "clios").read_text(encoding="utf-8")
        self.assertIn('SYSTEM_ROOT="${CLIOS_INSTALL_ROOT:-/opt/clios}/current"', launcher)
        self.assertIn('exec "$SYSTEM_PYTHON" -u "$SYSTEM_MAIN" "$@"', launcher)

    def test_installer_finishes_with_system_service_instructions(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("CliOS est installé dans /opt/clios/current", installer)
        self.assertIn("Voulez-vous démarrer CliOS maintenant ?", installer)
        self.assertIn('start clios.service', installer)

    def test_overlayfs_permission_is_limited_to_raspi_config_actions(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        sudoers = (ROOT / "installation/etc/sudoers.d/clios-overlayfs.in").read_text(encoding="utf-8")
        helper = (ROOT / "tools/toggle_overlayfs.sh").read_text(encoding="utf-8")
        for action in ("get_overlay_now", "enable_overlayfs", "disable_overlayfs"):
            self.assertIn(f"/usr/bin/raspi-config nonint {action}", sudoers)
        self.assertNotIn("NOPASSWD:ALL", sudoers)
        self.assertIn("visudo -cf", installer)
        self.assertIn("sudo -n /usr/bin/raspi-config", helper)

    def test_usb_mount_prepares_only_runtime_directories(self):
        helper = (ROOT / "installation/usr/local/libexec/clios-usb-mount").read_text(encoding="utf-8")
        self.assertIn("for managed_dir in dash_save logs trips trips_mock config diagnostics", helper)
        self.assertIn('chmod 2775 "${clios_root}/${managed_dir}"', helper)
        self.assertNotIn("chown -R", helper)
        mounted_branch = helper.split('if [[ -n "$source" ]]', 1)[1].split("local clios_root", 1)[0]
        self.assertNotIn("return 0", mounted_branch)

    def test_updater_unit_keeps_hardening_and_prepares_only_its_state_directory(self):
        unit = (ROOT / "installation/etc/systemd/system/clios-updater.service").read_text(encoding="utf-8")
        for directive in (
            "NoNewPrivileges=yes", "PrivateTmp=yes", "PrivateDevices=yes", "ProtectSystem=strict",
            "ProtectHome=yes", "MemoryDenyWriteExecute=yes", "StateDirectory=clios",
            "StateDirectoryMode=0770", "ReadWritePaths=/opt/clios /var/lib/clios /run/clios",
            "AmbientCapabilities=CAP_SETUID",
        ):
            self.assertIn(directive, unit)
        self.assertNotIn("Privileged=yes", unit)

    def test_gui_hides_cursor_and_desktop_forces_mock_by_default(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("--show-cursor", main)
        self.assertIn("if not args.show_cursor", main)
        self.assertIn('platform.system() != "Linux"', main)
        self.assertIn("args.mock = True", main)


if __name__ == "__main__":
    unittest.main()
