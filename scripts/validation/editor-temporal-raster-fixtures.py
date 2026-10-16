"""Build diagnostic manifests from the same original temporal API fixture."""
# ruff: noqa: E402
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))

from test_remotion_native import native_document
from test_temporal_exposure_render import exposure_direction

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.motion_recipes import TemporalExposureV1
from app.providers.studios.remotion_projection import compile_remotion_composition

destination = ROOT / "docs/studios/research/editor-oss-20261002/temporal-raster-diagnostic"
destination.mkdir(parents=True, exist_ok=True)
policy = TemporalExposureV1().model_dump(mode="json", by_alias=True)
for samples, shutter in [(0, 180), (2, 180), (8, 180), (16, 180), (8, 0)]:
    document, projection = native_document(ContextualPlanRequestV2.model_validate(exposure_direction(samples, shutter, policy)))
    manifest = compile_remotion_composition(document, projection, {})
    (destination / f"samples-{samples}-shutter-{shutter}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
print(json.dumps({"directory": str(destination), "scope": "diagnostic_reconstruction_not_API_job_evidence"}))
