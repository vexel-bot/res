from __future__ import annotations

import pytest
from test_studio_motion_graph import document, graph_payload

from app.domain.studios.motion import MotionGraphV1, MotionTrackV1, evaluate_motion_graph, project_motion_graph
from app.domain.studios.motion_derivatives import track_derivative


@pytest.fixture(autouse=True)
def clean_database():
    # These are pure contract/math tests; the API regression suite owns persistence.
    yield


def track(easing="linear", controls=None, keys=None):
    first = {"frame": 0, "value": 0, "easing": easing}
    if controls is not None:
        first["cubicBezier"] = controls
    return MotionTrackV1.model_validate(
        {
            "trackId": "test",
            "targetLayerId": "hook-text",
            "property": "position_x",
            "unit": "pixels",
            "keyframes": keys or [first, {"frame": 30, "value": 100}],
        }
    )


@pytest.mark.parametrize(
    "easing,velocity,acceleration",
    [
        ("linear", 100, 0),
        ("ease_in", 200, 200),
        ("ease_out", 200, 200),
        ("ease_in_out", 200, 400),
    ],
)
def test_two_key_curves_have_analytic_peaks(easing, velocity, acceleration):
    item = track(easing)
    assert track_derivative(item, 30, 1)[0] == pytest.approx(velocity)
    assert track_derivative(item, 30, 2)[0] == pytest.approx(acceleration)
    assert track_derivative(item, 24000 / 1001, 1)[0] == pytest.approx(velocity * 800 / 1001)


@pytest.mark.parametrize(
    "controls,velocity,acceleration",
    [
        ([1 / 3, 0, 2 / 3, 0], 300, 600),  # y=x³
        ([1 / 3, 2, 2 / 3, -1], 600, 3000),  # negative interior slope
        ([0.99, 0, 0.01, 1], 10000, None),  # narrow interior velocity peak
        ([0, 0, 1, 1], 100, 0),  # removable endpoint singularities, identity
    ],
)
def test_cubic_extrema_and_identity(controls, velocity, acceleration):
    item = track("cubic_bezier", controls)
    assert track_derivative(item, 30, 1)[0] == pytest.approx(velocity)
    if acceleration is not None:
        assert track_derivative(item, 30, 2)[0] == pytest.approx(acceleration)


@pytest.mark.parametrize("controls", [[0, 1, 1, 1], [1, 0, 0, 1], [0, 0, 0.5, 1]])
def test_singular_bezier_abstains_without_infinite_json(controls):
    item = track("cubic_bezier", controls)
    for order in [1, 2]:
        assert track_derivative(item, 30, order) == (
            None,
            ("velocity" if order == 1 else "acceleration") + "-singular-bezier-time",
        )


def test_half_open_range_excludes_hold_jump_at_end_and_detects_it_inside():
    item = track("hold")
    assert track_derivative(item, 30, 1, 0, 30)[0] == 0
    assert track_derivative(item, 30, 1, 0, 31) == (None, "velocity-discontinuous-hold")
    assert track_derivative(item, 30, 2)[0] is None
    assert track_derivative(item, 30, 1, 31, 40)[0] == 0
    assert track_derivative(item, 30, 1, 30, 40)[0] == 0


def test_interval_clips_curve_and_respects_endpoint_clamping():
    item = track("ease_out")
    assert track_derivative(item, 30, 1, 15, 30)[0] == pytest.approx(100)
    assert track_derivative(item, 30, 2, 0, 31)[0] == pytest.approx(200)
    assert track_derivative(track(), 30, 2, 0, 31) == (
        None,
        "acceleration-discontinuous-velocity",
    )
    assert track_derivative(item, 30, 2, 31, 40)[0] == 0


def test_acceleration_detects_internal_velocity_discontinuity():
    keys = [{"frame": 0, "value": 0}, {"frame": 15, "value": 50}, {"frame": 30, "value": 100}]
    assert track_derivative(track(keys=keys), 30, 2)[0] == 0
    keys[2]["value"] = 125
    assert track_derivative(track(keys=keys), 30, 2) == (None, "acceleration-discontinuous-velocity")


def test_graph_does_not_hide_incomplete_track_behind_a_finite_one():
    payload = graph_payload()
    payload["tracks"][1]["keyframes"] = [{"frame": 0, "value": 1}]
    payload["constraints"][0]["targetTrackIds"].append("track-cta-opacity")
    evaluation = evaluate_motion_graph(document(), MotionGraphV1.model_validate(payload))
    assert not evaluation.eligible_for_reviewed_projection
    assert evaluation.observations[0].measured_value is None
    assert evaluation.observations[0].reason == "velocity-needs-two-keyframes"


def test_graph_range_and_peak_prevent_old_false_approval():
    payload = graph_payload()
    payload["constraints"][0]["threshold"] = 400
    full = evaluate_motion_graph(document(), MotionGraphV1.model_validate(payload))
    assert full.observations[0].status == "failed"
    assert full.observations[0].measured_value == pytest.approx(600)
    payload["constraints"][0]["frameRange"] = {"startFrame": 6, "endFrameExclusive": 12}
    clipped = evaluate_motion_graph(document(), MotionGraphV1.model_validate(payload))
    assert clipped.observations[0].status == "passed"
    assert clipped.observations[0].measured_value == pytest.approx(300)


def test_legacy_saved_secant_receipt_cannot_authorize_reviewed_projection():
    payload = graph_payload()
    payload["status"] = "reviewed"
    graph = MotionGraphV1.model_validate(payload)
    evaluation = evaluate_motion_graph(document(), graph)
    evaluation.observations[0].reason = "maximum-velocity-evaluated"
    evaluation.observations[0].measured_value = 300
    with pytest.raises(ValueError, match="require current curve evaluation"):
        project_motion_graph(graph, "remotion", evaluation)
    fresh = evaluate_motion_graph(document(), graph)
    assert not project_motion_graph(graph, "remotion", fresh).preview_only


@pytest.mark.parametrize("controls", [[0.22, 0.75, 0.25, 1], [0.99, 0, 0.01, 1], [0.25, -0.4, 0.75, 1.4]])
def test_cubic_bounds_cover_independent_dense_derivative_oracle(controls):
    # Bernstein derivatives computed independently, without production root helpers.
    x1, y1, x2, y2 = controls
    sampled = [0.0, 0.0]
    for i in range(20001):
        t = i / 20000
        dx = 3 * ((1 - t) ** 2 * x1 + 2 * (1 - t) * t * (x2 - x1) + t**2 * (1 - x2))
        dy = 3 * ((1 - t) ** 2 * y1 + 2 * (1 - t) * t * (y2 - y1) + t**2 * (1 - y2))
        ddx = 6 * ((1 - t) * (x2 - 2 * x1) + t * (1 - 2 * x2 + x1))
        ddy = 6 * ((1 - t) * (y2 - 2 * y1) + t * (1 - 2 * y2 + y1))
        sampled[0] = max(sampled[0], 100 * abs(dy / dx))
        sampled[1] = max(sampled[1], 100 * abs((ddy * dx - dy * ddx) / dx**3))
    for order in [1, 2]:
        peak = track_derivative(track("cubic_bezier", controls), 30, order)[0]
        assert peak is not None
        assert peak >= sampled[order - 1] * (1 - 1e-9)
        assert peak == pytest.approx(sampled[order - 1], rel=2e-5)
