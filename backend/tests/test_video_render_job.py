from copy import deepcopy
from datetime import UTC, datetime

from conftest import register

from app.database import SessionLocal
from app.domain.studios.contracts import (
    VideoRenderEncodeResultV1,
    VideoTechnicalQualityCheckV1,
    VideoTechnicalQualityEvaluationV1,
    VideoTechnicalQualityMetricsV1,
)
from app.models import LibraryAsset, StudioGenerationJob
from app.providers.studios.video_quality import VIDEO_TECHNICAL_QUALITY_PROVIDERS
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.jobs import execute_job_once


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class FakeVideoRenderProvider:
    name = "hyperframes.cli"
    version = "fake-hyperframes-1"

    def render(self, document, request, assets, destination, progress, is_cancelled):
        assert document.revision == 1
        assert document.title == "UGC render fixado"
        assert request.document_revision == 1
        assert request.page_ids == ["scene-1"]
        assert len(assets) == 1
        source = next(iter(assets.values()))
        assert source.is_file()
        assert source.read_bytes() == b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
        progress(45)
        assert not is_cancelled()
        destination.write_bytes(b"\x00\x00\x00\x18ftypisomrender-video")
        return VideoRenderEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=request.output.width,
            height=request.output.height,
            duration_ms=1000,
            fps=request.output.fps,
            video_codec="h264",
            audio_codec="aac",
            render_duration_ms=125,
            frames_rendered=30,
            peak_rss_mb=128,
        )


class FakeVideoTechnicalQualityProvider:
    name = "builtin.ffmpeg-qc-v1"
    version = "fake-qc-1"

    def evaluate(self, artifact, *, expected, expected_duration_ms, policy, is_cancelled):
        assert artifact.read_bytes().endswith(b"render-video")
        assert expected_duration_ms == 1000
        assert not is_cancelled()
        return VideoTechnicalQualityEvaluationV1(
            provider=self.name,
            provider_version=self.version,
            policy=policy,
            status="passed",
            metrics=VideoTechnicalQualityMetricsV1(
                video_duration_ms=1000,
                audio_duration_ms=1000,
                duration_delta_ms=0,
                av_start_delta_ms=0,
                av_duration_delta_ms=0,
                black_duration_ms=0,
                black_frame_ratio=0,
                integrated_loudness_lufs=-16,
                true_peak_dbfs=-3,
                silence_duration_ms=0,
                silence_ratio=0,
            ),
            checks=[
                VideoTechnicalQualityCheckV1(
                    id="video_stream_count",
                    severity="blocker",
                    status="passed",
                    actual=1,
                    expected="1",
                    message="valid",
                )
            ],
            evaluated_at=datetime.now(UTC),
        )


def test_video_render_pins_document_and_persists_output_lineage(client, tmp_path, monkeypatch):
    from app.routers import assets as assets_router

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    token, workspace = register(client, "video-render@example.com", "Video Render")
    other_token, _ = register(client, "video-render-other@example.com", "Other Render")
    source_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
    uploaded = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "UGC source privado"},
        files={"file": ("ugc-source.mp4", source_bytes, "video/mp4")},
    )
    assert uploaded.status_code == 201, uploaded.text
    source_asset = uploaded.json()
    created = client.post(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "UGC render fixado",
            "contentType": "video",
            "brandRevision": 1,
            "brief": {
                "objective": "Renderizar UGC",
                "audience": "Social media",
                "hook": "Comece agora",
            },
            "composition": {
                "narrative": {
                    "audioMode": "natural-foley-only",
                    "voicePolicy": "prohibited",
                    "musicPolicy": "prohibited",
                    "captionMode": "editorial-burned-in",
                },
                "pages": [
                    {
                        "id": "scene-1",
                        "role": "ugc",
                        "width": 1080,
                        "height": 1920,
                        "safeArea": 48,
                        "background": "#10181c",
                        "layers": [],
                    }
                ],
                "mediaTimeline": {
                    "durationFrames": 30,
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "tracks": [
                        {
                            "id": "ugc-video",
                            "kind": "video",
                            "name": "UGC",
                            "muted": True,
                            "clips": [
                                {
                                    "id": "ugc-clip-1",
                                    "assetId": source_asset["id"],
                                    "timeline": {"startFrame": 0, "durationFrames": 30},
                                    "source": {"startMicroseconds": 0, "durationMicroseconds": 1_000_000},
                                }
                            ],
                        }
                    ],
                },
            },
            "assets": [
                {
                    "id": source_asset["id"],
                    "mediaType": "video/mp4",
                    "checksum": source_asset["checksumSha256"],
                    "rightsStatus": "verified",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    document = created.json()
    render_body = {
        "workspaceId": workspace,
        "documentId": document["documentId"],
        "expectedDocumentRevision": 1,
        "expectedDocumentVersion": 1,
        "pageIds": ["scene-1"],
        "provider": "hyperframes.cli",
        "output": {
            "format": "mp4",
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "videoCodec": "h264",
            "audioCodec": "aac",
            "quality": "draft",
        },
    }
    unavailable = client.post(
        "/api/v1/studios/v1/video-renders",
        headers={**auth(token), "Idempotency-Key": "video-render-unavailable-001"},
        json=render_body,
    )
    assert unavailable.status_code == 422
    assert unavailable.json()["detail"]["code"] == "video_render_provider_unavailable"

    monkeypatch.setitem(VIDEO_RENDER_PROVIDERS, "hyperframes.cli", FakeVideoRenderProvider())
    monkeypatch.setitem(
        VIDEO_TECHNICAL_QUALITY_PROVIDERS,
        "builtin.ffmpeg-qc-v1",
        FakeVideoTechnicalQualityProvider(),
    )
    from app import tasks

    queued: list[str] = []
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    headers = {**auth(token), "Idempotency-Key": "video-render-ugc-001"}
    accepted = client.post(
        "/api/v1/studios/v1/video-renders",
        headers=headers,
        json=render_body,
    )
    assert accepted.status_code == 202, accepted.text
    job = accepted.json()
    assert job["executionCapability"] == "media_cpu"
    assert job["queueName"] == "studio.media.cpu"
    assert job["request"]["documentSnapshot"]["revision"] == 1
    replay = client.post(
        "/api/v1/studios/v1/video-renders",
        headers=headers,
        json=render_body,
    )
    assert replay.status_code == 202 and replay.json()["id"] == job["id"]
    assert queued == [job["id"]]

    with SessionLocal() as db:
        job_record = db.get(StudioGenerationJob, job["id"])
        execution_status = execute_job_once(db, job_record)
        assert execution_status == "succeeded", (job_record.error_code, job_record.error_message)
    completed = client.get(f"/api/v1/studios/v1/jobs/{job['id']}", headers=auth(token)).json()
    result = completed["result"]
    assert result["schemaVersion"] == "studio.video-render-result.v1"
    assert result["documentRevision"] == 1 and result["documentVersion"] == 1
    assert result["artifact"]["width"] == 1080
    assert result["provider"] == "hyperframes.cli"
    assert result["qualityEvaluation"]["status"] == "passed"
    assert client.get(f"/api/v1/studios/v1/jobs/{job['id']}", headers=auth(other_token)).status_code == 404
    recovered = client.get(
        "/api/v1/studios/v1/jobs",
        headers=auth(token),
        params={
            "workspace_id": workspace,
            "document_id": document["documentId"],
            "job_type": "video_render",
            "limit": 1,
        },
    )
    assert recovered.status_code == 200, recovered.text
    assert [record["id"] for record in recovered.json()] == [job["id"]]
    hidden = client.get(
        "/api/v1/studios/v1/jobs",
        headers=auth(other_token),
        params={"workspace_id": workspace},
    )
    assert hidden.status_code == 404

    with SessionLocal() as db:
        job_record = db.get(StudioGenerationJob, job["id"])
        failed_result = deepcopy(job_record.result_payload)
        failed_result["qualityEvaluation"]["status"] = "failed"
        failed_result["qualityEvaluation"]["checks"][0]["status"] = "failed"
        job_record.result_payload = failed_result
        db.commit()
    blocked_review = client.post(
        f"/api/v1/studios/v1/documents/{document['documentId']}/reviews",
        headers=auth(token),
        json={"comment": "QC deve bloquear", "renderJobId": job["id"]},
    )
    assert blocked_review.status_code == 422
    assert blocked_review.json()["detail"]["code"] == "studio_review_render_quality_failed"
    with SessionLocal() as db:
        job_record = db.get(StudioGenerationJob, job["id"])
        job_record.result_payload = result
        db.commit()

    review_response = client.post(
        f"/api/v1/studios/v1/documents/{document['documentId']}/reviews",
        headers=auth(token),
        json={"comment": "Revisar o MP4 exato", "renderJobId": job["id"]},
    )
    assert review_response.status_code == 201, review_response.text
    review = review_response.json()
    assert review["renderJobId"] == job["id"]
    assert review["renderAssetId"] == result["artifact"]["assetId"]
    assert review["renderChecksumSha256"] == result["artifact"]["checksumSha256"]
    assert review["snapshot"]["revision"] == 1
    assert review["listeningReview"] is None

    decision_url = f"/api/v1/studios/v1/reviews/{review['id']}/decisions"
    missing_listening = client.post(
        decision_url,
        headers=auth(token),
        json={"action": "approve", "comment": "A mídia visual foi aprovada."},
    )
    assert missing_listening.status_code == 409
    assert missing_listening.json()["detail"]["code"] == "studio_review_listening_required"
    listening = {
        "renderAssetId": review["renderAssetId"],
        "renderChecksumSha256": review["renderChecksumSha256"],
        "listenedEntireMix": True,
        "speechAbsent": "pass",
        "musicAbsent": "pass",
        "naturalSoundsCoherent": "fail",
        "mixBalanced": "inconclusive",
    }
    forged = client.post(
        decision_url,
        headers=auth(token),
        json={
            "action": "request_changes",
            "comment": "O som não acompanha o gesto.",
            "listeningReview": {**listening, "renderChecksumSha256": "0" * 64},
        },
    )
    assert forged.status_code == 409
    assert forged.json()["detail"]["code"] == "studio_review_listening_render_mismatch"
    with SessionLocal() as db:
        rendered_asset = db.get(LibraryAsset, review["renderAssetId"])
        rendered_path = get_object_storage(rendered_asset.storage_backend).local_path(rendered_asset.storage_key)
        assert rendered_path is not None
        original_render = rendered_path.read_bytes()
        rendered_path.write_bytes(b"tampered-after-human-preview")
    changed_render = client.post(
        decision_url,
        headers=auth(token),
        json={
            "action": "request_changes",
            "comment": "O arquivo mudou depois da escuta.",
            "listeningReview": listening,
        },
    )
    assert changed_render.status_code == 409
    assert changed_render.json()["detail"]["code"] == "studio_publication_render_changed"
    rendered_path.write_bytes(original_render)
    changed_after_listening = client.post(
        decision_url,
        headers=auth(token),
        json={
            "action": "request_changes",
            "comment": "O som não acompanha o gesto.",
            "listeningReview": listening,
        },
    )
    assert changed_after_listening.status_code == 200, changed_after_listening.text
    listening_record = changed_after_listening.json()["listeningReview"]
    assert listening_record["reviewId"] == review["id"]
    assert listening_record["documentVersion"] == 1
    assert listening_record["snapshotChecksumSha256"]
    assert listening_record["result"] == "needs_changes"
    assert listening_record["publicationAdmitted"] is False
    assert listening_record["reviewerId"] == changed_after_listening.json()["decidedBy"]
    assert client.get(
        "/api/v1/studios/v1/reviews/latest",
        headers=auth(other_token),
        params={"workspace_id": workspace, "document_id": document["documentId"]},
    ).status_code == 404

    current = client.get(
        f"/api/v1/studios/v1/documents/{document['documentId']}",
        headers=auth(token),
    ).json()
    current["title"] = "Documento alterado depois do render e da revisão"
    replaced = client.put(
        f"/api/v1/studios/v1/documents/{document['documentId']}",
        headers=auth(token),
        json={"expectedRevision": current["revision"], "document": current},
    )
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["revision"] == current["revision"] + 1

    with SessionLocal() as db:
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        assert asset.object_metadata["generationJobId"] == job["id"]
        assert asset.object_metadata["documentRevision"] == 1
        assert asset.object_metadata["derivation"] == "video_render"
        assert asset.object_metadata["qualityEvaluation"]["status"] == "passed"
        assert get_object_storage(asset.storage_backend).exists(asset.storage_key)

    direct = client.post(
        "/api/v1/studios/v1/jobs",
        headers={**auth(token), "Idempotency-Key": "direct-video-render-001"},
        json={
            "workspaceId": workspace,
            "documentId": document["documentId"],
            "jobType": "video_render",
            "provider": "hyperframes.cli",
            "request": {},
        },
    )
    assert direct.status_code == 422
    assert direct.json()["detail"]["code"] == "use_video_render_endpoint"
