from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.advanced_capabilities import AdvancedCapabilityAuditV1

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_ROOT = Path(r"C:\Users\edugu\Downloads\clicko-oss-evaluation")
DEFAULT_OUTPUT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "advanced-capabilities-20260901-v1"
    / "audit.json"
)
AUDITED_AT = datetime(2026, 9, 1, 20, 0, tzinfo=UTC)

CANDIDATES = (
    ("openvoice-v2", "voice_clone", "OpenVoice", "LICENSE", "MIT", "review_required"),
    ("chatterbox-ptbr", "voice_clone", "Chatterbox", "LICENSE", "MIT", "review_required"),
    ("kokoro-openvoice", "voice_clone", "Kokoro", "LICENSE", "Apache-2.0", "review_required"),
    ("heygem-caladog", "avatar_video", "HeyGem-Caladog", "LICENSE", "Community", "review_required"),
    ("duix-avatar", "avatar_video", "Duix-Avatar", "LICENSE", "Community", "review_required"),
    ("liveportrait", "avatar_video", "LivePortrait", "LICENSE", "MIT", "review_required"),
    ("musetalk", "lip_sync", "MuseTalk", "LICENSE", "MIT", "review_required"),
    ("latentsync", "lip_sync", "LatentSync", "LICENSE", "Apache-2.0", "review_required"),
    ("echomimic-v3", "generative_scene", "echomimic_v3", "LICENSE.txt", "Apache-2.0", "review_required"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def revision(path: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build_audit(source_root: Path) -> AdvancedCapabilityAuditV1:
    candidates = []
    for candidate_id, capability, directory, license_name, code_license, license_status in CANDIDATES:
        path = (source_root / directory).resolve()
        license_path = path / license_name
        if not path.is_dir() or not license_path.is_file():
            raise ValueError(f"advanced_candidate_source_missing:{candidate_id}")
        candidates.append(
            {
                "candidateId": candidate_id,
                "capability": capability,
                "repositoryName": directory,
                "sourceRevision": revision(path),
                "localSourceAvailable": True,
                "licenseDocumentDigestSha256": digest(license_path),
                "codeLicense": code_license,
                "transitiveLicenseStatus": license_status,
                "modelAssetStatus": "incomplete",
                "ptBrStatus": "unmeasured",
                "hardwareStatus": "unmeasured",
                "supplyChainStatus": "incomplete",
                "providerRegistryStatus": "not_registered",
                "biometricInferenceExecuted": False,
                "notes": [
                    "Código local e licença raiz inventariados; isso não valida pesos ou dependências transitivas.",
                    "Nenhum dado biométrico foi usado nesta auditoria.",
                ],
            }
        )
    return AdvancedCapabilityAuditV1.model_validate(
        {
            "auditId": "clicko-advanced-video-capabilities-v1",
            "candidates": candidates,
            "identitySlots": [
                {
                    "slotId": f"authorized-identity-slot-{index:02d}",
                    "authorizationStatus": "not_acquired",
                    "benchmarkCaseIds": [],
                    "privateArtifactCount": 0,
                }
                for index in range(1, 7)
            ],
            "authorizedIdentityCount": 0,
            "executedBenchmarkCaseCount": 0,
            "revocationRailImplemented": True,
            "deletionRailImplemented": True,
            "revocationDeletionDrillPassed": False,
            "publishSyntheticGrantCount": 0,
            "enabledProviderIds": [],
            "fallbackModes": ["real_person", "licensed_stock", "faceless_motion"],
            "activationEligible": False,
            "blockers": [
                "six_authorized_identities_required",
                "twenty_four_private_benchmark_cases_required",
                "transitive_license_review_required",
                "pt_br_quality_unmeasured",
                "eligible_gpu_attestation_missing",
                "supply_chain_sbom_provenance_signature_incomplete",
                "revocation_deletion_drill_required",
                "publish_synthetic_grants_missing",
                "provider_registry_intentionally_empty",
            ],
            "auditedAt": AUDITED_AT.isoformat(),
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build_audit(args.source_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(audit.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "candidates": len(audit.candidates),
                "authorizedIdentities": audit.authorized_identity_count,
                "benchmarkCases": audit.executed_benchmark_case_count,
                "enabledProviders": audit.enabled_provider_ids,
                "activationEligible": audit.activation_eligible,
            }
        )
    )


if __name__ == "__main__":
    main()
