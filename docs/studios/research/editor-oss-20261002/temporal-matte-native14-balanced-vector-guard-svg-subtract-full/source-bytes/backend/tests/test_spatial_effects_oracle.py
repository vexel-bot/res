"""Known independent Gaussian and compositing vectors before reading renderer pixels."""
import math

import pytest
from test_spatial_effects_render import expected_rgb, gaussian_pixel_axis, rectangle_alpha


@pytest.fixture(autouse=True)
def clean_database():
    yield


def test_gaussian_integral_conserves_rectangle_area_and_sharp_edges():
    assert gaussian_pixel_axis(2, 2, 4, 0) == 1
    assert gaussian_pixel_axis(0, 2, 4, 0) == 0
    assert gaussian_pixel_axis(5, 2, 4, 0) == .5
    total = sum(2 * gaussian_pixel_axis(x, 2, 4, 4) for x in range(-60, 70, 2))
    assert total == pytest.approx(4, abs=1e-12)


def test_known_gaussian_boundary_and_source_over_shadow():
    # Far from the perpendicular edges, a blurred step averages the normal CDF.
    sigma = 4
    expected = (math.erf(2 / (sigma * math.sqrt(2))) / 2
                + sigma * (math.exp(-2 ** 2 / (2 * sigma ** 2)) - 1) / math.sqrt(2 * math.pi) / 2)
    assert gaussian_pixel_axis(0, 0, 1000, sigma) == pytest.approx(.5 + expected)
    assert rectangle_alpha("hard", 90, 148, 0, (32, 12)) == 1
    assert expected_rgb(0, 90, 148, "spatial") == pytest.approx([127.5, 0, 0], abs=1e-12)
    assert expected_rgb(0, 42, 132, "spatial") == pytest.approx([255, 255, 255], abs=1e-12)
    assert expected_rgb(0, 258, 148, "spatial") == pytest.approx([0, 0, 0], abs=1e-12)
