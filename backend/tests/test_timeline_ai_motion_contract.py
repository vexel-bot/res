"""Regression for real Opus responses that used per-frame motion shorthand."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator
from test_video_frontend_contract import draft

from app.domain.studios.contracts import CreativeCompositionV1, MediaTimelineV1
from app.services.studios import timeline_ai, timeline_editor


def project(keys):
    composition = draft("workspace")["composition"]
    composition["mediaTimeline"]["tracks"] = [{
        "id": "visual", "kind": "video", "name": "Cena",
        "clips": [{"id": "scene", "assetId": "generated-video", "timeline": {
            "startFrame": 0, "durationFrames": 144,
        }, "keyframes": keys}],
    }]
    return SimpleNamespace(content_type="video", native_editor_state=None,
                           composition=CreativeCompositionV1.model_validate(composition))


def test_planning_schema_declares_executable_motion_and_rejects_generic_objects():
    contract = project([])
    schema = timeline_ai.capability(contract)["commands"][0]["inputSchema"]
    Draft202012Validator.check_schema(schema)
    payload = {"timeline": contract.composition.media_timeline.model_dump(mode="json", by_alias=True)}
    clip = payload["timeline"]["tracks"][0]["clips"][0]
    clip["keyframes"] = [{"property": "scale", "frame": 0, "value": 1}]
    assert not list(Draft202012Validator(schema).iter_errors(payload))
    clip["keyframes"] = [{"frame": 0, "scale": 1}]
    assert list(Draft202012Validator(schema).iter_errors(payload))
    clip["keyframes"] = []
    clip["transform"] = {"arbitraryFilter": "unsupported"}
    assert list(Draft202012Validator(schema).iter_errors(payload))


def test_opus_shorthand_expands_without_mutation_and_passes_renderer_validation():
    contract = project([])
    commands = [{"id": "timeline.replace", "params": {
        "timeline": contract.composition.media_timeline.model_dump(mode="json", by_alias=True),
    }}]
    keys = [{"frame": 0, "scale": 1, "y": 18}, {"frame": 143, "scale": 1.04}]
    commands[0]["params"]["timeline"]["tracks"][0]["clips"][0]["keyframes"] = keys
    original = deepcopy(commands)
    normalized = timeline_ai.normalize_commands(commands)
    assert commands == original
    timeline = MediaTimelineV1.model_validate(normalized[0]["params"]["timeline"])
    assert timeline.tracks[0].clips[0].keyframes == [
        {"property": "scale", "frame": 0, "value": 1.0, "easing": "linear"},
        {"property": "y", "frame": 0, "value": 18.0, "easing": "linear"},
        {"property": "scale", "frame": 143, "value": 1.04, "easing": "linear"},
    ]
    contract.composition.media_timeline = timeline
    assert timeline_editor.validate(contract) == {"generated-video"}
    assert timeline_ai.normalize_commands(normalized) == normalized


@pytest.mark.parametrize("key", [
    {"frame": 0, "unknown": 1}, {"frame": -1, "scale": 1},
    {"frame": 0, "scale": 0}, {"frame": 0, "opacity": 2},
    {"frame": 0, "scale": 1, "script": "code"}, {"frame": 0},
])
def test_normalization_does_not_admit_unsupported_or_invalid_motion(key):
    commands = [{"id": "timeline.replace", "params": {"timeline": {"tracks": [
        {"clips": [{"keyframes": [key]}]},
    ]}}}]
    with pytest.raises(ValueError):
        timeline_ai.normalize_commands(commands)
