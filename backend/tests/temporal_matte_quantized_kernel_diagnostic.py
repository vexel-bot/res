"""Explicit API qualification for the independently calibrated affine raster profile.

Preserves the historical diagnostic and its verdicts. This new profile uses
unchanged authored fixtures, frames, probes and error limits. It is specific to
the pinned four-bit SwiftShader rasterizer, large affine quads and PNG mattes;
it does not qualify perspective, degenerate meshes or arbitrary paths.
"""
# ruff: noqa: F811
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project

from app.database import SessionLocal
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.jobs import execute_job_once
from tests.temporal_matte_kernel_diagnostic import (
    FRAMES,
    VARIANTS,
    direction_for,
    inverse,
    mul,
    original_mask,
    probe_points,
    times_for,
    worlds,
)

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
REFERENCE = ROOT / "scripts/validation/editor-temporal-matte-quantized-reference.py"
spec = importlib.util.spec_from_file_location("quantized_affine_png_reference_v1", REFERENCE)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
expected_pixel = reference.expected_pixel


def reference_profile():
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    raster = ROOT / "scripts/validation/editor-temporal-matte-quad-raster-reference.py"
    geometry = ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py"
    runtime_path = STUDY / "swiftshader-subpixel-runtime.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    # Use the declared WebGL precision, never observed output pixels, to select
    # the grid. The runtime receipt also seals the renderer and browser bytes.
    assert runtime["values"]["subpixelBits"] == 4
    browser = (ROOT / "workers/remotion-benchmark/node_modules/.remotion/chrome-headless-shell/win64" /
               "chrome-headless-shell-win64/chrome-headless-shell.exe")
    assert sha(browser) == runtime["browserSha256"]
    quad_path = STUDY / "temporal-matte-quad-raster-conformance.json"
    textured_path = STUDY / "temporal-matte-textured-source-conformance.json"
    quad = json.loads(quad_path.read_text(encoding="utf-8"))
    textured = json.loads(textured_path.read_text(encoding="utf-8"))
    assert quad["referenceScriptSha256"] == textured["rasterReferenceSha256"] == sha(raster)
    assert quad["geometryScriptSha256"] == sha(geometry)
    assert textured["referenceScriptSha256"] == sha(REFERENCE)
    assert quad["calibrationCases"] == 6 and len(quad["records"]) == 28
    assert len(textured["records"]) == 7
    assert sum(row["pixelCount"] for row in textured["records"]) == 716800
    assert all(not row["failedProbesAtOriginalThreshold"] for row in quad["records"] + textured["records"])
    return {"id": "swiftshader4_affine_png_v1", "referenceSha256": sha(REFERENCE),
            "rasterReferenceSha256": sha(raster), "geometryReferenceSha256": sha(geometry),
            "runtimeReceiptSha256": sha(runtime_path), "quadConformanceSha256": sha(quad_path),
            "texturedConformanceSha256": sha(textured_path), "pixelErrorLimitExclusive": 8,
            "matrixErrorLimitExclusive": .002, "historicalDiagnosticChanged": False}
