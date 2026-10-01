from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.verify_duplex_research import verify

ROOT = Path(__file__).resolve().parents[2]
ALTERNATIVES = ROOT / "workers/speech-gpu/duplex-alternatives.research.json"
QWEN = ROOT / "workers/speech-gpu/qwen3-omni-30b-a3b.vendor-manifest.v1.json"
PERSONAPLEX = ROOT / "workers/speech-gpu/personaplex-reference.artifacts.json"
SPEECH_MANIFEST = ROOT / "workers/speech-gpu/worker.manifest.json"


def test_duplex_research_gate_accepts_only_disabled_candidates() -> None:
    assert verify(ALTERNATIVES, QWEN, PERSONAPLEX, SPEECH_MANIFEST) == {
        "candidateCount": 6,
        "personaplexDecision": "rejected",
        "providersEnabled": [],
        "qwenLicenseDecision": "review_required",
        "qwenWeightBytesDownloaded": 0,
        "qwenWeightFileCount": 15,
        "status": "duplex-research-gates-verified",
    }


def test_duplex_research_gate_rejects_claimed_qwen_download(tmp_path: Path) -> None:
    qwen = json.loads(QWEN.read_text(encoding="utf-8"))
    qwen["weightsDownloaded"] = True
    tampered = tmp_path / "qwen.json"
    tampered.write_text(json.dumps(qwen), encoding="utf-8")

    with pytest.raises(SystemExit, match="qwen_manifest_binding_mismatch"):
        verify(ALTERNATIVES, tampered, PERSONAPLEX, SPEECH_MANIFEST)
