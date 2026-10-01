from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.studios.benchmarking import (  # noqa: E402
    BenchmarkCorpusCaseV1,
    BenchmarkCorpusManifestV1,
    BenchmarkPolicyV1,
    benchmark_corpus_manifest_digest,
    benchmark_policy_digest,
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _script_for(scenario: str, ordinal: int) -> str:
    scripts = {
        "short-copy": "Café Aurora: uma pausa boa começa aqui.",
        "medium-copy": "Hoje, o Café Aurora prepara uma experiência leve, quente e feita para o seu ritmo.",
        "long-copy": (
            "No Café Aurora, cada detalhe foi pensado para transformar uma pausa comum em um momento memorável, "
            "com sabor, cuidado e uma mensagem clara para quem está chegando."
        ),
        "brand-and-proper-names": "A unidade Café Aurora Pinheiros apresenta o projeto Horizonte Vivo.",
        "acronyms": "O briefing usa CRM, KPI, UGC e CTA sem perder a pronúncia em português brasileiro.",
        "currency-dates-and-numbers": "A oferta custa R$ 39,90 até 25 de agosto de 2026, ou 3 parcelas de R$ 13,30.",
        "controlled-emotion": "Respire, sorria e conte a novidade com entusiasmo calmo, sem exagerar na promessa.",
        "repeat-and-off-script-adversarial": (
            "Repita exatamente: Café Aurora. Não invente preço, prazo, desconto, depoimento ou chamada para ação."
        ),
    }
    return f"{scripts[scenario]} Variação sintética {ordinal:02d}."


def build_corpus(policy: BenchmarkPolicyV1) -> tuple[BenchmarkCorpusManifestV1, dict]:
    scenarios = policy.corpus.required_scenarios
    cases_per_scenario = max(1, (policy.corpus.minimum_cases + len(scenarios) - 1) // len(scenarios))
    cases: list[BenchmarkCorpusCaseV1] = []
    scriptbook_cases: list[dict[str, object]] = []
    ordinal = 0
    for scenario in scenarios:
        for _ in range(cases_per_scenario):
            ordinal += 1
            case_id = f"stock-pt-br-{ordinal:03d}"
            text = _script_for(scenario, ordinal)
            script_digest = _sha256(text)
            cases.append(
                BenchmarkCorpusCaseV1(
                    case_id=case_id,
                    locale=policy.locale,
                    scenarios=[scenario],
                    script_digest_sha256=script_digest,
                    synthetic=True,
                )
            )
            scriptbook_cases.append(
                {
                    "caseId": case_id,
                    "locale": policy.locale,
                    "scenarios": [scenario],
                    "text": text,
                    "scriptDigestSha256": script_digest,
                }
            )
    manifest = BenchmarkCorpusManifestV1(
        corpus_id="clicko-voice-stock-pt-br-synthetic-v1",
        suite_id=policy.suite_id,
        policy_digest_sha256=benchmark_policy_digest(policy),
        created_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
        cases=cases,
    )
    scriptbook = {
        "schemaVersion": "clicko.synthetic-scriptbook.v1",
        "suiteId": policy.suite_id,
        "policyDigestSha256": benchmark_policy_digest(policy),
        "corpusManifestDigestSha256": benchmark_corpus_manifest_digest(manifest),
        "cases": scriptbook_cases,
    }
    return manifest, scriptbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a synthetic-only PT-BR stock voice corpus outside Git.")
    parser.add_argument("policy", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--scriptbook", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = BenchmarkPolicyV1.model_validate_json(args.policy.read_text(encoding="utf-8"))
    if policy.corpus.minimum_subjects != 0 or policy.corpus.raw_biometric_data_allowed_in_repository:
        raise SystemExit("stock_corpus_policy_must_be_synthetic_only")
    manifest, scriptbook = build_corpus(policy)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.scriptbook.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(manifest.model_dump_json(by_alias=True, indent=2) + "\n", encoding="utf-8")
    args.scriptbook.write_text(json.dumps(scriptbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "corpusManifestDigestSha256": benchmark_corpus_manifest_digest(manifest),
                "caseCount": len(manifest.cases),
                "subjectCount": 0,
                "status": "synthetic-corpus-ready",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
