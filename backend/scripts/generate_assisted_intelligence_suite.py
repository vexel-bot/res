from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.assisted_intelligence import (
    AssistedIntelligenceCaseEvidenceV1,
    AssistedIntelligenceSuiteEvidenceV1,
    EditOperationDecisionV1,
    ReviewedEditPlanV1,
    StoryboardOptionSetV1,
    beat_digest,
    build_reviewed_edit_plan,
)
from app.domain.studios.creative_autonomy import (
    CreativeAutonomyCaseV1,
    CreativePilotCasebookV1,
    creative_casebook_digest,
)
from app.domain.studios.intelligence import (
    EditProposalV1,
    LStoryboardV1,
    MediaIndexV1,
    edit_proposal_digest,
    l_storyboard_digest,
    media_index_digest,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASEBOOK = (
    REPOSITORY_ROOT
    / "benchmarks"
    / "studios"
    / "creative"
    / "video-creative-pilot-casebook.v1.json"
)
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "assisted-intelligence-20260901-v1"
    / "manifest.json"
)
GENERATED_AT = datetime(2026, 9, 1, 18, 0, tzinfo=UTC)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _lineage(case_id: str) -> dict[str, object]:
    return {
        "provider": "builtin.localized-editorial-v1",
        "providerVersion": "1.0.0",
        "model": "deterministic-rules",
        "modelRevision": "clicko-p4-20260901",
        "parametersDigestSha256": _sha(f"{case_id}:parameters"),
        "promptDigestSha256": _sha(f"{case_id}:prompt"),
        "generatedAt": GENERATED_AT.isoformat(),
    }


def _media_index(case: CreativeAutonomyCaseV1) -> MediaIndexV1:
    checksum = _sha(f"{case.case_id}:authorized-placeholder-source")
    contract_digest = _sha(
        json.dumps(case.model_dump(mode="json", by_alias=True), sort_keys=True)
    )
    evidence = []
    entries = []
    for beat in case.script.beats:
        start = beat.start_milliseconds * 1000
        end = (beat.start_milliseconds + beat.duration_milliseconds) * 1000
        evidence_id = f"{beat.beat_id}-temporal"
        evidence.append(
            {
                "evidenceId": evidence_id,
                "evidenceType": "human_annotation",
                "assetId": f"{case.case_id}-source",
                "assetChecksumSha256": checksum,
                "interval": {"startMicroseconds": start, "endMicroseconds": end},
                "sourceContractId": beat.evidence_ids[0],
                "sourceContractDigestSha256": contract_digest,
                "summary": f"Beat localizado: {beat.message}",
            }
        )
        entries.append(
            {
                "entryId": f"{beat.beat_id}-entry",
                "kind": "claim" if beat.narrative_role in {"proof", "demo"} else "scene",
                "interval": {"startMicroseconds": start, "endMicroseconds": end},
                "label": beat.purpose,
                "confidence": 1.0,
                "evidenceIds": [evidence_id],
                "attributes": {"beatId": beat.beat_id, "role": beat.narrative_role},
            }
        )
    return MediaIndexV1.model_validate(
        {
            "indexId": f"{case.case_id}-index",
            "workspaceId": "clicko-video-pilot",
            "mediaIngestId": f"{case.case_id}-ingest",
            "sourceAssetId": f"{case.case_id}-source",
            "sourceChecksumSha256": checksum,
            "durationMicroseconds": case.script.target_duration_milliseconds * 1000,
            "status": "partial",
            "evidence": evidence,
            "entries": entries,
            "abstentions": ["Aprovação editorial humana continua obrigatória."],
            "lineage": [_lineage(case.case_id)],
            "createdAt": GENERATED_AT.isoformat(),
        }
    )


def _storyboard(case: CreativeAutonomyCaseV1, index: MediaIndexV1, strategy: str) -> LStoryboardV1:
    suffix = strategy.split("_")[0]
    purpose_prefix = {
        "clarity_first": "Clareza",
        "proof_first": "Prova",
        "rhythm_first": "Ritmo",
    }[strategy]
    return LStoryboardV1.model_validate(
        {
            "storyboardId": f"{case.case_id}-lboard-{suffix}",
            "workspaceId": index.workspace_id,
            "documentId": f"{case.case_id}-document",
            "documentRevision": 1,
            "mediaIndexId": index.index_id,
            "mediaIndexDigestSha256": media_index_digest(index),
            "targetDurationMicroseconds": case.script.target_duration_milliseconds * 1000,
            "beats": [
                {
                    "beatId": beat.beat_id,
                    "order": beat.order,
                    "narrativeRole": beat.narrative_role,
                    "purpose": f"{purpose_prefix}: {beat.purpose}",
                    "targetInterval": {
                        "startMicroseconds": beat.start_milliseconds * 1000,
                        "endMicroseconds": (
                            beat.start_milliseconds + beat.duration_milliseconds
                        )
                        * 1000,
                    },
                    "sourceEvidenceIds": [f"{beat.beat_id}-temporal"],
                    "copyText": beat.on_screen_text,
                }
                for beat in case.script.beats
            ],
            "lineage": _lineage(case.case_id),
            "createdAt": GENERATED_AT.isoformat(),
        }
    )


def _option_set(case: CreativeAutonomyCaseV1, index: MediaIndexV1) -> StoryboardOptionSetV1:
    option_set_id = f"{case.case_id}-options"
    options = []
    selected_board: LStoryboardV1 | None = None
    for strategy, suffix, score in (
        ("clarity_first", "clarity", 0.91),
        ("proof_first", "proof", 0.87),
        ("rhythm_first", "rhythm", 0.84),
    ):
        board = _storyboard(case, index, strategy)
        if suffix == "clarity":
            selected_board = board
        options.append(
            {
                "optionId": f"{option_set_id}-{suffix}",
                "strategy": strategy,
                "storyboard": board.model_dump(mode="json", by_alias=True),
                "storyboardDigestSha256": l_storyboard_digest(board),
                "critiques": [
                    {
                        "critiqueId": f"{case.case_id}-{suffix}-critique-{beat.order}",
                        "beatId": beat.beat_id,
                        "verdict": "repair" if suffix == "clarity" and beat.order == 2 else "pass",
                        "dimensions": {
                            "clarity": score,
                            "evidence": 1.0,
                            "continuity": 0.9,
                            "rhythm": 0.86 if suffix != "rhythm" else 0.96,
                            "feasibility": 0.95,
                        },
                        "evidenceIds": beat.source_evidence_ids,
                        "diagnosis": (
                            "O beat está correto, mas pode entregar sua função mais cedo."
                            if suffix == "clarity" and beat.order == 2
                            else "Beat localizado, evidenciado e executável."
                        ),
                        "repairInstruction": (
                            "Reescrever somente o propósito deste beat, preservando timing, evidência e demais beats."
                            if suffix == "clarity" and beat.order == 2
                            else None
                        ),
                    }
                    for beat in board.beats
                ],
                "score": score,
            }
        )
    assert selected_board is not None
    original = selected_board.beats[2]
    repaired = original.model_copy(
        update={"purpose": f"Clareza: entregar {original.narrative_role} sem preâmbulo adicional."}
    )
    return StoryboardOptionSetV1.model_validate(
        {
            "optionSetId": option_set_id,
            "workspaceId": index.workspace_id,
            "documentId": f"{case.case_id}-document",
            "documentRevision": 1,
            "mediaIndexId": index.index_id,
            "mediaIndexDigestSha256": media_index_digest(index),
            "options": options,
            "selectedOptionId": f"{option_set_id}-clarity",
            "selectionRationale": "Maior score agregado com evidência completa; um beat recebe reparo localizado.",
            "repair": {
                "repairId": f"{case.case_id}-repair-2",
                "optionId": f"{option_set_id}-clarity",
                "sourceStoryboardDigestSha256": l_storyboard_digest(selected_board),
                "repairedBeatId": original.beat_id,
                "originalBeatDigestSha256": beat_digest(original),
                "repairedBeat": repaired.model_dump(mode="json", by_alias=True),
                "preservedBeatIds": [
                    beat.beat_id for beat in selected_board.beats if beat.beat_id != original.beat_id
                ],
                "repairEvidenceIds": original.source_evidence_ids,
                "repairedAt": GENERATED_AT.isoformat(),
            },
            "createdAt": GENERATED_AT.isoformat(),
        }
    )


def _proposal_and_review(
    case: CreativeAutonomyCaseV1,
    index: MediaIndexV1,
    option_set: StoryboardOptionSetV1,
) -> tuple[EditProposalV1, ReviewedEditPlanV1]:
    selected = next(
        item for item in option_set.options if item.option_id == option_set.selected_option_id
    ).storyboard
    first, second, third = selected.beats[:3]
    proposal = EditProposalV1.model_validate(
        {
            "proposalId": f"{case.case_id}-proposal",
            "workspaceId": index.workspace_id,
            "documentId": option_set.document_id,
            "baseDocumentRevision": 1,
            "mediaIndexId": index.index_id,
            "mediaIndexDigestSha256": media_index_digest(index),
            "storyboardId": selected.storyboard_id,
            "storyboardDigestSha256": l_storyboard_digest(selected),
            "operations": [
                {
                    "operationId": f"{case.case_id}-marker",
                    "kind": "add_marker",
                    "targetTrackId": "markers-editorial",
                    "interval": first.target_interval.model_dump(mode="json", by_alias=True),
                    "label": "Hook localizado",
                    "evidenceIds": first.source_evidence_ids,
                    "confidence": 0.95,
                    "rationale": "Marca editorial derivada do beat e de sua evidência temporal.",
                },
                {
                    "operationId": f"{case.case_id}-caption",
                    "kind": "add_caption",
                    "targetTrackId": "captions-editorial",
                    "interval": second.target_interval.model_dump(mode="json", by_alias=True),
                    "text": second.copy_text or second.purpose,
                    "evidenceIds": second.source_evidence_ids,
                    "confidence": 0.91,
                    "rationale": "Legenda localizada, ajustável e não aplicada silenciosamente.",
                },
                {
                    "operationId": f"{case.case_id}-motion",
                    "kind": "apply_motion_preset",
                    "targetTrackId": "overlays-editorial",
                    "interval": third.target_interval.model_dump(mode="json", by_alias=True),
                    "presetId": f"{case.family}-subtle",
                    "intensity": "subtle",
                    "evidenceIds": third.source_evidence_ids,
                    "confidence": 0.84,
                    "rationale": "Motion sugerido apenas no beat evidenciado; requer escolha humana.",
                },
            ],
            "affectedTrackIds": [
                "markers-editorial",
                "captions-editorial",
                "overlays-editorial",
            ],
            "estimatedDurationBeforeMicroseconds": index.duration_microseconds,
            "estimatedDurationAfterMicroseconds": index.duration_microseconds,
            "abstentions": index.abstentions,
            "lineage": _lineage(case.case_id),
            "createdAt": GENERATED_AT.isoformat(),
        }
    )
    caption = proposal.operations[1]
    adjusted = caption.model_copy(update={"text": f"{caption.text} · ajuste humano"})
    decisions = [
        EditOperationDecisionV1(
            operation_id=proposal.operations[0].operation_id,
            decision="accept",
            reason="Marcador mantém rastreabilidade editorial.",
        ),
        EditOperationDecisionV1(
            operation_id=caption.operation_id,
            decision="adjust",
            reason="Copy ajustada sem trocar timing, alvo ou evidência.",
            adjusted_operation=adjusted,
        ),
        EditOperationDecisionV1(
            operation_id=proposal.operations[2].operation_id,
            decision="reject",
            reason="Rejeição demonstra que nenhuma sugestão é aplicada automaticamente.",
        ),
    ]
    before_digest = _sha(f"{case.case_id}:document-revision:1")
    review = build_reviewed_edit_plan(
        review_id=f"{case.case_id}-review",
        proposal=proposal,
        expected_document_revision=1,
        decisions=decisions,
        before_snapshot_digest_sha256=before_digest,
        reviewed_by="pilot-human-review-fixture",
        reviewed_at=GENERATED_AT,
    )
    assert review.proposal_digest_sha256 == edit_proposal_digest(proposal)
    return proposal, review


def build_suite(casebook: CreativePilotCasebookV1) -> AssistedIntelligenceSuiteEvidenceV1:
    cases = []
    for case in casebook.cases:
        index = _media_index(case)
        options = _option_set(case, index)
        proposal, review = _proposal_and_review(case, index, options)
        cases.append(
            AssistedIntelligenceCaseEvidenceV1(
                case_id=case.case_id,
                media_index=index,
                option_set=options,
                proposal=proposal,
                reviewed_plan=review,
                eligible=True,
            )
        )
    return AssistedIntelligenceSuiteEvidenceV1(
        suite_id="clicko-assisted-intelligence-pilot-v1",
        source_casebook_digest_sha256=creative_casebook_digest(casebook),
        cases=cases,
        eligible=True,
        generated_at=GENERATED_AT,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--casebook", type=Path, default=DEFAULT_CASEBOOK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    casebook = CreativePilotCasebookV1.model_validate_json(
        args.casebook.read_text(encoding="utf-8")
    )
    suite = build_suite(casebook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(suite.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), "eligible": suite.eligible, "cases": len(suite.cases)}))


if __name__ == "__main__":
    main()
