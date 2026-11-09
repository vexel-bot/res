import json
from copy import deepcopy

import httpx
import pytest
from test_studio_llm_connections import config, payload

from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios.timeline_ai import patch_timeline


def sample():
    return {
        "tracks": [
            {
                "id": "scenes",
                "kind": "video",
                "clips": [
                    {
                        "id": "shot",
                        "assetId": "asset",
                        "timeline": {"startFrame": 0, "durationFrames": 96},
                        "source": {"startMicroseconds": 0, "durationMicroseconds": 4000000},
                        "transform": {"x": 10, "scale": 1},
                    }
                ],
            },
            {
                "id": "voice",
                "kind": "audio",
                "clips": [
                    {"id": "narration", "assetId": "voice", "timeline": {"startFrame": 0, "durationFrames": 1000}}
                ],
            },
        ]
    }


def test_patch_preserves_unrequested_voice_source_and_fields():
    before = sample()
    original = deepcopy(before)
    after = patch_timeline(before, [{"trackId": "scenes", "itemId": "shot", "changes": {"transform": {"scale": 1.08}}}])
    assert before == original
    assert after["tracks"][1] == before["tracks"][1]
    assert after["tracks"][0]["clips"][0]["source"] == before["tracks"][0]["clips"][0]["source"]
    assert after["tracks"][0]["clips"][0]["transform"] == {"x": 10, "scale": 1.08}


@pytest.mark.parametrize(
    "changes", [{"assetId": "invented"}, {"id": "new"}, {"filter": "script"}, {}, {"transform": None}]
)
def test_patch_rejects_identity_invention_and_unsupported_fields(changes):
    with pytest.raises(ValueError):
        patch_timeline(sample(), [{"trackId": "scenes", "itemId": "shot", "changes": changes}])


def test_patch_locked_and_missing_items_fail_without_mutation():
    before = sample()
    before["tracks"][0]["locked"] = True
    with pytest.raises(ValueError):
        patch_timeline(before, [{"trackId": "scenes", "itemId": "shot", "changes": {"text": "x"}}])
    with pytest.raises(ValueError):
        patch_timeline(sample(), [{"trackId": "missing", "itemId": "shot", "changes": {"text": "x"}}])


def test_visual_images_are_encoded_in_multimodal_message_not_prompt(tmp_path):
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"jpeg-frame")

    def handler(request):
        body = json.loads(request.content)
        content = body["messages"][1]["content"]
        assert content[0]["type"] == "text"
        assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
        assert "base64" not in content[0]["text"]
        return httpx.Response(200, json=payload("openai_chat"))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        p = UniversalLLMPlanner(config(), "test", client=client)
        assert p.plan("chosen-model", {}, [(image, "image/jpeg")])["text"]


def test_visual_payload_is_bounded(tmp_path):
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"x" * 512001)
    p = UniversalLLMPlanner(config(), "test")
    with pytest.raises(ValueError, match="llm_visual_input_limit"):
        p.plan("chosen-model", {}, [(image, "image/jpeg")])
