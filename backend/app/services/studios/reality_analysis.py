from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from ...domain.studios.providers import (
    ObjectTrackingProvider,
    PhysicalPlausibilityProvider,
    PhysicalSceneUnderstandingProvider,
    ProgressCallback,
    VideoWorldModelProvider,
    VisualGeometryProvider,
)
from ...domain.studios.reality import (
    PhysicalPlausibilityEvaluationV1,
    PhysicalPlausibilityPolicyV1,
    PhysicalPlausibilityRequestV1,
    RealityAnalysisRequestV1,
    RealityContributionV1,
    RealityFrameRangeV1,
    RealityModelV1,
    ShotRealityConstraintSetV1,
    validate_physical_evaluation_bindings,
    validate_physical_evaluation_request,
    validate_physical_request_bindings,
    validate_reality_model_bindings,
)

CancellationCheck = Callable[[], bool]


class _StageProgress:
    def __init__(self, outer: ProgressCallback, start: int, end: int) -> None:
        self.outer = outer
        self.start = start
        self.end = end
        self.last = -1

    def __call__(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise ValueError("reality_provider_progress_out_of_range")
        if value < self.last:
            raise ValueError("reality_provider_progress_regressed")
        self.last = value
        self.outer(self.start + round((self.end - self.start) * value / 100))


class RealityAnalysisOrchestrator:
    """Runs replaceable observers and returns one validated canonical RealityModelV1."""

    def __init__(
        self,
        *,
        geometry: VisualGeometryProvider,
        tracking: ObjectTrackingProvider,
        scene: PhysicalSceneUnderstandingProvider,
        world_model: VideoWorldModelProvider | None = None,
    ) -> None:
        self.geometry = geometry
        self.tracking = tracking
        self.scene = scene
        self.world_model = world_model

    def analyze(
        self,
        source: Path,
        request: RealityAnalysisRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityModelV1:
        self._check_cancelled(is_cancelled)
        self._verify_source(source, request)
        progress(0)

        geometry = RealityContributionV1.model_validate(
            self.geometry.observe(
                source,
                request,
                _StageProgress(progress, 0, 25),
                is_cancelled,
            )
        )
        self._validate_contribution(geometry, request, "geometry", self.geometry)
        self._check_cancelled(is_cancelled)

        tracking = RealityContributionV1.model_validate(
            self.tracking.observe(
                source,
                request,
                _StageProgress(progress, 25, 50),
                is_cancelled,
            )
        )
        self._validate_contribution(tracking, request, "tracking", self.tracking)
        contributions = [geometry, tracking]
        self._validate_contribution_set(contributions)
        self._check_cancelled(is_cancelled)

        if self.world_model is not None:
            preliminary = RealityModelV1.model_validate(
                self.scene.synthesize(
                    request,
                    contributions,
                    _StageProgress(progress, 50, 65),
                    is_cancelled,
                )
            )
            self._validate_model(preliminary, request, contributions)
            self._check_cancelled(is_cancelled)
            predictive = RealityContributionV1.model_validate(
                self.world_model.predict(
                    source,
                    request,
                    preliminary,
                    _StageProgress(progress, 65, 80),
                    is_cancelled,
                )
            )
            self._validate_contribution(predictive, request, "world_model", self.world_model)
            contributions.append(predictive)
            self._validate_contribution_set(contributions)
            scene_progress = _StageProgress(progress, 80, 98)
        else:
            scene_progress = _StageProgress(progress, 50, 98)

        result = RealityModelV1.model_validate(
            self.scene.synthesize(
                request,
                contributions,
                scene_progress,
                is_cancelled,
            )
        )
        self._check_cancelled(is_cancelled)
        self._validate_model(result, request, contributions)
        progress(100)
        return result

    @staticmethod
    def _verify_source(source: Path, request: RealityAnalysisRequestV1) -> None:
        if not source.is_file():
            raise ValueError("reality_source_unavailable")
        digest = hashlib.sha256()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != request.source_asset.checksum.lower():
            raise ValueError("reality_source_checksum_mismatch")

    @staticmethod
    def _check_cancelled(is_cancelled: CancellationCheck) -> None:
        if is_cancelled():
            raise InterruptedError("reality_analysis_cancelled")

    @staticmethod
    def _validate_contribution(
        contribution: RealityContributionV1,
        request: RealityAnalysisRequestV1,
        expected_kind: str,
        provider: object,
    ) -> None:
        if contribution.analysis_id != request.analysis_id:
            raise ValueError("reality_contribution_analysis_mismatch")
        if contribution.source_asset_checksum_sha256.lower() != request.source_asset.checksum.lower():
            raise ValueError("reality_contribution_asset_mismatch")
        if contribution.lineage.contribution_kind != expected_kind:
            raise ValueError("reality_contribution_kind_mismatch")
        if (
            contribution.lineage.provider != getattr(provider, "name", None)
            or contribution.lineage.provider_version != getattr(provider, "version", None)
        ):
            raise ValueError("reality_contribution_provider_mismatch")
        shot_ids = {shot.shot_id for shot in request.shots}
        for camera in contribution.camera_observations:
            if camera.shot_id not in shot_ids:
                raise ValueError("reality_contribution_shot_mismatch")
        ranges: list[RealityFrameRangeV1] = [item.frame_range for item in contribution.evidence]
        ranges.extend(item.frame_range for item in contribution.camera_observations)
        ranges.extend(item.frame_range for item in contribution.tracks)
        ranges.extend(item.frame_range for item in contribution.relations)
        ranges.extend(item.frame_range for item in contribution.events)
        ranges.extend(item.frame_range for item in contribution.hypotheses)
        if any(item.end_frame_exclusive > request.total_frames for item in ranges):
            raise ValueError("reality_contribution_range_exceeds_source")

    @staticmethod
    def _validate_contribution_set(contributions: list[RealityContributionV1]) -> None:
        contribution_ids = [item.lineage.contribution_id for item in contributions]
        evidence_ids = [evidence.evidence_id for item in contributions for evidence in item.evidence]
        if len(contribution_ids) != len(set(contribution_ids)):
            raise ValueError("reality_contribution_id_collision")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("reality_evidence_id_collision")

    @staticmethod
    def _validate_model(
        model: RealityModelV1,
        request: RealityAnalysisRequestV1,
        contributions: list[RealityContributionV1],
    ) -> None:
        validate_reality_model_bindings(model, request)
        lineage = {item.contribution_id: item for item in model.lineage}
        evidence_ids = {item.evidence_id for item in model.evidence}
        for contribution in contributions:
            expected_lineage = contribution.lineage
            if lineage.get(expected_lineage.contribution_id) != expected_lineage:
                raise ValueError("reality_model_lineage_dropped_or_changed")
            missing_evidence = {item.evidence_id for item in contribution.evidence} - evidence_ids
            if missing_evidence:
                raise ValueError("reality_model_evidence_dropped")


class PhysicalQualityOrchestrator:
    """Runs an advisory evaluator and proves it evaluated the exact immutable inputs."""

    def __init__(self, provider: PhysicalPlausibilityProvider) -> None:
        self.provider = provider

    def evaluate(
        self,
        request: PhysicalPlausibilityRequestV1,
        model: RealityModelV1,
        constraints: ShotRealityConstraintSetV1,
        policy: PhysicalPlausibilityPolicyV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> PhysicalPlausibilityEvaluationV1:
        if is_cancelled():
            raise InterruptedError("video_physical_qc_cancelled")
        validate_physical_request_bindings(request, model, constraints, policy)
        progress(0)
        evaluation = PhysicalPlausibilityEvaluationV1.model_validate(
            self.provider.evaluate(
                request,
                model,
                constraints,
                policy,
                _StageProgress(progress, 0, 98),
                is_cancelled,
            )
        )
        if is_cancelled():
            raise InterruptedError("video_physical_qc_cancelled")
        if evaluation.policy != policy:
            raise ValueError("physical_qc_policy_changed_by_provider")
        if not any(
            item.provider == self.provider.name and item.provider_version == self.provider.version
            for item in evaluation.evaluator_lineage
        ):
            raise ValueError("physical_qc_provider_lineage_missing")
        validate_physical_evaluation_request(evaluation, request)
        validate_physical_evaluation_bindings(evaluation, model, constraints)
        progress(100)
        return evaluation
