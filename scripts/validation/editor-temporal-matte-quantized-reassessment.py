"""Keep original API verdicts alongside the separately calibrated reference."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
API = STUDY / "temporal-matte-native14-balanced-vector-guard-svg-subtract-crf10-full"
reference_path = ROOT / "scripts/validation/editor-temporal-matte-quantized-reference.py"
spec = importlib.util.spec_from_file_location("independent_quantized_reference", reference_path)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
from tests.temporal_matte_kernel_diagnostic import original_mask  # noqa: E402

mask = original_mask()
records = []
for file in sorted(API.glob("*/evidence.json")):
    evidence = json.loads(file.read_text(encoding="utf-8"))
    video = file.parent / "matte-exposure.mp4"
    assert hashlib.sha256(video.read_bytes()).hexdigest() == evidence["renderResult"]["artifact"]["checksumSha256"]
    scope, branch, mode, invert = evidence["variant"].split("-")
    checks = []
    for check in evidence["pixelChecks"]:
        expected = reference.expected_pixel(mask, check["frame"], scope, branch, mode, invert == "inverted", check["x"], check["y"])
        checks.append({"frame": check["frame"], "x": check["x"], "y": check["y"], "quantizedReferenceChannel": expected,
                       "originalReferenceChannel": check["expectedChannel"], "observedRgb": check["observedRgb"],
                       "maximumChannelError": max(abs(channel - expected) for channel in check["observedRgb"])})
    records.append({"variant": evidence["variant"], "originalVerdict": evidence["measurementStatus"],
                    "originalFailures": evidence["failures"], "videoSha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                    "maximumQuantizedReferenceError": max(check["maximumChannelError"] for check in checks),
                    "failedQuantizedReferenceProbes": [check for check in checks if check["maximumChannelError"] >= 8], "checks": checks})
report = {"scope": "actual_API_reassessment_with_independent_quantized_reference", "productionAdmission": "pending", "originalOracleChanged": False,
          "referenceScriptSha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
          "analysisScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "limitations": "Reassessment of retained videos only; a separate new API run and regressions remain necessary before admission.", "records": records}
(STUDY / "temporal-matte-quantized-reassessment.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps([{ "variant": record["variant"], "maximumError": record["maximumQuantizedReferenceError"],
                  "failedProbes": len(record["failedQuantizedReferenceProbes"])} for record in records]))
