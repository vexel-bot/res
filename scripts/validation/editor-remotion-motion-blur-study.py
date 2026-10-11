"""Verify the pinned Remotion motion-blur mechanism against the native adapter."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "workers/remotion-benchmark"
PACKAGE = WORKER / "node_modules/@remotion/motion-blur"
source_path = PACKAGE / "dist/cjs/CameraMotionBlur.js"
native_path = WORKER / "src/temporal-exposure.tsx"
package = json.loads((PACKAGE / "package.json").read_text(encoding="utf-8"))
source = source_path.read_text(encoding="utf-8")
native = native_path.read_text(encoding="utf-8")
required_source_patterns = {
    "isolated_parent": "isolation: 'isolate'",
    "plus_lighter": "mixBlendMode: 'plus-lighter'",
    "weighted_filter": "filter: `opacity(${1 / actualSamples})`",
    "frozen_sample": "Freeze",
}
required_native_patterns = {
    "isolated_parent": "isolation:'isolate'",
    "plus_lighter": "mixBlendMode:'plus-lighter'",
    "weighted_filter": "filter:`opacity(${1/frames.length})`",
    "sample_policy": "centered_clipped",
}
assert package["version"] == "4.0.527"
assert all(pattern in source for pattern in required_source_patterns.values())
assert all(pattern in native for pattern in required_native_patterns.values())
report = {
    "scope": "pinned_open_source_mechanism_comparison",
    "package": "@remotion/motion-blur",
    "version": package["version"],
    "license": package["license"],
    "source": str(source_path.relative_to(ROOT)).replace("\\", "/"),
    "sourceSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    "nativeAdapter": str(native_path.relative_to(ROOT)).replace("\\", "/"),
    "nativeAdapterSha256": hashlib.sha256(native_path.read_bytes()).hexdigest(),
    "sharedMechanisms": required_source_patterns,
    "nativeAdditionalPolicy": [
        "TemporalExposureV1",
        "center_frame external ancestors",
        "local_subtree effective draw times",
        "static reduction only for identical registered draw inputs",
    ],
    "qualification": "native temporal matte with moving external ancestor remains pending",
    "humanReview": "pending",
}
output = ROOT / "docs/studios/research/editor-oss-20261002/remotion-motion-blur-study.json"
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"package": package["version"], "sourceSha256": report["sourceSha256"], "output": str(output)}))
