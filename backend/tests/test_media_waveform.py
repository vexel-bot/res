import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import register

from app.database import SessionLocal
from app.domain.studios.contracts import (
    AudioStreamV1,
    AudioWaveformBucketV1,
    AudioWaveformManifestV1,
    AudioWaveformSpecV1,
    FrameRateV1,
    MediaProbeResultV1,
    MediaProxyEncodeResultV1,
    MediaProxySpecV1,
    VideoStreamV1,
)
from app.models import LibraryAsset, StudioMediaIngest
from app.providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from app.providers.studios.media_waveform import (
    MEDIA_WAVEFORM_PROVIDERS,
    FFmpegMediaWaveformProvider,
)
from app.routers import assets as assets_router
from app.services.object_storage import get_object_storage, sha256_file
from app.services.studios.media_proxy import _build_time_map


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def spec_digest(spec: AudioWaveformSpecV1) -> str:
    raw = json.dumps(
        spec.model_dump(by_alias=True, mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class FakeWaveformProbeProvider:
    name = "builtin.ffprobe"
    version = "fake-waveform-probe-1"

    def probe(self, path: Path, *, asset_id: str, checksum_sha256: str | None) -> MediaProbeResultV1:
        return MediaProbeResultV1(
            provider=self.name,
            provider_version=self.version,
            asset_id=asset_id,
            checksum_sha256=checksum_sha256,
            container="mp4",
            duration_microseconds=5_000_000,
            size_bytes=path.stat().st_size,
            video_streams=[
                VideoStreamV1(
                    index=0,
                    codec="h264",
                    width=1080,
                    height=1920,
                    frame_rate=FrameRateV1(numerator=30, denominator=1),
                )
            ],
            audio_streams=[
                AudioStreamV1(
                    index=1,
                    codec="aac",
                    sample_rate=48_000,
                    channels=1,
                    start_microseconds=250_000,
                )
            ],
        )


class FakeMediaWaveformProvider:
    name = "builtin.ffmpeg-waveform"
    version = "fake-waveform-1"

    def generate(
        self,
        source,
        destination,
        *,
        media_ingest_id,
        source_asset_id,
        source_checksum_sha256,
        audio_stream_index,
        start_microseconds,
        source_duration_microseconds,
        spec,
        progress,
        is_cancelled,
    ):
        assert source.read_bytes()[4:8] == b"ftyp"
        assert audio_stream_index == 1
        assert start_microseconds == 250_000
        assert source_duration_microseconds == 5_000_000
        assert not is_cancelled()
        progress(55)
        manifest = AudioWaveformManifestV1(
            media_ingest_id=media_ingest_id,
            source_asset_id=source_asset_id,
            source_checksum_sha256=source_checksum_sha256,
            audio_stream_index=audio_stream_index,
            start_microseconds=start_microseconds,
            duration_microseconds=20_000,
            sample_rate=spec.sample_rate,
            samples_per_bucket=spec.sample_rate // spec.points_per_second,
            total_samples=960,
            bucket_count=2,
            buckets=[
                AudioWaveformBucketV1(minimum=-1200, maximum=1500, rms=800),
                AudioWaveformBucketV1(minimum=-800, maximum=900, rms=500),
            ],
            provider=self.name,
            provider_version=self.version,
            spec=spec,
            spec_digest=spec_digest(spec),
        )
        destination.write_text(
            json.dumps(manifest.model_dump(by_alias=True, mode="json"), sort_keys=True),
            encoding="utf-8",
        )
        return manifest


def test_media_waveform_is_async_tenant_scoped_and_persists_json_asset(
    client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    monkeypatch.setitem(MEDIA_PROBE_PROVIDERS, "builtin.ffprobe", FakeWaveformProbeProvider())
    monkeypatch.setitem(
        MEDIA_WAVEFORM_PROVIDERS,
        "builtin.ffmpeg-waveform",
        FakeMediaWaveformProvider(),
    )
    token, workspace = register(client, "waveform@example.com", "Waveform Studio")
    other_token, _ = register(client, "waveform-other@example.com", "Other Waveform")
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "UGC com voz"},
        files={
            "file": (
                "ugc.mp4",
                b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2",
                "video/mp4",
            )
        },
    )
    assert uploaded.status_code == 201, uploaded.text

    from app import tasks

    queued: list[str] = []
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    ingest = client.post(
        "/api/v1/studios/v1/media-ingests",
        headers={**auth(token), "Idempotency-Key": "waveform-ingest-001"},
        json={"workspaceId": workspace, "assetId": uploaded.json()["id"]},
    ).json()
    tasks.execute_studio_generation.run(ingest["generationJobId"])

    body = {
        "workspaceId": workspace,
        "spec": {"sampleRate": 48_000, "pointsPerSecond": 100, "includeRms": True},
    }
    headers = {**auth(token), "Idempotency-Key": "waveform-generate-001"}
    accepted = client.post(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}/waveform",
        headers=headers,
        json=body,
    )
    assert accepted.status_code == 202, accepted.text
    job = accepted.json()
    assert job["jobType"] == "media_waveform"
    assert job["provider"] == "builtin.ffmpeg-waveform"
    assert job["executionCapability"] == "media_cpu"
    assert job["queueName"] == "studio.media.cpu"
    replay = client.post(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}/waveform",
        headers=headers,
        json=body,
    )
    assert replay.status_code == 202 and replay.json()["id"] == job["id"]
    assert queued.count(job["id"]) == 1
    assert client.post(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}/waveform",
        headers={**auth(other_token), "Idempotency-Key": "waveform-foreign-001"},
        json=body,
    ).status_code == 404
    direct = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "waveform-direct-001"},
        json={
            "workspaceId": workspace,
            "jobType": "media_waveform",
            "provider": "builtin.ffmpeg-waveform",
            "request": {"mediaIngestId": ingest["id"]},
        },
    )
    assert direct.status_code == 422
    assert direct.json()["detail"]["code"] == "use_media_waveform_endpoint"

    assert tasks.execute_studio_generation.run(job["id"])["status"] == "succeeded"
    completed = client.get(f"/api/v1/studios/v1/jobs/{job['id']}", headers=auth(token)).json()
    result = completed["result"]
    assert result["schemaVersion"] == "studio.audio-waveform-result.v1"
    assert result["bucketCount"] == 2
    assert result["startMicroseconds"] == 250_000
    ready = client.get(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}",
        headers=auth(token),
    ).json()
    assert ready["waveformAssetId"] == result["waveformAssetId"]
    content = client.get(
        f"/api/v1/assets/{result['waveformAssetId']}/content",
        headers=auth(token),
    )
    assert content.status_code == 200
    manifest = content.json()
    assert manifest["schemaVersion"] == "studio.audio-waveform-manifest.v1"
    assert manifest["buckets"][0] == {"minimum": -1200, "maximum": 1500, "rms": 800}
    listed = client.get(
        "/api/v1/assets",
        params={"workspace_id": workspace},
        headers=auth(token),
    )
    assert listed.status_code == 200, listed.text
    public_waveform = next(asset for asset in listed.json() if asset["id"] == result["waveformAssetId"])
    assert public_waveform["type"] == "waveform"
    assert public_waveform["metadata"]["derivation"] == "audio_waveform"
    with SessionLocal() as db:
        ingest_record = db.get(StudioMediaIngest, ingest["id"])
        waveform_asset = db.get(LibraryAsset, result["waveformAssetId"])
        assert ingest_record.waveform_asset_id == waveform_asset.id
        assert waveform_asset.object_metadata["derivedFromAssetId"] == uploaded.json()["id"]
        assert waveform_asset.object_metadata["derivation"] == "audio_waveform"
        assert get_object_storage(waveform_asset.storage_backend).exists(waveform_asset.storage_key)


@pytest.mark.skipif(
    not shutil.which("ffmpeg"),
    reason="FFmpeg binary unavailable",
)
def test_ffmpeg_waveform_provider_streams_pcm_deterministically(tmp_path):
    source = tmp_path / "source.wav"
    first = tmp_path / "waveform-first.json"
    second = tmp_path / "waveform-second.json"
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=8000:duration=0.2",
            "-c:a",
            "pcm_s16le",
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    provider = FFmpegMediaWaveformProvider("ffmpeg", 30)
    spec = AudioWaveformSpecV1(sample_rate=8_000, points_per_second=100)
    progress: list[int] = []
    kwargs = {
        "media_ingest_id": "ingest-smoke",
        "source_asset_id": "asset-smoke",
        "source_checksum_sha256": sha256_file(source),
        "audio_stream_index": 0,
        "start_microseconds": 250_000,
        "source_duration_microseconds": 200_000,
        "spec": spec,
        "progress": progress.append,
        "is_cancelled": lambda: False,
    }
    manifest = provider.generate(source, first, **kwargs)
    provider.generate(source, second, **{**kwargs, "progress": lambda _: None})
    assert manifest.total_samples == 1600
    assert manifest.bucket_count == 20
    assert manifest.start_microseconds == 250_000
    assert any(bucket.maximum > 0 and bucket.minimum < 0 for bucket in manifest.buckets)
    assert first.read_bytes() == second.read_bytes()
    assert progress[0] == 12 and progress[-1] == 86
    with pytest.raises(InterruptedError, match="media_waveform_cancelled"):
        provider.generate(source, tmp_path / "cancelled.json", **{**kwargs, "is_cancelled": lambda: True})


@pytest.mark.skipif(
    not shutil.which("ffmpeg"),
    reason="FFmpeg binary unavailable",
)
def test_ffmpeg_waveform_provider_clamps_aac_padding_to_probed_duration(tmp_path):
    source = tmp_path / "source.m4a"
    destination = tmp_path / "waveform.json"
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000:duration=2",
            "-c:a",
            "aac",
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    provider = FFmpegMediaWaveformProvider("ffmpeg", 30)
    manifest = provider.generate(
        source,
        destination,
        media_ingest_id="ingest-aac",
        source_asset_id="asset-aac",
        source_checksum_sha256=sha256_file(source),
        audio_stream_index=0,
        start_microseconds=0,
        source_duration_microseconds=2_000_000,
        spec=AudioWaveformSpecV1(sample_rate=48_000, points_per_second=100),
        progress=lambda _: None,
        is_cancelled=lambda: False,
    )
    assert manifest.total_samples == 96_000
    assert manifest.duration_microseconds == 2_000_000


def test_proxy_time_map_fails_closed_when_duration_drifts_beyond_one_frame():
    source = LibraryAsset(
        id="source-asset",
        workspace_id="workspace",
        title="source",
        asset_type="video",
        tags=[],
        checksum_sha256="a" * 64,
    )
    proxy = LibraryAsset(
        id="proxy-asset",
        workspace_id="workspace",
        title="proxy",
        asset_type="video",
        tags=[],
        checksum_sha256="b" * 64,
    )
    ingest = StudioMediaIngest(
        id="ingest",
        workspace_id="workspace",
        asset_id=source.id,
        status="ready",
        probe_provider="builtin.ffprobe",
        media_info=MediaProbeResultV1(
            provider="builtin.ffprobe",
            provider_version="test",
            asset_id=source.id,
            checksum_sha256=source.checksum_sha256,
            container="mp4",
            duration_microseconds=5_000_000,
            size_bytes=100,
            video_streams=[
                VideoStreamV1(
                    index=0,
                    codec="h264",
                    width=1080,
                    height=1920,
                    frame_rate=FrameRateV1(numerator=30, denominator=1),
                )
            ],
        ).model_dump(by_alias=True, mode="json"),
        validation_errors=[],
        idempotency_key="fixture",
        requested_by="user",
    )
    encoded = MediaProxyEncodeResultV1(
        provider="builtin.ffmpeg-proxy",
        provider_version="test",
        width=720,
        height=1280,
        frame_rate=FrameRateV1(numerator=30, denominator=1),
        duration_microseconds=5_100_000,
        video_codec="h264",
    )
    with pytest.raises(ValueError, match="media_proxy_timing_drift"):
        _build_time_map(
            ingest=ingest,
            source_asset=source,
            proxy_asset=proxy,
            source_checksum=source.checksum_sha256,
            proxy_checksum=proxy.checksum_sha256,
            spec=MediaProxySpecV1(target_fps=30),
            encoded=encoded,
        )
