from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.domain.studios.video_factory import VideoFactoryProgramEvidenceV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FACTORY_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "factory-20260901-v1"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=FACTORY_ROOT / "program-manifest.json")
    parser.add_argument("--output-root", type=Path, default=FACTORY_ROOT)
    args = parser.parse_args()
    program = VideoFactoryProgramEvidenceV1.model_validate_json(
        args.program.read_text(encoding="utf-8")
    )
    jobs = [*program.pilot.jobs, *program.calibration.jobs]
    decisions = {
        "schemaVersion": "clicko.video-factory-human-review-packet.v1",
        "programId": program.program_id,
        "instructions": (
            "BLOQUEADO PARA APROVAÇÃO FINAL: os MP4s atuais são transcodes de animatics "
            "placeholder. Use-os apenas para revisar mensagem, beat_order, copy e shot_intent. "
            "Não troque decision para approved até que mídia autorizada/gerada, motion final "
            "e mix de áudio substituam os placeholders."
        ),
        "reviews": [
            {
                "jobId": job.job_id,
                "wave": job.wave,
                "caseId": job.case_id,
                "artifactPath": job.artifact_path,
                "artifactDigestSha256": job.artifact_digest_sha256,
                "decision": "pending",
                "reviewId": None,
                "reviewedBy": None,
                "reviewedAt": None,
                "notes": None,
            }
            for job in jobs
        ],
    }
    lines = [
        "# Pacote de revisão humana — fábrica de vídeo 12 + 24",
        "",
        "> **Escopo atual: storyboard/animatic somente.** A pré-revisão automática comprovou "
        "que os MP4s são transcodes de placeholders, sem footage autorizado/gerado, motion final "
        "ou mix de áudio. Eles não podem receber aprovação audiovisual final nem promover a onda.",
        "",
        "Você pode revisar mensagem, ordem dos beats, copy e intenção de shot. O manifesto da "
        "pré-revisão está em `machine-pre-review.json`. Este pacote não concede publicação, voz "
        "ou identidade sintética.",
        "",
        "| Onda | Job | Caso | MP4 | SHA-256 | Estado |",
        "|---|---|---|---|---|---|",
    ]
    for job in jobs:
        assert job.artifact_path and job.artifact_digest_sha256
        artifact = (REPOSITORY_ROOT / job.artifact_path).resolve()
        lines.append(
            f"| {job.wave} | `{job.job_id}` | `{job.case_id}` | "
            f"[abrir MP4](<{artifact}>) | `{job.artifact_digest_sha256}` | pending |"
        )
    lines.extend(
        [
            "",
        "## Gate",
        "",
        "O template de decisão final permanece deliberadamente `pending` e não deve ser importado "
        "enquanto `machine-pre-review.json` tiver `promotionEligible: false`. Depois de substituir "
        "os placeholders por edições reais, gere nova pré-revisão. Só então, além das 36 decisões, "
        "preencha `infrastructure-cost-policy.template.json` e salve como "
            "`infrastructure-cost-policy.json`. Salve as decisões como `human-review-decisions.json`. "
            "O importador valida reviewer, timestamp, notas, arquivo e SHA-256.",
            "",
            "Os 64 jobs de escala só podem ser despachados quando todas as decisões exigidas "
            "estiverem registradas, os bloqueios de custo forem resolvidos e as duas ondas forem promovidas.",
        ]
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    (args.output_root / "human-review-decisions.template.json").write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_root / "infrastructure-cost-policy.template.json").write_text(
        json.dumps(
            {
                "schemaVersion": "studio.factory-infrastructure-cost-policy.v1",
                "policyId": None,
                "cpuHourlyCostUsd": None,
                "calculationMethod": None,
                "approvedBy": None,
                "approvedAt": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output_root / "human-review-packet.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"reviewCount": len(jobs), "status": "pending"}))


if __name__ == "__main__":
    main()
