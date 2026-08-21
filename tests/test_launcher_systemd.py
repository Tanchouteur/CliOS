import pathlib
import unittest

from tools.clios_launcher import application_args


ROOT = pathlib.Path(__file__).parents[1]


class LauncherSystemdTest(unittest.TestCase):
    def test_launcher_removes_only_argparse_separator(self):
        self.assertEqual(application_args(["--", "--ui", "gui"]), ["--ui", "gui"])
        self.assertEqual(application_args(["--ui", "gui"]), ["--ui", "gui"])

    def test_headless_service_starts_from_multi_user_target(self):
        service = (ROOT / "installation/etc/systemd/system/clios.service").read_text(encoding="utf-8")
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        for payload in (service, installer):
            self.assertIn("WantedBy=multi-user.target", payload)
            self.assertNotIn("WantedBy=graphical.target", payload)
            self.assertNotIn("After=graphical.target", payload)


if __name__ == "__main__":
    unittest.main()
