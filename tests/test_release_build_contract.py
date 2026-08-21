import pathlib
import unittest

from src.release_contract import ReleaseContractError, channel_for_version
from tools import build_release


class ReleaseBuildContractTest(unittest.TestCase):
    def test_current_version_is_rc_and_refuses_stable_asset(self):
        version = (pathlib.Path(__file__).parents[1] / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(channel_for_version(version), "beta")
        with self.assertRaises(ReleaseContractError):
            build_release.build(pathlib.Path("/tmp/clios-invalid-channel-test"), "stable", "https://github.com")

    def test_every_locked_requirement_has_at_least_one_hash(self):
        for target in ("bookworm-arm64", "trixie-arm64"):
            with self.subTest(target=target):
                lock = (pathlib.Path(__file__).parents[1] / f"requirements-{target}.lock").read_text(encoding="utf-8")
                blocks = []
                current = ""
                for line in lock.splitlines():
                    if line and not line[0].isspace() and not line.startswith("#"):
                        if current:
                            blocks.append(current)
                        current = line
                    elif current:
                        current += " " + line.strip()
                if current:
                    blocks.append(current)
                self.assertGreater(len(blocks), 10)
                for block in blocks:
                    self.assertIn("==", block)
                    self.assertIn("--hash=sha256:", block)


if __name__ == "__main__":
    unittest.main()
