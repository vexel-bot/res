from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...domain.studios.benchmarking import (
    BenchmarkEvidenceBundleV1,
    SpeechBenchmarkCleanupBundleV1,
    SpeechBenchmarkCleanupCaseV1,
)
from ..object_storage import sha256_file


def _asset_id(run_id: str, case_id: str, role: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{case_id}:{role}".encode()).hexdigest()
    return f"asset-{digest[:40]}"


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"benchmark_evidence_exists:{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".clicko-write-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _persist_or_validate_json(path: Path, payload: dict[str, Any]) -> None:
    """Persist a snapshot file once or verify an identical prior write.

    Snapshot stages are resumable because a process can stop after any one of
    their three files is made durable.  Existing content is never overwritten:
    an exact JSON match is accepted and every mismatch remains fail closed.
    """

    if not path.exists():
        _atomic_json(path, payload)
        return
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"benchmark_snapshot_existing_path_invalid:{path.name}")
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"benchmark_snapshot_existing_json_unreadable:{path.name}") from error
    if existing != payload:
        raise ValueError(f"benchmark_snapshot_existing_json_mismatch:{path.name}")


class PrivateSpeechBenchmarkEvidenceSink:
    """Fresh, private filesystem sink used only in an isolated benchmark worker."""

    def __init__(self, root: Path, *, run_id: str, forbidden_root: Path) -> None:
        resolved_root = self._resolve_safe_root(root, forbidden_root)
        resolved_root.mkdir(parents=True, exist_ok=False)
        os.chmod(resolved_root, 0o700)
        self.root = resolved_root
        self.run_id = run_id
        self._assets: dict[str, tuple[str, str, list[Path]]] = {}
        self._deleted_assets: set[str] = set()
        _atomic_json(
            self.root / "control" / "run-anchor.json",
            {
                "schemaVersion": "studio.speech-benchmark-private-run-anchor.v1",
                "runId": run_id,
            },
        )

    @staticmethod
    def _resolve_safe_root(root: Path, forbidden_root: Path) -> Path:
        resolved_forbidden = forbidden_root.resolve()
        resolved_root = root.resolve()
        if resolved_root == resolved_forbidden or resolved_root.is_relative_to(resolved_forbidden):
            raise ValueError("benchmark_private_root_must_stay_outside_repository")
        return resolved_root

    @classmethod
    def open_existing(
        cls,
        root: Path,
        *,
        run_id: str,
        forbidden_root: Path,
    ) -> PrivateSpeechBenchmarkEvidenceSink:
        resolved_root = cls._resolve_safe_root(root, forbidden_root)
        if not resolved_root.is_dir() or root.is_symlink():
            raise ValueError("benchmark_private_root_missing_or_symlinked")
        anchor_path = resolved_root / "control" / "run-anchor.json"
        try:
            anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("benchmark_private_run_anchor_unreadable") from error
        if anchor != {
            "schemaVersion": "studio.speech-benchmark-private-run-anchor.v1",
            "runId": run_id,
        }:
            raise ValueError("benchmark_private_run_anchor_mismatch")
        instance = cls.__new__(cls)
        instance.root = resolved_root
        instance.run_id = run_id
        instance._assets = {}
        instance._deleted_assets = set()
        instance._load_existing_assets()
        return instance

    def _load_existing_assets(self) -> None:
        for sidecar in sorted((self.root / "metadata").glob("*.json")):
            try:
                payload = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError("benchmark_private_audio_metadata_unreadable") from error
            case_id = payload.get("caseId")
            asset_id = payload.get("assetId")
            checksum = str(payload.get("checksumSha256", "")).lower()
            if (
                payload.get("schemaVersion") != "studio.speech-benchmark-private-audio.v1"
                or not isinstance(case_id, str)
                or asset_id != _asset_id(self.run_id, case_id, "audio")
                or len(checksum) != 64
                or any(character not in "0123456789abcdef" for character in checksum)
            ):
                raise ValueError("benchmark_private_audio_metadata_invalid")
            audio = self.root / "audio" / f"{hashlib.sha256(case_id.encode()).hexdigest()}.wav"
            if audio.is_file() and sha256_file(audio) != checksum:
                raise ValueError("benchmark_private_reopen_checksum_mismatch")
            if asset_id in self._assets:
                raise ValueError("benchmark_private_asset_duplicate")
            self._assets[asset_id] = (case_id, checksum, [audio, sidecar])
        for provenance in sorted((self.root / "provenance").glob("*.json")):
            try:
                payload = json.loads(provenance.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError("benchmark_private_provenance_unreadable") from error
            case_id = payload.get("caseId")
            asset_id = payload.get("assetId")
            if (
                not isinstance(case_id, str)
                or asset_id != _asset_id(self.run_id, case_id, "provenance")
                or asset_id in self._assets
            ):
                raise ValueError("benchmark_private_provenance_invalid")
            self._assets[asset_id] = (case_id, "", [provenance])

    def persist_output(self, case_id: str, source: Path, metadata: dict[str, Any]) -> str:
        if source.suffix.lower() != ".wav" or not source.is_file():
            raise ValueError("benchmark_private_output_must_be_wav")
        expected_checksum = str(metadata.get("checksumSha256", "")).lower()
        if sha256_file(source) != expected_checksum:
            raise ValueError("benchmark_private_output_checksum_mismatch")
        asset_id = _asset_id(self.run_id, case_id, "audio")
        token = hashlib.sha256(case_id.encode()).hexdigest()
        destination = self.root / "audio" / f"{token}.wav"
        sidecar = self.root / "metadata" / f"{token}.json"
        if destination.exists() or sidecar.exists() or asset_id in self._assets:
            raise FileExistsError("benchmark_private_output_already_exists")
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(prefix=".clicko-audio-", dir=destination.parent)
        os.close(handle)
        temporary = Path(temporary_name)
        try:
            shutil.copyfile(source, temporary)
            if sha256_file(temporary) != expected_checksum:
                raise ValueError("benchmark_private_copy_checksum_mismatch")
            os.chmod(temporary, 0o600)
            os.replace(temporary, destination)
            _atomic_json(
                sidecar,
                {
                    "schemaVersion": "studio.speech-benchmark-private-audio.v1",
                    "assetId": asset_id,
                    "caseId": case_id,
                    **metadata,
                },
            )
        except Exception:
            temporary.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            sidecar.unlink(missing_ok=True)
            raise
        self._assets[asset_id] = (case_id, expected_checksum, [destination, sidecar])
        return asset_id

    def persist_provenance(self, case_id: str, payload: dict[str, Any]) -> str:
        asset_id = _asset_id(self.run_id, case_id, "provenance")
        token = hashlib.sha256(case_id.encode()).hexdigest()
        destination = self.root / "provenance" / f"{token}.json"
        _atomic_json(destination, {"assetId": asset_id, **payload})
        self._assets[asset_id] = (case_id, "", [destination])
        return asset_id

    def evidence_bundle_asset_id(self, stage: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", stage):
            raise ValueError("benchmark_snapshot_stage_invalid")
        return _asset_id(self.run_id, stage, "evidence-bundle")

    def persist_snapshot(self, artifacts: Any, *, stage: str) -> dict[str, str]:
        evidence_asset_id = self.evidence_bundle_asset_id(stage)
        if artifacts.run.run_id != self.run_id or artifacts.evidence_bundle.run_id != self.run_id:
            raise ValueError("benchmark_snapshot_run_mismatch")
        if stage == "initial" and artifacts.run.evidence_refs.get(
            "raw_metric_bundle"
        ) != evidence_asset_id:
            raise ValueError("benchmark_snapshot_raw_bundle_binding_mismatch")
        directory = self.root / "snapshots" / stage
        run_path = directory / "benchmark-run.json"
        evidence_path = directory / "evidence-bundle.json"
        run_payload = artifacts.run.model_dump(by_alias=True, mode="json")
        evidence_payload = {
            "assetId": evidence_asset_id,
            **artifacts.evidence_bundle.model_dump(by_alias=True, mode="json"),
        }
        _persist_or_validate_json(run_path, run_payload)
        _persist_or_validate_json(evidence_path, evidence_payload)
        files = []
        for role, path in (("benchmark_run", run_path), ("evidence_bundle", evidence_path)):
            files.append(
                {
                    "role": role,
                    "relativePath": path.relative_to(self.root).as_posix(),
                    "checksumSha256": sha256_file(path),
                    "sizeBytes": path.stat().st_size,
                }
            )
        package_path = directory / "package-manifest.json"
        package_payload = {
            "schemaVersion": "studio.speech-benchmark-private-package.v1",
            "runId": self.run_id,
            "stage": stage,
            "evidenceBundleAssetId": evidence_asset_id,
            "files": files,
        }
        _persist_or_validate_json(package_path, package_payload)
        return {
            "evidenceBundleAssetId": evidence_asset_id,
            "packageManifestDigestSha256": sha256_file(package_path),
        }

    def review_bundle_asset_id(self) -> str:
        return _asset_id(self.run_id, self.run_id, "blinded-review-bundle")

    def persist_review_plan(self, plan: Any) -> dict[str, Any]:
        if plan.run_id != self.run_id:
            raise ValueError("speech_review_storage_run_mismatch")
        plan_asset_id = _asset_id(self.run_id, plan.plan_id, "review-plan")
        organizer_path = self.root / "review" / "organizer" / "review-plan.json"
        _atomic_json(
            organizer_path,
            {"assetId": plan_asset_id, **plan.model_dump(by_alias=True, mode="json")},
        )
        packet_records = []
        for packet in plan.packets:
            packet_asset_id = _asset_id(self.run_id, packet.packet_id, "reviewer-packet")
            packet_path = self.root / "review" / "packets" / f"{packet.packet_id}.json"
            _atomic_json(
                packet_path,
                {"assetId": packet_asset_id, **packet.model_dump(by_alias=True, mode="json")},
            )
            packet_records.append(
                {
                    "packetAssetId": packet_asset_id,
                    "packetId": packet.packet_id,
                    "checksumSha256": sha256_file(packet_path),
                }
            )
        index_path = self.root / "review" / "organizer" / "packet-index.json"
        _atomic_json(
            index_path,
            {
                "schemaVersion": "studio.speech-review-private-index.v1",
                "runId": self.run_id,
                "planAssetId": plan_asset_id,
                "planChecksumSha256": sha256_file(organizer_path),
                "packets": packet_records,
            },
        )
        return {
            "planAssetId": plan_asset_id,
            "packetCount": len(packet_records),
            "packetIndexDigestSha256": sha256_file(index_path),
        }

    def persist_review_result(self, bundle: Any, artifacts: Any) -> dict[str, str]:
        if bundle.run_id != self.run_id or artifacts.run.run_id != self.run_id:
            raise ValueError("speech_review_result_storage_run_mismatch")
        asset_id = self.review_bundle_asset_id()
        if artifacts.run.evidence_refs.get("blinded_human_review") != asset_id:
            raise ValueError("speech_review_result_asset_binding_mismatch")
        bundle_path = self.root / "review" / "organizer" / "review-bundle.json"
        _atomic_json(
            bundle_path,
            {"assetId": asset_id, **bundle.model_dump(by_alias=True, mode="json")},
        )
        snapshot = self.persist_snapshot(artifacts, stage="post-review")
        return {
            "reviewBundleAssetId": asset_id,
            "reviewBundleDigestSha256": sha256_file(bundle_path),
            **snapshot,
        }

    def delete(self, asset_id: str) -> bool:
        record = self._assets.pop(asset_id, None)
        if record is None:
            return asset_id in self._deleted_assets
        for path in record[2]:
            path.unlink(missing_ok=True)
        absent = all(not path.exists() for path in record[2])
        if absent:
            self._deleted_assets.add(asset_id)
        return absent

    def finalize_audio_cleanup(
        self,
        evidence: BenchmarkEvidenceBundleV1,
        *,
        cleanup_bundle_id: str,
    ) -> tuple[str, SpeechBenchmarkCleanupBundleV1]:
        if (self.root / "receipts" / "cleanup-bundle.json").exists():
            raise ValueError("speech_benchmark_cleanup_already_finalized")
        cases: list[SpeechBenchmarkCleanupCaseV1] = []
        for execution in evidence.case_executions:
            output_id = execution.output_asset_id
            if output_id is None:
                active_for_case = [
                    asset_id
                    for asset_id, record in self._assets.items()
                    if record[0] == execution.case_id and record[1]
                ]
                verified_absent = not active_for_case
                cases.append(
                    SpeechBenchmarkCleanupCaseV1(
                        case_id=execution.case_id,
                        deletion_attempted=False,
                        deleted=False,
                        verified_absent=verified_absent,
                        failure_reason=None if verified_absent else "unexpected_case_audio_remains",
                    )
                )
                continue
            record = self._assets.get(output_id)
            checksum = execution.output_checksum_sha256
            failure_reason: str | None = None
            try:
                deleted = self.delete(output_id)
            except OSError as error:
                deleted = False
                failure_reason = f"audio_delete_failed:{type(error).__name__}"
            verified_absent = deleted and record is not None
            cases.append(
                SpeechBenchmarkCleanupCaseV1(
                    case_id=execution.case_id,
                    output_asset_id=output_id,
                    output_checksum_sha256=checksum,
                    deletion_attempted=True,
                    deleted=deleted,
                    verified_absent=verified_absent,
                    failure_reason=(
                        None
                        if verified_absent
                        else failure_reason or "audio_delete_not_verified"
                    ),
                )
            )
        bundle = SpeechBenchmarkCleanupBundleV1(
            bundle_id=cleanup_bundle_id,
            run_id=self.run_id,
            generated_at=datetime.now(UTC),
            cases=cases,
        )
        cleanup_asset_id = _asset_id(self.run_id, cleanup_bundle_id, "cleanup")
        destination = self.root / "receipts" / "cleanup-bundle.json"
        _atomic_json(
            destination,
            {
                "assetId": cleanup_asset_id,
                **bundle.model_dump(by_alias=True, mode="json"),
            },
        )
        self._assets[cleanup_asset_id] = ("cleanup-bundle", "", [destination])
        return cleanup_asset_id, bundle

    def load_cleanup_bundle(self) -> tuple[str, SpeechBenchmarkCleanupBundleV1]:
        source = self.root / "receipts" / "cleanup-bundle.json"
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("speech_benchmark_cleanup_bundle_unreadable") from error
        asset_id = payload.pop("assetId", None)
        bundle = SpeechBenchmarkCleanupBundleV1.model_validate(payload)
        expected_asset_id = _asset_id(self.run_id, bundle.bundle_id, "cleanup")
        if asset_id != expected_asset_id or bundle.run_id != self.run_id:
            raise ValueError("speech_benchmark_cleanup_bundle_binding_mismatch")
        return asset_id, bundle
