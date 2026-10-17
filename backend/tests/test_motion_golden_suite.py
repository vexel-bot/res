from __future__ import annotations

import hashlib
from pathlib import Path

from app.domain.studios.motion_benchmark import MotionGoldenSuiteEvidenceV1


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SUITE_ROOT = (
    REPOSITORY_ROOT
    / "artifacts"
    / "validation"
    / "video-creative-pilot"
    / "motion-goldens-20260901-v1"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_motion_golden_suite_is_complete_repeatable_and_materialized() -> None:
    suite = MotionGoldenSuiteEvidenceV1.model_validate_json(
        (SUITE_ROOT / "manifest.json").read_text(encoding="utf-8")
    )

    assert suite.eligible is True
    assert suite.blockers == []
    assert {item.family for item in suite.cases} == {
        "presenter_ugc",
        "split_screen_proof",
        "motion_visual_essay",
        "cinematic_hybrid",
    }
    for item in suite.cases:
        assert item.exact_artifact_repeat is True
        assert item.exact_checkpoint_repeat is True
        assert item.reduced_motion_static_track_count >= 1
        assert len(item.covered_property_paths) >= 8
        assert {
            "typography.fontSizePx",
            "typography.fontWeight",
            "transform.translateX",
        } <= set(item.covered_property_paths)

        normal = REPOSITORY_ROOT / item.normal.artifact_path
        reduced = REPOSITORY_ROOT / item.reduced_motion.artifact_path
        assert normal.is_file() and normal.stat().st_size > 0
        assert reduced.is_file() and reduced.stat().st_size > 0
        assert _sha256(normal) == item.normal.artifact_digest_sha256
        assert _sha256(reduced) == item.reduced_motion.artifact_digest_sha256
        assert item.normal.checkpoint_frame_digests != item.reduced_motion.checkpoint_frame_digests

        family_root = SUITE_ROOT / item.family
        for frame, digest in item.normal.checkpoint_frame_digests.items():
            checkpoint = family_root / "normal-frames" / f"frame-{frame:03d}.png"
            assert _sha256(checkpoint) == digest
        for frame, digest in item.reduced_motion.checkpoint_frame_digests.items():
            checkpoint = family_root / "reduced-motion-frames" / f"frame-{frame:03d}.png"
            assert _sha256(checkpoint) == digest
