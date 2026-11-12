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



def test_cut_changes_editable_timing_and_preserves_audio_and_source_assets():
    comp = CreativeCompositionV1.model_validate({
        "pages":[{"id":"main","width":540,"height":960,"layers":[
            {"id":"headline","kind":"text","x":40,"y":80,"width":400,"height":90,
             "properties":{"schemaVersion":"studio.local-layer.v1","text":"A foto apresenta.","durationFrames":24}}
        ]}],
        "mediaTimeline":{"frameRate":{"numerator":24,"denominator":1},"durationFrames":48,"tracks":[
            {"id":"video","kind":"video","muted":True,"clips":[
                {"id":"take","assetId":"footage","timeline":{"startFrame":0,"durationFrames":24},
                 "source":{"startMicroseconds":0,"durationMicroseconds":1000000}}
            ]},
            {"id":"audio","kind":"audio","clips":[
                {"id":"music","assetId":"sound","timeline":{"startFrame":0,"durationFrames":48}}
            ]},
        ]},
    })
    cut = motion_claude.CutRefinement.model_validate({
        "edits":[{"id":"headline","startFrame":8,"durationFrames":32,"color":"#F1CF94","zIndex":4}],
        "clipSlips":[{"trackId":"video","clipId":"take","sourceStartMicroseconds":250000}],
        "background":"#202B21","rationale":"Atrasar a cartela e usar outro momento do plano."
    })
    edited = motion_claude.apply_refinement(comp, cut, {})
    assert edited.pages[0].background == "#202B21"
    assert edited.pages[0].layers[0].properties["startFrame"] == 8
    assert edited.pages[0].layers[0].properties["text"] == "A foto apresenta."
    assert edited.media_timeline.duration_frames == comp.media_timeline.duration_frames
    assert edited.media_timeline.tracks[1] == comp.media_timeline.tracks[1]
    assert edited.media_timeline.tracks[0].clips[0].asset_id == "footage"
    assert edited.media_timeline.tracks[0].clips[0].source.start_microseconds == 250000
    assert comp.media_timeline.tracks[0].clips[0].source.start_microseconds == 0
    with pytest.raises(ValueError, match="editorial_claude_clip_invalid"):
        motion_claude.apply_refinement(comp, cut, {"footage":"interface"})


def test_creative_cut_reorders_real_clip_and_builds_graphic_within_source():
    comp = CreativeCompositionV1.model_validate({
        "pages":[{"id":"main","width":540,"height":960,"layers":[
            {"id":"title","kind":"text","width":400,"height":100,"properties":{"text":"Primeiro título"}}
        ]}],
        "mediaTimeline":{"frameRate":{"numerator":24,"denominator":1},"durationFrames":48,"tracks":[
            {"id":"video","kind":"video","muted":True,"clips":[
                {"id":"shot","assetId":"real","timeline":{"startFrame":0,"durationFrames":24},
                 "source":{"startMicroseconds":0,"durationMicroseconds":1000000}}
            ]}
        ]},
    })
    plan = motion_claude.CreativeCut.model_validate({
        "edits":[{"id":"title","text":"Monte sua gravação."}],
        "graphics":[{"x":10,"y":30,"width":400,"height":100,"fill":"#141A21","zIndex":1,
                     "startFrame":0,"durationFrames":48}],
        "recuts":[{"trackId":"video","clipId":"shot","startFrame":12,"durationFrames":24,
                   "sourceStartMicroseconds":500000,"crop":{"width":0.8,"height":0.8,"x":0.5,"y":0.5}}],
        "rationale":"Abrir na ação e sustentar a leitura."
    })
    revised = motion_claude.apply_refinement(comp, plan, {}, {"real": 1500000})
    assert revised.pages[0].layers[0].properties["text"] == "Monte sua gravação."
    assert revised.pages[0].layers[1].kind == "shape"
    clip = revised.media_timeline.tracks[0].clips[0]
    assert clip.timeline.start_frame == 12 and clip.transform["crop"]["width"] == 0.8
    with pytest.raises(ValueError, match="editorial_claude_source_outside_media"):
        motion_claude.apply_refinement(comp, plan, {}, {"real": 1499999})
    assert comp.media_timeline.tracks[0].clips[0].timeline.start_frame == 0


def test_creative_caption_uses_its_actual_animated_backplate_for_contrast():
    comp = CreativeCompositionV1.model_validate({
        "pages":[{"id":"main","width":540,"height":960,"background":"#141A21","layers":[
            {"id":"cta","kind":"text","x":42,"y":115,"width":478,"height":100,"zIndex":8,
             "properties":{"text":"Abra o Studio de Vídeo.","align":"center","fontSize":34,"color":"#FFF6E4",
                           "startFrame":24,"durationFrames":24}},
            {"id":"plate","kind":"shape","x":42,"y":110,"width":456,"height":97,"zIndex":7,
             "properties":{"fill":"#F3CA68","startFrame":24,"durationFrames":24,
                           "keyframes":[{"property":"opacity","frame":0,"value":0},
                                        {"property":"opacity","frame":8,"value":1}]}}
        ]}],
        "mediaTimeline":{"frameRate":{"numerator":24,"denominator":1},"durationFrames":48,"tracks":[]},
    })
    assert motion_claude._layout_creative_text(comp) == ["cta"]
    title, plate = comp.pages[0].layers
    assert title.properties["text"] == "Abra o Studio de Vídeo."
    assert motion_claude.motion_editorial.contrast(title.properties["color"], plate.properties["fill"]) >= 4.5
    assert not motion_claude.motion_editorial._text_legibility(comp)


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


@pytest.mark.skipif(not timeline_ffmpeg.capability()["available"], reason="Real FFmpeg required")
def test_adjacent_video_clips_hold_last_decoded_frame(tmp_path):
    import subprocess

    source = tmp_path / "source.mp4"
    subprocess.run([
        timeline_ffmpeg.tool("ffmpeg"), "-nostdin", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=64x96:r=25:d=2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ], check=True, capture_output=True, timeout=20)
    doc = CreativeDocumentV1.model_validate({
        "documentId":"boundary", "workspaceId":"test", "title":"Boundary", "contentType":"video",
        "correlationId":"test", "brandMemoryRef":{"id":"test","revision":1},
        "createdAt":"2026-01-01T00:00:00Z", "updatedAt":"2026-01-01T00:00:00Z",
        "brief":{"objective":"Preserve visual cut boundaries", "audience":"QA"},
        "composition":{
            "pages":[{"id":"main","width":320,"height":480,"background":"#000000","layers":[]}],
            "mediaTimeline":{"frameRate":{"numerator":24,"denominator":1},"durationFrames":48,
                "tracks":[{"id":"video","kind":"video","muted":True,"clips":[
                    {"id":"a","assetId":"source","timeline":{"startFrame":0,"durationFrames":23},
                     "source":{"startMicroseconds":0,"durationMicroseconds":958333},
                     "transform":{"originalAudioEnabled":False}},
                    {"id":"b","assetId":"source","timeline":{"startFrame":23,"durationFrames":25},
                     "source":{"startMicroseconds":0,"durationMicroseconds":1041667},
                     "transform":{"originalAudioEnabled":False}},
                ]}]},
        },
        "assets":[{"id":"source","mediaType":"video/mp4","origin":"workspace"}],
    })
    output, _ = timeline_ffmpeg.render(doc, {"source":source}, tmp_path,
                                       {"source":timeline_ffmpeg.probe(source)}, lambda:False)
    result = subprocess.run([
        timeline_ffmpeg.tool("ffmpeg"), "-nostdin", "-v", "error", "-i", str(output),
        "-an", "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1",
    ], capture_output=True, check=True, timeout=20)
    assert len(result.stdout) == 48*3
    # All frames, including the final frame of each clip, retain the source.
    assert all(result.stdout[index] > 150 for index in range(0, len(result.stdout), 3))
