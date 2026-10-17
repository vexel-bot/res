from pathlib import Path

from conftest import register

from app.database import SessionLocal
from app.domain.studios.contracts import FrameRateV1, MediaProbeResultV1, VideoStreamV1
from app.models import LibraryAsset, StudioMediaIngest
from app.providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from app.routers import assets as assets_router


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class FakeMediaProbeProvider:
    name = "builtin.ffprobe"
    version = "fake-ffprobe-1"

    def probe(self, path: Path, *, asset_id: str, checksum_sha256: str | None) -> MediaProbeResultV1:
        assert path.read_bytes()[4:8] == b"ftyp"
        return MediaProbeResultV1(
            provider=self.name,
            provider_version=self.version,
            asset_id=asset_id,
            checksum_sha256=checksum_sha256,
            container="mov,mp4,m4a,3gp,3g2,mj2",
            duration_microseconds=5_000_000,
            size_bytes=path.stat().st_size,
            bitrate=1_200_000,
            video_streams=[
                VideoStreamV1(
                    index=0,
                    codec="h264",
                    width=1080,
                    height=1920,
                    pixel_format="yuv420p",
                    frame_rate=FrameRateV1(numerator=30, denominator=1),
                    duration_microseconds=5_000_000,
                )
            ],
            provider_trace={"fixture": True},
        )


def test_media_ingest_is_tenant_scoped_idempotent_and_runs_outside_request(client, tmp_path, monkeypatch):
    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    monkeypatch.setitem(MEDIA_PROBE_PROVIDERS, "builtin.ffprobe", FakeMediaProbeProvider())
    token, workspace = register(client, "media-ingest@example.com", "Media Ingest")
    other_token, _ = register(client, "media-ingest-other@example.com", "Other Media")
    video_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "UGC source"},
        files={"file": ("ugc.mp4", video_bytes, "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    asset_id = uploaded.json()["id"]

    from app import tasks

    queued: list[str] = []
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    headers = {**auth(token), "Idempotency-Key": "media-ingest-ugc-001"}
    created = client.post(
        "/api/v1/studios/v1/media-ingests",
        headers=headers,
        json={"workspaceId": workspace, "assetId": asset_id},
    )
    assert created.status_code == 202, created.text
    ingest = created.json()
    assert ingest["status"] == "pending"
    assert ingest["generationJobId"] == queued[0]

    replay = client.post(
        "/api/v1/studios/v1/media-ingests",
        headers=headers,
        json={"workspaceId": workspace, "assetId": asset_id},
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == ingest["id"]
    assert queued == [ingest["generationJobId"]]

    assert client.get(
        "/api/v1/studios/v1/media-ingests",
        headers=auth(other_token),
        params={"workspace_id": workspace},
    ).status_code == 404
    direct_job = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "direct-media-probe-001"},
        json={
            "workspaceId": workspace,
            "jobType": "media_probe",
            "provider": "builtin.ffprobe",
            "request": {"mediaIngestId": ingest["id"], "assetId": asset_id},
        },
    )
    assert direct_job.status_code == 422
    assert direct_job.json()["detail"]["code"] == "use_media_ingest_endpoint"

    assert tasks.execute_studio_generation.run(ingest["generationJobId"]) == {
        "status": "succeeded",
        "jobId": ingest["generationJobId"],
    }
    ready = client.get(
        f"/api/v1/studios/v1/media-ingests/{ingest['id']}",
        headers=auth(token),
    )
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["mediaInfo"]["videoStreams"][0]["height"] == 1920
    assert ready.json()["mediaInfo"]["provider"] == "builtin.ffprobe"

    with SessionLocal() as db:
        record = db.get(StudioMediaIngest, ingest["id"])
        asset = db.get(LibraryAsset, asset_id)
        assert record.validation_errors == []
        assert len(asset.checksum_sha256) == 64
        assert asset.object_metadata["mediaProbeSchema"] == "studio.media-probe.v1"
