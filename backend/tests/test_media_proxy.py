import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import register

from app.database import SessionLocal
from app.domain.studios.contracts import (
    AudioStreamV1,
    FrameRateV1,
    MediaProbeResultV1,
    MediaProxyEncodeResultV1,
    MediaProxySpecV1,
    VideoStreamV1,
)
from app.models import LibraryAsset, StudioMediaIngest
from app.providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from app.providers.studios.media_proxy import MEDIA_PROXY_PROVIDERS, FFmpegMediaProxyProvider
from app.routers import assets as assets_router
from app.services.object_storage import get_object_storage


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class FakeMediaProbeProvider:
    name = "builtin.ffprobe"
    version = "fake-probe-1"

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
                    start_microseconds=0,
                )
            ],
        )


class FakeMediaProxyProvider:
    name = "builtin.ffmpeg-proxy"
    version = "fake-ffmpeg-1"

    def transcode(self, source, destination, spec, progress, is_cancelled):
        assert source.read_bytes()[4:8] == b"ftyp"
        assert spec.max_width == 720 and spec.max_height == 1280
        progress(55)
        assert not is_cancelled()
        destination.write_bytes(b"\x00\x00\x00\x18ftypisomproxy-video")
        return MediaProxyEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=720,
            height=1280,
            frame_rate=FrameRateV1(numerator=30, denominator=1),
            duration_microseconds=5_000_000,
            video_codec="h264",
            audio_codec="aac",
        )


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg binaries unavailable",
)
def test_ffmpeg_media_proxy_real_smoke(tmp_path):
    source = tmp_path / "source.mp4"
    destination = tmp_path / "proxy.mp4"
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
            "color=c=blue:s=360x640:r=30000/1001:d=1.001",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=1.001",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    progress: list[int] = []
    result = FFmpegMediaProxyProvider("ffmpeg", 60).transcode(
        source,
        destination,
        MediaProxySpecV1(max_width=360, max_height=640, target_fps=30),
        progress.append,
        lambda: False,
    )
    assert destination.stat().st_size > 0
    assert result.width == 360 and result.height == 640
    assert result.video_codec == "h264"
    assert result.audio_codec == "aac"
    assert progress == [15, 78]


def test_media_proxy_is_async_versioned_lineage_and_cancel_safe(client, tmp_path, monkeypatch):
    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    monkeypatch.setitem(MEDIA_PROBE_PROVIDERS, "builtin.ffprobe", FakeMediaProbeProvider())
    monkeypatch.setitem(MEDIA_PROXY_PROVIDERS, "builtin.ffmpeg-proxy", FakeMediaProxyProvider())
    token, workspace = register(client, "media-proxy@example.com", "Media Proxy")
    other_token, _ = register(client, "media-proxy-other@example.com", "Other Proxy")
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "UGC original"},
        files={
            "file": (
                "ugc.mp4",
                b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2",
                "video/mp4",
            )
        },
    )
    assert uploaded.status_code == 201, uploaded.text
    source_asset_id = uploaded.json()["id"]

    from app import tasks

    queued: list[str] = []
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    ingest = client.post(
        "/api/v1/studios/v1/media-ingests",
        headers={**auth(token), "Idempotency-Key": "proxy-ingest-001"},
        json={"workspaceId": workspace, "assetId": source_asset_id},
    ).json()
    tasks.execute_studio_generation.run(ingest["generationJobId"])

    body = {
        "workspaceId": workspace,
        "spec": {
            "maxWidth": 720,
            "maxHeight": 1280,
            "targetFps": 30,
            "quality": "draft",
        },
    }
    headers = {**auth(token), "Idempotency-Key": "editing-proxy-001"}
    created = client.post(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}/proxy",
        headers=headers,
        json=body,
    )
    assert created.status_code == 202, created.text
    job = created.json()
    assert job["status"] == "queued"
    assert job["executionCapability"] == "media_cpu"
    assert job["queueName"] == "studio.media.cpu"

    replay = client.post(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}/proxy",
        headers=headers,
        json=body,
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == job["id"]
    assert queued.count(job["id"]) == 1
    assert client.post(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}/proxy",
        headers={**auth(other_token), "Idempotency-Key": "foreign-proxy-001"},
        json=body,
    ).status_code == 404

    direct = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "direct-proxy-001"},
        json={
            "workspaceId": workspace,
            "jobType": "video_proxy",
            "provider": "builtin.ffmpeg-proxy",
            "request": {"mediaIngestId": ingest["id"]},
        },
    )
    assert direct.status_code == 422
    assert direct.json()["detail"]["code"] == "use_media_proxy_endpoint"

    assert tasks.execute_studio_generation.run(job["id"])["status"] == "succeeded"
    completed = client.get(f"/api/v1/studios/v1/jobs/{job['id']}", headers=auth(token)).json()
    result = completed["result"]
    assert result["schemaVersion"] == "studio.media-proxy-result.v1"
    assert result["sourceAssetId"] == source_asset_id
    assert result["width"] == 720 and result["height"] == 1280
    assert result["timeMap"]["sourceAssetId"] == source_asset_id
    assert result["timeMap"]["maxDriftMicroseconds"] == 0
    assert result["timeMap"]["segments"] == [
        {
            "sourceStartMicroseconds": 0,
            "representationStartMicroseconds": 0,
            "durationMicroseconds": 5_000_000,
            "rateNumerator": 1,
            "rateDenominator": 1,
        }
    ]
    ready = client.get(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}", headers=auth(token)
    ).json()
    assert ready["proxyAssetId"] == result["proxyAssetId"]

    with SessionLocal() as db:
        proxy_asset = db.get(LibraryAsset, result["proxyAssetId"])
        source_asset = db.get(LibraryAsset, source_asset_id)
        ingest_record = db.get(StudioMediaIngest, ingest["id"])
        assert proxy_asset.object_metadata["derivedFromAssetId"] == source_asset_id
        assert proxy_asset.object_metadata["derivation"] == "video_proxy"
        assert proxy_asset.object_metadata["mediaTimeMap"] == result["timeMap"]
        assert proxy_asset.checksum_sha256 != source_asset.checksum_sha256
        assert get_object_storage(proxy_asset.storage_backend).exists(proxy_asset.storage_key)
        first_proxy_id = ingest_record.proxy_asset_id
        assert ingest_record.proxy_time_map == result["timeMap"]

    cancelled = client.post(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}/proxy",
        headers={**auth(token), "Idempotency-Key": "editing-proxy-cancel-001"},
        json=body,
    ).json()
    cancelled_response = client.post(
        f"/api/v1/studios/v1/jobs/{cancelled['id']}/cancel",
        headers=auth(token),
        json={"reason": "User changed source"},
    )
    assert cancelled_response.status_code == 200
    assert tasks.execute_studio_generation.run(cancelled["id"])["status"] == "cancelled"
    with SessionLocal() as db:
        assert db.get(StudioMediaIngest, ingest["id"]).proxy_asset_id == first_proxy_id
