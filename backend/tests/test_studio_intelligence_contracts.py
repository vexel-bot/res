from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain.studios.assisted_intelligence import (
    EditOperationDecisionV1,
    StoryboardOptionSetV1,
    beat_digest,
    build_reviewed_edit_plan,
    storyboard_option_set_digest,
)
from app.domain.studios.contracts import CreativeDocumentV1
from app.domain.studios.intelligence import (
    EditProposalApplicationV1,
    EditProposalV1,
    LStoryboardV1,
    MediaIndexV1,
    edit_proposal_digest,
    evaluate_edit_proposal_application,
    l_storyboard_digest,
    materialize_edit_decision_set_request,
    media_index_digest,
    validate_storyboard_bindings,
)

NOW = datetime(2026, 8, 26, 17, 30, tzinfo=UTC)
CHECKSUM = "a" * 64
DIGEST = "b" * 64


def lineage() -> dict[str, object]:
    return {
        "provider": "evaluation.qwen3-vl",
        "providerVersion": "0.0.0-not-promoted",
        "model": "Qwen3-VL-4B-Instruct",
        "modelRevision": "ebb281ec70b05090aa6165b016eac8ec08e71b17",
        "parametersDigestSha256": DIGEST,
        "promptDigestSha256": "c" * 64,
        "generatedAt": NOW.isoformat(),
    }


def media_index() -> MediaIndexV1:
    return MediaIndexV1.model_validate(
        {
            "indexId": "index-1",
            "workspaceId": "workspace-1",
            "mediaIngestId": "ingest-1",
            "sourceAssetId": "asset-video-1",
            "sourceChecksumSha256": CHECKSUM,
            "durationMicroseconds": 5_000_000,
            "status": "partial",
            "evidence": [
                {
                    "evidenceId": "evidence-pause-1",
                    "evidenceType": "audio",
                    "assetId": "asset-video-1",
                    "assetChecksumSha256": CHECKSUM,
                    "interval": {
                        "startMicroseconds": 1_200_000,
                        "endMicroseconds": 1_500_000,
                    },
                    "sourceContractId": "waveform-1",
                    "sourceContractDigestSha256": "d" * 64,
                    "summary": "Low-energy pause confirmed by waveform evidence.",
                },
                {
                    "evidenceId": "evidence-hook-1",
                    "evidenceType": "transcript",
                    "assetId": "asset-video-1",
                    "assetChecksumSha256": CHECKSUM,
                    "interval": {
                        "startMicroseconds": 0,
                        "endMicroseconds": 1_200_000,
                    },
                    "sourceContractId": "transcript-1",
                    "sourceContractDigestSha256": "e" * 64,
                    "summary": "Opening promise and product name.",
                },
            ],
            "entries": [
                {
                    "entryId": "entry-pause-1",
                    "kind": "silence",
                    "interval": {
                        "startMicroseconds": 1_200_000,
                        "endMicroseconds": 1_500_000,
                    },
                    "label": "Long pause",
                    "confidence": 0.93,
                    "evidenceIds": ["evidence-pause-1"],
                }
            ],
            "abstentions": ["fast-hand-motion-needs-human-review"],
            "lineage": [lineage()],
            "createdAt": NOW.isoformat(),
        }
    )


def document() -> CreativeDocumentV1:
    return CreativeDocumentV1.model_validate(
        {
            "documentId": "document-1",
            "workspaceId": "workspace-1",
            "title": "UGC assistido",
            "contentType": "video",
            "revision": 3,
            "version": 3,
            "correlationId": "correlation-1",
            "brandMemoryRef": {"id": "brand-1", "revision": 7},
            "brief": {
                "objective": "Criar um anúncio UGC curto",
                "audience": "Gestores de social media",
                "hook": "Comece melhor",
            },
            "composition": {
                "pages": [
                    {
                        "id": "scene-1",
                        "width": 1080,
                        "height": 1920,
                        "layers": [],
                    }
                ],
                "mediaTimeline": {
                    "frameRate": {"numerator": 30, "denominator": 1},
                    "durationFrames": 150,
                    "tracks": [
                        {
                            "id": "video-main",
                            "kind": "video",
                            "clips": [
                                {
                                    "id": "clip-1",
                                    "assetId": "asset-video-1",
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
                    "id": "asset-video-1",
                    "mediaType": "video/mp4",
                    "checksum": CHECKSUM,
                    "rightsStatus": "verified",
                }
            ],
            "createdAt": NOW.isoformat(),
            "updatedAt": NOW.isoformat(),
        }
    )


def storyboard(index: MediaIndexV1) -> LStoryboardV1:
    return LStoryboardV1.model_validate(
        {
            "storyboardId": "storyboard-1",
            "workspaceId": "workspace-1",
            "documentId": "document-1",
            "documentRevision": 3,
            "mediaIndexId": index.index_id,
            "mediaIndexDigestSha256": media_index_digest(index),
            "targetDurationMicroseconds": 4_700_000,
            "beats": [
                {
                    "beatId": "beat-hook",
                    "order": 0,
                    "narrativeRole": "hook",
                    "purpose": "State the promise immediately.",
                    "targetInterval": {
                        "startMicroseconds": 0,
                        "endMicroseconds": 1_200_000,
                    },
                    "sourceEvidenceIds": ["evidence-hook-1"],
                    "copyText": "Comece melhor.",
                },
                {
                    "beatId": "beat-proof",
                    "order": 1,
                    "narrativeRole": "proof",
                    "purpose": "Continue after removing the pause.",
                    "targetInterval": {
                        "startMicroseconds": 1_200_000,
                        "endMicroseconds": 4_700_000,
                    },
                    "sourceEvidenceIds": ["evidence-pause-1"],
                },
            ],
            "lineage": lineage(),
            "createdAt": NOW.isoformat(),
        }
    )


def proposal(index: MediaIndexV1, board: LStoryboardV1) -> EditProposalV1:
    return EditProposalV1.model_validate(
        {
            "proposalId": "proposal-1",
            "workspaceId": "workspace-1",
            "documentId": "document-1",
            "baseDocumentRevision": 3,
            "mediaIndexId": index.index_id,
            "mediaIndexDigestSha256": media_index_digest(index),
            "storyboardId": board.storyboard_id,
            "storyboardDigestSha256": l_storyboard_digest(board),
            "operations": [
                {
                    "operationId": "remove-pause-1",
                    "kind": "remove_range",
                    "sourceTrackId": "video-main",
                    "interval": {
                        "startMicroseconds": 1_200_000,
                        "endMicroseconds": 1_500_000,
                    },
                    "evidenceIds": ["evidence-pause-1"],
                    "confidence": 0.93,
                    "rationale": "Remove a measured low-energy pause without cutting speech.",
                }
            ],
            "affectedTrackIds": ["video-main"],
            "estimatedDurationBeforeMicroseconds": 5_000_000,
            "estimatedDurationAfterMicroseconds": 4_700_000,
            "abstentions": ["fast-hand-motion-needs-human-review"],
            "lineage": lineage(),
            "createdAt": NOW.isoformat(),
        }
    )


def application(proposal: EditProposalV1) -> EditProposalApplicationV1:
    return EditProposalApplicationV1.model_validate(
        {
            "proposalId": proposal.proposal_id,
            "proposalDigestSha256": edit_proposal_digest(proposal),
            "expectedDocumentRevision": 3,
            "selectedOperationIds": ["remove-pause-1"],
            "humanConfirmed": True,
            "appliedBy": "user-1",
            "appliedAt": NOW.isoformat(),
        }
    )


def test_media_index_storyboard_and_proposal_are_digest_bound() -> None:
    index = media_index()
    board = storyboard(index)
    edit = proposal(index, board)

    validate_storyboard_bindings(index, board)
    assert len(media_index_digest(index)) == 64
    assert len(l_storyboard_digest(board)) == 64
    assert len(edit_proposal_digest(edit)) == 64
    assert edit.human_apply_required is True
    assert index.abstentions == ["fast-hand-motion-needs-human-review"]


def test_media_index_rejects_unknown_evidence_and_wrong_asset_binding() -> None:
    payload = media_index().model_dump(mode="json", by_alias=True)
    payload["entries"][0]["evidenceIds"] = ["missing"]
    with pytest.raises(ValidationError, match="unknown evidence"):
        MediaIndexV1.model_validate(payload)

    payload = media_index().model_dump(mode="json", by_alias=True)
    payload["evidence"][0]["assetId"] = "other-asset"
    with pytest.raises(ValidationError, match="indexed source asset"):
        MediaIndexV1.model_validate(payload)


def test_complete_media_index_cannot_hide_abstentions() -> None:
    payload = media_index().model_dump(mode="json", by_alias=True)
    payload["status"] = "complete"

    with pytest.raises(ValidationError, match="unresolved abstentions"):
        MediaIndexV1.model_validate(payload)


def test_storyboard_rejects_tampered_index_binding() -> None:
    index = media_index()
    board = storyboard(index).model_copy(update={"media_index_digest_sha256": "f" * 64})

    with pytest.raises(ValueError, match="digest"):
        validate_storyboard_bindings(index, board)


def test_model_generated_proposal_cannot_self_declare_applied() -> None:
    index = media_index()
    board = storyboard(index)
    payload = proposal(index, board).model_dump(mode="json", by_alias=True)
    payload["status"] = "applied"

    with pytest.raises(ValidationError, match="cannot declare itself applied"):
        EditProposalV1.model_validate(payload)


def test_human_confirmed_remove_range_materializes_existing_reviewed_path() -> None:
    index = media_index()
    board = storyboard(index)
    edit = proposal(index, board)
    apply = application(edit)

    gate = evaluate_edit_proposal_application(document(), index, board, edit, apply)
    request = materialize_edit_decision_set_request(
        document(),
        index,
        board,
        edit,
        apply,
        media_ingest_id="ingest-1",
        transcript_id="transcript-1",
    )

    assert gate.eligible is True
    assert request.document_id == "document-1"
    assert request.decisions[0].operation == "remove"
    assert request.decisions[0].status == "accepted"
    assert request.decisions[0].source == "proposal:proposal-1"


def test_stale_or_tampered_application_fails_closed() -> None:
    index = media_index()
    board = storyboard(index)
    edit = proposal(index, board)
    apply = application(edit).model_copy(
        update={"expected_document_revision": 2, "proposal_digest_sha256": "f" * 64}
    )

    gate = evaluate_edit_proposal_application(document(), index, board, edit, apply)

    assert gate.eligible is False
    assert "stale_application_document_revision" in gate.blocking_reasons
    assert "proposal_digest_mismatch" in gate.blocking_reasons


def test_unimplemented_operation_is_visible_but_not_applicable() -> None:
    index = media_index()
    board = storyboard(index)
    payload = proposal(index, board).model_dump(mode="json", by_alias=True)
    payload["operations"] = [
        {
            "operationId": "caption-1",
            "kind": "add_caption",
            "targetTrackId": "captions-main",
            "interval": {"startMicroseconds": 0, "endMicroseconds": 1_200_000},
            "text": "Comece melhor.",
            "evidenceIds": ["evidence-hook-1"],
            "confidence": 0.9,
            "rationale": "Reinforce the opening hook.",
        }
    ]
    payload["affectedTrackIds"] = ["captions-main"]
    edit = EditProposalV1.model_validate(payload)
    apply_payload = application(proposal(index, board)).model_dump(mode="json", by_alias=True)
    apply_payload["proposalDigestSha256"] = edit_proposal_digest(edit)
    apply_payload["selectedOperationIds"] = ["caption-1"]
    apply = EditProposalApplicationV1.model_validate(apply_payload)

    gate = evaluate_edit_proposal_application(document(), index, board, edit, apply)

    assert gate.eligible is False
    assert "operation_applicator_unavailable:caption-1" in gate.blocking_reasons
    with pytest.raises(ValueError, match="not eligible"):
        materialize_edit_decision_set_request(
            document(), index, board, edit, apply, media_ingest_id="ingest-1"
        )


def test_proposal_digest_changes_when_provider_output_is_tampered() -> None:
    index = media_index()
    board = storyboard(index)
    original = proposal(index, board)
    payload = deepcopy(original.model_dump(mode="json", by_alias=True))
    payload["operations"][0]["confidence"] = 0.51
    tampered = EditProposalV1.model_validate(payload)

    assert edit_proposal_digest(tampered) != edit_proposal_digest(original)


def test_three_storyboard_options_bind_critique_and_localized_repair() -> None:
    index = media_index()
    base = storyboard(index)
    options = []
    for suffix, strategy, score in (
        ("clarity", "clarity_first", 0.86),
        ("proof", "proof_first", 0.82),
        ("rhythm", "rhythm_first", 0.79),
    ):
        board = base.model_copy(update={"storyboard_id": f"storyboard-{suffix}"})
        options.append(
            {
                "optionId": f"option-set-1-{suffix}",
                "strategy": strategy,
                "storyboard": board.model_dump(mode="json", by_alias=True),
                "storyboardDigestSha256": l_storyboard_digest(board),
                "critiques": [
                    {
                        "critiqueId": f"critique-{suffix}-{beat.beat_id}",
                        "beatId": beat.beat_id,
                        "verdict": "repair" if suffix == "clarity" and beat.order == 1 else "pass",
                        "dimensions": {
                            "clarity": 0.9,
                            "evidence": 0.95,
                            "continuity": 0.88,
                            "rhythm": 0.8,
                            "feasibility": 0.94,
                        },
                        "evidenceIds": beat.source_evidence_ids,
                        "diagnosis": "Beat localized against temporal evidence.",
                        "repairInstruction": (
                            "Tighten only this proof beat."
                            if suffix == "clarity" and beat.order == 1
                            else None
                        ),
                    }
                    for beat in board.beats
                ],
                "score": score,
            }
        )
    selected = base.model_copy(update={"storyboard_id": "storyboard-clarity"})
    original = selected.beats[1]
    repaired = original.model_copy(update={"purpose": "Show proof immediately after the measured pause."})
    option_set = StoryboardOptionSetV1.model_validate(
        {
            "optionSetId": "option-set-1",
            "workspaceId": "workspace-1",
            "documentId": "document-1",
            "documentRevision": 3,
            "mediaIndexId": index.index_id,
            "mediaIndexDigestSha256": media_index_digest(index),
            "options": options,
            "selectedOptionId": "option-set-1-clarity",
            "selectionRationale": "Best evidence and clarity score.",
            "repair": {
                "repairId": "repair-proof-1",
                "optionId": "option-set-1-clarity",
                "sourceStoryboardDigestSha256": l_storyboard_digest(selected),
                "repairedBeatId": original.beat_id,
                "originalBeatDigestSha256": beat_digest(original),
                "repairedBeat": repaired.model_dump(mode="json", by_alias=True),
                "preservedBeatIds": [selected.beats[0].beat_id],
                "repairEvidenceIds": original.source_evidence_ids,
                "repairedAt": NOW.isoformat(),
            },
            "createdAt": NOW.isoformat(),
        }
    )

    assert len(option_set.options) == 3
    assert option_set.repair is not None
    assert option_set.repair.preserved_beat_ids == ["beat-hook"]
    assert len(storyboard_option_set_digest(option_set)) == 64


def test_reviewed_plan_accept_reject_adjust_is_evidence_stable_and_reversible() -> None:
    index = media_index()
    board = storyboard(index)
    payload = proposal(index, board).model_dump(mode="json", by_alias=True)
    payload["operations"].append(
        {
            "operationId": "marker-hook-1",
            "kind": "add_marker",
            "targetTrackId": "video-main",
            "interval": {"startMicroseconds": 0, "endMicroseconds": 1_200_000},
            "label": "Hook",
            "evidenceIds": ["evidence-hook-1"],
            "confidence": 0.9,
            "rationale": "Keep the hook visible for human review.",
        }
    )
    edit = EditProposalV1.model_validate(payload)
    adjusted_payload = edit.operations[0].model_dump(mode="json", by_alias=True)
    adjusted_payload["interval"]["endMicroseconds"] = 1_450_000
    decisions = [
        EditOperationDecisionV1.model_validate(
            {
                "operationId": "remove-pause-1",
                "decision": "adjust",
                "reason": "Keep fifty milliseconds of room tone.",
                "adjustedOperation": adjusted_payload,
            }
        ),
        EditOperationDecisionV1(
            operation_id="marker-hook-1",
            decision="reject",
            reason="Marker is unnecessary for this cut.",
        ),
    ]
    before_digest = "9" * 64
    reviewed = build_reviewed_edit_plan(
        review_id="review-1",
        proposal=edit,
        expected_document_revision=3,
        decisions=decisions,
        before_snapshot_digest_sha256=before_digest,
        reviewed_by="user-1",
        reviewed_at=NOW,
    )

    assert [item.operation_id for item in reviewed.accepted_operations] == ["remove-pause-1"]
    assert reviewed.rejected_operation_ids == ["marker-hook-1"]
    assert reviewed.before_snapshot_digest_sha256 == reviewed.inverse_snapshot_digest_sha256
    assert reviewed.accepted_operations[0].evidence_ids == ["evidence-pause-1"]

    tampered = deepcopy(adjusted_payload)
    tampered["evidenceIds"] = ["evidence-hook-1"]
    with pytest.raises(ValueError, match="evidence cannot change"):
        build_reviewed_edit_plan(
            review_id="review-2",
            proposal=edit,
            expected_document_revision=3,
            decisions=[
                EditOperationDecisionV1.model_validate(
                    {
                        "operationId": "remove-pause-1",
                        "decision": "adjust",
                        "reason": "Tampered evidence.",
                        "adjustedOperation": tampered,
                    }
                ),
                decisions[1],
            ],
            before_snapshot_digest_sha256=before_digest,
            reviewed_by="user-1",
            reviewed_at=NOW,
        )
