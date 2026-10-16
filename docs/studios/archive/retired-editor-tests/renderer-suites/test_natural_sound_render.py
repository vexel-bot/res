import hashlib
import math
import struct
import subprocess
import wave

import pytest
from conftest import register
from test_ffmpeg_ugc_video_render_provider import create_source, ugc_fixture

from app.domain.studios.contracts import CreativeDocumentV1
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS


def make_sound(path, frequency=880):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        output.writeframes(b"".join(struct.pack("<h", round(8000 * math.sin(2 * math.pi * frequency * i / 48000)))
                                  for i in range(96000)))


def sound_document(paths):
    document, request = ugc_fixture()
    raw = document.model_dump(by_alias=True, mode="json")
    raw["composition"]["mediaTimeline"]["tracks"][1]["muted"] = True
    for index, path in enumerate(paths):
        asset_id = f"sound-{index}"
        raw["assets"].append({
            "id": asset_id, "version": 1, "mediaType": "audio/wav", "origin": "workspace",
            "rightsStatus": "unknown", "checksum": hashlib.sha256(path.read_bytes()).hexdigest(),
            "provenance": {"purpose": "natural-sound-candidate", "source": "user-upload"},
        })
        raw["composition"]["mediaTimeline"]["tracks"].append({
            "id": f"audio-natural-{index}", "kind": "audio", "name": "Technical sound fixture",
            "clips": [{"id": f"sound-clip-{index}", "assetId": asset_id,
                       "timeline": {"startFrame": 9 + index * 18, "durationFrames": 9},
                       "source": {"startMicroseconds": 200_000, "durationMicroseconds": 300_000},
                       "gainDb": -6, "fadeInFrames": 1, "fadeOutFrames": 1}],
        })
    request.asset_ids = [asset["id"] for asset in raw["assets"]]
    return CreativeDocumentV1.model_validate(raw), request


def test_external_sounds_render_at_requested_times_without_original_voice(tmp_path):
    source = tmp_path / "source.mp4"
    create_source(source)
    paths = [tmp_path / "sound-a.wav", tmp_path / "sound-b.wav"]
    for index, path in enumerate(paths):
        make_sound(path, 880 + index * 440)
    original_bytes = [path.read_bytes() for path in [source, *paths]]
    document, request = sound_document(paths)
    assets = {"asset-source": source, **{f"sound-{i}": path for i, path in enumerate(paths)}}
    provider = VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-ugc-v1"]
    plan = provider._plan(document, request, assets)
    graph = provider._filter_graph(plan, 1080, 1920)
    assert "[0:a" not in graph
    assert "amix=inputs=3:duration=first" in graph
    destination = tmp_path / "mixed.mp4"
    result = provider.render(document, request, assets, destination, lambda _: None, lambda: False)
    assert result.frames_rendered == 48
    assert "ffmpeg_ugc_natural_sound_review_pending" in result.warnings
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(destination), "-vn", "-ac", "1", "-ar", "48000",
                          "-f", "s16le", "pipe:1"], capture_output=True, check=True, timeout=60).stdout
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)

    def rms(start, end):
        section = samples[round(start * 48000):round(end * 48000)]
        return math.sqrt(sum(value * value for value in section) / len(section))

    assert rms(0.05, 0.2) < 2
    assert 2000 < rms(0.4, 0.5) < 3600  # -6 dB, not source's 440 Hz or normalized amix.
    assert rms(0.7, 0.8) < 2
    assert 2000 < rms(1.0, 1.1) < 3600
    assert rms(1.35, 1.5) < 2
    assert [path.read_bytes() for path in [source, *paths]] == original_bytes


def test_licensed_music_requires_verified_rights_and_explicit_policy(tmp_path):
    source = tmp_path / "source.mp4"
    create_source(source)
    music = tmp_path / "music.wav"
    make_sound(music, 660)
    document, request = sound_document([music])
    reference = document.assets[-1]
    reference.provenance["purpose"] = "licensed-music-candidate"
    provider = VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-ugc-v1"]
    assets = {"asset-source": source, "sound-0": music}

    with pytest.raises(ValueError, match="ffmpeg_ugc_music_rights_required"):
        provider._plan(document, request, assets)

    reference.rights_status = "verified"
    with pytest.raises(ValueError, match="ffmpeg_ugc_music_policy_required"):
        provider._plan(document, request, assets)

    document.composition.narrative["musicPolicy"] = "licensed-with-rights"
    plan = provider._plan(document, request, assets)
    assert len(plan.sounds) == 1
    assert "ffmpeg_ugc_licensed_music_mixed" in plan.warnings
    assert "ffmpeg_ugc_natural_sound_review_pending" not in plan.warnings


@pytest.mark.parametrize("mutation,code", [
    ("duration", "ffmpeg_ugc_sound_range_invalid"),
    ("purpose", "ffmpeg_ugc_sound_reference_invalid"),
    ("gain", "ffmpeg_ugc_sound_range_invalid"),
    ("pan", "ffmpeg_ugc_sound_effects_unsupported"),
    ("source", "ffmpeg_ugc_sound_source_out_of_bounds"),
])
def test_sound_renderer_rejects_unsupported_or_invalid_inputs(tmp_path, mutation, code):
    source = tmp_path / "source.mp4"
    create_source(source)
    sound = tmp_path / "sound.wav"
    make_sound(sound)
    document, request = sound_document([sound])
    clip = document.composition.media_timeline.tracks[-1].clips[0]
    if mutation == "duration":
        clip.timeline.start_frame = 45
    elif mutation == "purpose":
        document.assets[-1].provenance = {}
    elif mutation == "gain":
        clip.gain_db = math.nan
    elif mutation == "pan":
        clip.pan = 0.5
    else:
        clip.source.start_microseconds = 1_900_000
    provider = VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-ugc-v1"]
    with pytest.raises(ValueError, match=code):
        provider.render(document, request, {"asset-source": source, "sound-0": sound},
                        tmp_path / "invalid.mp4", lambda _: None, lambda: False)


def test_audio_ingest_reuses_worker_and_tenant_boundary(client, tmp_path, monkeypatch):
    from app import tasks
    from app.routers import assets as assets_router

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path / "storage"))
    queued = []
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    token, workspace = register(client, "sound-ingest@example.com")
    other, _ = register(client, "sound-ingest-other@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    sound = tmp_path / "sound.wav"
    make_sound(sound)
    upload = client.post("/api/v1/assets/upload", headers=headers,
                         data={"workspace_id": workspace, "title": "Technical sound fixture"},
                         files={"file": ("sound.wav", sound.read_bytes(), "audio/wav")})
    assert upload.status_code == 201, upload.text
    asset_id = upload.json()["id"]
    ingest_headers = {**headers, "Idempotency-Key": "natural-sound-001"}
    payload = {"workspaceId": workspace, "assetId": asset_id}
    response = client.post("/api/v1/studios/v1/media-ingests", headers=ingest_headers, json=payload)
    assert response.status_code == 202, response.text
    ingest = response.json()
    assert ingest["status"] == "pending"
    replay = client.post("/api/v1/studios/v1/media-ingests", headers=ingest_headers, json=payload)
    assert replay.json()["id"] == ingest["id"]
    assert len(queued) == 1
    assert tasks.execute_studio_generation.run(ingest["generationJobId"])["status"] == "succeeded"
    ready = client.get(f"/api/v1/studios/v1/media-ingests/{ingest['id']}", headers=headers).json()
    assert ready["status"] == "ready"
    assert ready["mediaInfo"]["videoStreams"] == []
    assert len(ready["mediaInfo"]["audioStreams"]) == 1
    assert ready["mediaInfo"]["checksumSha256"] == hashlib.sha256(sound.read_bytes()).hexdigest()
    foreign = {"Authorization": f"Bearer {other}", "Idempotency-Key": "foreign-sound"}
    assert client.post("/api/v1/studios/v1/media-ingests", headers=foreign, json=payload).status_code == 404
    assert client.get(f"/api/v1/assets/{asset_id}/content", headers=foreign).status_code == 404


def test_silent_video_accepts_natural_sound_and_trimmed_away_sound_stays_silent(tmp_path):
    original = tmp_path / "original.mp4"
    create_source(original)
    source = tmp_path / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(original), "-c:v", "copy", "-an", str(source)],
                   check=True, timeout=30)
    sound = tmp_path / "sound.wav"
    make_sound(sound)
    document, request = sound_document([sound])
    timeline = document.composition.media_timeline
    timeline.tracks = [track for track in timeline.tracks if track.id != "audio-main"]
    # The fixture uses this ID for its paired original track.
    timeline.tracks = [track for track in timeline.tracks if not (
        track.kind == "audio" and all(clip.asset_id == "asset-source" for clip in track.clips)
    )]
    assets = {"asset-source": source, "sound-0": sound}
    provider = VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-ugc-v1"]
    result = provider.render(document, request, assets, tmp_path / "with-sound.mp4", lambda _: None, lambda: False)
    assert "ffmpeg_ugc_natural_sound_review_pending" in result.warnings
    timeline.tracks[-1].clips = []
    output = tmp_path / "detached.mp4"
    result = provider.render(document, request, assets, output, lambda _: None, lambda: False)
    assert "ffmpeg_ugc_natural_sound_review_pending" not in result.warnings
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(output), "-vn", "-f", "s16le", "pipe:1"],
                         capture_output=True, check=True, timeout=30).stdout
    assert len(pcm) > 48000 and not any(pcm)
