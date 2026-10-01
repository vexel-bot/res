from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from ...domain.studios.contracts import (
    BrandMemoryReferenceV1,
    CreativeBriefV1,
    CreativeCompositionV1,
    CreativeDocumentV1,
    CreativeLayerV1,
    CreativePageV1,
    ProviderLineageV1,
)
from ...domain.studios.intelligence import (
    PlanningCopyRequestV1,
    PlanningCopyResultV1,
    PlanningCopyRevisionContextV1,
)
from ...domain.studios.ugc_acceptance import (
    UgcAdAcceptanceCasebookV1,
    UgcAdAcceptanceCaseV1,
    UgcArtifactEvidenceV1,
    UgcCapabilityGateV1,
    UgcCriterionResultV1,
)
from ..creatives import render_creative
from .compatibility import composition_page_to_canvas

AVATAR_COLORS = {
    "lia": ("#ff8f70", "#3f1710"),
    "maya": ("#b9a3ff", "#241a4c"),
    "nina": ("#ff6f91", "#451020"),
    "caio": ("#63c7ff", "#082d43"),
    "theo": ("#5dd6a5", "#0b3628"),
    "bento": ("#f3c75f", "#3c2c05"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_digest(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(by_alias=True, mode="json")
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_ugc_acceptance_casebook(path: Path) -> UgcAdAcceptanceCasebookV1:
    book = UgcAdAcceptanceCasebookV1.model_validate_json(path.read_text(encoding="utf-8"))
    policy = path.parent.parent / "intelligence/planning-copy-pt-br-policy.v1.json"
    if not policy.is_file() or sha256_file(policy) != book.policy_digest_sha256:
        raise ValueError("ugc_casebook_policy_digest_mismatch")
    return book


def _criterion(
    criterion_id: str,
    passed: bool,
    *,
    score: float,
    weight: float,
    evidence: list[str],
    notes: list[str] | None = None,
) -> UgcCriterionResultV1:
    return UgcCriterionResultV1(
        criterion_id=criterion_id,
        status="pass" if passed else "fail",
        score=score,
        weight=weight,
        evidence=evidence,
        notes=notes or [],
    )


def evaluate_planning_copy(
    case: UgcAdAcceptanceCaseV1,
    result: PlanningCopyResultV1,
) -> list[UgcCriterionResultV1]:
    draft = result.draft
    combined = " ".join(
        [
            draft.brief.hook,
            draft.brief.cta,
            draft.script,
            *(beat.copy_text for beat in draft.storyboard),
            *(beat.on_screen_text for beat in draft.storyboard),
        ]
    ).lower()
    roles = [beat.narrative_role for beat in draft.storyboard]
    criteria: list[UgcCriterionResultV1] = []
    unexpected_script = any("\u3400" <= char <= "\u9fff" for char in combined)
    criteria.append(
        _criterion(
            "pt_br_script_contamination",
            not unexpected_script,
            score=0 if unexpected_script else 5,
            weight=1,
            evidence=["Triagem CJK no corpus PT-BR sem termos CJK autorizados; não mede fluência."],
        )
    )

    hook_ok = bool(draft.brief.hook.strip()) and bool(roles) and roles[0] == "hook"
    criteria.append(
        _criterion(
            "hook_clarity",
            hook_ok,
            score=5 if hook_ok else 1,
            weight=1.5,
            evidence=[draft.brief.hook[:240] or "hook ausente", f"firstRole={roles[0] if roles else 'none'}"],
        )
    )
    hook_words = len(draft.brief.hook.split())
    hook_ok = 3 <= hook_words <= 14
    criteria.append(
        _criterion(
            "hook_pacing",
            hook_ok,
            score=5 if hook_ok else 1,
            weight=0.75,
            evidence=[f"hookWords={hook_words}", "target=3-14"],
        )
    )
    cta_ok = bool(draft.brief.cta.strip()) and "cta" in roles
    criteria.append(
        _criterion(
            "cta_clarity",
            cta_ok,
            score=5 if cta_ok else 1,
            weight=1.25,
            evidence=[draft.brief.cta[:240] or "CTA ausente", f"roles={','.join(roles)}"],
        )
    )

    internal_leaks = [
        fragment for fragment in ("kit de anúncio", "benchmark", "pipeline", "prompt") if fragment in combined
    ]
    criteria.append(
        _criterion(
            "product_fidelity",
            not internal_leaks,
            score=5 if not internal_leaks else 0,
            weight=1.5,
            evidence=[f"product={case.request.product[:180]}"],
            notes=[f"internalLeak={','.join(internal_leaks)}"] if internal_leaks else [],
        )
    )

    missing_terms = [term for term in case.expectation.required_terms if term.lower() not in combined]
    criteria.append(
        _criterion(
            "message_alignment",
            not missing_terms,
            score=5 if not missing_terms else max(0, 5 - 2 * len(missing_terms)),
            weight=1.5,
            evidence=[f"required={','.join(case.expectation.required_terms)}"],
            notes=[f"missing={','.join(missing_terms)}"] if missing_terms else [],
        )
    )

    found_forbidden = [fragment for fragment in case.expectation.forbidden_claims if fragment.lower() in combined]
    criteria.append(
        _criterion(
            "forbidden_claims",
            not found_forbidden,
            score=5 if not found_forbidden else 0,
            weight=2,
            evidence=[f"checked={len(case.expectation.forbidden_claims)}"],
            notes=[f"found={','.join(found_forbidden)}"] if found_forbidden else [],
        )
    )

    structure_ok = (
        len(draft.storyboard) >= case.expectation.minimum_storyboard_beats and "hook" in roles and "cta" in roles
    )
    criteria.append(
        _criterion(
            "storyboard_structure",
            structure_ok,
            score=5 if structure_ok else 2,
            weight=1.25,
            evidence=[f"beats={len(draft.storyboard)}", f"roles={','.join(roles)}"],
        )
    )

    duration = case.deliverables.video_duration_seconds
    word_count = len(draft.script.split())
    minimum_words = {15: 24, 20: 32, 30: 48}[duration]
    maximum_words = {15: 44, 20: 58, 30: 84}[duration]
    pacing_ok = minimum_words <= word_count <= maximum_words
    criteria.append(
        _criterion(
            "spoken_pacing",
            pacing_ok,
            score=5 if pacing_ok else (3 if word_count <= maximum_words * 1.2 else 1),
            weight=1,
            evidence=[f"words={word_count}", f"target={minimum_words}-{maximum_words}", f"duration={duration}s"],
        )
    )

    claims_safe = all(claim.evidence_ids or claim.requires_human_review for claim in draft.claims)
    sensitive_abstention = case.expectation.sensitive_category == "none" or bool(draft.abstentions)
    safety_ok = claims_safe and sensitive_abstention
    criteria.append(
        _criterion(
            "review_routing",
            safety_ok,
            score=5 if safety_ok else 0,
            weight=2,
            evidence=[
                f"claims={len(draft.claims)}",
                f"abstentions={len(draft.abstentions)}",
                f"sensitive={case.expectation.sensitive_category}",
            ],
            notes=[] if safety_ok else ["Alegação sem evidência/revisão ou categoria sensível sem abstenção."],
        )
    )
    spoken = " ".join(beat.copy_text.strip() for beat in draft.storyboard)
    same_script = " ".join(spoken.split()) == " ".join(draft.script.split())
    criteria.append(
        _criterion(
            "single_spoken_source",
            same_script,
            score=5 if same_script else 0,
            weight=1,
            evidence=[f"scriptMatchesOrderedBeats={same_script}"],
        )
    )
    complete_sentences = bool(draft.storyboard) and all(
        beat.copy_text.strip().endswith((".", "?", "!", "…")) for beat in draft.storyboard
    )
    criteria.append(
        _criterion(
            "spoken_sentence_completion",
            complete_sentences,
            score=5 if complete_sentences else 0,
            weight=1,
            evidence=["Terminação de frase é apenas triagem; gramática e naturalidade exigem revisão."],
        )
    )
    criteria.append(
        UgcCriterionResultV1(
            criterion_id="editorial_review",
            status="manual_review",
            score=None,
            notes=[
                "Presença de campos, palavras ou flags não comprova qualidade editorial nem veracidade.",
                "Revisar oferta, alegações, naturalidade PT-BR, persuasão e adequação visual antes de usar.",
            ],
        )
    )

    scene_tokens = {
        token.strip(".,;:()") for token in case.scene.setting.lower().split() if len(token.strip(".,;:()")) >= 5
    }
    visual_text = " ".join(beat.visual_direction for beat in draft.storyboard).lower()
    matched_scene_tokens = sorted(token for token in scene_tokens if token in visual_text)
    scene_ok = bool(matched_scene_tokens)
    criteria.append(
        _criterion(
            "scene_direction_alignment",
            scene_ok,
            score=5 if scene_ok else 2,
            weight=0.75,
            evidence=[f"matched={','.join(matched_scene_tokens[:8]) or 'none'}"],
        )
    )
    return criteria


def weighted_score(criteria: list[UgcCriterionResultV1]) -> float:
    scored = [item for item in criteria if item.score is not None]
    numerator = sum(float(item.score) * item.weight for item in scored)
    denominator = sum(item.weight for item in scored)
    return round(numerator / denominator, 3) if denominator else 0


REQUIRED_PREFLIGHT_CRITERIA = {
    "pt_br_script_contamination",
    "hook_clarity",
    "hook_pacing",
    "cta_clarity",
    "product_fidelity",
    "message_alignment",
    "forbidden_claims",
    "storyboard_structure",
    "spoken_pacing",
    "review_routing",
    "single_spoken_source",
    "spoken_sentence_completion",
    "scene_direction_alignment",
    "artifact_integrity",
}


def automated_preflight_status(criteria: list[UgcCriterionResultV1]) -> str:
    """No numeric average may compensate for a failed or missing required check."""
    by_id = {item.criterion_id: item for item in criteria}
    if len(by_id) != len(criteria) or not REQUIRED_PREFLIGHT_CRITERIA.issubset(by_id):
        return "fail"
    return "pass" if all(by_id[key].status == "pass" for key in REQUIRED_PREFLIGHT_CRITERIA) else "fail"


def build_ugc_revision_request(
    case: UgcAdAcceptanceCaseV1,
    previous: PlanningCopyResultV1,
) -> PlanningCopyRequestV1:
    """Supply actionable criticism without mutating the frozen brief or replacing model copy."""
    checks = evaluate_planning_copy(case, previous)
    feedback = [
        "Revisar apenas a redação e as cenas; preservar canal, formato, restrições, fatos e oferta do INPUT_JSON.",
        "Uma frase completa e curta por cena. O roteiro é a concatenação dessas cinco falas.",
    ]
    feedback.extend(
        f"Corrigir {check.criterion_id}: {'; '.join([*check.evidence, *check.notes])}"
        for check in checks
        if check.status == "fail"
    )
    updated = case.request.model_dump()
    updated["revision_context"] = PlanningCopyRevisionContextV1(
        previous_request_id=previous.request_id,
        previous_script=previous.draft.script,
        feedback=feedback,
        locked_fields=["channel", "format", "restrictions", "evidence"],
    )
    return PlanningCopyRequestV1.model_validate(updated)


def verify_ad_kit(
    case: UgcAdAcceptanceCaseV1,
    artifacts: list[UgcArtifactEvidenceV1],
    *,
    allowed_root: Path,
) -> UgcCriterionResultV1:
    """Read actual bytes, fail on omission/tampering, inspect media rather than trusting declared sizes."""
    errors: list[str] = []
    expected = {"planning-json", "visual-png", "carousel-zip", "animatic-mp4", "manifest-json"}
    kinds = [artifact.artifact_type for artifact in artifacts]
    if set(kinds) != expected or len(kinds) != len(expected):
        errors.append("artifact_set_missing_or_duplicated")
    for artifact in artifacts:
        path = Path(artifact.path).resolve()
        if not path.is_relative_to(allowed_root.resolve()):
            errors.append(f"{artifact.artifact_type}:outside_run_root")
            continue
        try:
            if path.stat().st_size != artifact.size_bytes or sha256_file(path) != artifact.checksum_sha256:
                raise ValueError("artifact_checksum_or_size_mismatch")
            if artifact.artifact_type == "planning-json":
                planning = PlanningCopyResultV1.model_validate_json(path.read_text(encoding="utf-8"))
                if planning.request_id != case.case_id:
                    raise ValueError("planning_case_mismatch")
            elif artifact.artifact_type == "visual-png":
                with Image.open(path) as visual:
                    visual.load()
                    if visual.size != (1080, 1350) or visual.format != "PNG":
                        raise ValueError("visual_geometry_or_format_mismatch")
            elif artifact.artifact_type == "carousel-zip":
                with zipfile.ZipFile(path) as archive:
                    expected_pages = [f"{index:02d}.png" for index in range(1, case.deliverables.carousel_pages + 1)]
                    if archive.namelist() != ["manifest.json", *expected_pages]:
                        raise ValueError("carousel_page_order_or_count_mismatch")
                    manifest = json.loads(archive.read("manifest.json"))
                    if manifest.get("caseId") != case.case_id:
                        raise ValueError("carousel_case_mismatch")
                    if manifest.get("orderedPages") != [
                        f"{case.case_id}-{i}" for i in range(1, len(expected_pages) + 1)
                    ]:
                        raise ValueError("carousel_page_manifest_mismatch")
                    for name in expected_pages:
                        with Image.open(io.BytesIO(archive.read(name))) as page:
                            page.load()
                            if page.size != (1080, 1350) or page.format != "PNG":
                                raise ValueError("carousel_geometry_or_format_mismatch")
            elif artifact.artifact_type == "animatic-mp4":
                probe = probe_video(path)
                if (probe["width"], probe["height"]) != (1080, 1920):
                    raise ValueError("video_geometry_mismatch")
                if abs(float(probe["duration"]) - case.deliverables.video_duration_seconds) > 0.1:
                    raise ValueError("video_duration_mismatch")
                if abs(float(probe["fps"]) - case.deliverables.video_fps) > 0.01 or probe["codec"] != "h264":
                    raise ValueError("video_fps_or_codec_mismatch")
                ffmpeg = shutil.which("ffmpeg")
                if not ffmpeg:
                    raise ValueError("ffmpeg_decode_unavailable")
                decoded = subprocess.run(
                    [ffmpeg, "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
                    capture_output=True,
                    check=False,
                    timeout=90,
                )
                if decoded.returncode:
                    raise ValueError("video_decode_failed")
            elif artifact.artifact_type == "manifest-json":
                manifest = json.loads(path.read_text(encoding="utf-8"))
                if manifest.get("caseId") != case.case_id or any(
                    manifest.get(key) is not False
                    for key in (
                        "avatarInferenceExecuted",
                        "voiceCloneExecuted",
                        "lipSyncExecuted",
                        "publicationEnabled",
                    )
                ):
                    raise ValueError("manifest_claims_or_case_mismatch")
        except (
            OSError,
            ValueError,
            KeyError,
            IndexError,
            ZeroDivisionError,
            RuntimeError,
            zipfile.BadZipFile,
            subprocess.TimeoutExpired,
        ) as error:
            errors.append(f"{artifact.artifact_type}:{type(error).__name__}:{str(error)[:120]}")
    return _criterion(
        "artifact_integrity",
        not errors,
        score=5 if not errors else 0,
        weight=1,
        evidence=[f"verifiedArtifacts={len(artifacts)}"],
        notes=errors,
    )


def _shape(
    layer_id: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    radius: int = 0,
    shape: str = "rectangle",
    z: int = 0,
) -> CreativeLayerV1:
    return CreativeLayerV1(
        id=layer_id,
        kind="shape",
        name=layer_id,
        x=x,
        y=y,
        width=width,
        height=height,
        z_index=z,
        properties={"type": "shape", "shape": shape, "fill": fill, "radius": radius},
    )


def _text(
    layer_id: str,
    text: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    size: int,
    color: str,
    align: str = "left",
    z: int = 10,
) -> CreativeLayerV1:
    return CreativeLayerV1(
        id=layer_id,
        kind="text",
        name=layer_id,
        x=x,
        y=y,
        width=width,
        height=height,
        z_index=z,
        properties={
            "type": "text",
            "text": text or "Revisão necessária",
            "fontSize": size,
            "minFontSize": max(18, round(size * 0.48)),
            "fontFamily": "DejaVu Sans",
            "fontWeight": "bold",
            "color": color,
            "align": align,
            "lineHeight": 1.08,
        },
    )


def _page(
    case: UgcAdAcceptanceCaseV1,
    *,
    page_id: str,
    eyebrow: str,
    headline: str,
    body: str,
    width: int,
    height: int,
    role: str,
) -> CreativePageV1:
    accent, ink = AVATAR_COLORS[case.avatar.candidate_id]
    scale = height / 1350
    safe = round(72 * min(scale, 1.25))
    avatar_size = round(min(width * 0.34, height * 0.22))
    avatar_x = width - safe - avatar_size
    avatar_y = round(height * 0.13)
    layers = [
        _shape("stage", x=0, y=0, width=width, height=height, fill="#101216", z=0),
        _shape(
            "scene-panel",
            x=safe,
            y=round(height * 0.08),
            width=width - 2 * safe,
            height=round(height * 0.84),
            fill=ink,
            radius=round(42 * scale),
            z=1,
        ),
        _shape(
            "avatar-slot",
            x=avatar_x,
            y=avatar_y,
            width=avatar_size,
            height=avatar_size,
            fill=accent,
            shape="ellipse",
            z=3,
        ),
        _text(
            "avatar-initials",
            case.avatar.display_name[:2].upper(),
            x=avatar_x,
            y=avatar_y + avatar_size * 0.28,
            width=avatar_size,
            height=avatar_size * 0.45,
            size=round(avatar_size * 0.26),
            color=ink,
            align="center",
            z=4,
        ),
        _text(
            "catalog-label",
            f"AVATAR CATÁLOGO · {case.avatar.display_name}\nINFERÊNCIA PENDENTE",
            x=safe * 1.5,
            y=round(height * 0.13),
            width=max(240, avatar_x - safe * 2),
            height=round(height * 0.11),
            size=round(25 * scale),
            color=accent,
            z=5,
        ),
        _text(
            "eyebrow",
            eyebrow.upper(),
            x=safe * 1.5,
            y=round(height * 0.35),
            width=width - safe * 3,
            height=round(height * 0.08),
            size=round(27 * scale),
            color=accent,
            z=5,
        ),
        _text(
            "headline",
            headline,
            x=safe * 1.5,
            y=round(height * 0.43),
            width=width - safe * 3,
            height=round(height * 0.24),
            size=round(64 * scale),
            color="#ffffff",
            z=5,
        ),
        _text(
            "body",
            body,
            x=safe * 1.5,
            y=round(height * 0.70),
            width=width - safe * 3,
            height=round(height * 0.13),
            size=round(31 * scale),
            color="#ebeef5",
            z=5,
        ),
        _text(
            "scene-label",
            f"CENÁRIO: {case.scene.setting}",
            x=safe * 1.5,
            y=round(height * 0.86),
            width=width - safe * 3,
            height=round(height * 0.04),
            size=round(18 * scale),
            color="#aeb4c0",
            z=5,
        ),
    ]
    return CreativePageV1(
        id=page_id,
        role=role,
        width=width,
        height=height,
        safe_area=safe,
        background="#101216",
        layers=layers,
    )


def build_ad_document(
    case: UgcAdAcceptanceCaseV1,
    result: PlanningCopyResultV1,
    *,
    content_type: str,
    vertical_video: bool = False,
) -> CreativeDocumentV1:
    draft = result.draft
    if content_type == "visual":
        page_specs = [("visual", "Anúncio UGC", draft.brief.hook, draft.brief.cta)]
        width, height = case.deliverables.visual_width, case.deliverables.visual_height
    else:
        beats = draft.storyboard[:5]
        while len(beats) < 5:
            beats.append(None)
        page_specs = [
            ("hook", "O ponto de partida", draft.brief.hook, case.concept),
            (
                "problem",
                "Por que importa",
                beats[1].on_screen_text if beats[1] else case.concept,
                beats[1].copy_text if beats[1] else draft.script,
            ),
            (
                "benefit",
                "Como funciona",
                beats[2].on_screen_text if beats[2] else draft.brief.promise,
                beats[2].copy_text if beats[2] else draft.brief.angle,
            ),
            (
                "proof",
                "O que precisa ser validado",
                beats[3].on_screen_text if beats[3] else "Revisão antes de publicar",
                beats[3].copy_text
                if beats[3]
                else "Sem prova inventada: oferta, direitos e alegações seguem para revisão.",
            ),
            ("cta", "Próximo passo", draft.brief.cta, "Confirme oferta, direitos e revisão antes de publicar."),
        ]
        if vertical_video:
            width, height = case.deliverables.video_width, case.deliverables.video_height
        else:
            width, height = case.deliverables.carousel_width, case.deliverables.carousel_height

    pages = [
        _page(
            case,
            page_id=f"{case.case_id}-{index + 1}",
            eyebrow=eyebrow,
            headline=headline,
            body=body,
            width=width,
            height=height,
            role=role,
        )
        for index, (role, eyebrow, headline, body) in enumerate(page_specs)
    ]
    now = datetime.now(UTC)
    resolved_type = "video" if vertical_video else content_type
    return CreativeDocumentV1(
        document_id=f"benchmark-{case.case_id}-{resolved_type}",
        workspace_id=case.request.workspace_id,
        title=f"{case.concept} · {resolved_type}",
        content_type=resolved_type,
        correlation_id=f"ugc-acceptance:{case.case_id}",
        brand_memory_ref=BrandMemoryReferenceV1(id=case.request.brand_memory_ref.id, revision=1),
        brief=CreativeBriefV1(
            objective=case.request.objective,
            audience=case.request.audience,
            angle=draft.brief.angle,
            promise=draft.brief.promise,
            hook=draft.brief.hook,
            cta=draft.brief.cta,
            channel=case.request.channel,
            format=case.request.format,
            tone=case.request.tone,
            restrictions=case.request.restrictions,
        ),
        composition=CreativeCompositionV1(
            pages=pages,
            narrative={
                "caseId": case.case_id,
                "avatarCatalogSlot": case.avatar.candidate_id,
                "avatarInferenceExecuted": False,
                "scene": case.scene.model_dump(by_alias=True, mode="json"),
            },
        ),
        lineage=[
            ProviderLineageV1(
                provider="clicko.canonical-static-compositor",
                model=None,
                provider_version="ugc-acceptance-v1",
                parameters={"avatarMode": "catalog-placeholder", "publicationEnabled": False},
                generated_at=now,
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _render_document(document: CreativeDocumentV1) -> list[Image.Image]:
    return [
        render_creative(composition_page_to_canvas(document, index), {})
        for index in range(len(document.composition.pages))
    ]


def _artifact(
    artifact_type: str,
    path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
    duration_seconds: float | None = None,
    page_count: int | None = None,
) -> UgcArtifactEvidenceV1:
    return UgcArtifactEvidenceV1(
        artifact_type=artifact_type,
        path=str(path.resolve()),
        checksum_sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        page_count=page_count,
    )


def render_ad_kit(
    case: UgcAdAcceptanceCaseV1,
    result: PlanningCopyResultV1,
    output_directory: Path,
) -> list[UgcArtifactEvidenceV1]:
    output_directory.mkdir(parents=True, exist_ok=True)
    artifacts: list[UgcArtifactEvidenceV1] = []

    planning_path = output_directory / "planning-result.json"
    planning_path.write_text(result.model_dump_json(by_alias=True, indent=2), encoding="utf-8")
    artifacts.append(_artifact("planning-json", planning_path))

    visual_document = build_ad_document(case, result, content_type="visual")
    visual_path = output_directory / "visual-1080x1350.png"
    _render_document(visual_document)[0].save(visual_path, format="PNG", optimize=True)
    artifacts.append(_artifact("visual-png", visual_path, width=1080, height=1350, page_count=1))

    carousel_document = build_ad_document(case, result, content_type="carousel")
    carousel_images = _render_document(carousel_document)
    carousel_path = output_directory / "carousel-1080x1350.zip"
    with zipfile.ZipFile(carousel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "schemaVersion": "studio.ugc-carousel-export.v1",
                    "caseId": case.case_id,
                    "orderedPages": [page.id for page in carousel_document.composition.pages],
                    "avatarInferenceExecuted": False,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        for index, image in enumerate(carousel_images, start=1):
            payload = io.BytesIO()
            image.save(payload, format="PNG", optimize=True)
            archive.writestr(f"{index:02d}.png", payload.getvalue())
    artifacts.append(
        _artifact(
            "carousel-zip",
            carousel_path,
            width=1080,
            height=1350,
            page_count=len(carousel_images),
        )
    )

    video_document = build_ad_document(case, result, content_type="carousel", vertical_video=True)
    video_images = _render_document(video_document)
    frame_paths: list[Path] = []
    for index, image in enumerate(video_images, start=1):
        frame_path = output_directory / f"animatic-frame-{index:02d}.png"
        image.save(frame_path, format="PNG", optimize=True)
        frame_paths.append(frame_path)
    video_path = output_directory / "editorial-animatic-1080x1920.mp4"
    encode_animatic(
        frame_paths,
        video_path,
        duration_seconds=case.deliverables.video_duration_seconds,
        fps=case.deliverables.video_fps,
    )
    probe = probe_video(video_path)
    artifacts.append(
        _artifact(
            "animatic-mp4",
            video_path,
            width=probe["width"],
            height=probe["height"],
            duration_seconds=probe["duration"],
            page_count=len(frame_paths),
        )
    )

    manifest_path = output_directory / "kit-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schemaVersion": "studio.ugc-ad-kit-manifest.v1",
                "caseId": case.case_id,
                "avatarCandidateId": case.avatar.candidate_id,
                "avatarInferenceExecuted": False,
                "voiceCloneExecuted": False,
                "lipSyncExecuted": False,
                "publicationEnabled": False,
                "artifacts": [item.model_dump(by_alias=True, mode="json") for item in artifacts],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    artifacts.append(_artifact("manifest-json", manifest_path))
    return artifacts


def encode_animatic(frame_paths: list[Path], output_path: Path, *, duration_seconds: int, fps: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg_not_available")
    if not frame_paths:
        raise ValueError("animatic_requires_frames")
    concat_path = output_path.with_suffix(".concat.txt")
    frame_duration = duration_seconds / len(frame_paths)
    lines: list[str] = []
    for path in frame_paths:
        escaped = path.resolve().as_posix().replace("'", "'\\''")
        lines.extend([f"file '{escaped}'", f"duration {frame_duration:.6f}"])
    final_escaped = frame_paths[-1].resolve().as_posix().replace("'", "'\\''")
    lines.append(f"file '{final_escaped}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t",
        str(duration_seconds),
        "-vf",
        f"fps={fps},format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "24",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=180)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg_animatic_failed: {completed.stderr[-1000:]}")


def probe_video(path: Path) -> dict[str, float | int | str]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe_not_available")
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,codec_name,avg_frame_rate:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError("ffprobe_animatic_failed")
    payload = json.loads(completed.stdout)
    stream = payload["streams"][0]
    numerator, denominator = stream["avg_frame_rate"].split("/")
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": float(payload["format"]["duration"]),
        "fps": float(numerator) / float(denominator),
        "codec": str(stream["codec_name"]),
    }


def standard_capability_gates(*, generated: bool, rendered: bool) -> list[UgcCapabilityGateV1]:
    return [
        UgcCapabilityGateV1(
            capability="planning_copy",
            status="executed" if generated else "blocked",
            reason="Qwen self-hosted retornou contrato válido."
            if generated
            else "Provider de planejamento não concluiu.",
        ),
        UgcCapabilityGateV1(
            capability="static_composition",
            status="executed" if rendered else "blocked",
            reason="Compositor canônico renderizou PNG." if rendered else "Sem copy estruturada para compor.",
        ),
        UgcCapabilityGateV1(
            capability="carousel_export",
            status="executed" if rendered else "blocked",
            reason="Exportador gerou conjunto ordenado." if rendered else "Sem composição disponível.",
        ),
        UgcCapabilityGateV1(
            capability="video_animatic",
            status="executed" if rendered else "blocked",
            reason="FFmpeg codificou animatic editorial com áudio silencioso."
            if rendered
            else "Sem quadros disponíveis.",
        ),
        UgcCapabilityGateV1(
            capability="avatar_inference",
            status="blocked",
            reason="Nenhum IdentityVersion ativo, provider aprovado ou GPU de avatar disponível neste host.",
        ),
        UgcCapabilityGateV1(
            capability="voice_clone",
            status="blocked",
            reason="Nenhum VoiceVersion consentido e worker GPU Chatterbox executável neste host.",
        ),
        UgcCapabilityGateV1(
            capability="lip_sync",
            status="blocked",
            reason="Lip-sync depende de áudio e avatar finais aprovados; não pode ser inferido do animatic.",
        ),
    ]
