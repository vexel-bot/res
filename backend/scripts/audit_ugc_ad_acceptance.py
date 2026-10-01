"""Reassess immutable UGC runs against actual artifact bytes and current mandatory preflight.

This is an offline audit. It makes no inference calls, alters no old results and never
promotes a provider or a creative. Changed criteria are a new assessment, not a new model run.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.studios.ugc_acceptance import UgcAdAcceptanceRunV1  # noqa: E402
from app.services.studios.ugc_acceptance import (  # noqa: E402
    automated_preflight_status,
    canonical_json_digest,
    evaluate_planning_copy,
    load_ugc_acceptance_casebook,
    sha256_file,
    verify_ad_kit,
    weighted_score,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path, nargs="+")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    casebook_path = ROOT / "benchmarks/studios/ugc/ugc-ad-creative-acceptance-casebook.v1.json"
    book = load_ugc_acceptance_casebook(casebook_path)
    cases = {case.case_id: case for case in book.cases}
    audits = []
    markdown = [
        "# UGC — auditoria de evidências e pré-revisão",
        "",
        "São saídas experimentais de Qwen + composição estática + animatic silencioso. "
        "Não há imagem gerada por modelo, avatar em movimento, voz clonada ou lip-sync nestes kits. "
        "Notas são heurísticas de triagem, não MOS, avaliação de persuasão ou autorização de publicação.",
        "",
    ]
    for report_path in args.reports:
        run = UgcAdAcceptanceRunV1.model_validate_json(report_path.read_text(encoding="utf-8"))
        if run.casebook_digest_sha256 != canonical_json_digest(book):
            raise SystemExit("Frozen casebook does not match report; do not silently rescore a different corpus.")
        if {item.case_id for item in run.results} != set(cases):
            raise SystemExit("Run does not contain exactly the ten casebook cases.")
        rows = []
        markdown += [f"## {run.run_id}", ""]
        for result in run.results:
            case = cases[result.case_id]
            criteria = evaluate_planning_copy(case, result.planning_result) if result.planning_result else []
            integrity = verify_ad_kit(case, result.artifacts, allowed_root=report_path.parent)
            criteria.append(integrity)
            failures = [item.criterion_id for item in criteria if item.status == "fail"]
            status = automated_preflight_status(criteria)
            row = {
                "caseId": case.case_id,
                "originalStatus": result.automated_status,
                "currentPreflightStatus": status,
                "score": weighted_score(criteria),
                "artifactIntegrity": integrity.status,
                "blockingChecks": failures,
                "criteria": [item.model_dump(by_alias=True, mode="json") for item in criteria],
                "humanReview": "pending",
                "ugcAdDelivery": "not_complete",
            }
            rows.append(row)
            print(f"{run.run_id} / {case.case_id}: integrity={integrity.status}, preflight={status}", flush=True)
            markdown += [
                f"### {case.case_id} — {case.avatar.display_name}",
                "",
                f"Nicho: {case.niche}. Cenário: {case.scene.setting}.",
                "",
                f"Pré-verificação: **{status}**. Integridade dos arquivos: **{integrity.status}**. "
                f"Revisões necessárias: {', '.join(failures) or 'revisão editorial humana'}.",
                "",
            ]
            if result.planning_result:
                draft = result.planning_result.draft
                markdown += [
                    f"Hook: {draft.brief.hook}",
                    "",
                    f"CTA: {draft.brief.cta}",
                    "",
                    f"Roteiro do modelo: {draft.script}",
                    "",
                    "Falas das cenas (fonte que precisa coincidir com o roteiro):",
                    "",
                    *[f"- {beat.narrative_role}: {beat.copy_text}" for beat in draft.storyboard],
                    "",
                ]
        audits.append(
            {
                "sourceRun": run.run_id,
                "sourceReportSha256": sha256_file(report_path),
                "sourceReport": str(report_path.resolve()),
                "cases": rows,
                "preflightPassed": sum(row["currentPreflightStatus"] == "pass" for row in rows),
                "artifactsVerified": sum(row["artifactIntegrity"] == "pass" for row in rows),
            }
        )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    evaluator_source = ROOT / "backend/app/services/studios/ugc_acceptance.py"
    (args.output_dir / "evaluator-source.py").write_bytes(evaluator_source.read_bytes())
    payload = {
        "schemaVersion": "studio.ugc-ad-evidence-audit.v1",
        "assessedAt": datetime.now(UTC).isoformat(),
        "casebookDigestSha256": canonical_json_digest(book),
        "evaluatorSourceSha256": sha256_file(evaluator_source),
        "assessmentOnly": True,
        "newInferenceExecuted": False,
        "publicationEnabled": False,
        "unexecutedCapabilities": ["image_synthesis", "avatar_inference", "voice_clone", "lip_sync"],
        "runs": audits,
    }
    (args.output_dir / "audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "review.md").write_text("\n".join(markdown), encoding="utf-8")
    print(json.dumps({"runsAudited": len(audits), "output": str(args.output_dir.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
