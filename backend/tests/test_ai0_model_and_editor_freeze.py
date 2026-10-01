from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.studios.artifacts import ArtifactInventoryV1, artifact_inventory_digest
from app.domain.studios.benchmarking import BenchmarkPolicyV1, benchmark_policy_digest
from app.domain.studios.contracts import StudioWorkerRuntimeManifestV1
from app.domain.studios.experiments import (
    AvatarAdExperimentProtocolV1,
    avatar_ad_experiment_protocol_digest,
)

ROOT = Path(__file__).resolve().parents[2]

AVATAR_POLICY = ROOT / "benchmarks/studios/identity/avatar-ad-pt-br-policy.v1.json"
EDITING_POLICY = ROOT / "benchmarks/studios/editing/video-edit-planner-pt-br-policy.v1.json"
PLANNING_POLICY = ROOT / "benchmarks/studios/intelligence/planning-copy-pt-br-policy.v1.json"
PROTOCOL = ROOT / "benchmarks/studios/identity/avatar-ad-experiment-protocol.v1.json"

AVATAR_POLICY_DIGEST = "c7cfb5898ef0c8a1621787923fe8ed2ef027174bc2577c7007cb3d140cf9bd8e"
EDITING_POLICY_DIGEST = "1e07d491e5ad6850e6bb9fcd76ea861e1bdf3f40c53bcb6b5f4440109c20a8ed"
PLANNING_POLICY_DIGEST = "88a37ca064d36a8b0f3c58fe4751f0a721b008359a80fe62212c452b4b17bc54"
PROTOCOL_DIGEST = "6bab1ba9ffd1c9275fc28ac2dd9b246db48e51cbaddc2290bfe156ff27d2674f"

INVENTORIES = {
    "workers/speech-gpu/chatterbox.artifacts.json": (
        "review_required",
        "45242126fc08a9e2a57ab95e268d3155ed9c44ee9312a1f9e1998ed3869e0819",
    ),
    "workers/speech-gpu/openvoice-v2.artifacts.json": (
        "incomplete",
        "6e744823eef5c761cc5b27fea42b398bde309c5cf36d2bd77a7ae06dde5496e1",
    ),
    "workers/vision-gpu/providers/ditto-upstream.artifacts.json": (
        "rejected",
        "fcc0ebfda3812f2e1b99a5aaa0179c1afd75c60ade62eda1a43fe7f61eec9f64",
    ),
    "workers/vision-gpu/providers/echomimic-v3-flash.artifacts.json": (
        "incomplete",
        "33696f22b163998e1da9ad3035ed1fa6f5563f2d9a83f0abb5716cd9b83049a1",
    ),
    "workers/vision-gpu/providers/wan2-2-animate.artifacts.json": (
        "incomplete",
        "2ba98e4996d9d7e68d6d6d86ea0b30fba63b4a64f564cf995219bec1c6a31470",
    ),
    "workers/vision-gpu/providers/qwen3-vl-edit-planner.artifacts.json": (
        "incomplete",
        "12d48fcf7573e9b1b10f967c0c39ed45af5e17d920bd5e047d3fd2261be8f192",
    ),
    "workers/llm-gpu/providers/qwen3-planning-copy.artifacts.json": (
        "incomplete",
        "b81d63250d935ca5f6875a57fee0e44051ba706dbf96e8e081bb9c815acd6f67",
    ),
    "workers/llm-gpu/providers/kimi-k2-5-planning-copy.artifacts.json": (
        "incomplete",
        "2f747a155fa2b5182a82cf5804090feeed5968390bf41bc7174311b76d0a251d",
    ),
    "workers/media-cpu/providers/motion-canvas.artifacts.json": (
        "incomplete",
        "690514270cb301739318feda830aba85de01b19f8c64394de9558b227c39f9a2",
    ),
    "workers/media-cpu/providers/opentimelineio.artifacts.json": (
        "incomplete",
        "bb5f3a7bb619d84b6f0bf3ad162f7c9ab1cc9be38ff08a0841e7e0a5c1014816",
    ),
    "workers/media-cpu/providers/pyscenedetect.artifacts.json": (
        "incomplete",
        "a8c0266611d7a1545a6b87e341c43034d11d453e682ab74c27d336e2b6dd5afc",
    ),
}


def _policy(path: Path) -> BenchmarkPolicyV1:
    return BenchmarkPolicyV1.model_validate_json(path.read_text(encoding="utf-8"))


def _protocol_payload() -> dict[str, object]:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_ai0_policies_and_staged_protocol_are_frozen() -> None:
    avatar_policy = _policy(AVATAR_POLICY)
    editing_policy = _policy(EDITING_POLICY)
    planning_policy = _policy(PLANNING_POLICY)
    protocol = AvatarAdExperimentProtocolV1.model_validate(_protocol_payload())

    assert (
        avatar_policy.status
        == editing_policy.status
        == planning_policy.status
        == protocol.status
        == "frozen"
    )
    assert benchmark_policy_digest(avatar_policy) == AVATAR_POLICY_DIGEST
    assert benchmark_policy_digest(editing_policy) == EDITING_POLICY_DIGEST
    assert benchmark_policy_digest(planning_policy) == PLANNING_POLICY_DIGEST
    assert [candidate.candidate_id for candidate in planning_policy.candidates] == [
        "qwen3-4b-instruct-2507",
        "qwen3-30b-a3b-instruct-2507",
        "qwen3-30b-a3b-thinking-2507",
        "kimi-k2-5",
    ]
    assert protocol.benchmark_policy_digest_sha256 == AVATAR_POLICY_DIGEST
    assert avatar_ad_experiment_protocol_digest(protocol) == PROTOCOL_DIGEST
    assert (protocol.catalog.total_profiles, protocol.catalog.men, protocol.catalog.women) == (
        6,
        3,
        3,
    )
    assert [item.expected_output_count for item in protocol.rounds] == [6, 24, 96]
    assert [item.max_experiment_spend_usd for item in protocol.rounds] == [25, 100, 400]
    assert protocol.catalog.publication_allowed_during_benchmark is False


def test_round_matrix_cannot_claim_the_wrong_output_count() -> None:
    payload = deepcopy(_protocol_payload())
    payload["rounds"][2]["expectedOutputCount"] = 95

    with pytest.raises(ValidationError, match="matrix size"):
        AvatarAdExperimentProtocolV1.model_validate(payload)


def test_round_cannot_skip_a_prior_gate() -> None:
    payload = deepcopy(_protocol_payload())
    payload["rounds"][2]["prerequisiteRoundIds"] = ["missing-round"]

    with pytest.raises(ValidationError, match="earlier rounds"):
        AvatarAdExperimentProtocolV1.model_validate(payload)


@pytest.mark.parametrize("relative_path,expected", INVENTORIES.items())
def test_ai0_inventory_is_recomputable_and_fail_closed(
    relative_path: str,
    expected: tuple[str, str],
) -> None:
    status, digest = expected
    inventory = ArtifactInventoryV1.model_validate_json(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )

    assert inventory.status == status
    assert artifact_inventory_digest(inventory) == digest
    assert inventory.status != "approved"
    assert any(
        record.resolution_status != "resolved" or record.license.decision != "approved"
        for record in inventory.artifacts
        if record.required
    )
    serialized = (ROOT / relative_path).read_text(encoding="utf-8").lower()
    assert "c:/users/" not in serialized
    assert "api_key" not in serialized
    assert "private_key" not in serialized


def test_ditto_rejection_is_bound_to_the_upstream_checkpoint_chain() -> None:
    inventory = ArtifactInventoryV1.model_validate_json(
        (ROOT / "workers/vision-gpu/providers/ditto-upstream.artifacts.json").read_text(
            encoding="utf-8"
        )
    )
    rejected = [item for item in inventory.artifacts if item.resolution_status == "rejected"]

    assert [item.artifact_id for item in rejected] == ["ditto-upstream-checkpoints"]
    assert rejected[0].license.commercial_saas_use_allowed is False
    assert "InsightFace" in rejected[0].license.declared_license


def test_ai0_does_not_advertise_new_models_or_editing_tools() -> None:
    speech = StudioWorkerRuntimeManifestV1.model_validate_json(
        (ROOT / "workers/speech-gpu/worker.manifest.json").read_text(encoding="utf-8")
    )
    vision = StudioWorkerRuntimeManifestV1.model_validate_json(
        (ROOT / "workers/vision-gpu/worker.manifest.json").read_text(encoding="utf-8")
    )
    llm = StudioWorkerRuntimeManifestV1.model_validate_json(
        (ROOT / "workers/llm-gpu/worker.manifest.json").read_text(encoding="utf-8")
    )
    media = StudioWorkerRuntimeManifestV1.model_validate_json(
        (ROOT / "workers/media-cpu/worker.manifest.json").read_text(encoding="utf-8")
    )

    assert speech.providers == []
    assert vision.providers == []
    assert llm.providers == []
    forbidden = {
        "qwen3-vl",
        "qwen3",
        "kimi",
        "ditto",
        "echomimic",
        "wan2.2",
        "motion-canvas",
        "otio",
        "pyscenedetect",
    }
    advertised = [*media.providers, *speech.providers, *vision.providers, *llm.providers]
    assert not forbidden.intersection(provider.lower() for provider in advertised)
