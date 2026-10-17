from __future__ import annotations

import hashlib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from app.domain.studios.contracts import CreativeBriefV1
from app.domain.studios.intelligence import (
    IntelligenceLineageV1,
    PlanningClaimV1,
    PlanningCopyDraftV1,
    PlanningCopyResultV1,
    PlanningStoryboardBeatV1,
    planning_copy_request_digest,
)
from app.services.studios.ugc_acceptance import (
    _render_document,
    automated_preflight_status,
    build_ad_document,
    build_ugc_revision_request,
    encode_animatic,
    evaluate_planning_copy,
    load_ugc_acceptance_casebook,
    probe_video,
    render_ad_kit,
    sha256_file,
    verify_ad_kit,
    weighted_score,
)

ROOT = Path(__file__).resolve().parents[2]
CASEBOOK_PATH = ROOT / "benchmarks/studios/ugc/ugc-ad-creative-acceptance-casebook.v1.json"


def _result(case, *, forbidden: str | None = None) -> PlanningCopyResultV1:
    beats = [
        PlanningStoryboardBeatV1(
            beat_id="hook",
            order=0,
            narrative_role="hook",
            duration_seconds=3,
            visual_direction=f"Plano médio na {case.scene.setting}.",
            copy_text="Seu café muda toda semana?",
            on_screen_text="Café sem aposta",
        ),
        PlanningStoryboardBeatV1(
            beat_id="problem",
            order=1,
            narrative_role="problem",
            duration_seconds=3,
            visual_direction="Avatar mostra a caneca e explica o problema.",
            copy_text="Escolher sem contexto vira tentativa.",
            on_screen_text="Escolha com contexto",
        ),
        PlanningStoryboardBeatV1(
            beat_id="demo",
            order=2,
            narrative_role="demo",
            duration_seconds=3,
            visual_direction="Detalhe do pacote e do preparo.",
            copy_text="A assinatura organiza uma seleção rotativa.",
            on_screen_text="Seleção rotativa",
        ),
        PlanningStoryboardBeatV1(
            beat_id="offer",
            order=3,
            narrative_role="offer",
            duration_seconds=3,
            visual_direction="Oferta aparece como texto sujeito a confirmação.",
            copy_text="Confirme as condições do primeiro envio.",
            on_screen_text="Condições sob revisão",
            requires_human_review=True,
        ),
        PlanningStoryboardBeatV1(
            beat_id="cta",
            order=4,
            narrative_role="cta",
            duration_seconds=3,
            visual_direction="Avatar aponta para o CTA.",
            copy_text="Conheça a assinatura.",
            on_screen_text="Conheça a assinatura",
        ),
    ]
    script = " ".join(beat.copy_text for beat in beats) + (f" {forbidden}." if forbidden else "")
    draft = PlanningCopyDraftV1(
        brief=CreativeBriefV1(
            objective=case.request.objective,
            audience=case.request.audience,
            angle="consistência de escolha",
            promise="uma escolha mais organizada",
            hook="Seu café muda toda semana?",
            cta="Conheça a assinatura",
            channel=case.request.channel,
            format=case.request.format,
            tone=case.request.tone,
            restrictions=case.request.restrictions,
        ),
        script=script,
        claims=[
            PlanningClaimV1(
                claim_id="offer-review",
                text="Condições do primeiro envio",
                evidence_ids=[],
                requires_human_review=True,
            )
        ],
        storyboard=beats,
        abstentions=["Preço e disponibilidade precisam de confirmação."],
    )
    return PlanningCopyResultV1(
        request_id=case.request.request_id,
        request_digest_sha256=planning_copy_request_digest(case.request),
        workspace_id=case.request.workspace_id,
        status="partial",
        draft=draft,
        lineage=IntelligenceLineageV1(
            provider="test",
            provider_version="1",
            model="fixture",
            model_revision="fixture-v1",
            parameters_digest_sha256=hashlib.sha256(b"parameters").hexdigest(),
            prompt_digest_sha256=hashlib.sha256(b"prompt").hexdigest(),
            generated_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )


def test_casebook_covers_exactly_ten_niches_and_all_six_catalog_slots() -> None:
    casebook = load_ugc_acceptance_casebook(CASEBOOK_PATH)
    assert len(casebook.cases) == 10
    assert len({case.niche for case in casebook.cases}) == 10
    assert {case.avatar.candidate_id for case in casebook.cases} == {
        "lia",
        "maya",
        "nina",
        "caio",
        "theo",
        "bento",
    }
    assert all(case.avatar.catalog_only for case in casebook.cases)
    assert all(not case.avatar.production_eligible for case in casebook.cases)
    assert all(case.avatar.identity_version_id is None for case in casebook.cases)
    assert not casebook.publication_enabled
    assert not casebook.real_biometric_data_allowed


def test_copy_rubric_passes_safe_structure_and_catches_forbidden_claim() -> None:
    case = load_ugc_acceptance_casebook(CASEBOOK_PATH).cases[0]
    safe = evaluate_planning_copy(case, _result(case))
    assert all(item.status == "pass" for item in safe if item.criterion_id != "editorial_review")
    assert next(item for item in safe if item.criterion_id == "editorial_review").status == "manual_review"
    assert weighted_score(safe) == 5

    unsafe = evaluate_planning_copy(case, _result(case, forbidden="o melhor do Brasil"))
    forbidden = next(item for item in unsafe if item.criterion_id == "forbidden_claims")
    assert forbidden.status == "fail"
    assert forbidden.score == 0
    assert weighted_score(unsafe) < 5


def test_canonical_compositor_renders_visual_and_five_page_carousel() -> None:
    case = load_ugc_acceptance_casebook(CASEBOOK_PATH).cases[0]
    result = _result(case)
    visual = build_ad_document(case, result, content_type="visual")
    carousel = build_ad_document(case, result, content_type="carousel")

    visual_images = _render_document(visual)
    carousel_images = _render_document(carousel)
    assert visual_images[0].size == (1080, 1350)
    assert len(carousel_images) == case.deliverables.carousel_pages == 5
    assert all(image.size == (1080, 1350) for image in carousel_images)
    assert carousel.composition.narrative["avatarInferenceExecuted"] is False


def test_ffmpeg_animatic_has_expected_geometry_and_duration(tmp_path: Path) -> None:
    frames = []
    for index, color in enumerate(("#101216", "#ff8f70"), start=1):
        path = tmp_path / f"frame-{index}.png"
        Image.new("RGB", (320, 480), color).save(path)
        frames.append(path)
    output = tmp_path / "animatic.mp4"
    encode_animatic(frames, output, duration_seconds=1, fps=25)
    probe = probe_video(output)
    assert probe["width"] == 320
    assert probe["height"] == 480
    assert 0.9 <= probe["duration"] <= 1.1


def test_real_kit_validation_rejects_false_dimensions_and_tampering(tmp_path: Path) -> None:
    case = load_ugc_acceptance_casebook(CASEBOOK_PATH).cases[0]
    artifacts = render_ad_kit(case, _result(case), tmp_path)
    assert verify_ad_kit(case, artifacts, allowed_root=tmp_path).status == "pass"
    carousel = next(item for item in artifacts if item.artifact_type == "carousel-zip")
    with zipfile.ZipFile(carousel.path) as archive:
        assert archive.namelist() == ["manifest.json", "01.png", "02.png", "03.png", "04.png", "05.png"]
    visual = next(item for item in artifacts if item.artifact_type == "visual-png")
    Image.new("RGB", (320, 320), "white").save(visual.path)
    # Even a matching checksum and claimed 1080x1350 dimensions cannot fool byte inspection.
    visual.checksum_sha256 = sha256_file(Path(visual.path))
    visual.size_bytes = Path(visual.path).stat().st_size
    assert "visual_geometry" in str(verify_ad_kit(case, artifacts, allowed_root=tmp_path).notes)
    Path(carousel.path).write_bytes(b"corrupt archive")
    assert "checksum_or_size" in str(verify_ad_kit(case, artifacts, allowed_root=tmp_path).notes)


def test_missing_checks_and_forbidden_claim_cannot_be_compensated_by_average() -> None:
    case = load_ugc_acceptance_casebook(CASEBOOK_PATH).cases[0]
    checks = evaluate_planning_copy(case, _result(case))
    assert automated_preflight_status(checks) == "fail"  # artifact verification missing
    from app.domain.studios.ugc_acceptance import UgcCriterionResultV1

    checks.append(UgcCriterionResultV1(criterion_id="artifact_integrity", status="pass", score=5))
    assert automated_preflight_status(checks) == "pass"
    next(item for item in checks if item.criterion_id == "forbidden_claims").status = "fail"
    assert weighted_score(checks) == 5  # deliberately inconsistent numeric score
    assert automated_preflight_status(checks) == "fail"


def test_compact_worker_has_single_spoken_source_and_rejects_free_offer() -> None:
    from app.providers.studios.openai_compatible_planning import _ugc_worker_to_draft, _UgcWorkerDraft

    case = load_ugc_acceptance_casebook(CASEBOOK_PATH).cases[0]
    draft = _result(case).draft
    worker = _UgcWorkerDraft(
        hook=draft.brief.hook,
        angle=draft.brief.angle,
        promise=draft.brief.promise,
        cta=draft.brief.cta,
        beats=[
            {
                "role": beat.narrative_role,
                "copyText": beat.copy_text,
                "onScreenText": beat.on_screen_text,
                "visualDirection": beat.visual_direction,
            }
            for beat in draft.storyboard
        ],
    )
    canonical = _ugc_worker_to_draft(case.request, worker)
    assert canonical.script == " ".join(beat.copy_text for beat in canonical.storyboard)
    assert canonical.brief.restrictions == case.request.restrictions
    assert canonical.abstentions
    worker.cta = "Peça seu café gratuito."
    with pytest.raises(ValueError, match="invented offer"):
        _ugc_worker_to_draft(case.request, worker)


def test_revision_feedback_preserves_locked_facts_and_changes_request_digest() -> None:
    case = load_ugc_acceptance_casebook(CASEBOOK_PATH).cases[0]
    previous = _result(case, forbidden="o melhor do Brasil")
    original = case.request.model_dump()
    revision = build_ugc_revision_request(case, previous)
    assert revision.revision_context is not None
    assert any("forbidden_claims" in note for note in revision.revision_context.feedback)
    assert revision.revision_context.previous_script == previous.draft.script
    for field in ("channel", "format", "restrictions", "evidence", "product", "offer"):
        assert getattr(revision, field) == getattr(case.request, field)
    assert planning_copy_request_digest(revision) != planning_copy_request_digest(case.request)
    assert case.request.model_dump() == original


def test_failed_retry_keeps_original_report_and_writes_derived_receipt(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace

    from app.domain.studios.ugc_acceptance import (
        UgcAdAcceptanceCaseResultV1,
        UgcAdAcceptanceRunV1,
        UgcCriterionResultV1,
    )
    from app.services.studios.ugc_acceptance import canonical_json_digest, standard_capability_gates
    from scripts import run_ugc_ad_acceptance as cli

    book = load_ugc_acceptance_casebook(CASEBOOK_PATH)
    now = datetime.now(UTC)
    previous_run = UgcAdAcceptanceRunV1(
        suite_id=book.suite_id,
        run_id="retry-source",
        casebook_digest_sha256=canonical_json_digest(book),
        started_at=now,
        completed_at=now,
        results=[
            UgcAdAcceptanceCaseResultV1(
                case_id=case.case_id,
                planning_result=_result(case),
                criteria=[UgcCriterionResultV1(criterion_id="pipeline_execution", status="fail", score=0)],
                capability_gates=standard_capability_gates(generated=True, rendered=False),
                weighted_score=0,
                automated_status="fail",
            )
            for case in book.cases
        ],
    )
    original = tmp_path / "source.json"
    # A historical pass is not reusable under a newer evaluator, especially without artifact bytes.
    previous_run.results[1].automated_status = "pass"
    previous_run.results[1].weighted_score = 5
    original.write_text(previous_run.model_dump_json(by_alias=True), encoding="utf-8")
    before = original.read_bytes()
    monkeypatch.setattr(
        cli,
        "_arguments",
        lambda: SimpleNamespace(
            casebook=CASEBOOK_PATH,
            case_ids=[book.cases[0].case_id],
            retry_report=original,
            api_key="synthetic-test-only",
            base_url="http://localhost:18080",
            model="fixture",
            model_revision="fixture",
            max_output_tokens=950,
            timeout_seconds=1,
            output_root=tmp_path / "derived",
            run_id=None,
        ),
    )

    class UnavailableProvider:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def plan(self, *args):
            raise RuntimeError("synthetic_provider_unavailable")

    monkeypatch.setattr(cli, "OpenAICompatiblePlanningCopyProvider", UnavailableProvider)
    assert cli.main() == 2
    assert original.read_bytes() == before
    reports = list((tmp_path / "derived").glob("*/run-report.json"))
    assert len(reports) == 1
    assert reports[0] != original
    derived = UgcAdAcceptanceRunV1.model_validate_json(reports[0].read_text(encoding="utf-8"))
    assert derived.results[1].automated_status == "fail"
    assert any(check.criterion_id == "artifact_integrity" for check in derived.results[1].criteria)
    assert list(reports[0].parent.glob("retries/retry-*.json"))
    requests = list(reports[0].parent.glob("*.request.json"))
    assert len(requests) == 1
    assert "revisionContext" in requests[0].read_text(encoding="utf-8")


def test_default_font_preserves_requested_size_when_platform_fonts_are_missing(monkeypatch) -> None:
    from app.services import creatives

    # Force just the external font candidates to fail, without replacing Pillow's built-in loader.
    truetype = creatives.ImageFont.truetype

    def missing_external_font(candidate, *args, **kwargs):
        if isinstance(candidate, str):
            raise OSError("font unavailable")
        return truetype(candidate, *args, **kwargs)

    monkeypatch.setattr(creatives.ImageFont, "truetype", missing_external_font)
    small = creatives._font(20).getbbox("Café")
    large = creatives._font(60).getbbox("Café")
    assert (large[3] - large[1]) > 2 * (small[3] - small[1])
