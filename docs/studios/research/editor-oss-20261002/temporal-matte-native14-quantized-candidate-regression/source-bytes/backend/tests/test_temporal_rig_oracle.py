"""Independent geometric oracle checked against hand-computable areas/pivots."""
import pytest
from test_temporal_rig_render import clipped_area, quadrilateral


@pytest.fixture(autouse=True)
def clean_database():
    yield


def test_affine_oracle_authored_origin_and_two_border_offsets():
    points, alpha = quadrilateral(0, 0, "control")
    assert points == [(72, 82), (168, 82), (168, 154), (72, 154)]
    assert alpha == pytest.approx(.3)


def test_area_oracle_square_triangle_touch_and_reversed_winding():
    square = [(0, 0), (4, 0), (4, 4), (0, 4)]
    triangle = [(0, 0), (2, 0), (0, 2)]
    assert clipped_area(square, 1, 1) == 4
    assert clipped_area(square, 4, 0) == 0
    assert clipped_area(triangle, 0, 0) == 2
    assert clipped_area(list(reversed(triangle)), 0, 0) == 2
    assert clipped_area(triangle, 2, 0) == 0


def test_affine_oracle_rotation_preserves_scaled_area():
    points, alpha = quadrilateral(29, 29, "rig")
    area = abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(points, points[1:] + points[:1], strict=True))) / 2
    assert area == pytest.approx(96 * 72 * .9 * 1.05 * 1.1 * .9)
    assert alpha == pytest.approx(.26)
