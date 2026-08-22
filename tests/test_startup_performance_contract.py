import subprocess
import sys
import unittest


class StartupPerformanceContractTest(unittest.TestCase):
    def test_cabin_noise_module_defers_heavy_audio_imports(self):
        script = (
            "import sys; import src.services.cabin_noise_service; "
            "assert 'numpy' not in sys.modules; "
            "assert 'sounddevice' not in sys.modules"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
