from __future__ import annotations

import copy
from pathlib import Path

import pytest
from test_native_motion_recipes import direction_with, recipe
from test_remotion_native import native_document

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import AssetReferenceV1
from app.domain.studios.typography import graphemes, segment_text


@pytest.fixture(autouse=True)
def clean_database():
    # Contract/Unicode tests are pure. Actual API/render tests use their own module.
    yield


def typography_direction(text, unit="character", duration=60, stagger=3, hold=15):
    spec = recipe("integrated_type", textUnit=unit, staggerFrames=stagger, readingHoldFrames=hold)
    spec["endFrameExclusive"] = duration
    payload = direction_with([]).model_dump(mode="json", by_alias=True)
    scene = payload["scenes"][0]
    scene["durationFrames"] = duration
    scene["motionRecipes"] = [spec]
    scene["elements"][0].update(
        text=text,
        durationFrames=duration,
        x=16,
        y=60,
        width=288,
        height=100,
        fontSize=42,
        fontWeight=400,
        color="#ffffff",
        visualRole="hero",
    )
    return ContextualPlanRequestV2.model_validate(payload)


def test_all_official_unicode17_grapheme_break_vectors():
    tested = 0
    source = Path(__file__).parent / "fixtures/unicode17/GraphemeBreakTest.txt"
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        raw = line.split("#", 1)[0].strip()
        if not raw:
            continue
        expected, cluster = [], ""
        for token in raw.split():
            if token == "÷":
                if cluster:
                    expected.append(cluster)
                    cluster = ""
            elif token != "×":
                cluster += chr(int(token, 16))
        if cluster:
            expected.append(cluster)
        assert graphemes("".join(expected)) == expected, f"official vector line {line_number}"
        tested += 1
    assert tested == 766


@pytest.mark.parametrize(
    "text,expected",
    [
        ("AÇÃO", ["A", "Ç", "Ã", "O"]),
        ("AC\u0327A\u0303O", ["A", "C\u0327", "A\u0303", "O"]),
        ("👨‍👩‍👧‍👦", ["👨‍👩‍👧‍👦"]),
        ("👍🏽🇧🇷", ["👍🏽", "🇧🇷"]),
        ("\u1100\u1161\u11a8", ["\u1100\u1161\u11a8"]),
        ("A \t\r\n B", ["A", " ", "\t", "\r\n", " ", "B"]),
    ],
)
def test_materialized_units_preserve_text_and_contiguous_animation_indices(text, expected):
    segmentation = segment_text(text, "character")
    assert [u.text for u in segmentation.units] == expected
    assert "".join(u.text for u in segmentation.units) == text
    assert [u.animation_index for u in segmentation.units if u.animation_index is not None] == list(
        range(segmentation.animated_count),
    )


def test_whitespace_is_preserved_and_does_not_consume_stagger():
    for unit in ["word", "character"]:
        spec = segment_text(" A\u00a0\u202fB \t\r\n", unit)
        assert spec.animated_count == 2
        assert "".join(u.text for u in spec.units) == " A\u00a0\u202fB \t\r\n"
    assert [u.text for u in segment_text("Uma palavra", "word").units] == ["Uma", " ", "palavra"]


def test_normalization_is_not_a_silent_content_rewrite():
    composed = segment_text("AÇÃO", "character")
    decomposed = segment_text("AC\u0327A\u0303O", "character")
    assert composed.animated_count == decomposed.animated_count == 4
    assert composed.text_checksum_sha256 != decomposed.text_checksum_sha256


def test_whitespace_only_and_unregistered_segmenter_do_not_fall_back(monkeypatch):
    import regex

    with pytest.raises(ValueError, match="visible_unit_required"):
        segment_text(" \t\r\n", "character")
    monkeypatch.setattr(regex, "__version__", "another-version")
    with pytest.raises(ValueError, match="segmenter_version_mismatch"):
        segment_text("Título", "character")










def test_duplicate_typography_and_hidden_hold_interval_rejected():
    direction = typography_direction("Título")
    duplicate = copy.deepcopy(direction.scenes[0].motion_recipes[0])
    duplicate.id = "duplicate"
    direction.scenes[0].motion_recipes.append(duplicate)
    with pytest.raises(ValueError, match="typography_target_conflict"):
        native_document(direction)
    direction = typography_direction("Título")
    direction.scenes[0].elements[0].duration_frames = 20
    with pytest.raises(ValueError, match="target_interval"):
        native_document(direction)
