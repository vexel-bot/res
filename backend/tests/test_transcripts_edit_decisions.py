from conftest import register
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    LibraryAsset,
    StudioEditDecisionSet,
    StudioMediaIngest,
    StudioTranscript,
    User,
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_transcript_captions_and_edit_decisions_are_versioned_and_tenant_scoped(client):
    token, workspace = register(client, "transcript-owner@example.com", "Transcript Studio")
    other_token, _ = register(client, "transcript-other@example.com", "Other Transcript")
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == "transcript-owner@example.com"))
        assert user_id is not None
        asset = LibraryAsset(
            workspace_id=workspace,
            title="UGC ready",
            asset_type="video",
            tags=[],
            storage_key=f"{workspace}/raw/ugc-ready.mp4",
            storage_backend="local",
            media_type="video/mp4",
            size_bytes=1000,
            checksum_sha256="a" * 64,
        )
        db.add(asset)
        db.flush()
        ingest = StudioMediaIngest(
            workspace_id=workspace,
            asset_id=asset.id,
            status="ready",
            probe_provider="builtin.ffprobe",
            media_info={
                "schemaVersion": "studio.media-probe.v1",
                "provider": "builtin.ffprobe",
                "providerVersion": "test",
                "assetId": asset.id,
                "checksumSha256": "a" * 64,
                "container": "mp4",
                "durationMicroseconds": 5_000_000,
                "sizeBytes": 1000,
                "videoStreams": [
                    {
                        "index": 0,
                        "codec": "h264",
                        "width": 1080,
                        "height": 1920,
                        "frameRate": {"numerator": 30, "denominator": 1},
                    }
                ],
                "audioStreams": [],
                "providerTrace": {},
            },
            validation_errors=[],
            idempotency_key="fixture-ingest",
            requested_by=user_id,
        )
        db.add(ingest)
        db.commit()
        db.refresh(asset)
        db.refresh(ingest)
        asset_id = asset.id
        ingest_id = ingest.id

    transcript_body = {
        "workspaceId": workspace,
        "mediaIngestId": ingest_id,
        "locale": "pt-BR",
        "status": "ready",
        "segments": [
            {
                "id": "segment-1",
                "startMicroseconds": 0,
                "endMicroseconds": 2_000_000,
                "text": "Seu conteúdo pode começar melhor.",
                "confidence": 0.94,
                "speaker": "creator",
                "words": [
                    {
                        "id": "word-1",
                        "startMicroseconds": 0,
                        "endMicroseconds": 400_000,
                        "text": "Seu",
                        "confidence": 0.98,
                    }
                ],
            },
            {
                "id": "segment-2",
                "startMicroseconds": 2_000_000,
                "endMicroseconds": 5_000_000,
                "text": "Corte a pausa e preserve a intenção.",
                "confidence": 0.9,
                "speaker": "creator",
            },
        ],
    }
    transcript_headers = {**auth(token), "Idempotency-Key": "manual-transcript-001"}
    created = client.post(
        "/api/v1/studios/v1/transcripts",
        headers=transcript_headers,
        json=transcript_body,
    )
    assert created.status_code == 201, created.text
    transcript = created.json()
    assert transcript["revision"] == 1
    assert transcript["provider"] == "manual"

    replay = client.post(
        "/api/v1/studios/v1/transcripts",
        headers=transcript_headers,
        json=transcript_body,
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == transcript["id"]
    assert client.get(
        f"/api/v1/studios/v1/transcripts/{transcript['id']}", headers=auth(other_token)
    ).status_code == 404

    transcript["segments"][0]["text"] = "Seu anúncio pode começar muito melhor."
    replaced = client.put(
        f"/api/v1/studios/v1/transcripts/{transcript['id']}",
        headers=auth(token),
        json={"expectedRevision": 1, "transcript": transcript},
    )
    assert replaced.status_code == 200, replaced.text
    transcript = replaced.json()
    assert transcript["revision"] == 2 and transcript["version"] == 2
    conflict = client.put(
        f"/api/v1/studios/v1/transcripts/{transcript['id']}",
        headers=auth(token),
        json={"expectedRevision": 1, "transcript": transcript},
    )
    assert conflict.status_code == 409

    document_response = client.post(
        "/api/v1/studios/v1/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "UGC assistido",
            "contentType": "video",
            "brandRevision": 1,
            "brief": {
                "objective": "Criar anúncio UGC curto",
                "audience": "Gestores de social media",
                "hook": "Comece melhor",
            },
            "composition": {
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
                    "durationFrames": 150,
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "tracks": [
                        {
                            "id": "video-main",
                            "kind": "video",
                            "clips": [
                                {
                                    "id": "clip-source",
                                    "assetId": asset_id,
                                    "timeline": {"startFrame": 0, "durationFrames": 150},
                                    "source": {
                                        "startMicroseconds": 0,
                                        "durationMicroseconds": 5_000_000,
                                    },
                                }
                            ],
                        }
                    ],
                },
            },
            "assets": [
                {
                    "id": asset_id,
                    "mediaType": "video/mp4",
                    "checksum": "a" * 64,
                    "rightsStatus": "verified",
                }
            ],
        },
    )
    assert document_response.status_code == 201, document_response.text
    document = document_response.json()
    captioned = client.post(
        f"/api/v1/studios/v1/transcripts/{transcript['id']}/apply-captions",
        headers=auth(token),
        json={
            "documentId": document["documentId"],
            "expectedDocumentRevision": 1,
            "trackId": "captions-main",
            "style": {"preset": "brand-bold"},
        },
    )
    assert captioned.status_code == 200, captioned.text
    document = captioned.json()
    captions = next(
        track for track in document["composition"]["mediaTimeline"]["tracks"] if track["kind"] == "caption"
    )
    assert captions["cues"][0]["timeline"] == {"startFrame": 0, "durationFrames": 60}
    assert captions["cues"][1]["timeline"] == {"startFrame": 60, "durationFrames": 90}
    assert captions["cues"][0]["sourceSegmentId"] == "segment-1"

    decision_headers = {**auth(token), "Idempotency-Key": "edit-decisions-001"}
    decision_created = client.post(
        "/api/v1/studios/v1/edit-decision-sets",
        headers=decision_headers,
        json={
            "workspaceId": workspace,
            "mediaIngestId": ingest_id,
            "transcriptId": transcript["id"],
            "documentId": document["documentId"],
            "decisions": [
                {
                    "id": "remove-pause-1",
                    "operation": "remove",
                    "startMicroseconds": 1_200_000,
                    "endMicroseconds": 1_500_000,
                    "status": "suggested",
                    "reason": "Pausa longa",
                    "confidence": 0.91,
                    "source": "manual-review",
                }
            ],
        },
    )
    assert decision_created.status_code == 201, decision_created.text
    decision_set = decision_created.json()
    decision_set["decisions"][0]["status"] = "accepted"
    decision_replaced = client.put(
        f"/api/v1/studios/v1/edit-decision-sets/{decision_set['id']}",
        headers=auth(token),
        json={"expectedRevision": 1, "decisionSet": decision_set},
    )
    assert decision_replaced.status_code == 200, decision_replaced.text
    decision_set = decision_replaced.json()
    assert decision_set["revision"] == 2
    assert decision_set["decisions"][0]["status"] == "accepted"

    applied = client.post(
        f"/api/v1/studios/v1/edit-decision-sets/{decision_set['id']}/apply",
        headers=auth(token),
        json={
            "documentId": document["documentId"],
            "expectedDocumentRevision": document["revision"],
            "expectedDecisionRevision": decision_set["revision"],
            "sourceTrackId": "video-main",
        },
    )
    assert applied.status_code == 200, applied.text
    document = applied.json()
    timeline = document["composition"]["mediaTimeline"]
    assert timeline["durationFrames"] == 141
    video = next(track for track in timeline["tracks"] if track["id"] == "video-main")
    assert [clip["timeline"] for clip in video["clips"]] == [
        {"startFrame": 0, "durationFrames": 36},
        {"startFrame": 36, "durationFrames": 105},
    ]
    assert [clip["source"] for clip in video["clips"]] == [
        {"startMicroseconds": 0, "durationMicroseconds": 1_200_000},
        {"startMicroseconds": 1_500_000, "durationMicroseconds": 3_500_000},
    ]
    captions = next(track for track in timeline["tracks"] if track["kind"] == "caption")
    assert [cue["timeline"] for cue in captions["cues"]] == [
        {"startFrame": 0, "durationFrames": 36},
        {"startFrame": 36, "durationFrames": 15},
        {"startFrame": 51, "durationFrames": 90},
    ]
    applied_set = client.get(
        f"/api/v1/studios/v1/edit-decision-sets/{decision_set['id']}",
        headers=auth(token),
    ).json()
    assert applied_set["status"] == "applied"
    assert applied_set["revision"] == 3 and applied_set["version"] == 3
    replay = client.post(
        f"/api/v1/studios/v1/edit-decision-sets/{decision_set['id']}/apply",
        headers=auth(token),
        json={
            "documentId": document["documentId"],
            "expectedDocumentRevision": document["revision"],
            "expectedDecisionRevision": applied_set["revision"],
            "sourceTrackId": "video-main",
        },
    )
    assert replay.status_code == 422
    assert replay.json()["detail"]["code"] == "studio_edit_decision_already_applied"

    with SessionLocal() as db:
        assert len(db.get(StudioTranscript, transcript["id"]).versions) == 1
        assert len(db.get(StudioEditDecisionSet, decision_set["id"]).versions) == 2
