"""Controlled API job for locating browser small-sigma approximation; not qualification."""
# ruff: noqa: F811
import test_spatial_effects_render as fixture
from test_contextual_editing import media as media
from test_contextual_editing import project as project


def test_controlled_small_sigma_against_continuous_reference(client, project, monkeypatch, tmp_path):
    original_direction = fixture.spatial_direction
    original_sample = fixture.sample_rgba
    sigmas = {0: .25, 1: .75, 4: 1.25, 8: 1.75, 29: 3.75}

    def direction(variant):
        raw = original_direction(variant)
        animated = next(e for e in raw["scenes"][0]["elements"] if e["id"] == "animated")
        animated["animations"][0]["keyframes"] = [{"frame": frame, "value": sigma, "easing": "linear"}
                                                   for frame, sigma in sigmas.items()]
        return raw

    def sample(target, frame, x, y, variant):
        # Reuse the continuous reference, translating its sigma-time relation only.
        return original_sample(target, sigmas[frame] / 16 if target == "animated" else frame, x, y, variant)

    monkeypatch.setattr(fixture, "spatial_direction", direction)
    monkeypatch.setattr(fixture, "sample_rgba", sample)
    fixture.test_spatial_effects_actual_api_and_gaussian_pixels(client, project, monkeypatch, tmp_path, "spatial")
