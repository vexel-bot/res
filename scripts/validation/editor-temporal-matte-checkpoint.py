"""Keep failed qualification separate from current admitted-capability regression."""
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "docs/studios/research/editor-oss-20261002"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


sources = read(DIRECTORY / "temporal-matte-native13-current-sources.json")
assert all(sha(ROOT/name) == digest for name, digest in sources["sources"].items())
regression = read(DIRECTORY / "temporal-matte-native13-regression-run.json")
assert regression["exitCode"] == 0 and not regression["sourceDrift"]
cases = ET.parse(DIRECTORY / "temporal-matte-native13-regression-tests.xml").findall(".//testcase")
assert len(cases) == 188
assert not any(c.find(tag) is not None for c in cases for tag in ["failure", "error", "skipped"])
current_gate = read(DIRECTORY / "temporal-matte-native13-admission/child-external-alpha-normal/negative.json")
assert current_gate["httpStatus"] == 422 and not current_gate["publishedArtifact"]
assert "temporal_matte_moving_external_ancestor_pending" in json.dumps(current_gate["response"])

experiments = []
for phase in ["temporal-matte-native13-render", "temporal-matte-native13-control-diagnostic",
              "temporal-matte-native13-qualified-render", "temporal-matte-native13-inversion-stage-diagnostic"]:
    for path in sorted((DIRECTORY/phase).glob("*/evidence.json")):
        data = read(path)
        result = data["renderResult"]
        video = path.parent / "matte-exposure.mp4"
        assert sha(video) == result["artifact"]["checksumSha256"]
        assert result["providerVersion"] == "4.0.527-native.13"
        assert result["qualityEvaluation"]["status"] == "passed"
        assert result["documentRevision"] == data["inspection"]["document"]["revision"]
        assert data["humanReview"] == "pending"
        matrices = data["matrixChecks"]
        assert len(matrices) == 6 and max(c["maximumError"] for c in matrices) < .002
        experimental = {"phase": phase, "variant": data["variant"], "jobId": result["jobId"],
            "video": video.relative_to(ROOT).as_posix(), "checksum": sha(video), "qc": "passed",
            "measurementStatus": data["measurementStatus"], "probes": len(data["pixelChecks"]),
            "maximumChannelError": max(c["maximumChannelError"] for c in data["pixelChecks"]),
            "failures": data["failures"], "matrixMaximumError": max(c["maximumError"] for c in matrices)}
        if phase.endswith("inversion-stage-diagnostic"):
            intermediate = path.parent/"graphics-intermediate.mp4"
            receipt = data["renderMetadata"]["contextualEditing"]["rendererChecks"]["graphics"]["remotionReceipt"]
            assert sha(intermediate) == receipt["videoSha256"]
            raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(intermediate), "-f", "rawvideo",
                                  "-pix_fmt", "rgb24", "pipe:1"], check=True, capture_output=True).stdout
            comparisons = []
            for probe in data["pixelChecks"]:
                if probe["maximumChannelError"] < 8:
                    continue
                frame, x, y = probe["frame"], probe["x"], probe["y"]
                rgb = [sum(raw[(frame*320*320+(y+dy)*320+x+dx)*3+c]
                           for dx in range(2) for dy in range(2))/4 for c in range(3)]
                comparisons.append({"frame": frame, "x": x, "y": y,
                    "expected": probe["expectedChannel"], "intermediateRgb": rgb, "finalRgb": probe["observedRgb"]})
            experimental["intermediateFailureComparisons"] = comparisons
        experiments.append(experimental)
assert len(experiments) == 12
latest = [e for e in experiments if e["phase"].endswith("inversion-stage-diagnostic")]
assert len(latest) == 3 and sum(e["measurementStatus"] == "passed" for e in latest) == 1
assert sum(len(e["failures"]) for e in latest) == 3

renders, negatives = [], []
for suffix in ["spatial", "rig", "exposure", "matte", "typography", "command"]:
    for path in sorted((DIRECTORY/("temporal-matte-native13-regression-"+suffix)).glob("*/evidence.json")):
        data = read(path)
        if "renderResult" not in data:
            assert data["publishedArtifact"] is False
            negatives.append(path.relative_to(ROOT).as_posix())
            continue
        result = data["renderResult"]
        assert result["providerVersion"] == "4.0.527-native.13"
        assert result["qualityEvaluation"]["status"] == "passed"
        video = next(p for p in path.parent.glob("*.mp4") if p.name != "graphics-intermediate.mp4")
        assert sha(video) == result["artifact"]["checksumSha256"]
        assert data["humanReview"] == "pending"
        if suffix in {"rig", "spatial"}:
            assert data["measurementStatus"] == "passed" and not data["failures"]
        renders.append({"path": video.relative_to(ROOT).as_posix(), "sha256": sha(video), "jobId": result["jobId"]})
assert len(renders) == 22 and len(negatives) == 1
report = {"schemaVersion": "res.temporal-matte-qualification-checkpoint.v1",
    "generatedAt": datetime.now(UTC).isoformat(), "sourceDrift": False, "sources": sources,
    "currentRegressionCasesPassed": len(cases), "admittedCapabilityMP4s": renders, "negativeJobs": negatives,
    "combinedAdmission": "pending", "currentAPIRejection": current_gate, "experiments": experiments,
    "remainingExperimentalProbeFailures": 3, "humanReview": "pending",
    "limitations": ["Combined experiments preceded restoration of the API admission gate",
        "Experimental phases were not separately frozen; provider version alone does not identify their source bytes",
        "Continuous and two-stage raster oracle attempts remain evidence, not broad mask qualification",
        "Three edge probes remain unresolved; no tolerance was increased or probe removed",
        "Human commercial comparisons and three fresh autonomy briefs remain pending"]}
(DIRECTORY / "temporal-matte-checkpoint.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"regressionPassed": len(cases), "admittedMP4s": len(renders),
                  "experimentalMP4s": len(experiments), "remainingProbes": 3, "combinedAdmission": "pending"}))
