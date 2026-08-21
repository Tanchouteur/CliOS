import unittest

from tools.verify_requirements_alignment import verify


class RequirementsAlignmentTest(unittest.TestCase):
    def test_common_constraints_match_both_arm64_locks(self):
        self.assertEqual(verify(), [])


if __name__ == "__main__":
    unittest.main()
