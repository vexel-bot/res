"""Reconstruct diagnostic manifests from retained real API inspection snapshots."""
# ruff: noqa: E402
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain.studios.contracts import CreativeDocumentV1
from app.domain.studios.motion import MotionGraphV1, evaluate_motion_graph, project_motion_graph
from app.providers.studios.remotion_projection import compile_remotion_composition

folder = ROOT / "docs/studios/research/editor-oss-20261002/temporal-rig-raster"
folder.mkdir(parents=True, exist_ok=True)
for variant in ["control", "rig", "child", "disjoint"]:
    file = ROOT / "docs/studios/research/editor-oss-20261002/temporal-rig-render" / variant / "evidence.json"
    evidence = json.loads(file.read_text(encoding="utf-8"))
    document = CreativeDocumentV1.model_validate(evidence["inspection"]["document"])
    graph = MotionGraphV1.model_validate(document.composition.narrative["editorialV2"]["motionGraph"])
    projection = project_motion_graph(graph, "remotion", evaluate_motion_graph(document, graph))
    manifest = compile_remotion_composition(document, projection, {})
    receipt = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
    assert manifest["nativeCompositionDigest"] == receipt["nativeCompositionDigest"]
    manifest["diagnosticOrigin"] = {"scope": "reconstruction_not_new_API_MP4_proof",
                                     "jobId": evidence["renderResult"]["jobId"],
                                     "evidenceSha256": hashlib.sha256(file.read_bytes()).hexdigest()}
    (folder / (variant + ".json")).write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
print(json.dumps({"manifests": 4, "folder": str(folder)}))
