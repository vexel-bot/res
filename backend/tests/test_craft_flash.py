import pytest
from PIL import Image, ImageDraw

from app.services.studios.craft_flash import inspect_transition_flash


def frames(values, *, start=0):
    return [(index, Image.new("L", (80, 50), value)) for index, value in enumerate(values, start)]


def test_transition_flash_returns_time_and_area():
    report = inspect_transition_flash(frames([15] * 10 + [55, 110, 75, 45] + [15] * 16), 24)
    assert report["status"] == "flagged"
    assert len(report["events"]) == 1
    event = report["events"][0]
    assert event["peakFrame"] == 11
    assert event["timeSeconds"] == pytest.approx(11 / 24, abs=0.0001)
    assert event["areaFraction"] == 1
    assert event["meanLift"] == 95


def test_white_scene_cut_and_slow_light_change_are_allowed():
    assert inspect_transition_flash(frames([15] * 10 + [180] * 30), 24)["status"] == "pass"
    assert inspect_transition_flash(frames(list(range(10, 100)) + list(range(100, 10, -1))), 24)["status"] == "pass"


def test_small_light_source_does_not_flag_whole_transition():
    images = frames([12] * 30)
    for index in range(11, 15):
        ImageDraw.Draw(images[index][1]).rectangle((25, 15, 45, 30), fill=240)
    assert inspect_transition_flash(images, 24)["status"] == "pass"


def test_unobserved_gaps_are_inconclusive():
    assert inspect_transition_flash(frames([10, 200]), 24)["status"] == "inconclusive"
    samples = frames([10, 10, 200]) + frames([10, 10, 10], start=22)
    report = inspect_transition_flash(samples, 24)
    assert report["status"] == "inconclusive"
    assert report["events"] == []


def test_invalid_timebase_is_inconclusive():
    assert inspect_transition_flash(frames([1, 2, 3]), 0)["status"] == "inconclusive"
