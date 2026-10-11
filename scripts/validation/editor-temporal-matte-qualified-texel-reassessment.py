"""Reassess retained outputs with an exact-texel-conformant research reference.

No original test, production gate or threshold is changed by this report.
Affine antialiasing remains a separate qualification requirement.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "docs/studios/research/editor-oss-20261002"
source = ROOT / "scripts/validation/editor-temporal-matte-center-sampling-study.py"
namespace = {"__file__": str(source), "__name__": "research_function_only"}
exec(compile(source.read_text(encoding="utf-8").split("conformance =")[0], str(source), "exec"), namespace)
center_pixel = namespace["center_sampled_pixel"]
frame0_path = STUDY / "temporal-matte-svg-subtract-frame0-controls/analysis.json"
frame0 = json.loads(frame0_path.read_text(encoding="utf-8"))
encode_path = STUDY / "temporal-matte-svg-subtract-final-encode-study-v2/analysis.json"
encode = json.loads(encode_path.read_text(encoding="utf-8"))
assert all(not record["failedProbesAtOriginalThreshold"] for case in frame0["cases"] for record in case["records"])
assert encode["crf14ControlMatchesAllApiProbes"]
cache, records, conformance_checks = {}, [], []
# These 3,840 texture blocks have full target coverage and an integer source
# translation. A stationary control reference must return authored texels
# exactly; the moving target does not alter coverage at any of these blocks.
for case in frame0["cases"]:
    if case["variant"] == "child-external-unmasked":
        continue
    invert = case["variant"].endswith("inverted")
    center = next(record for record in case["records"] if record["name"] == "center")
    maximum = 0
    for check in center["checks"]:
        expected = center_pixel(0, "control", "external", "alpha", invert, check["x"], check["y"])
        maximum = max(maximum, abs(expected - check["exactTranslatedTexelChannel"]))
    assert maximum < 1e-9
    conformance_checks.append({"variant": case["variant"], "exactTextureBlockCount": len(center["checks"]), "maximumReferenceError": maximum})
for record in encode["records"]:
    video = encode_path.parent / (record["variant"] + "-crf" + str(record["crf"]) + ".mp4")
    assert hashlib.sha256(video.read_bytes()).hexdigest() == record["outputSha256"]
    scope, branch, mode, inverted = record["variant"].split("-")
    checks = []
    for check in record["checks"]:
        key = (record["variant"], check["frame"], check["x"], check["y"])
        if key not in cache:
            cache[key] = center_pixel(check["frame"], scope, branch, mode, inverted == "inverted", check["x"], check["y"])
        expected = cache[key]
        checks.append({"frame": check["frame"], "x": check["x"], "y": check["y"], "centerTextureResearchChannel": expected,
                       "originalOracleChannel": check["expectedChannel"], "observedRgb": check["observedRgb"],
                       "maximumChannelError": max(abs(channel - expected) for channel in check["observedRgb"])})
    records.append({"variant": record["variant"], "crf": record["crf"], "outputSha256": record["outputSha256"],
                    "maximumResearchReferenceError": max(check["maximumChannelError"] for check in checks),
                    "originalReferenceMaximumError": record["maximumChannelError"],
                    "failedResearchReferenceProbes": [check for check in checks if check["maximumChannelError"] >= 8], "checks": checks})
report = {"scope": "research_only_exact_texel_conformant_reassessment", "productionAdmission": "pending",
          "originalOracleChanged": False, "tolerance": 8,
          "referenceLimitation": "Texel identity proven for integer translation/full content coverage; affine AA still requires independent qualification.",
          "frame0AnalysisSha256": hashlib.sha256(frame0_path.read_bytes()).hexdigest(),
          "encodeAnalysisSha256": hashlib.sha256(encode_path.read_bytes()).hexdigest(),
          "referenceScriptSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "analysisScriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "conformance": conformance_checks, "records": records}
assert math.isclose(sum(c["exactTextureBlockCount"] for c in conformance_checks), 3840)
(STUDY / "temporal-matte-qualified-texel-reassessment.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps([{ "variant": record["variant"], "crf": record["crf"],
                   "maximumError": record["maximumResearchReferenceError"], "failedProbes": len(record["failedResearchReferenceProbes"])}
                 for record in records]))
