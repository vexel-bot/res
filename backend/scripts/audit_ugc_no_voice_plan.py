"""Audit the frozen natural-sound/caption UGC plan without generating or publishing media."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.studios.ugc_acceptance import sha256_file  # noqa: E402
from app.services.studios.ugc_no_voice import (  # noqa: E402
    audit_no_voice_casebook,
    canonical_digest,
    load_ugc_no_voice_casebook,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--casebook",
        type=Path,
        default=ROOT / "benchmarks/studios/ugc/ugc-no-voice-natural-caption-casebook.v1.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    book = load_ugc_no_voice_casebook(args.casebook)
    audit = audit_no_voice_casebook(book)
    args.output_dir.mkdir(parents=True, exist_ok=False)

    domain_source = ROOT / "backend/app/domain/studios/ugc_no_voice.py"
    evaluator_source = ROOT / "backend/app/services/studios/ugc_no_voice.py"
    shutil.copyfile(args.casebook, args.output_dir / args.casebook.name)
    shutil.copyfile(domain_source, args.output_dir / "contract-source.py")
    shutil.copyfile(evaluator_source, args.output_dir / "evaluator-source.py")

    payload = audit.model_dump(by_alias=True, mode="json")
    payload["evidence"] = {
        "casebookSourceSha256": sha256_file(args.casebook),
        "canonicalCasebookDigestSha256": canonical_digest(book),
        "contractSourceSha256": sha256_file(domain_source),
        "evaluatorSourceSha256": sha256_file(evaluator_source),
    }
    (args.output_dir / "audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    assessments = {item.case_id: item for item in audit.assessments}
    markdown = [
        "# UGC sem voz — auditoria do plano congelado",
        "",
        "Perfil: somente sons naturais/foley e legendas editoriais queimadas no vídeo. ",
        "Voz, conversa captada e música são proibidas. Esta auditoria não gera mídia e não publica.",
        "",
        f"Suite: `{book.suite_id}`.",
        "",
        f"Digest canônico: `{audit.casebook_digest_sha256}`.",
        "",
        "## Casos",
        "",
    ]
    for case in book.cases:
        assessment = assessments[case.case_id]
        markdown += [
            f"### {case.case_id} — {case.niche}",
            "",
            f"Casting: {case.avatar.display_name} (slot de catálogo, não produzido). ",
            f"Plano: **{assessment.planning_status}**. Produção: **{assessment.production_status}**.",
            "",
            "Legendas:",
            "",
            *[
                f"- {caption.start_seconds:.1f}–{caption.end_seconds:.1f}s: "
                + " / ".join(caption.lines)
                for caption in case.captions
            ],
            "",
            "Sons naturais planejados:",
            "",
            *[
                f"- {sound.start_seconds:.1f}–{sound.end_seconds:.1f}s: {sound.sound_direction}"
                for sound in case.natural_sounds
            ],
            "",
            "Gates bloqueados:",
            "",
            *[
                f"- {gate.capability}: {gate.reason}"
                for gate in assessment.capability_gates
                if gate.status == "blocked"
            ],
            "",
        ]
    markdown += [
        "## Decisão",
        "",
        "Aprovar os dez storyboards para aquisição controlada de takes e sons. Não chamar nenhum ",
        "deles de anúncio final até que os gates de direitos, checksum, ausência de fala/música, ",
        "avatar/take e revisão humana tenham evidência real.",
        "",
    ]
    (args.output_dir / "review.md").write_text("\n".join(markdown), encoding="utf-8")

    summary = {
        "suiteId": book.suite_id,
        "casebookDigestSha256": audit.casebook_digest_sha256,
        "plansPassed": sum(item.planning_status == "pass" for item in audit.assessments),
        "productionReady": sum(item.production_status == "ready" for item in audit.assessments),
        "voiceExecuted": False,
        "musicUsed": False,
        "naturalSoundAssetsSupplied": False,
        "externalPublicationExecuted": False,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
