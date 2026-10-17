from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from ...domain.studios.ugc_no_voice import (
    UgcNoVoiceCapabilityGateV1,
    UgcNoVoiceCaseAssessmentV1,
    UgcNoVoiceCasebookV1,
    UgcNoVoiceCreativeCaseV1,
    UgcNoVoiceEditorialReviewEvidenceV1,
    UgcNoVoicePlanAuditV1,
    UgcNoVoiceProfileV1,
    UgcNoVoiceSoundEvidenceV1,
    UgcNoVoiceVideoEvidenceV1,
)

MAX_CAPTION_CHARACTERS_PER_SECOND = 18.0
REQUIRED_PLAN_CHECKS = {
    "audio_policy",
    "caption_roles",
    "caption_readability",
    "caption_timeline",
    "natural_sound_plan",
    "claim_safety",
    "catalog_identity_boundary",
}


def canonical_digest(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(by_alias=True, mode="json")  # type: ignore[union-attr]
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_ugc_no_voice_casebook(path: Path) -> UgcNoVoiceCasebookV1:
    return UgcNoVoiceCasebookV1.model_validate_json(path.read_text(encoding="utf-8"))


def _caption_text(lines: list[str]) -> str:
    return " ".join(line.strip() for line in lines)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_path(path_value: str, checksum: str, allowed_root: Path) -> Path | None:
    path = Path(path_value).resolve()
    if not path.is_relative_to(allowed_root.resolve()) or not path.is_file():
        return None
    return path if _sha256_file(path).lower() == checksum.lower() else None


def evaluate_no_voice_plan(
    case: UgcNoVoiceCreativeCaseV1,
    profile: UgcNoVoiceProfileV1,
) -> dict[str, str]:
    combined_caption = " ".join(_caption_text(caption.lines) for caption in case.captions).lower()
    audio_policy = (
        profile.audio_mode == "natural-foley-only"
        and profile.voice_policy == "prohibited"
        and profile.captured_speech_policy == "prohibited"
        and profile.music_policy == "prohibited"
    )
    roles = [caption.role for caption in case.captions]
    caption_roles = roles[0] == "hook" and roles[-1] == "cta" and "demo" in roles
    caption_readability = all(
        len(_caption_text(caption.lines)) / (caption.end_seconds - caption.start_seconds)
        <= MAX_CAPTION_CHARACTERS_PER_SECOND
        for caption in case.captions
    )
    caption_timeline = all(
        caption.end_seconds <= next_caption.start_seconds
        for caption, next_caption in zip(case.captions, case.captions[1:], strict=False)
    ) and case.captions[-1].end_seconds <= case.duration_seconds
    natural_sound_plan = len(case.natural_sounds) >= 2 and all(
        sound.source_license_required and not sound.captured_speech_allowed and not sound.music_allowed
        for sound in case.natural_sounds
    )
    claim_safety = not any(claim.lower() in combined_caption for claim in case.forbidden_claims)
    catalog_identity_boundary = (
        case.avatar.catalog_only
        and not case.avatar.production_eligible
        and case.avatar.identity_version_id is None
        and case.avatar.voice_version_id is None
    )
    values = {
        "audio_policy": audio_policy,
        "caption_roles": caption_roles,
        "caption_readability": caption_readability,
        "caption_timeline": caption_timeline,
        "natural_sound_plan": natural_sound_plan,
        "claim_safety": claim_safety,
        "catalog_identity_boundary": catalog_identity_boundary,
    }
    return {key: "pass" if passed else "fail" for key, passed in values.items()}


def _sound_assets_ready(
    case: UgcNoVoiceCreativeCaseV1,
    evidence: list[UgcNoVoiceSoundEvidenceV1],
    *,
    allowed_root: Path | None,
) -> bool:
    if allowed_root is None:
        return False
    expected = {cue.cue_id for cue in case.natural_sounds}
    actual = {item.cue_id for item in evidence}
    if actual != expected or len(actual) != len(evidence):
        return False
    resolved_root = allowed_root.resolve()
    for item in evidence:
        path = _verified_path(item.path, item.checksum_sha256, resolved_root)
        report_path = _verified_path(
            item.speech_report_path,
            item.speech_report_checksum_sha256,
            resolved_root,
        )
        if path is None or report_path is None:
            return False
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            ffprobe = shutil.which("ffprobe")
            ffmpeg = shutil.which("ffmpeg")
            if not ffprobe or not ffmpeg:
                return False
            probed = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=codec_type:format=duration",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if probed.returncode:
                return False
            probe = json.loads(probed.stdout)
            stream = probe["streams"][0]
            actual_duration = float(probe["format"]["duration"])
            decoded = subprocess.run(
                [ffmpeg, "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
                capture_output=True,
                check=False,
                timeout=60,
            )
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            KeyError,
            IndexError,
            ValueError,
            subprocess.TimeoutExpired,
        ):
            return False
        if (
            path.stat().st_size != item.size_bytes
            or stream.get("codec_type") != "audio"
            or abs(actual_duration - item.duration_seconds) > 0.1
            or decoded.returncode
            or item.speech_detection_status != "pass"
            or item.music_detection_status != "pass"
            or item.human_listening_status != "pass"
            or report.get("cueId") != item.cue_id
            or str(report.get("assetChecksumSha256", "")).lower() != item.checksum_sha256.lower()
            or report.get("speechDetector") != item.speech_detector
            or report.get("speechDetectionStatus") != "pass"
            or report.get("musicDetectionStatus") != "pass"
        ):
            return False
    return True


def _video_ready(
    case: UgcNoVoiceCreativeCaseV1,
    evidence: UgcNoVoiceVideoEvidenceV1 | None,
    *,
    allowed_root: Path | None,
) -> bool:
    if evidence is None or allowed_root is None:
        return False
    video_path = _verified_path(evidence.path, evidence.checksum_sha256, allowed_root)
    report_path = _verified_path(
        evidence.final_mix_report_path,
        evidence.final_mix_report_checksum_sha256,
        allowed_root,
    )
    if video_path is None or report_path is None or video_path.stat().st_size != evidence.size_bytes:
        return False
    if (
        abs(evidence.duration_seconds - case.duration_seconds) > 0.1
        or evidence.fps != case.fps
        or evidence.speech_detection_status != "pass"
        or evidence.music_detection_status != "pass"
        or evidence.human_visual_review_status != "pass"
        or evidence.human_listening_status != "pass"
    ):
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return False
        completed = subprocess.run(
            [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if completed.returncode:
            return False
        probe = json.loads(completed.stdout)
        video_stream = next(item for item in probe["streams"] if item.get("codec_type") == "video")
        audio_stream = next(item for item in probe["streams"] if item.get("codec_type") == "audio")
        numerator, denominator = video_stream["avg_frame_rate"].split("/")
        actual_fps = float(numerator) / float(denominator)
        actual_duration = float(probe["format"]["duration"])
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        KeyError,
        StopIteration,
        ValueError,
        ZeroDivisionError,
        subprocess.TimeoutExpired,
    ):
        return False
    return (
        video_stream.get("codec_name") == "h264"
        and (int(video_stream.get("width", 0)), int(video_stream.get("height", 0)))
        == (case.width, case.height)
        and audio_stream.get("codec_type") == "audio"
        and abs(actual_fps - case.fps) <= 0.01
        and abs(actual_duration - case.duration_seconds) <= 0.1
        and report.get("caseId") == case.case_id
        and str(report.get("caseDigestSha256", "")).lower() == canonical_digest(case)
        and str(report.get("videoChecksumSha256", "")).lower() == evidence.checksum_sha256.lower()
        and report.get("speechDetectionStatus") == "pass"
        and report.get("musicDetectionStatus") == "pass"
    )


def _editorial_ready(
    case: UgcNoVoiceCreativeCaseV1,
    evidence: UgcNoVoiceEditorialReviewEvidenceV1 | None,
) -> bool:
    return bool(
        evidence
        and evidence.case_id == case.case_id
        and evidence.case_digest_sha256.lower() == canonical_digest(case)
        and all(
            status == "approved"
            for status in (
                evidence.copy_status,
                evidence.caption_status,
                evidence.synchronization_status,
                evidence.safety_status,
            )
        )
    )


def capability_gates(
    case: UgcNoVoiceCreativeCaseV1,
    profile: UgcNoVoiceProfileV1,
    *,
    sound_evidence: list[UgcNoVoiceSoundEvidenceV1] | None = None,
    allowed_root: Path | None = None,
    video_evidence: UgcNoVoiceVideoEvidenceV1 | None = None,
    editorial_review: UgcNoVoiceEditorialReviewEvidenceV1 | None = None,
) -> list[UgcNoVoiceCapabilityGateV1]:
    checks = evaluate_no_voice_plan(case, profile)
    plan_ready = REQUIRED_PLAN_CHECKS.issubset(checks) and all(checks[key] == "pass" for key in REQUIRED_PLAN_CHECKS)
    sounds_ready = _sound_assets_ready(case, sound_evidence or [], allowed_root=allowed_root)
    video_ready = _video_ready(case, video_evidence, allowed_root=allowed_root)
    voice_absence = sounds_ready and video_ready
    music_absence = sounds_ready and video_ready
    editorial_ready = _editorial_ready(case, editorial_review)
    gates = [
        UgcNoVoiceCapabilityGateV1(
            capability="caption_plan",
            status="executed" if plan_ready else "blocked",
            reason="Legenda editorial cronometrada passou no contrato mecânico."
            if plan_ready
            else "A legenda editorial falhou em pelo menos uma checagem obrigatória.",
        ),
        UgcNoVoiceCapabilityGateV1(
            capability="natural_sound_assets",
            status="executed" if sounds_ready else "blocked",
            reason="Todos os cues têm arquivo, checksum, licença e escuta humana verificados."
            if sounds_ready
            else "Não foram fornecidos todos os arquivos naturais com licença, checksum e escuta verificados.",
        ),
        UgcNoVoiceCapabilityGateV1(
            capability="voice_absence",
            status="executed" if voice_absence else "blocked",
            reason="Detector rastreável e escuta humana não encontraram fala."
            if voice_absence
            else "Ausência de fala ainda não foi comprovada por detector rastreável e escuta humana.",
        ),
        UgcNoVoiceCapabilityGateV1(
            capability="music_absence",
            status="executed" if music_absence else "blocked",
            reason="Detector rastreável e escuta humana não encontraram música."
            if music_absence
            else "Ausência de música ainda não foi comprovada por detector rastreável e escuta humana.",
        ),
        UgcNoVoiceCapabilityGateV1(
            capability="avatar_video",
            status="executed" if video_ready else "blocked",
            reason="Take UGC e direitos de imagem foram verificados."
            if video_ready
            else "O slot de casting não é um avatar produzido; arquivo, mix final e direitos estão pendentes.",
        ),
        UgcNoVoiceCapabilityGateV1(
            capability="editorial_review",
            status="executed" if editorial_ready else "blocked",
            reason="Revisão humana aprovou copy, legibilidade, sincronismo e segurança."
            if editorial_ready
            else "Revisão humana de copy, legibilidade, sincronismo e segurança está pendente.",
        ),
        UgcNoVoiceCapabilityGateV1(
            capability="publication",
            status="blocked",
            reason="Este corpus é um benchmark local e seu perfil proíbe publicação externa.",
        ),
    ]
    return gates


def assess_no_voice_case(
    case: UgcNoVoiceCreativeCaseV1,
    profile: UgcNoVoiceProfileV1,
    *,
    sound_evidence: list[UgcNoVoiceSoundEvidenceV1] | None = None,
    allowed_root: Path | None = None,
    video_evidence: UgcNoVoiceVideoEvidenceV1 | None = None,
    editorial_review: UgcNoVoiceEditorialReviewEvidenceV1 | None = None,
) -> UgcNoVoiceCaseAssessmentV1:
    checks = evaluate_no_voice_plan(case, profile)
    planning_status = (
        "pass"
        if REQUIRED_PLAN_CHECKS.issubset(checks) and all(checks[key] == "pass" for key in REQUIRED_PLAN_CHECKS)
        else "fail"
    )
    gates = capability_gates(
        case,
        profile,
        sound_evidence=sound_evidence,
        allowed_root=allowed_root,
        video_evidence=video_evidence,
        editorial_review=editorial_review,
    )
    required_for_video = {
        "caption_plan",
        "natural_sound_assets",
        "voice_absence",
        "music_absence",
        "avatar_video",
        "editorial_review",
    }
    by_capability = {gate.capability: gate.status for gate in gates}
    production_status = (
        "ready" if all(by_capability[capability] == "executed" for capability in required_for_video) else "blocked"
    )
    return UgcNoVoiceCaseAssessmentV1(
        case_id=case.case_id,
        planning_checks=checks,
        planning_status=planning_status,
        production_status=production_status,
        capability_gates=gates,
    )


def audit_no_voice_casebook(book: UgcNoVoiceCasebookV1) -> UgcNoVoicePlanAuditV1:
    return UgcNoVoicePlanAuditV1(
        suite_id=book.suite_id,
        casebook_digest_sha256=canonical_digest(book),
        assessed_at=datetime.now(UTC),
        assessments=[assess_no_voice_case(case, book.profile) for case in book.cases],
    )
