from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.creative_replan import CreativeReplanStateV1
from app.domain.studios.video_factory import (
    FactoryIterationRejectionV1,
    VideoFactoryProgramEvidenceV1,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)
DEFAULT_OUTPUT = FACTORY_ROOT / "creative-replan-state-20260901-v2.json"

PROMPTS = (
    ("business_objective", "Qual resultado de negócio o primeiro golden deve produzir?"),
    ("audience_and_offer", "Para qual audiência e oferta o golden será criado?"),
    ("channel_and_duration", "Qual canal, objetivo editorial e duração serão usados?"),
    ("golden_format_family", "Qual única família de formato será testada primeiro?"),
    ("presenter_policy", "O golden terá apresentador? Se sim, qual autorização existe?"),
    (
        "media_sources_and_rights",
        "Quais fontes de imagem serão usadas e quais direitos comprovam o uso?",
    ),
    ("voice_policy", "O vídeo usará voz humana autorizada, licenciada ou nenhuma voz?"),
    (
        "reference_matrix",
        "Quais referências observáveis definem hook, montagem, motion, som e CTA?",
    ),
    (
        "quality_rubric_and_owner",
        "Quais critérios aprovam o golden e quem responde pelo aceite humano?",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--program",
        type=Path,
        default=FACTORY_ROOT / "current-program-manifest.json",
    )
    parser.add_argument(
        "--rejection",
        type=Path,
        default=FACTORY_ROOT / "iteration-rejection-20260901-v1.json",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    program = VideoFactoryProgramEvidenceV1.model_validate_json(
        args.program.read_text(encoding="utf-8")
    )
    rejection = FactoryIterationRejectionV1.model_validate_json(
        args.rejection.read_text(encoding="utf-8")
    )
    if rejection.program_id != program.program_id or not rejection.replan_required:
        raise ValueError("creative_replan_rejection_binding_invalid")
    blockers = [f"decision_pending:{key}" for key, _prompt in PROMPTS]
    state = CreativeReplanStateV1.model_validate(
        {
            "replanId": "clicko-video-creative-replan-20260901-v2",
            "previousProgramId": program.program_id,
            "previousRejectionId": rejection.rejection_id,
            "status": "awaiting_decisions",
            "decisions": [
                {"key": key, "prompt": prompt, "status": "pending"}
                for key, prompt in PROMPTS
            ],
            "approvedDecisionCount": 0,
            "goldenJobLimit": 1,
            "goldenProductionEligible": False,
            "batchDispatchAuthorized": False,
            "rejectedArtifactReuseAuthorized": False,
            "externalPublicationAuthorized": False,
            "blockers": blockers,
            "evaluatedAt": datetime.now(UTC),
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(state.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "approvedDecisions": state.approved_decision_count,
                "requiredDecisions": len(state.decisions),
                "goldenProductionEligible": state.golden_production_eligible,
                "goldenJobLimit": state.golden_job_limit,
                "batchDispatchAuthorized": state.batch_dispatch_authorized,
            }
        )
    )


if __name__ == "__main__":
    main()
