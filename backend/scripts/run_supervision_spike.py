"""Run the synthetic, no-network Supervision SV-1 spike.

The command expects an isolated Supervision 0.30.1 runtime on ``PYTHONPATH``.
It never downloads a detector, reads human media, mutates a worker manifest or
registers a provider.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import socket
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

import numpy as np

from app.domain.studios.contracts import AssetReferenceV1, FrameRateV1
from app.domain.studios.reality import (
    RealityAnalysisRequestV1,
    RealityFrameRangeV1,
    RealityShotV1,
)
from app.providers.studios.supervision_detection import (
    SupervisionAdapterConfig,
    SupervisionClassSpec,
    SupervisionDetectionAdapter,
    SupervisionFrameInput,
)

ROOT = Path(__file__).resolve().parents[2]
VISION_MANIFEST = ROOT / "workers/vision-gpu/worker.manifest.json"
SOURCE_REVISION = "5f25aa0ee6dc22891415b6e3d2e1689ce7a32952"
FROZEN_TIME = datetime(2026, 8, 27, 21, 0, tzinfo=UTC)


class _NetworkDenied(AbstractContextManager[None]):
    def __enter__(self) -> None:
        self._connect = socket.socket.connect
        self._connect_ex = socket.socket.connect_ex
        self._create_connection = socket.create_connection

        def denied(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError("supervision_spike_network_denied")

        socket.socket.connect = denied  # type: ignore[method-assign]
        socket.socket.connect_ex = denied  # type: ignore[method-assign]
        socket.create_connection = denied  # type: ignore[assignment]
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        socket.socket.connect = self._connect  # type: ignore[method-assign]
        socket.socket.connect_ex = self._connect_ex  # type: ignore[method-assign]
        socket.create_connection = self._create_connection  # type: ignore[assignment]
        return None


def main() -> int:
    args = _parse_args()
    with _NetworkDenied():
        supervision = importlib.import_module("supervision")
        if str(supervision.__version__) != "0.30.1":
            raise SystemExit(f"unexpected Supervision version: {supervision.__version__}")
        request = _request()
        frames = _frames(supervision)
        adapter = SupervisionDetectionAdapter(
            SupervisionAdapterConfig(
                source_provider="synthetic.fixture-detector",
                source_provider_version="1.0.0",
                source_code_digest_sha256="a" * 64,
                model_id="synthetic-no-weights",
                model_revision="fixture-v1",
                model_digest_sha256="b" * 64,
                class_map={
                    0: SupervisionClassSpec("Person", "person"),
                    1: SupervisionClassSpec("Product", "rigid_object"),
                },
            ),
            supervision_module=supervision,
        )
        first_progress: list[int] = []
        first = adapter.project(
            request,
            frames,
            first_progress.append,
            lambda: False,
            generated_at=FROZEN_TIME,
        )
        second = adapter.project(
            request,
            frames,
            lambda _value: None,
            lambda: False,
            generated_at=FROZEN_TIME,
        )

    first_payload = first.contribution.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    second_payload = second.contribution.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
    )
    first_digest = _digest(first_payload)
    second_digest = _digest(second_payload)
    first_overlay_digests = [item.checksum_sha256 for item in first.overlays]
    second_overlay_digests = [item.checksum_sha256 for item in second.overlays]
    manifest = json.loads(VISION_MANIFEST.read_text(encoding="utf-8"))
    checks = {
        "canonical_contract": first.contribution.schema_version
        == "studio.reality-contribution.v1",
        "deterministic_contract": first_digest == second_digest,
        "deterministic_overlays": first_overlay_digests == second_overlay_digests,
        "evidence_bound": all(
            sample.evidence_ids
            for track in first.contribution.tracks
            for sample in track.samples
        ),
        "external_tracker_preserved_without_raw_id": (
            len(first.contribution.tracks) == 2
            and all("17" not in track.track_id for track in first.contribution.tracks)
        ),
        "no_physics_claims": (
            not first.contribution.relations
            and not first.contribution.hypotheses
            and not first.contribution.events
        ),
        "network_guard_active": True,
        "worker_provider_manifest_empty": manifest["providers"] == [],
        "synthetic_only": True,
        "weights_absent": True,
    }
    report = {
        "schemaVersion": "clicko.supervision-spike-report.v1",
        "candidate": {
            "name": "supervision",
            "version": str(supervision.__version__),
            "sourceRevision": SOURCE_REVISION,
            "status": "evaluation",
            "advertisedByWorkerManifest": False,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": str(np.__version__),
            "platform": platform.platform(),
            "isolatedRuntime": True,
            "networkDeniedDuringRun": True,
        },
        "input": {
            "kind": "synthetic",
            "frames": len(frames),
            "detections": sum(len(frame.detections) for frame in frames),
            "humanData": False,
            "modelWeights": False,
        },
        "output": {
            "contributionDigestSha256": first_digest,
            "entities": len(first.contribution.entities),
            "tracks": len(first.contribution.tracks),
            "evidence": len(first.contribution.evidence),
            "overlayDigestsSha256": first_overlay_digests,
            "progress": first_progress,
        },
        "checks": checks,
        "passed": all(checks.values()),
        "limitations": [
            "SV-1 proves projection and explainable overlays, not detector quality.",
            "The candidate runtime is a local Windows evaluation target, not the Linux OCI promotion artifact.",
            "No zone, metrics, throughput, SBOM or provider promotion claim is made by this report.",
        ],
    }
    if not report["passed"]:
        raise SystemExit("Supervision spike checks failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    return 0


def _request() -> RealityAnalysisRequestV1:
    return RealityAnalysisRequestV1(
        analysis_id="supervision-real-spike-001",
        workspace_id="workspace-synthetic-spike",
        source_asset=AssetReferenceV1(
            id="asset-synthetic-spike",
            version=1,
            media_type="video/mp4",
            checksum="c" * 64,
            origin="synthetic-test",
            rights_status="verified",
            provenance={"synthetic": True, "humanData": False},
        ),
        source_time_map_id="time-map-synthetic-spike",
        source_time_map_digest_sha256="d" * 64,
        frame_rate=FrameRateV1(numerator=30, denominator=1),
        total_frames=12,
        shots=[
            RealityShotV1(
                shot_id="shot-synthetic-spike",
                frame_range=RealityFrameRangeV1(
                    start_frame=0,
                    end_frame_exclusive=12,
                ),
                transition_in="start",
                transition_out="end",
            )
        ],
        analysis_policy_digest_sha256="e" * 64,
    )


def _frames(supervision) -> list[SupervisionFrameInput]:
    scene = np.zeros((120, 240, 3), dtype=np.uint8)
    first_masks = np.zeros((2, 120, 240), dtype=bool)
    first_masks[0, 20:90, 20:100] = True
    first_masks[1, 35:105, 130:220] = True
    second_masks = np.zeros((1, 120, 240), dtype=bool)
    second_masks[0, 24:94, 35:115] = True
    return [
        SupervisionFrameInput(
            frame_index=2,
            width=240,
            height=120,
            scene_bgr=scene,
            detections=supervision.Detections(
                xyxy=np.array([[20, 20, 100, 90], [130, 35, 220, 105]], dtype=float),
                mask=first_masks,
                confidence=np.array([0.93, 0.88]),
                class_id=np.array([0, 1]),
                tracker_id=np.array([17, 24]),
            ),
        ),
        SupervisionFrameInput(
            frame_index=7,
            width=240,
            height=120,
            scene_bgr=scene,
            detections=supervision.Detections(
                xyxy=np.array([[35, 24, 115, 94]], dtype=float),
                mask=second_masks,
                confidence=np.array([0.91]),
                class_id=np.array([0]),
                tracker_id=np.array([17]),
            ),
        ),
    ]


def _digest(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
