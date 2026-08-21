import pathlib
import unittest


ROOT = pathlib.Path(__file__).parents[1]


class PowerPolicyContractTest(unittest.TestCase):
    def test_polkit_rule_is_limited_to_power_and_reboot(self):
        rule = (ROOT / "installation/etc/polkit-1/rules.d/49-clios-power.rules.in").read_text(encoding="utf-8")
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn('subject.user === "@CLIOS_USER@"', rule)
        self.assertIn("org.freedesktop.login1.power-off", rule)
        self.assertIn("org.freedesktop.login1.reboot", rule)
        self.assertNotIn("NOPASSWD", rule)
        self.assertNotIn("org.freedesktop.*", rule)
        self.assertIn("49-clios-power.rules", installer)


if __name__ == "__main__":
    unittest.main()
