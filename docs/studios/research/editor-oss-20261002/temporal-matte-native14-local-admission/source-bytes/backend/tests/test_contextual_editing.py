import shutil
import struct
import subprocess
from datetime import UTC, datetime

import pytest

from app.domain.studios.contextual_editing import ContextualPlanRequestV1
from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.providers.studios.contextual_render import ContextualFFmpegProvider, inspect_document


def document(width=320, height=320):
    return CreativeDocumentV1(
        document_id="document",
        workspace_id="workspace",
        title="Edição contextual",
        content_type="video",
        correlation_id="contextual-test",
        brand_memory_ref={"id": "brand", "revision": 1},
        brief={"objective": "Explicar com precisão", "audience": "Pessoas interessadas"},
        assets=[{"id": "source", "mediaType": "video/mp4", "checksum": "a" * 64, "rightsStatus": "verified"}],
        composition={
            "pages": [{"id": "page", "width": width, "height": height, "safeArea": 16}],
            "mediaTimeline": {
                "frameRate": {"numerator": 25, "denominator": 1},
                "durationFrames": 50,
                "tracks": [
                    {
                        "id": "main",
                        "kind": "video",
                        "clips": [
                            {
                                "id": "clip",
                                "assetId": "source",
                                "timeline": {"startFrame": 0, "durationFrames": 50},
                                "source": {"startMicroseconds": 0, "durationMicroseconds": 2_000_000},
                            }
                        ],
                    }
                ],
            },
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def request(doc):
    page = doc.composition.pages[0]
    return VideoRenderRequestV1(
        workspace_id=doc.workspace_id,
        document_id=doc.document_id,
        document_revision=doc.revision,
        document_version=doc.version,
        page_ids=[page.id],
        asset_ids=[a.id for a in doc.assets],
        output={"width": page.width, "height": page.height, "fps": 25},
        correlation_id="test",
    )


def ffmpeg(*args):
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-threads",
            "2",
            "-filter_threads",
            "1",
            *map(str, args[:-1]),
            "-threads",
            "2",
            str(args[-1]),
        ],
        check=True,
        capture_output=True,
        timeout=40,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


@pytest.fixture
def media(tmp_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg integration runtime unavailable")
    source = tmp_path / "source.mp4"
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=blue:s=320x320:r=25:d=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2:sample_rate=48000",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        source,
    )
    return {"source": source}


def test_inspector_rejects_unknown_effects_and_unsupported_motion():
    doc = document()
    clip = doc.composition.media_timeline.tracks[0].clips[0]
    clip.effects = [{"kind": "tracking"}]
    assert ("clip", "clip_operation_unsupported") in inspect_document(doc)
    clip.effects = [{"kind": "freeze", "contrast": 2}]
    assert inspect_document(doc)
    clip.effects = []
    clip.transform = {"x": float("nan")}
    assert inspect_document(doc)


def test_generic_intent_requires_no_offer_and_protects_message():
    intent = ContextualPlanRequestV1(
        expected_document_revision=1,
        intent={"objective": "Explicar uma ressalva", "format": "interview", "script": "Não garante resultado."},
    )
    assert intent.intent.preserve_message
    with pytest.raises(ValueError):
        ContextualPlanRequestV1(expected_document_revision=1, intent={"objective": "x", "preserveMessage": False})


@pytest.mark.parametrize("size", [(320, 320), (320, 568), (568, 320)])
def test_real_render_multitrack_mask_keyframes_and_audio(media, tmp_path, size):
    from PIL import Image

    doc = document(*size)
    image = tmp_path / "red.png"
    Image.new("RGB", (100, 50), "red").save(image)
    mask = tmp_path / "mask.png"
    m = Image.new("L", (100, 100), 0)
    m.paste(255, (0, 0, 50, 100))
    m.save(mask)
    raw = doc.model_dump(mode="json", by_alias=True)
    raw["assets"].extend([{"id": "red", "mediaType": "image/png"}, {"id": "mask", "mediaType": "image/png"}])
    raw["composition"]["mediaTimeline"]["tracks"].extend(
        [
            {
                "id": "support",
                "kind": "overlay",
                "clips": [
                    {
                        "id": "support-clip",
                        "assetId": "red",
                        "timeline": {"startFrame": 0, "durationFrames": 50},
                        "transform": {"fit": "contain", "width": 100, "height": 100, "originalAudioEnabled": False},
                        "keyframes": [
                            {
                                "trackId": "move",
                                "targetLayerId": "support-clip",
                                "property": "position_x",
                                "unit": "pixels",
                                "keyframes": [{"frame": 0, "value": 0}, {"frame": 49, "value": 100}],
                            }
                        ],
                    }
                ],
            },
            {"id": "mask-track", "kind": "mask", "targetTrackId": "support", "artifactAssetId": "mask"},
        ]
    )
    doc = CreativeDocumentV1.model_validate(raw)
    assert not inspect_document(doc)
    out = tmp_path / "result.mp4"
    result = ContextualFFmpegProvider("ffmpeg", 60).render(
        doc, request(doc), {**media, "red": image, "mask": mask}, out, lambda _: None, lambda: False
    )
    assert result.frames_rendered == 50
    assert "support-clip" in result.rendered_layer_ids
    pixels = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            "1",
            "-i",
            str(out),
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        capture_output=True,
        check=True,
    ).stdout
    frame = Image.frombytes("RGB", size, pixels)
    # The translated left half is red; the masked right half reveals blue.
    assert frame.getpixel((70, 40))[0] > 200
    assert frame.getpixel((125, 40))[2] > 200
    assert frame.getpixel((70, 10))[2] > 200  # mask must preserve transparent letterboxing
    assert out.stat().st_size > 1000


def test_short_delayed_effect_survives_contextual_mix(media, tmp_path):
    from app.domain.studios.contracts import AssetReferenceV1, AudioTrackV1
    from app.providers.studios.procedural_audio import render as render_procedural_sound
    from app.services.object_storage import sha256_file

    sound = tmp_path / "publish.wav"
    render_procedural_sound("publish_confirm", sound)
    doc = document()
    doc.composition.media_timeline.tracks[0].muted = True
    doc.assets.append(
        AssetReferenceV1(
            id="publish",
            media_type="audio/wav",
            checksum=sha256_file(sound),
            rights_status="verified",
            origin="generated",
        )
    )
    doc.composition.media_timeline.tracks.append(
        AudioTrackV1(
            id="effect",
            clips=[
                {
                    "id": "publish-effect",
                    "assetId": "publish",
                    "timeline": {"startFrame": 25, "durationFrames": 6},
                    "source": {"startMicroseconds": 0, "durationMicroseconds": 240_000},
                    "gainDb": -4,
                }
            ],
        )
    )
    destination = tmp_path / "short-effect.mp4"
    result = ContextualFFmpegProvider("ffmpeg", 60).render(
        doc,
        request(doc),
        {**media, "publish": sound},
        destination,
        lambda _: None,
        lambda: False,
    )

    pcm = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            "1",
            "-t",
            "0.3",
            "-i",
            str(destination),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-f",
            "s16le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)

    assert result.rendered_audio_clip_ids == ["publish-effect"]
    assert max(abs(sample) for sample in samples) > 100


def test_real_freeze_speed_color_text_and_fades(media, tmp_path):
    doc = document()
    clip = doc.composition.media_timeline.tracks[0].clips[0]
    clip.effects = [
        {"kind": "freeze"},
        {"kind": "color", "exposure": 0.3, "saturation": 0.8},
        {"kind": "fade", "inFrames": 5, "outFrames": 5},
    ]
    from app.domain.studios.contracts import CaptionTrackV1

    doc.composition.media_timeline.tracks.append(
        CaptionTrackV1(
            id="captions",
            cues=[
                {
                    "id": "text",
                    "text": "Não garante resultado.",
                    "timeline": {"startFrame": 10, "durationFrames": 30},
                    "style": {"fontSize": 18},
                }
            ],
        )
    )
    out = tmp_path / "freeze.mp4"
    result = ContextualFFmpegProvider("ffmpeg", 60).render(doc, request(doc), media, out, lambda _: None, lambda: False)
    assert result.rendered_caption_track_ids == ["captions"]
    clip.effects = []
    clip.playback_rate = 2
    clip.timeline.duration_frames = 25
    doc.composition.media_timeline.duration_frames = 25
    doc.composition.media_timeline.tracks = [doc.composition.media_timeline.tracks[0]]
    result = ContextualFFmpegProvider("ffmpeg", 60).render(
        doc, request(doc), media, tmp_path / "fast.mp4", lambda _: None, lambda: False
    )
    assert abs(result.duration_ms - 1000) < 100


@pytest.fixture
def project(client, media, tmp_path, monkeypatch):
    from conftest import register
    from sqlalchemy import select

    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import CreativeDocument, LibraryAsset, StudioMediaIngest, User
    from app.services.object_storage import get_object_storage
    from app.services.studios.compatibility import persist_contract

    monkeypatch.setattr(get_settings(), "storage_path", str(tmp_path / "storage"))
    token, workspace_id = register(client, "contextual@example.com")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "contextual@example.com"))
        stored = get_object_storage().put_file(
            media["source"], key=f"{workspace_id}/source.mp4", media_type="video/mp4", metadata={}
        )
        asset = LibraryAsset(
            workspace_id=workspace_id,
            title="Explicação original",
            asset_type="video",
            media_type="video/mp4",
            storage_key=stored.key,
            storage_backend=stored.backend,
            checksum_sha256=stored.checksum_sha256,
            size_bytes=stored.size_bytes,
        )
        db.add(asset)
        db.flush()
        db.add(
            StudioMediaIngest(
                workspace_id=workspace_id,
                asset_id=asset.id,
                status="ready",
                requested_by=user.id,
                idempotency_key="source-ingest",
            )
        )
        doc = document()
        doc.workspace_id = workspace_id
        doc.assets[0].id = asset.id
        doc.assets[0].checksum = asset.checksum_sha256
        doc.composition.media_timeline.tracks[0].clips[0].asset_id = asset.id
        record = CreativeDocument(workspace_id=workspace_id, title=doc.title, document={}, created_by=user.id)
        db.add(record)
        db.flush()
        doc.document_id = record.id
        persist_contract(record, doc)
        db.commit()
        return {"token": token, "workspace": workspace_id, "document": record.id, "asset": asset.id}


def create_plan(client, project, **overrides):
    body = {
        "expectedDocumentRevision": 1,
        "intent": {"objective": "Compreender a explicação", "format": "interview"},
        **overrides,
    }
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans",
        headers={"Authorization": f"Bearer {project['token']}", "Idempotency-Key": "contextual-test-plan"},
        json=body,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_api_draft_first_idempotency_and_real_worker(client, project, monkeypatch):
    from sqlalchemy import select

    from app import tasks
    from app.database import SessionLocal
    from app.models import StudioDomainEvent, StudioGenerationJob
    from app.services.studios.jobs import execute_job_once

    plan = create_plan(client, project)
    assert plan["status"] == "ready", plan["blockers"]
    assert plan["humanApproved"] is False
    assert create_plan(client, project)["id"] == plan["id"]
    headers = {"Authorization": f"Bearer {project['token']}"}
    applied = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/apply",
        headers=headers,
        json={"expectedPlanRevision": 1},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["review"]["status"] == "draft"
    assert applied.json()["revision"] == 2
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    render_body = {
        "workspaceId": project["workspace"],
        "documentId": project["document"],
        "expectedDocumentRevision": 2,
        "expectedDocumentVersion": 1,
        "contextualPlanId": plan["id"],
        "provider": "builtin.ffmpeg-contextual-v1",
        "output": {"width": 320, "height": 320, "fps": 25},
    }
    headers["Idempotency-Key"] = "contextual-render-key"
    rendered = client.post("/api/v1/studios/v1/video-renders", headers=headers, json=render_body)
    assert rendered.status_code == 202, rendered.text
    replay = client.post("/api/v1/studios/v1/video-renders", headers=headers, json=render_body)
    assert replay.status_code == 202, replay.text
    assert replay.json()["id"] == rendered.json()["id"]
    with SessionLocal() as db:
        events = db.scalars(
            select(StudioDomainEvent).where(StudioDomainEvent.event_type == "studio.editing.cost_reserved")
        ).all()
        assert len(events) == 1
        job = db.get(StudioGenerationJob, rendered.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        assert job.result_payload["artifact"]["width"] == 320


def test_unsupported_requires_explicit_choice_and_cannot_skip_via_feedback(client, project):
    plan = create_plan(client, project, requiredTechniques=["tracking"])
    assert plan["status"] == "awaiting_choice"
    headers = {"Authorization": f"Bearer {project['token']}"}
    base = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}"
    denied = client.post(base + "/apply", headers=headers, json={"expectedPlanRevision": 1})
    assert denied.status_code == 409
    choice = client.post(
        base + "/choices",
        headers=headers,
        json={"expectedPlanRevision": 1, "blockerId": plan["blockers"][0]["id"], "alternativeId": "omit"},
    )
    assert choice.status_code == 200, choice.text
    assert choice.json()["status"] == "ready"
    stale = client.post(
        base + "/choices",
        headers=headers,
        json={"expectedPlanRevision": 1, "blockerId": plan["blockers"][0]["id"], "alternativeId": "omit"},
    )
    assert stale.status_code == 409


def test_budget_blocks_before_job_and_tenant_isolation(client, project, monkeypatch):
    from conftest import register

    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "studio_editing_monthly_budget_cents", 0)
    plan = create_plan(client, project)
    assert any(b["code"] == "budget_exceeded" for b in plan["blockers"])
    other_token, _ = register(client, "contextual-other@example.com")
    response = client.get(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/latest",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code in {403, 404}


def test_reference_ingest_keeps_dated_metrics_and_deduplicates_chunks(client, project):
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import KnowledgeChunk, KnowledgeDocument
    from app.services.studios.editing_repertoire import seed_techniques

    source = seed_techniques()[1]
    body = {
        "technique": source.model_dump(mode="json", by_alias=True),
        "sourceUrl": source.sources[0],
        "observedAt": "2026-09-01T12:00:00Z",
        "publishedAt": "2026-08-20T12:00:00Z",
        "metrics": {"views": 10},
        "limitations": ["Retenção indisponível; sem inferência causal."],
    }
    url = f"/api/v1/studios/v1/editing/observations?workspace_id={project['workspace']}"
    headers = {"Authorization": f"Bearer {project['token']}"}
    first = client.post(url, headers=headers, json=body)
    assert first.status_code == 200, first.text
    second = client.post(url, headers=headers, json=body)
    assert len(second.json()["observations"]) == 1
    body.update(observedAt="2026-09-02T12:00:00Z", metrics={"views": 15})
    third = client.post(url, headers=headers, json=body)
    assert len(third.json()["observations"]) == 2
    assert third.json()["causalPerformanceClaim"] is False
    with SessionLocal() as db:
        assert len(db.scalars(select(KnowledgeDocument)).all()) == 1
        assert db.scalars(select(KnowledgeChunk)).first() is not None


def test_real_paired_source_audio_and_music_ducking(tmp_path):
    import array
    import math

    from app.domain.studios.contracts import AssetReferenceV1, AudioTrackV1

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg unavailable")
    source, music = tmp_path / "speech.mp4", tmp_path / "music.wav"
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=blue:s=320x320:r=25:d=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=2:sample_rate=48000",
        "-af",
        "volume='if(between(t,0.6,1.4),4,0)':eval=frame",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        source,
    )
    ffmpeg("-f", "lavfi", "-i", "sine=frequency=880:duration=2:sample_rate=48000", music)
    doc = document()
    video = doc.composition.media_timeline.tracks[0]
    video.muted = True  # The current editor uses this to mute embedded audio, not the picture.
    doc.assets.append(AssetReferenceV1(id="music", media_type="audio/wav"))
    original = video.clips[0].model_dump(mode="json", by_alias=True)
    original["id"] = "original-audio"
    music_clip = {
        **original,
        "id": "music-clip",
        "assetId": "music",
        "gainDb": -6,
        "fadeInFrames": 2,
        "fadeOutFrames": 2,
        "effects": [{"kind": "audio_role", "role": "music"}],
    }
    doc.composition.media_timeline.tracks.extend(
        [AudioTrackV1(id="audio-main", clips=[original]), AudioTrackV1(id="music-track", clips=[music_clip])]
    )
    out = tmp_path / "ducked.mp4"
    result = ContextualFFmpegProvider("ffmpeg", 60).render(
        doc, request(doc), {"source": source, "music": music}, out, lambda _: None, lambda: False
    )
    assert "clip" in result.rendered_layer_ids
    samples = array.array("f")
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(out), "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    ).stdout
    samples.frombytes(pcm)

    def amplitude(frequency, start):
        window = samples[round(start * 48000) : round((start + 0.15) * 48000)]
        real = sum(v * math.cos(2 * math.pi * frequency * i / 48000) for i, v in enumerate(window))
        imag = sum(v * math.sin(2 * math.pi * frequency * i / 48000) for i, v in enumerate(window))
        return math.hypot(real, imag) / len(window)

    assert amplitude(880, 0.9) < amplitude(880, 0.2) * 0.7
    assert amplitude(440, 0.9) > amplitude(440, 0.2) * 5


def test_objective_changes_support_composition_and_feedback_is_local(client, project):
    headers = {"Authorization": f"Bearer {project['token']}"}
    base = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans"
    payload = {
        "expectedDocumentRevision": 1,
        "intent": {"objective": "Explicar a mensagem"},
        "beats": [
            {
                "id": "beat",
                "clipId": "clip",
                "purpose": "Demonstrar o detalhe",
                "supportAssetId": project["asset"],
                "onScreenText": "Não garante resultado.",
            }
        ],
    }
    first = client.post(base, headers={**headers, "Idempotency-Key": "message-plan"}, json=payload)
    assert first.status_code == 200, first.text
    payload["intent"]["objective"] = "Mostrar o detalhe do produto"
    second = client.post(base, headers={**headers, "Idempotency-Key": "demonstration-plan"}, json=payload)
    assert second.status_code == 200, second.text
    first, second = first.json(), second.json()

    def support(plan):
        return next(
            t["clips"][0]
            for t in plan["draftDocument"]["composition"]["mediaTimeline"]["tracks"]
            if t["kind"] == "overlay"
        )

    assert support(first)["transform"]["width"] < support(second)["transform"]["width"]
    assert second["intent"]["emphasis"] == "demonstration"
    original_track = second["draftDocument"]["composition"]["mediaTimeline"]["tracks"][0]
    changed = client.post(
        base + f"/{second['id']}/feedback",
        headers=headers,
        json={"expectedPlanRevision": 1, "feedback": "menos texto", "beatIds": ["beat"]},
    )
    assert changed.status_code == 200, changed.text
    tracks = changed.json()["draftDocument"]["composition"]["mediaTimeline"]["tracks"]
    assert tracks[0] == original_track
    assert support(changed.json()) == support(second)
    assert not any(t.get("cues") for t in tracks)


def test_feedback_never_resolves_unrelated_choice(client, project):
    plan = create_plan(
        client,
        project,
        requiredTechniques=["tracking"],
        beats=[{"id": "beat", "clipId": "clip", "purpose": "Explicar", "onScreenText": "Texto opcional"}],
    )
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/feedback",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={"expectedPlanRevision": 1, "feedback": "menos texto", "beatIds": ["beat"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "awaiting_choice"
    assert any(b["code"] == "technique_unavailable" for b in response.json()["blockers"])


def test_changed_document_and_short_support_block_before_render(client, project):
    from app.database import SessionLocal
    from app.models import CreativeDocument

    plan = create_plan(
        client,
        project,
        beats=[
            {
                "id": "beat",
                "clipId": "clip",
                "purpose": "Mostrar",
                "supportAssetId": project["asset"],
                "supportSourceStartMicroseconds": 1_500_000,
            }
        ],
    )
    assert any(b["code"] == "source_out_of_bounds" for b in plan["blockers"])
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        record.revision += 1
        db.commit()
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/apply",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={"expectedPlanRevision": 1},
    )
    assert response.status_code == 409


def test_budget_resolution_change_requires_choice_and_preserves_duration(client, project, monkeypatch):
    from app.config import get_settings
    from app.database import SessionLocal
    from app.models import CreativeDocument
    from app.services.studios.compatibility import persist_contract, record_to_contract

    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        snapshot = record_to_contract(record)
        snapshot.composition.pages[0].width = 1080
        snapshot.composition.pages[0].height = 1920
        persist_contract(record, snapshot)
        db.commit()
    monkeypatch.setattr(get_settings(), "studio_editing_monthly_budget_cents", 2)
    monkeypatch.setattr(get_settings(), "studio_editing_infrastructure_reserve_cents", 0)
    plan = create_plan(client, project)
    blocker = next(b for b in plan["blockers"] if b["code"] == "budget_exceeded")
    assert any(a["id"] == "reduce-resolution" for a in blocker["alternatives"])
    assert plan["draftDocument"]["composition"]["pages"][0]["width"] == 1080
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/choices",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={"expectedPlanRevision": 1, "blockerId": blocker["id"], "alternativeId": "reduce-resolution"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "ready"
    assert result["estimatedCostCents"] <= 2
    assert result["draftDocument"]["composition"]["pages"][0]["height"] == 720
    assert result["draftDocument"]["composition"]["mediaTimeline"]["durationFrames"] == 50


@pytest.mark.parametrize(
    "genre",
    [
        "presenter",
        "screen-tutorial",
        "interview",
        "product-demo",
        "archive-narrative",
        "photo-sequence",
        "silent-video",
    ],
)
def test_generic_formats_preserve_existing_message_and_source(client, project, genre):
    plan = create_plan(
        client,
        project,
        intent={
            "objective": "Preservar a história",
            "format": genre,
            "script": "Não promete resultado. Depende das condições.",
            "lockedFacts": ["Depende das condições."],
        },
    )
    assert plan["intent"]["script"] == "Não promete resultado. Depende das condições."
    assert plan["intent"]["lockedFacts"] == ["Depende das condições."]
    clip = plan["draftDocument"]["composition"]["mediaTimeline"]["tracks"][0]["clips"][0]
    assert clip["source"] == {"startMicroseconds": 0, "durationMicroseconds": 2_000_000}
    assert plan["status"] == "ready"


def test_ducking_requires_music_and_audible_speech(client, project):
    plan = create_plan(client, project, requiredTechniques=["ducking"])
    assert plan["status"] == "awaiting_choice"
    assert any(b["code"] == "technique_requires_material" and b["targetId"] == "ducking" for b in plan["blockers"])


def test_scaled_clip_is_checked_before_render():
    doc = document(1920, 1080)
    doc.composition.media_timeline.tracks[0].clips[0].transform = {"scale": 4}
    assert ("clip", "clip_operation_unsupported") in inspect_document(doc)


def test_render_receipt_rejects_missing_layer_and_omission_that_still_exists():
    from types import SimpleNamespace

    from app.services.studios.contextual_editing import verify_render_receipt

    plan = SimpleNamespace(
        draft_document=document(), operations=[SimpleNamespace(operation_id="decision", target_id="clip", kind="keep")]
    )
    receipt = SimpleNamespace(rendered_layer_ids=[], rendered_audio_clip_ids=[], rendered_caption_track_ids=[])
    with pytest.raises(ValueError, match="editing_render_coverage_incomplete"):
        verify_render_receipt(plan, receipt)
    receipt.rendered_layer_ids = ["clip"]
    assert verify_render_receipt(plan, receipt)[0]["operationId"] == "decision"
    plan.operations[0].kind = "omit_optional"
    with pytest.raises(ValueError, match="editing_operation_coverage_incomplete"):
        verify_render_receipt(plan, receipt)


def attach_transcript(project):
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.domain.studios.contracts import TranscriptDocumentV1
    from app.models import StudioMediaIngest, StudioTranscript

    with SessionLocal() as db:
        ingest = db.scalar(select(StudioMediaIngest).where(StudioMediaIngest.asset_id == project["asset"]))
        stamp = datetime.now(UTC)
        transcript = TranscriptDocumentV1(
            id="selection-transcript",
            workspace_id=project["workspace"],
            media_ingest_id=ingest.id,
            asset_id=project["asset"],
            status="reviewed",
            segments=[
                {
                    "id": "sentence",
                    "startMicroseconds": 400_000,
                    "endMicroseconds": 1_600_000,
                    "text": "Não garante resultado.",
                }
            ],
            created_by=ingest.requested_by,
            updated_by=ingest.requested_by,
            created_at=stamp,
            updated_at=stamp,
        )
        db.add(
            StudioTranscript(
                id=transcript.id,
                workspace_id=project["workspace"],
                media_ingest_id=ingest.id,
                asset_id=project["asset"],
                status="reviewed",
                revision=1,
                version=1,
                provider="manual",
                transcript_document=transcript.model_dump(mode="json", by_alias=True),
                idempotency_key="selection-transcript",
                created_by=ingest.requested_by,
                updated_by=ingest.requested_by,
            )
        )
        db.commit()
    return transcript


def test_source_selection_keeps_negation_and_retimes_captions(client, project, monkeypatch):
    transcript = attach_transcript(project)
    plan = create_plan(
        client,
        project,
        beats=[
            {
                "id": "beat",
                "clipId": "clip",
                "purpose": "Explicar",
                "transcriptId": transcript.id,
                "transcriptRevision": 1,
                "captionFromTranscript": True,
                "sourceDecisions": [
                    {
                        "id": "keep-sentence",
                        "operation": "keep",
                        "startMicroseconds": 200_000,
                        "endMicroseconds": 1_800_000,
                        "status": "suggested",
                    }
                ],
            }
        ],
    )
    assert plan["status"] == "ready", plan["blockers"]
    timeline = plan["draftDocument"]["composition"]["mediaTimeline"]
    assert timeline["durationFrames"] == 40
    assert timeline["tracks"][0]["clips"][0]["source"]["startMicroseconds"] == 200_000
    cue = next(t["cues"][0] for t in timeline["tracks"] if t["kind"] == "caption")
    assert cue["text"] == "Não garante resultado."
    assert cue["timeline"] == {"startFrame": 5, "durationFrames": 30}
    assert plan["sourceTranscripts"][transcript.id]["revision"] == 1
    assert any(o["kind"] == "assemble" for o in plan["operations"])
    from app import tasks
    from app.database import SessionLocal
    from app.models import LibraryAsset, StudioGenerationJob
    from app.services.studios.jobs import execute_job_once

    headers = {"Authorization": f"Bearer {project['token']}"}
    applied = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/apply",
        headers=headers,
        json={"expectedPlanRevision": 1},
    )
    assert applied.status_code == 200, applied.text
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    queued = client.post(
        "/api/v1/studios/v1/video-renders",
        headers={**headers, "Idempotency-Key": "selected-render"},
        json={
            "workspaceId": project["workspace"],
            "documentId": project["document"],
            "expectedDocumentRevision": 2,
            "expectedDocumentVersion": 1,
            "provider": "builtin.ffmpeg-contextual-v1",
            "contextualPlanId": plan["id"],
            "output": {"width": 320, "height": 320, "fps": 25},
        },
    )
    assert queued.status_code == 202, queued.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, queued.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        asset = db.get(LibraryAsset, job.result_payload["artifact"]["assetId"])
        assert len(asset.object_metadata["contextualEditing"]["operationChecks"]) == len(plan["operations"])


def test_unsafe_selection_offers_original_without_changing_source(client, project):
    transcript = attach_transcript(project)
    plan = create_plan(
        client,
        project,
        beats=[
            {
                "id": "beat",
                "clipId": "clip",
                "purpose": "Explicar",
                "transcriptId": transcript.id,
                "transcriptRevision": 1,
                "sourceDecisions": [
                    {"id": "remove-negation", "operation": "remove", "startMicroseconds": 0, "endMicroseconds": 800_000}
                ],
            }
        ],
    )
    assert plan["status"] == "awaiting_choice"
    blocker = next(b for b in plan["blockers"] if b["targetId"] == "assembly")
    assert blocker["code"] == "editing_selection_would_change_message"
    source = plan["draftDocument"]["composition"]["mediaTimeline"]["tracks"][0]["clips"][0]["source"]
    assert source["startMicroseconds"] == 0 and source["durationMicroseconds"] == 2_000_000
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/choices",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={"expectedPlanRevision": 1, "blockerId": blocker["id"], "alternativeId": "keep-original"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ready"
    assert response.json()["draftDocument"]["composition"]["mediaTimeline"]["durationFrames"] == 50


def test_changed_transcript_invalidates_plan_even_with_same_document(client, project):
    from app.database import SessionLocal
    from app.models import StudioTranscript

    transcript = attach_transcript(project)
    plan = create_plan(
        client,
        project,
        beats=[
            {
                "id": "beat",
                "clipId": "clip",
                "purpose": "Explicar",
                "transcriptId": transcript.id,
                "transcriptRevision": 1,
                "captionFromTranscript": True,
            }
        ],
    )
    with SessionLocal() as db:
        db.get(StudioTranscript, transcript.id).revision = 2
        db.commit()
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/apply",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={"expectedPlanRevision": 1},
    )
    assert response.status_code == 409, response.text


def test_reorder_preserves_all_clips_and_attached_captions():
    from app.domain.studios.contracts import CaptionTrackV1
    from app.services.studios.contextual_assembly import assemble

    doc = document()
    timeline = doc.composition.media_timeline
    first = timeline.tracks[0].clips[0]
    second = first.model_copy(deep=True)
    second.id = "second"
    second.timeline.start_frame = 50
    timeline.tracks[0].clips.append(second)
    timeline.duration_frames = 100
    timeline.tracks.append(
        CaptionTrackV1(
            id="existing-captions",
            cues=[
                {
                    "id": "qualification",
                    "timeline": {"startFrame": 55, "durationFrames": 35},
                    "text": "Depende das condições.",
                }
            ],
        )
    )
    reordered, trace = assemble(doc, [], {}, ["second", "clip"])
    assert [c.id for c in reordered.tracks[0].clips] == ["second", "clip"]
    assert reordered.tracks[1].cues[0].timeline.start_frame == 5
    assert reordered.tracks[1].cues[0].text == "Depende das condições."
    assert trace[0]["fromStartFrame"] == 50
    assert first.timeline.start_frame == 0  # original untouched
    with pytest.raises(ValueError, match="preserve_all_clips"):
        assemble(doc, [], {}, ["second"])


def test_reference_profile_changes_composition_without_changing_brand(client, project):
    from app.services.studios.editing_repertoire import seed_techniques

    technique = seed_techniques()[1].model_dump(mode="json", by_alias=True)
    technique.update(
        id="product-window",
        title="Janela de demonstração",
        requiredCapabilities=["multitrack"],
        compositionProfile={
            "supportWidthRatio": 0.7,
            "supportHeightRatio": 0.3,
            "entrance": "fade",
            "entranceSeconds": 0.4,
        },
    )
    response = client.post(
        f"/api/v1/studios/v1/editing/observations?workspace_id={project['workspace']}",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={
            "technique": technique,
            "sourceUrl": technique["sources"][0],
            "observedAt": "2026-01-01T12:00:00Z",
            "metrics": {"views": 1_000_000},
        },
    )
    assert response.status_code == 200, response.text
    plan = create_plan(
        client,
        project,
        referenceTechniqueIds=["product-window"],
        beats=[{"id": "beat", "clipId": "clip", "purpose": "Demonstrar", "supportAssetId": project["asset"]}],
    )
    assert plan["status"] == "ready", plan["blockers"]
    draft = plan["draftDocument"]
    support = next(t["clips"][0] for t in draft["composition"]["mediaTimeline"]["tracks"] if t["kind"] == "overlay")
    assert support["transform"]["width"] == 224 and support["transform"]["height"] == 96
    assert support["effects"][0]["kind"] == "fade"
    assert draft["composition"]["pages"][0]["background"] == document().composition.pages[0].background
    evidence = next(e for e in plan["editorialEvidence"] if e.get("techniqueId") == "product-window")
    assert evidence["freshness"] == "historical" and evidence["causalPerformanceClaim"] is False
    assert any("product-window" in o["techniqueIds"] for o in plan["operations"])


def test_requested_reference_needs_material(client, project):
    plan = create_plan(client, project, referenceTechniqueIds=["depth"])
    assert any(b["code"] == "reference_material_required" for b in plan["blockers"])


def test_omitting_technique_never_deletes_original_with_same_id(client, project):
    from app.database import SessionLocal
    from app.models import CreativeDocument
    from app.services.studios.compatibility import persist_contract, record_to_contract

    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks[0].clips[0].id = "tracking"
        persist_contract(record, doc)
        db.commit()
    plan = create_plan(client, project, requiredTechniques=["tracking"])
    blocker = next(b for b in plan["blockers"] if b["code"] == "technique_unavailable")
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/choices",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={"expectedPlanRevision": 1, "blockerId": blocker["id"], "alternativeId": "omit"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["draftDocument"]["composition"]["mediaTimeline"]["tracks"][0]["clips"][0]["id"] == "tracking"
    assert response.json()["status"] == "ready"
