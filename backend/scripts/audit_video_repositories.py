# ruff: noqa: E501 -- audit prose is kept as readable evidence text.
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

PURPOSES = {
    "chatterbox": "speech synthesis and expressive voice research",
    "depth-anything-v2": "monocular depth estimation",
    "ditto-talkinghead": "authorized talking-head animation candidate",
    "duix-avatar": "authorized avatar generation candidate",
    "echomimic_v3": "audio-driven portrait animation candidate",
    "ffmpeg": "deterministic media probe, transform and encode foundation",
    "heygem-caladog": "authorized avatar benchmark candidate",
    "kokoro": "speech synthesis candidate",
    "latentSync": "lip synchronization candidate",
    "liveportrait": "authorized portrait animation candidate",
    "musetalk": "lip synchronization candidate",
    "opencv": "classical vision, geometry, color and measurement",
    "opentimelineio": "provider-neutral editorial interchange",
    "openvoice": "authorized voice-clone research candidate",
    "pyscenedetect": "shot-boundary candidate detection",
    "qwen3-vl": "semantic visual description candidate",
    "raft": "optical flow candidate",
    "sam2": "segmentation and mask continuity candidate",
    "tapnet": "point tracking candidate",
    "vjepa2": "temporal representation research candidate",
    "whisperx": "speech transcription and word alignment candidate",
    "supervision": "provider-isolated organization of detections, tracks, zones and annotations",
    "openmontage": "reference architecture for manifests, checkpoints, human gates and post-render inspection",
    "espeak-ng": "offline speech synthesis runtime and pronunciation fallback",
    "espeakng-loader": "runtime packaging and loading support for eSpeak NG",
    "fabric.js": "interactive canvas composition and object manipulation",
    "hyperframes": "programmatic motion/video composition candidate",
    "hyperframes-launch-video": "reference implementation for launch-video composition",
    "kimi-k2.5": "language-model planning research candidate",
    "konva": "interactive canvas scene graph for the editor",
    "lexical": "structured rich-text editing candidate",
    "misaki": "grapheme-to-phoneme and language preprocessing candidate",
    "motion-canvas": "programmatic TypeScript motion design candidate",
    "opencut": "open-source video-editor product and architecture reference",
    "opencut-classic": "legacy OpenCut editor architecture reference",
    "perth": "candidate capability whose exact role must be established from code and benchmark",
    "qwen3": "language-model planning and critique candidate",
    "react-timeline-editor": "timeline interaction component candidate",
    "remotion": "React-based deterministic video composition and rendering",
    "vane": "candidate capability whose exact role must be established from code and benchmark",
    "wan2.2": "generative video research candidate",
    "wavesurfer.js": "waveform visualization and audio navigation",
}

ADOPT = {"ffmpeg", "opencv", "opentimelineio", "pyscenedetect", "remotion"}
ADAPT = {
    "depth-anything-v2",
    "qwen3-vl",
    "raft",
    "sam2",
    "tapnet",
    "vjepa2",
    "whisperx",
    "supervision",
    "kokoro",
    "chatterbox",
    "espeak-ng",
    "fabric.js",
    "hyperframes",
    "konva",
    "misaki",
    "motion-canvas",
    "react-timeline-editor",
    "wavesurfer.js",
}


def run_git(repo: Path, *args: str) -> str:
    process = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    return process.stdout.strip()


def detect_license(repo: Path) -> tuple[str, str]:
    candidates = sorted(
        [path for pattern in ("LICENSE*", "COPYING*", "NOTICE*") for path in repo.glob(pattern) if path.is_file()],
        key=lambda item: item.name.lower(),
    )
    if not candidates:
        return "NOASSERTION", "license file not found at repository root"
    text = candidates[0].read_text(encoding="utf-8", errors="replace")[:12000].lower()
    matches = (
        ("AGPL-3.0", "affero general public license"),
        ("GPL-3.0", "gnu general public license"),
        ("Apache-2.0", "apache license"),
        ("MIT", "mit license"),
        ("BSD-3-Clause", "redistribution and use in source and binary forms"),
        ("MPL-2.0", "mozilla public license"),
        ("LGPL", "lesser general public license"),
    )
    for spdx, marker in matches:
        if marker in text:
            return spdx, candidates[0].name
    return "OTHER", candidates[0].name


def manifests(repo: Path) -> list[str]:
    names = (
        "pyproject.toml",
        "requirements.txt",
        "environment.yml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "Dockerfile",
        "docker-compose.yml",
        "setup.py",
    )
    return [name for name in names if (repo / name).exists()]


def infer_languages(repo: Path) -> list[str]:
    suffixes: dict[str, str] = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".js": "JavaScript",
        ".cpp": "C++",
        ".c": "C",
        ".rs": "Rust",
    }
    counts: dict[str, int] = {}
    checked = 0
    for path in repo.rglob("*"):
        if checked >= 5000:
            break
        if not path.is_file() or ".git" in path.parts:
            continue
        checked += 1
        language = suffixes.get(path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return [item[0] for item in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:4]]


def readme_summary(repo: Path) -> str:
    candidates = sorted(
        [path for path in repo.glob("README*") if path.is_file()],
        key=lambda item: (item.name.lower() != "readme.md", item.name.lower()),
    )
    if not candidates:
        return "README not found at repository root"
    text = candidates[0].read_text(encoding="utf-8", errors="replace")[:8000]
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"<[^>]+>", " ", raw)
        line = re.sub(r"!\[[^]]*\]\([^)]*\)", " ", line)
        line = re.sub(r"\[[^]]+\]\([^)]*\)", " ", line)
        line = re.sub(r"[#>*_`|~-]+", " ", line)
        line = " ".join(line.split())
        if len(line) < 20 or line.lower().startswith(("badge", "license", "copyright")):
            continue
        lines.append(line)
        if sum(len(item) for item in lines) >= 500:
            break
    return " ".join(lines)[:600] or "README contains no usable prose summary"


def capability_signals(repo: Path) -> dict[str, bool]:
    files = [
        path
        for name in ("README.md", "pyproject.toml", "requirements.txt", "package.json")
        if (path := repo / name).exists()
    ]
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace")[:50000] for path in files).lower()
    return {
        "gpu_signal": any(token in text for token in ("cuda", "gpu", "nvidia", "torch")),
        "container_recipe": (repo / "Dockerfile").exists() or (repo / "docker-compose.yml").exists(),
        "test_directory": (repo / "tests").exists() or (repo / "test").exists(),
        "pt_br_signal": any(token in text for token in ("pt-br", "portuguese", "português")),
    }


def audit(repo: Path) -> dict[str, object]:
    slug = repo.name.lower()
    license_spdx, license_file = detect_license(repo)
    origin = run_git(repo, "remote", "get-url", "origin") or "unknown"
    commit = run_git(repo, "rev-parse", "HEAD") or "unknown"
    exact_key = next((key for key in PURPOSES if key.lower() == slug), slug)
    purpose = PURPOSES.get(exact_key, "candidate capability requiring focused benchmark")
    signals = capability_signals(repo)
    if slug == "openmontage":
        decision = "reference-only"
        integration = "Reimplement manifest, checkpoint, decision-log and validation patterns independently; do not copy AGPL backend code without legal review."
    elif slug in ADOPT and license_spdx != "NOASSERTION":
        decision = "adopt"
        integration = (
            "Use behind a provider-neutral adapter with pinned version, deterministic fixtures and artifact lineage."
        )
    elif slug in ADAPT and license_spdx != "NOASSERTION":
        decision = "adapt"
        integration = "Evaluate behind an isolated worker/adapter; persist only canonical Clicko contracts."
    else:
        decision = "reference-only"
        integration = (
            "Keep outside the production domain until license, model assets, hardware and quality pass focused review."
        )
    risk = ["machine inventory does not validate model-weight or dataset licensing"]
    if license_spdx == "NOASSERTION":
        risk.append("root license not detected; fail closed")
    if license_spdx in {"AGPL-3.0", "GPL-3.0"}:
        risk.append("strong copyleft requires explicit legal/architecture review")
    if any(
        token in slug
        for token in ("avatar", "portrait", "talking", "muse", "echo", "ditto", "latent", "heygem", "openvoice")
    ):
        risk.append("biometric/identity use requires explicit consent, private benchmark and deletion controls")
    return {
        "schema_version": "studio.repository-capability-audit.v1",
        "repository_id": re.sub(r"[^a-z0-9._-]+", "-", slug),
        "path": str(repo),
        "origin_url": origin,
        "commit_sha": commit,
        "license_spdx": license_spdx,
        "license_evidence": license_file,
        "purpose": purpose,
        "manifests": manifests(repo),
        "languages_sampled": infer_languages(repo),
        "readme_summary_unverified": readme_summary(repo),
        "capability_signals": signals,
        "inputs": ["provider-specific; focused audit pending"],
        "outputs": ["provider-specific; must be projected to canonical contracts"],
        "hardware": (
            "GPU-related dependencies detected; exact VRAM/RAM envelope requires preflight"
            if signals["gpu_signal"]
            else "no GPU requirement established by static inventory; reproducible preflight still required"
        ),
        "pt_br_support": "partial_signal" if signals["pt_br_signal"] else "unknown",
        "quality": "not inferred from README; benchmark required",
        "determinism": "unknown",
        "observability": "partial: git provenance and manifests inventoried",
        "risks": risk,
        "integration": integration,
        "decision": decision,
        "benchmark": "license + dependency preflight, fixed fixture, resource envelope, output quality, repeatability, failure observability and PT-BR where relevant",
        "audit_status": "machine_inventory_complete_human_review_pending",
        "reviewed_at": datetime.now(UTC).isoformat(),
    }


def markdown(item: dict[str, object]) -> str:
    risks = "\n".join(f"- {risk}" for risk in item["risks"])
    return f"""# Auditoria — {item["repository_id"]}

**Status:** `{item["audit_status"]}`  
**Decisão provisória:** `{item["decision"]}`  
**Commit:** `{item["commit_sha"]}`  
**Origem:** {item["origin_url"]}  
**Licença detectada:** `{item["license_spdx"]}` em `{item["license_evidence"]}`

## Capacidade

{item["purpose"]}.

- Manifests: {", ".join(item["manifests"]) or "nenhum detectado"}
- Linguagens amostradas: {", ".join(item["languages_sampled"]) or "não identificadas"}
- Resumo do README, não verificado: {item["readme_summary_unverified"]}
- Sinais estáticos: `{json.dumps(item["capability_signals"], ensure_ascii=False)}`
- Hardware: {item["hardware"]}
- PT-BR: `{item["pt_br_support"]}`
- Determinismo: `{item["determinism"]}`
- Observabilidade: {item["observability"]}

## Integração proposta

{item["integration"]}

Tipos do repositório não podem atravessar worker/adapter para domínio, banco ou API. Somente contratos Clicko versionados são persistidos.

## Riscos

{risks}

## Benchmark mínimo

{item["benchmark"]}.

## Revisão necessária

- [ ] confirmar licença de código, pesos, datasets e exemplos;
- [ ] medir inputs, outputs, hardware, tempo e memória;
- [ ] executar fixture reproduzível sem mídia pessoal;
- [ ] avaliar segurança e cadeia de suprimentos;
- [ ] revisar suporte PT-BR;
- [ ] aprovar ou substituir a decisão provisória.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-root", type=Path, required=True)
    parser.add_argument("--supervision-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repos = [path for path in args.evaluation_root.iterdir() if path.is_dir() and (path / ".git").exists()]
    if args.supervision_root.exists():
        repos.append(args.supervision_root)
    audits = [audit(path) for path in sorted(repos, key=lambda item: item.name.lower())]
    args.output_root.mkdir(parents=True, exist_ok=True)
    for item in audits:
        (args.output_root / f"{item['repository_id']}.md").write_text(markdown(item), encoding="utf-8")
    (args.output_root / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "studio.repository-audit-registry.v1",
                "expected_count": 42,
                "actual_count": len(audits),
                "audits": audits,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if len(audits) == 42 else 2


if __name__ == "__main__":
    raise SystemExit(main())
