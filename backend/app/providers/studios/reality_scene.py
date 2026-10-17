from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from ...domain.studios.providers import CancellationCheck, ProgressCallback
from ...domain.studios.reality import (
    RealityAnalysisRequestV1,
    RealityContributionV1,
    RealityModelV1,
    RealityPrinciple,
    RealityProviderLineageV1,
)


class CanonicalContributionSceneProvider:
    """Deterministically assembles observations while abstaining from unsupported physics."""

    name = "builtin.canonical-reality-scene"
    version = "1.0.0"

    def synthesize(
        self,
        request: RealityAnalysisRequestV1,
        contributions: list[RealityContributionV1],
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityModelV1:
        progress(0)
        if is_cancelled():
            raise InterruptedError("reality_scene_synthesis_cancelled")
        contribution_ids = [item.lineage.contribution_id for item in contributions]
        if len(contribution_ids) != len(set(contribution_ids)):
            raise ValueError("reality_scene_contribution_collision")
        scene_id = f"canonical-scene-{hashlib.sha256(request.analysis_id.encode()).hexdigest()[:20]}"
        parameters = {
            "contributionDigests": [
                _contract_digest(item) for item in contributions
            ],
            "mode": "merge-and-abstain",
        }
        lineage = [item.lineage for item in contributions]
        lineage.append(
            RealityProviderLineageV1(
                contribution_id=scene_id,
                contribution_kind="scene",
                provider=self.name,
                provider_version=self.version,
                code_digest_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                input_digest_sha256=request.source_asset.checksum,
                parameters_digest_sha256=_canonical_digest(parameters),
                generated_at=datetime.now(UTC),
            )
        )
        camera = [item for contribution in contributions for item in contribution.camera_observations]
        tracks = [item for contribution in contributions for item in contribution.tracks]
        has_camera = any(item.confidence > 0 and item.motion != "unknown" for item in camera)
        has_motion = bool(tracks)
        abstained = _abstained_principles(
            has_camera=has_camera,
            has_motion=has_motion,
        )
        limitations = [
            limitation
            for contribution in contributions
            for limitation in contribution.limitations
        ]
        limitations.append(
            "Canonical assembly preserves evidence but does not add semantic or physical conclusions."
        )
        progress(80)
        if is_cancelled():
            raise InterruptedError("reality_scene_synthesis_cancelled")
        model = RealityModelV1(
            reality_model_id=(
                "reality-"
                + hashlib.sha256(
                    (request.analysis_id + request.source_asset.checksum).encode()
                ).hexdigest()[:24]
            ),
            analysis_id=request.analysis_id,
            workspace_id=request.workspace_id,
            source_asset=request.source_asset,
            source_time_map_id=request.source_time_map_id,
            source_time_map_digest_sha256=request.source_time_map_digest_sha256,
            analysis_policy_digest_sha256=request.analysis_policy_digest_sha256,
            frame_rate=request.frame_rate,
            total_frames=request.total_frames,
            shots=request.shots,
            status="partial" if has_camera or has_motion else "incomplete",
            camera_observations=camera,
            entities=[item for contribution in contributions for item in contribution.entities],
            tracks=tracks,
            relations=[item for contribution in contributions for item in contribution.relations],
            events=[item for contribution in contributions for item in contribution.events],
            hypotheses=[item for contribution in contributions for item in contribution.hypotheses],
            evidence=[item for contribution in contributions for item in contribution.evidence],
            lineage=lineage,
            abstained_principles=abstained,
            limitations=list(dict.fromkeys(limitations)),
            generated_at=datetime.now(UTC),
        )
        progress(100)
        return model


def _abstained_principles(*, has_camera: bool, has_motion: bool) -> list[RealityPrinciple]:
    supported = set()
    if has_camera:
        supported.add("camera_perspective")
    if has_motion:
        supported.add("motion")
    principles: list[RealityPrinciple] = [
        "permanence",
        "immutability",
        "continuity",
        "solidity",
        "support_gravity",
        "contact_collision",
        "motion",
        "approximate_conservation",
        "material_behavior",
        "causality",
        "biomechanics",
        "camera_perspective",
        "light_shadow_reflection",
        "event_sound",
        "editorial_continuity",
    ]
    return [item for item in principles if item not in supported]


def _contract_digest(contract: RealityContributionV1) -> str:
    return _canonical_digest(
        contract.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


def _canonical_digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
