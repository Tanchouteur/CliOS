import pathlib
import unittest


ROOT = pathlib.Path(__file__).parents[1]


class WindowsLauncherContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wrapper = (ROOT / "clios-windows.cmd").read_text(encoding="utf-8")
        cls.launcher = (ROOT / "tools/windows_launcher.ps1").read_text(encoding="utf-8")

    def test_cmd_wrapper_uses_a_temporary_execution_policy_and_forwards_arguments(self):
        self.assertIn("-ExecutionPolicy Bypass", self.wrapper)
        self.assertIn('tools\\windows_launcher.ps1" %*', self.wrapper)
        self.assertIn("pause >nul", self.wrapper)
        self.assertIn("exit /b %CLIOS_EXIT_CODE%", self.wrapper)

    def test_powershell_launcher_exposes_automation_options(self):
        for option in ("$SetupOnly", "$SmokeTest", "$ResetEnvironment", "$Scale"):
            self.assertIn(option, self.launcher)
        self.assertIn("ValueFromRemainingArguments", self.launcher)
        self.assertIn('Python.Python.3.12', self.launcher)
        self.assertIn('Get-FileHash -Algorithm SHA256', self.launcher)

    def test_launcher_always_runs_the_mock_with_a_visible_cursor(self):
        self.assertIn('$MainScript, "--mock", "--show-cursor"', self.launcher)
        self.assertIn('$env:QT_SCALE_FACTOR', self.launcher)
        self.assertIn('$env:QT_QPA_PLATFORM = "offscreen"', self.launcher)
        self.assertIn('$env:CLIOS_SMOKE_TEST = "1"', self.launcher)
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("CLIOS_SMOKE_TEST") == "1"', main)
        self.assertIn("QTimer.singleShot(3000, app.quit)", main)

    def test_windows_excludes_the_optional_pyo_engine(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn('pyo~=1.0.5; sys_platform != "win32"', requirements)


if __name__ == "__main__":
    unittest.main()
