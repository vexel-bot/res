"""Continuous authored-curve bounds; singular curves abstain instead of passing."""

from __future__ import annotations

from math import isclose, isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .motion import MotionKeyframeV1, MotionTrackV1


def _value(poly: list[float], t: float) -> float:
    result = 0.0
    for coefficient in reversed(poly):
        result = result * t + coefficient
    return result


def _derivative(poly: list[float]) -> list[float]:
    return [i * poly[i] for i in range(1, len(poly))] or [0.0]


def _multiply(a: list[float], b: list[float]) -> list[float]:
    result = [0.0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i + j] += x * y
    return result


def _subtract(a: list[float], b: list[float]) -> list[float]:
    return [(a[i] if i < len(a) else 0) - (b[i] if i < len(b) else 0) for i in range(max(len(a), len(b)))]


def _roots(poly: list[float], lo: float, hi: float) -> list[float]:
    """Isolate roots using derivative partitions, including repeated roots."""
    poly = poly.copy()
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    if len(poly) == 1:
        return []
    cuts = [lo, *_roots(_derivative(poly), lo, hi), hi]
    tolerance = 1e-12 * max(1.0, sum(abs(c) for c in poly))
    roots = [t for t in cuts if abs(_value(poly, t)) <= tolerance]
    for left, right in zip(cuts, cuts[1:], strict=False):
        left_value = _value(poly, left)
        if left_value * _value(poly, right) >= 0:
            continue
        for _ in range(60):
            mid = (left + right) / 2
            if left_value * _value(poly, mid) <= 0:
                right = mid
            else:
                left, left_value = mid, _value(poly, mid)
        roots.append((left + right) / 2)
    return sorted(set(roots))


def _parameter(x: list[float], progress: float) -> float:
    if progress in (0, 1):
        return progress
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _value(x, mid) < progress:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _segment(
    key: MotionKeyframeV1,
    order: int,
    lo: float,
    hi: float,
) -> float | None:
    if key.easing == "hold":
        return 0.0  # The jump at the next key is handled separately.
    if key.easing == "linear":
        return 1.0 if order == 1 else 0.0
    if key.easing == "ease_in":
        return 2 * hi if order == 1 else 2.0
    if key.easing == "ease_out":
        return 2 * (1 - lo) if order == 1 else 2.0
    if key.easing == "ease_in_out":
        return max(4 * min(t, 1 - t) for t in [lo, hi, min(hi, max(lo, 0.5))]) if order == 1 else 4.0
    assert key.cubic_bezier is not None
    x1, y1, x2, y2 = key.cubic_bezier
    if x1 == y1 and x2 == y2:
        return 1.0 if order == 1 else 0.0
    x = [0.0, 3 * x1, 3 * x2 - 6 * x1, 1 + 3 * x1 - 3 * x2]
    y = [0.0, 3 * y1, 3 * y2 - 6 * y1, 1 + 3 * y1 - 3 * y2]
    lo, hi = _parameter(x, lo), _parameter(x, hi)
    dx, dy = _derivative(x), _derivative(y)
    ddx, ddy = _derivative(dx), _derivative(dy)
    # A vanishing time derivative requires a limit analysis. Fail closed,
    # including near-singular curves where floating point is ill-conditioned.
    if min(_value(dx, t) for t in [lo, hi, *_roots(ddx, lo, hi)]) <= 1e-10:
        return None
    numerator = _subtract(_multiply(ddy, dx), _multiply(dy, ddx))
    critical = (
        numerator
        if order == 1
        else _subtract(
            _multiply(_derivative(numerator), dx),
            [3 * c for c in _multiply(numerator, ddx)],
        )
    )
    return max(
        abs(_value(dy, t) / _value(dx, t)) if order == 1 else abs(_value(numerator, t) / _value(dx, t) ** 3)
        for t in [lo, hi, *_roots(critical, lo, hi)]
    )


def track_derivative(
    track: MotionTrackV1,
    fps: float,
    order: int,
    start: float | None = None,
    end: float | None = None,
) -> tuple[float | None, str]:
    """Return a finite absolute peak and reason, within [start, end)."""
    label = "velocity" if order == 1 else "acceleration"
    keys = track.keyframes
    if len(keys) < 2:
        return None, f"{label}-needs-two-keyframes"
    explicit_range = start is not None and end is not None
    start = keys[0].frame if start is None else start
    end = keys[-1].frame if end is None else end
    peak = 0.0
    for left, right in zip(keys, keys[1:], strict=False):
        delta = right.value - left.value
        jump_in_range = start < right.frame and (right.frame < end if explicit_range else right.frame <= end)
        if left.easing == "hold" and delta != 0 and jump_in_range:
            return None, f"{label}-discontinuous-hold"
        lo, hi = max(start, left.frame), min(end, right.frame)
        if lo >= hi or delta == 0:
            continue
        span = right.frame - left.frame
        bound = _segment(left, order, (lo - left.frame) / span, (hi - left.frame) / span)
        if bound is None:
            return None, f"{label}-singular-bezier-time"
        peak = max(peak, abs(delta) * (fps / span) ** order * bound)
    if order == 2:
        for i, key in enumerate(keys):
            if not start < key.frame < end:
                continue
            if not explicit_range and i in (0, len(keys) - 1):
                continue
            velocities = []
            for left, right, progress in (
                (keys[i - 1], key, 1.0) if i > 0 else (None, None, 0.0),
                (key, keys[i + 1], 0.0) if i + 1 < len(keys) else (None, None, 0.0),
            ):
                if left is None or right is None or left.value == right.value:
                    velocities.append(0.0)
                    continue
                bound = _segment(left, 1, progress, progress)
                if bound is None:
                    return None, f"{label}-singular-bezier-time"
                # Bézier endpoint slope may be negative; other easings are monotone.
                sign = 1.0
                if left.easing == "cubic_bezier":
                    controls = left.cubic_bezier
                    assert controls is not None
                    sign = -1.0 if (controls[1] if progress == 0 else 1 - controls[3]) < 0 else 1.0
                velocities.append(sign * (right.value - left.value) * fps / (right.frame - left.frame) * bound)
            if not isclose(*velocities, rel_tol=1e-9, abs_tol=1e-9):
                return None, "acceleration-discontinuous-velocity"
    if not isfinite(peak):
        return None, f"{label}-nonfinite-bound"
    return peak, f"maximum-{label}-curve-evaluated"
