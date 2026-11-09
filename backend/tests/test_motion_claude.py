"""Claude transport and editorial mutations are bounded independently of real credits."""
import json
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError
from PIL import Image

from app.domain.studios.contracts import CreativeCompositionV1, CreativeDocumentV1
from app.providers.studios import timeline_ffmpeg
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios import motion_claude

CONFIG = {
    "protocol": "anthropic_messages", "baseUrl": "https://api.anthropic.com/v1",
    "models": ["claude-opus-5-5"], "authHeader": "x-api-key", "authPrefix": "",
    "billingMode": "metered", "extraHeaders": {"anthropic-workspace-id": "wrkspc_12345678901234567890"},
}


@pytest.mark.parametrize("stop_reason", ["end_turn", "max_tokens"])
def test_claude_images_workspace_and_chargeable_truncation(tmp_path, stop_reason):
    image = tmp_path / "sample.jpg"
    image.write_bytes(b"jpeg-fixture")
    def respond(request):
        assert str(request.url) == "https://api.anthropic.com/v1/messages"
        assert request.headers["anthropic-workspace-id"] == CONFIG["extraHeaders"]["anthropic-workspace-id"]
        assert request.headers["x-api-key"] == "test-fixture"
        body = json.loads(request.content)
        assert body["output_config"] == {"effort": "low"}
        assert body["messages"][0]["content"][1]["source"]["type"] == "base64"
        assert "edits" in body["system"]
        return httpx.Response(200, json={"stop_reason": stop_reason, "model": "claude-opus-5-5",
            "content": [{"type":"text","text":"{}"}], "usage":{"input_tokens":192, "output_tokens":94}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = UniversalLLMPlanner(CONFIG, "test-fixture", client=client).plan(
            motion_claude.MODEL, {"editorialMotion": True}, [(image, "image/jpeg")])
    assert result["usage"] == {"prompt_tokens":192, "completion_tokens":94}
    assert result["text"] == ("{}" if stop_reason == "end_turn" else "")


def test_scope_rejects_lookalike_anthropic_host(monkeypatch):
    connection = SimpleNamespace(provider="anthropic", config={**CONFIG, "baseUrl":"https://example.com/v1"})
    monkeypatch.setattr(motion_claude.llm_connections, "planner", lambda *_: (connection, None, None, None))
    with pytest.raises(ValueError, match="editorial_claude_connection_invalid"):
        motion_claude.binding(None, "workspace", "connection")


def test_refinement_keeps_text_and_does_not_allow_new_media():
    comp = CreativeCompositionV1.model_validate({"pages":[{"id":"main","width":540,"height":960,"layers":[
        {"id":"headline","kind":"text","x":40,"y":80,"width":400,"height":90,
         "properties":{"schemaVersion":"studio.local-layer.v1","text":"A foto apresenta.","fontSize":34}}
    ]}]})
    plan = motion_claude.MotionRefinement.model_validate({"edits":[{"id":"headline","x":60,"fontSize":36}],
        "rationale":"Revisar a margem."})
    applied = motion_claude.apply_refinement(comp, plan, {})
    assert applied.pages[0].layers[0].x == 60
    assert applied.pages[0].layers[0].properties["text"] == "A foto apresenta."
    assert comp.pages[0].layers[0].x == 40
    with pytest.raises(ValidationError):
        motion_claude.MotionRefinement.model_validate({"edits":[{"id":"headline","assetId":"foreign"}],"rationale":"Inválido"})
    with pytest.raises(ValueError, match="editorial_claude_layer_invalid"):
        motion_claude.apply_refinement(comp, plan.model_copy(update={"edits":[plan.edits[0].model_copy(update={"id":"other"})]}), {})


@pytest.mark.skipif(not timeline_ffmpeg.capability()["available"], reason="Real FFmpeg required")
def test_render_combines_alpha_scale_and_rotation_on_one_layer(tmp_path):
    image = tmp_path / "product.png"
    Image.new("RGBA", (420, 440), (220, 140, 55, 220)).save(image)
    doc = CreativeDocumentV1.model_validate({
        "documentId":"proof", "workspaceId":"test", "title":"Proof", "contentType":"video",
        "correlationId":"test", "brandMemoryRef":{"id":"test","revision":1},
        "createdAt":"2026-01-01T00:00:00Z", "updatedAt":"2026-01-01T00:00:00Z",
        "brief":{"objective":"Prove keyframes", "audience":"QA"},
        "composition":{
            "pages":[{"id":"main","width":540,"height":960,"durationMs":2000,"layers":[
                {"id":"product","kind":"image","x":50,"y":240,"width":420,"height":440,
                 "properties":{"schemaVersion":"studio.local-layer.v1","assetId":"image",
                    "keyframes":[
                        {"property":"opacity","frame":0,"value":.1},{"property":"opacity","frame":12,"value":1},
                        {"property":"scale","frame":0,"value":.75},{"property":"scale","frame":24,"value":1.1},
                        {"property":"rotation","frame":0,"value":-8},{"property":"rotation","frame":24,"value":0}
                    ]}}
            ]}],
            "mediaTimeline":{"frameRate":{"numerator":24,"denominator":1},"durationFrames":48,"tracks":[]},
        },
        "assets":[{"id":"image","mediaType":"image/png","origin":"workspace"}],
    })
    output, meta = timeline_ffmpeg.render(doc, {"image":image}, tmp_path, {}, lambda:False)
    assert output.stat().st_size > 0
    assert meta["durationSeconds"] == 2 and meta["videoCodec"] == "h264"
