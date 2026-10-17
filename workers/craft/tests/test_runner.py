"""Job isolation boundary: no Docker or engine mocks claim to validate pixels."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "craft_runner", Path(__file__).resolve().parents[1] / "run_adapter.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class JobPathTests(unittest.TestCase):
    def test_only_job_paths_are_translated_and_property_commands_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            params = {
                "mediaRoot": str(root),
                "outputPath": str(root / "out.png"),
                "media": [{"path": str(root / "assets/image.png")}],
                "commands": [
                    {
                        "id": "prop.set",
                        "params": {"path": "transform.position.x", "value": 12},
                    }
                ],
                "legacyDocument": {"text": "/job/this is user content"},
            }
            translated = runner.translate(params, root)
            self.assertEqual(translated["outputPath"], "/job/out.png")
            self.assertEqual(translated["media"][0]["path"], "/job/assets/image.png")
            self.assertEqual(translated["commands"], params["commands"])
            self.assertEqual(translated["legacyDocument"], params["legacyDocument"])

    def test_no_path_can_leave_the_materialized_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaises(ValueError):
                runner.translate({"outputPath": str(root.parent / "escape.png")}, root)
            with self.assertRaises(ValueError):
                runner.restore_paths({"path": "/job/../escape.png"}, root)

    def test_returned_artifact_path_is_restored_without_rewriting_layer_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            response = {
                "artifact": {"path": "/job/out.png"},
                "text": "/job/this is user content",
            }
            restored = runner.restore_paths(response, root)
            self.assertEqual(restored["artifact"]["path"], str(root / "out.png"))
            self.assertEqual(restored["text"], response["text"])


if __name__ == "__main__":
    unittest.main()
