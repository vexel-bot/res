"""Reconstruct diagnostic input; generate an explicitly separate GL study runner."""
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

directory = ROOT / "docs/studios/research/editor-oss-20261002/spatial-effects-gl-diagnostic"
directory.mkdir(parents=True, exist_ok=True)
evidence_path = directory.parent / "spatial-effects-fast-stage-diagnostic/exposure/evidence.json"
evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
document = CreativeDocumentV1.model_validate(evidence["inspection"]["document"])
graph = MotionGraphV1.model_validate(document.composition.narrative["editorialV2"]["motionGraph"])
manifest = compile_remotion_composition(document, project_motion_graph(
    graph, "remotion", evaluate_motion_graph(document, graph)), {})
receipt = evidence["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
assert manifest["nativeCompositionDigest"] == receipt["nativeCompositionDigest"]
manifest["encodeQuality"] = "high"
(directory / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
worker = ROOT / "workers/remotion-benchmark"
production = (worker / "render-hybrid.mjs").read_bytes()
source = production.decode("utf-8")
for call in ["selectComposition({serveUrl,", "renderMedia({serveUrl,"]:
    assert source.count(call) == 1
    source = source.replace(call, call + "chromiumOptions:{gl:'swangle'},")
runner = worker / "render-spatial-gl-diagnostic.mjs"
runner.write_text("// Generated research-only runner; not a provider or qualification.\n" + source, encoding="utf-8")
(directory / "origin.json").write_text(json.dumps({
    "scope": "reconstruction_and_alternate_GL_diagnostic_not_new_API_qualification",
    "evidenceSha256": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
    "productionRunnerSha256": hashlib.sha256(production).hexdigest(),
    "diagnosticRunnerSha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
    "difference": "explicit swangle in selection and rendering; no production edits"}, indent=2), encoding="utf-8")
print(json.dumps({"directory": str(directory), "runner": str(runner)}))
