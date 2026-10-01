from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.ugc_no_voice import (
    UgcEditorialCaptionCueV1,
    UgcNoVoiceCreativeCaseV1,
    UgcNoVoiceSoundEvidenceV1,
)
from app.services.studios.ugc_no_voice import (
    assess_no_voice_case,
    audit_no_voice_casebook,
    canonical_digest,
    evaluate_no_voice_plan,
    load_ugc_no_voice_casebook,
)

ROOT = Path(__file__).resolve().parents[2]
CASEBOOK = ROOT / "benchmarks/studios/ugc/ugc-no-voice-natural-caption-casebook.v1.json"


def test_frozen_no_voice_casebook_covers_ten_niches_and_six_casting_slots() -> None:
    book = load_ugc_no_voice_casebook(CASEBOOK)
    assert book.suite_id == "clicko.ugc-no-voice-natural-caption.pt-br.v1"
    assert len(book.cases) == 10
    assert len({case.niche for case in book.cases}) == 10
    assert {case.avatar.candidate_id for case in book.cases} == {
        "lia",
        "maya",
        "nina",
        "caio",
        "theo",
        "bento",
    }
    assert book.profile.audio_mode == "natural-foley-only"
    assert book.profile.voice_policy == "prohibited"
    assert book.profile.captured_speech_policy == "prohibited"
    assert book.profile.music_policy == "prohibited"
    assert not book.profile.publication_enabled
    assert canonical_digest(book) != "c75d4adaefcf21e05247166081085cb6ee6b0e456bafc0565524b3d5a9b44040"


def test_every_plan_passes_mechanical_checks_but_production_fails_closed() -> None:
    book = load_ugc_no_voice_casebook(CASEBOOK)
    audit = audit_no_voice_casebook(book)
    assert len(audit.assessments) == 10
    assert all(item.planning_status == "pass" for item in audit.assessments)
    assert all(item.production_status == "blocked" for item in audit.assessments)
    assert all(
        next(gate for gate in item.capability_gates if gate.capability == "natural_sound_assets").status
        == "blocked"
        for item in audit.assessments
    )
    assert all(
        next(gate for gate in item.capability_gates if gate.capability == "publication").status == "blocked"
        for item in audit.assessments
    )


def test_caption_contract_rejects_long_line_and_overlapping_timeline() -> None:
    with pytest.raises(ValidationError):
        UgcEditorialCaptionCueV1(
            cue_id="too-long",
            order=0,
            role="hook",
            start_seconds=0,
            end_seconds=2,
            lines=["x" * 43],
        )

    case = load_ugc_no_voice_casebook(CASEBOOK).cases[0]
    payload = case.model_dump()
    payload["captions"][1]["start_seconds"] = payload["captions"][0]["end_seconds"] - 0.1
    with pytest.raises(ValidationError, match="cannot overlap"):
        UgcNoVoiceCreativeCaseV1.model_validate(payload)


def test_forbidden_claim_in_editorial_caption_fails_plan() -> None:
    book = load_ugc_no_voice_casebook(CASEBOOK)
    case = book.cases[0]
    captions = list(case.captions)
    captions[2] = captions[2].model_copy(update={"lines": ["Envio gratuito"]})
    contaminated = case.model_copy(update={"captions": captions})
    checks = evaluate_no_voice_plan(contaminated, book.profile)
    assert checks["claim_safety"] == "fail"
    assert assess_no_voice_case(contaminated, book.profile).planning_status == "fail"


def test_unverified_or_missing_sound_bytes_cannot_open_audio_gates(tmp_path: Path) -> None:
    book = load_ugc_no_voice_casebook(CASEBOOK)
    case = book.cases[0]
    missing = tmp_path / "missing.wav"
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps({"speechDetectionStatus": "pass", "musicDetectionStatus": "pass"}),
        encoding="utf-8",
    )
    evidence = [
        UgcNoVoiceSoundEvidenceV1(
            cue_id=cue.cue_id,
            asset_id=f"asset-{cue.cue_id}",
            path=str(missing),
            checksum_sha256="0" * 64,
            size_bytes=1,
            duration_seconds=1,
            source_uri="recorded-in-house:fixture",
            license_name="produção própria",
            license_uri="recorded-in-house:rights-receipt",
            speech_detector="fixture-detector",
            speech_report_path=str(report),
            speech_report_checksum_sha256="0" * 64,
            speech_detection_status="pass",
            music_detection_status="pass",
            human_listening_status="pass",
        )
        for cue in case.natural_sounds
    ]
    assessment = assess_no_voice_case(case, book.profile, sound_evidence=evidence, allowed_root=tmp_path)
    assert assessment.production_status == "blocked"
    by_capability = {gate.capability: gate.status for gate in assessment.capability_gates}
    assert by_capability["natural_sound_assets"] == "blocked"
    assert by_capability["voice_absence"] == "blocked"
    assert by_capability["music_absence"] == "blocked"


def test_audit_cli_writes_bound_evidence_without_media_generation(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace

    from scripts import audit_ugc_no_voice_plan as cli

    output = tmp_path / "audit"
    monkeypatch.setattr(cli.argparse.ArgumentParser, "parse_args", lambda _self: SimpleNamespace(
        casebook=CASEBOOK,
        output_dir=output,
    ))
    assert cli.main() == 0
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    audit = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    assert summary["plansPassed"] == 10
    assert summary["productionReady"] == 0
    assert summary["voiceExecuted"] is False
    assert summary["musicUsed"] is False
    assert summary["naturalSoundAssetsSupplied"] is False
    assert audit["externalPublicationExecuted"] is False
    assert (output / "contract-source.py").is_file()
    assert (output / "evaluator-source.py").is_file()
