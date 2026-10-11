"""Analytic alpha/viewport/complement checks for the original raster oracle."""
import pytest
from temporal_matte_kernel_diagnostic import expected_pixel, original_mask, raster_value


@pytest.fixture(autouse=True)
def clean_database():
    yield


@pytest.mark.parametrize("u,v,mode,expected", [
    (-.1, 20, "alpha", 0), (.1, 20, "alpha", 1), (80, 20, "alpha", 0),
    (20.5, 20.5, "alpha", 0), (60.5, 20.5, "alpha", 1), (60.5, 20.5, "luminance", 0),
    (20.5, 60.5, "alpha", 128/255), (20.5, 60.5, "luminance", (128/255)**2)])
def test_original_png_coverage_has_viewport_and_premultiplied_values(u, v, mode, expected):
    assert raster_value(original_mask(), u, v, mode) == pytest.approx(expected)


@pytest.mark.parametrize("x,y,mode,invert,expected", [
    (104, 78, "alpha", False, 255*.9*.9*.85*.6),
    (98, 94, "alpha", False, 0), (100, 94, "alpha", False, 255*.9*.9*.85*.6),
    (142, 80, "alpha", False, 255*.9*.9*.85*.6), (142, 80, "luminance", False, 0),
    (142, 80, "luminance", True, 255*.9*.9*.85),
    (110, 134, "alpha", False, 128*.9*.9*.85*.6),
    (110, 134, "luminance", False, 128*(128/255)*.9*.9*.85*.6),
    (44, 92, "alpha", True, 255*.9*.9*.85/2)])
def test_axis_aligned_authored_pixels_have_analytic_values(x, y, mode, invert, expected):
    assert expected_pixel(original_mask(), 0, "control", "external", mode, invert, x, y) == pytest.approx(expected)
