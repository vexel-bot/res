from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "res_animatediff_adapter", ROOT / "adapters" / "animatediff_lightning.py"
)
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(3, 2)
        self.register_buffer("position", torch.arange(6, dtype=torch.float32).reshape(2, 3))


class SafeCheckpoint:
    def __init__(self, values):
        self.values = values

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def keys(self):
        return self.values.keys()

    def get_tensor(self, key):
        return self.values[key].clone()


class StreamedLoaderTests(unittest.TestCase):
    def test_meta_to_empty_copy_matches_reference_exactly(self):
        torch.manual_seed(17)
        reference = TinyModel()
        expected = {key: value.detach().clone() for key, value in reference.state_dict().items()}
        with torch.device("meta"):
            candidate = TinyModel()
        candidate.to_empty(device="cpu")
        targets = candidate.state_dict()
        loaded = adapter._copy_checkpoint_entries(
            torch,
            targets,
            lambda *_args, **_kwargs: SafeCheckpoint(expected),
            [Path("fixture.safetensors")],
        )
        self.assertEqual(loaded, set(expected))
        self.assertTrue(all(not value.is_meta for value in candidate.state_dict().values()))
        for key, value in candidate.state_dict().items():
            self.assertTrue(torch.equal(value, expected[key]), key)
            self.assertTrue(torch.isfinite(value).all(), key)
        sample = torch.tensor([[1.0, -2.0, 0.5]])
        self.assertTrue(torch.equal(candidate.linear(sample), reference.linear(sample)))

    def test_nonfinite_checkpoint_is_rejected(self):
        model = TinyModel()
        values = {key: value.detach().clone() for key, value in model.state_dict().items()}
        values["linear.weight"][0, 0] = float("nan")
        with self.assertRaisesRegex(ValueError, "checkpoint_nonfinite"):
            adapter._copy_checkpoint_entries(
                torch,
                model.state_dict(),
                lambda *_args, **_kwargs: SafeCheckpoint(values),
                [Path("fixture.safetensors")],
            )


if __name__ == "__main__":
    unittest.main()
