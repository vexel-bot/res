import hashlib
import json
from pathlib import Path

import pytest

from app.domain.studios.reality import (
    PhysicalPlausibilityEvaluationV1,
    PhysicalPlausibilityPolicyV1,
    PhysicalPlausibilityRequestV1,
    RealityAnalysisRequestV1,
    RealityContributionV1,
    RealityModelV1,
    ShotRealityConstraintSetV1,
    physical_plausibility_policy_digest,
    reality_model_digest,
    shot_reality_constraint_set_digest,
)
from app.services.studios.reality_analysis import (
    PhysicalQualityOrchestrator,
    RealityAnalysisOrchestrator,
)

ROOT = Path(__file__).resolve().parents[2]
REALITY_DIR = ROOT / "benchmarks" / "studios" / "reality"
FIXTURE_DIR = REALITY_DIR / "fixtures"


def fixture_json(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def runtime_policy() -> PhysicalPlausibilityPolicyV1:
    return PhysicalPlausibilityPolicyV1.model_validate_json(
        (REALITY_DIR / "physical-plausibility-policy.v1.json").read_text(encoding="utf-8")
    )


def source_bound_model(source_checksum: str) -> RealityModelV1:
    payload = fixture_json("reality-model-supported-cup.v1.json")
    payload["sourceAsset"]["checksum"] = source_checksum
    for lineage in payload["lineage"]:
        lineage["inputDigestSha256"] = source_checksum
    return RealityModelV1.model_validate(payload)


def request_for(model: RealityModelV1) -> RealityAnalysisRequestV1:
    return RealityAnalysisRequestV1(
        analysis_id=model.analysis_id,
        workspace_id=model.workspace_id,
        source_asset=model.source_asset,
        source_time_map_id=model.source_time_map_id,
        source_time_map_digest_sha256=model.source_time_map_digest_sha256,
        frame_rate=model.frame_rate,
        total_frames=model.total_frames,
        shots=model.shots,
        analysis_policy_digest_sha256=model.analysis_policy_digest_sha256,
    )


class FakeGeometry:
    name = "fixture.geometry"
    version = "1.0.0"

    def __init__(self, model: RealityModelV1) -> None:
        self.model = model

    def observe(self, source, request, progress, is_cancelled):
        progress(0)
        progress(100)
        return RealityContributionV1(
            analysis_id=request.analysis_id,
            source_asset_checksum_sha256=request.source_asset.checksum,
            lineage=next(item for item in self.model.lineage if item.contribution_id == "geometry-001"),
            evidence=[
                item for item in self.model.evidence if item.contribution_id == "geometry-001"
            ],
            camera_observations=self.model.camera_observations,
        )


class FakeTracking:
    name = "fixture.tracking"
    version = "1.0.0"

    def __init__(self, model: RealityModelV1, *, provider_name: str | None = None) -> None:
        self.model = model
        if provider_name:
            self.name = provider_name

    def observe(self, source, request, progress, is_cancelled):
        progress(0)
        progress(50)
        progress(100)
        return RealityContributionV1(
            analysis_id=request.analysis_id,
            source_asset_checksum_sha256=request.source_asset.checksum,
            lineage=next(item for item in self.model.lineage if item.contribution_id == "tracking-001"),
            evidence=[
                item for item in self.model.evidence if item.contribution_id == "tracking-001"
            ],
            entities=self.model.entities,
            tracks=self.model.tracks,
        )


class AlternativeFakeTracking(FakeTracking):
    name = "fixture.tracking-alternative"

    def observe(self, source, request, progress, is_cancelled):
        contribution = super().observe(source, request, progress, is_cancelled)
        return contribution.model_copy(
            update={
                "lineage": contribution.lineage.model_copy(update={"provider": self.name})
            }
        )


class FakeWorldModel:
    name = "fixture.world"
    version = "1.0.0"

    def __init__(self, model: RealityModelV1) -> None:
        scene = next(item for item in model.lineage if item.contribution_id == "scene-001")
        self.lineage = scene.model_copy(
            update={
                "contribution_id": "world-001",
                "contribution_kind": "world_model",
                "provider": self.name,
                "provider_version": self.version,
                "code_digest_sha256": "8" * 64,
                "parameters_digest_sha256": "9" * 64,
            }
        )

    def predict(self, source, request, reality_model, progress, is_cancelled):
        progress(0)
        progress(100)
        return RealityContributionV1(
            analysis_id=request.analysis_id,
            source_asset_checksum_sha256=request.source_asset.checksum,
            lineage=self.lineage,
            limitations=["Contract fake: no latent model was executed."],
        )


class FakeScene:
    name = "fixture.scene"
    version = "1.0.0"

    def __init__(self, model: RealityModelV1, *, drop_evidence: bool = False) -> None:
        self.model = model
        self.drop_evidence = drop_evidence
        self.calls = 0

    def synthesize(self, request, contributions, progress, is_cancelled):
        self.calls += 1
        progress(0)
        progress(100)
        contribution_lineage = [item.lineage for item in contributions]
        scene_lineage = next(
            item for item in self.model.lineage if item.contribution_id == "scene-001"
        )
        evidence = self.model.evidence
        if self.drop_evidence:
            evidence = [item for item in evidence if item.evidence_id != "evidence-camera-001"]
        return self.model.model_copy(
            update={"lineage": contribution_lineage + [scene_lineage], "evidence": evidence}
        )


def test_reality_orchestrator_composes_replaceable_providers_and_world_model(tmp_path):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"synthetic-contract-fixture")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    model = source_bound_model(checksum)
    scene = FakeScene(model)
    progress: list[int] = []
    orchestrator = RealityAnalysisOrchestrator(
        geometry=FakeGeometry(model),
        tracking=FakeTracking(model),
        scene=scene,
        world_model=FakeWorldModel(model),
    )

    result = orchestrator.analyze(source, request_for(model), progress.append, lambda: False)

    assert result.source_asset.checksum == checksum
    assert scene.calls == 2
    assert {item.contribution_id for item in result.lineage} >= {
        "geometry-001",
        "tracking-001",
        "world-001",
    }
    assert progress == sorted(progress)
    assert progress[0] == 0 and progress[-1] == 100

    replacement = RealityAnalysisOrchestrator(
        geometry=FakeGeometry(model),
        tracking=AlternativeFakeTracking(model),
        scene=FakeScene(model),
    ).analyze(source, request_for(model), lambda _: None, lambda: False)
    assert replacement.entities == result.entities
    assert replacement.tracks == result.tracks
    assert next(
        item for item in replacement.lineage if item.contribution_id == "tracking-001"
    ).provider == "fixture.tracking-alternative"


def test_reality_orchestrator_rejects_checksum_provider_and_evidence_tampering(tmp_path):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"synthetic-contract-fixture")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    model = source_bound_model(checksum)
    request = request_for(model)

    bad_request = request.model_copy(
        update={
            "source_asset": request.source_asset.model_copy(update={"checksum": "0" * 64})
        }
    )
    with pytest.raises(ValueError, match="reality_source_checksum_mismatch"):
        RealityAnalysisOrchestrator(
            geometry=FakeGeometry(model), tracking=FakeTracking(model), scene=FakeScene(model)
        ).analyze(source, bad_request, lambda _: None, lambda: False)

    with pytest.raises(ValueError, match="reality_contribution_provider_mismatch"):
        RealityAnalysisOrchestrator(
            geometry=FakeGeometry(model),
            tracking=FakeTracking(model, provider_name="tampered.provider"),
            scene=FakeScene(model),
        ).analyze(source, request, lambda _: None, lambda: False)

    with pytest.raises(ValueError, match="reality_model_evidence_dropped|camera evidence"):
        RealityAnalysisOrchestrator(
            geometry=FakeGeometry(model),
            tracking=FakeTracking(model),
            scene=FakeScene(model, drop_evidence=True),
        ).analyze(source, request, lambda _: None, lambda: False)


def test_reality_orchestrator_cancels_between_provider_stages(tmp_path):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"synthetic-contract-fixture")
    model = source_bound_model(hashlib.sha256(source.read_bytes()).hexdigest())
    observed = {"progress": 0}

    def progress(value: int) -> None:
        observed["progress"] = value

    with pytest.raises(InterruptedError, match="reality_analysis_cancelled"):
        RealityAnalysisOrchestrator(
            geometry=FakeGeometry(model), tracking=FakeTracking(model), scene=FakeScene(model)
        ).analyze(source, request_for(model), progress, lambda: observed["progress"] >= 25)
    assert observed["progress"] == 25


class FakePhysicalQuality:
    name = "fixture.physical-qc"
    version = "1.0.0"

    def __init__(self, evaluation: PhysicalPlausibilityEvaluationV1, *, wrong_asset: bool = False):
        self.evaluation = evaluation
        self.wrong_asset = wrong_asset

    def evaluate(self, request, reality_model, constraints, policy, progress, is_cancelled):
        progress(0)
        progress(100)
        if self.wrong_asset:
            return self.evaluation.model_copy(update={"rendered_asset_id": "wrong-asset"})
        return self.evaluation


def physical_fixture_bundle():
    model = RealityModelV1.model_validate(fixture_json("reality-model-supported-cup.v1.json"))
    constraints = ShotRealityConstraintSetV1.model_validate(
        fixture_json("shot-reality-constraints-supported-cup.v1.json")
    )
    evaluation = PhysicalPlausibilityEvaluationV1.model_validate(
        fixture_json("physical-evaluation-clear.v1.json")
    )
    policy = runtime_policy()
    request = PhysicalPlausibilityRequestV1(
        evaluation_id=evaluation.evaluation_id,
        workspace_id=evaluation.workspace_id,
        document_id=evaluation.document_id,
        document_revision=evaluation.document_revision,
        document_snapshot_digest_sha256=evaluation.document_snapshot_digest_sha256,
        render_job_id=evaluation.render_job_id,
        rendered_asset_id=evaluation.rendered_asset_id,
        rendered_asset_checksum_sha256=evaluation.rendered_asset_checksum_sha256,
        reality_model_id=model.reality_model_id,
        reality_model_digest_sha256=reality_model_digest(model),
        constraint_set_id=constraints.constraint_set_id,
        constraint_set_digest_sha256=shot_reality_constraint_set_digest(constraints),
        policy_digest_sha256=physical_plausibility_policy_digest(policy),
    )
    return request, model, constraints, policy, evaluation


def test_physical_quality_orchestrator_binds_exact_request_and_provider_lineage():
    request, model, constraints, policy, evaluation = physical_fixture_bundle()
    progress: list[int] = []

    result = PhysicalQualityOrchestrator(FakePhysicalQuality(evaluation)).evaluate(
        request, model, constraints, policy, progress.append, lambda: False
    )

    assert result is evaluation
    assert progress == sorted(progress)
    assert progress[0] == 0 and progress[-1] == 100


def test_physical_quality_orchestrator_rejects_request_and_result_swaps():
    request, model, constraints, policy, evaluation = physical_fixture_bundle()
    wrong_request = request.model_copy(update={"rendered_asset_checksum_sha256": "0" * 64})
    with pytest.raises(ValueError, match="rendered_asset_checksum_sha256 does not match"):
        PhysicalQualityOrchestrator(FakePhysicalQuality(evaluation)).evaluate(
            wrong_request, model, constraints, policy, lambda _: None, lambda: False
        )

    with pytest.raises(ValueError, match="rendered_asset_id does not match"):
        PhysicalQualityOrchestrator(FakePhysicalQuality(evaluation, wrong_asset=True)).evaluate(
            request, model, constraints, policy, lambda _: None, lambda: False
        )
