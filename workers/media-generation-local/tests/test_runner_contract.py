import sys
import unittest
from pathlib import Path


WORKER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKER))

from runner import _camera_prompt


class RunnerContractTests(unittest.TestCase):
    def test_camera_prompt_is_total_for_registered_and_unknown_inputs(self):
        self.assertEqual(_camera_prompt({"type": "static"}), "locked-off camera")
        self.assertEqual(_camera_prompt({"type": "push_in"}), "gentle camera push in")
        self.assertEqual(_camera_prompt({"type": "unknown"}), "locked-off camera")
        self.assertEqual(_camera_prompt({}), "locked-off camera")


if __name__ == "__main__":
    unittest.main()
