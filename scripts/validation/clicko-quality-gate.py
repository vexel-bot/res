"""Check local receipts before unlocking the single paid quality cycle."""
import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(output, controls, flash, tests):
    prepared = output / "cycle-receipt.json"
    animatic = output / "animatic.json"
    preparation = read(prepared)
    motion = read(controls)
    correction = read(flash)
    cases = ElementTree.parse(tests).findall(".//testcase")
    passing = {item.attrib["name"] for item in cases if not len(item)}
    required = {"test_capped_native_end_turn_requests_export_and_replay_does_not_renew_budget",
                "test_effectcraft_checkpoint_survives_two_interruptions_and_exports_after_resume"}
    checks = {
        "prepared": preparation["stage"] == "prepared" and len(preparation["references"]) == 4
                    and preparation["paidGenerations"] == 0 and len(preparation["preparedMaterials"]) == 15,
        "animatic": read(animatic)["sha256"] == sha(output / "orbita-animatic-local.mp4"),
        "engine": motion["nativeConformance"]["status"] == "pass",
        "reviewControls": motion["calibration"]["status"] == "pass",
        "knownFlash": correction["knownFlash"]["status"] == "pass",
        "recoveryAndExport": required <= passing,
        "testSuite": bool(cases) and len(cases) == len(passing),
        "zeroPaid": all(item["apiSpendUsd"] == 0 for item in (preparation, motion, correction, read(animatic))),
    }
    failed = [name for name, passed in checks.items() if not passed]
    result = {"schemaVersion": "clicko.quality-cycle-gate.v1", "status": "passed" if not failed else "failed",
              "apiSpendUsd": 0, "requiredFailures": failed, "checks": checks, "testsPassed": len(passing),
              "preparedReceiptSha256": sha(prepared), "animaticReceiptSha256": sha(animatic),
              "evidenceSha256": {"controls": sha(controls), "flash": sha(flash), "tests": sha(tests)},
              "executor": "effectcraft", "canvasIntegration": "no measured benefit in qualified scene",
              "limitations": ["Fixture conformance and real-engine delivery with simulated model",
                              "No perceptual audio or viewer approval", "No photographic segmentation qualification"]}
    (output / "local-gate.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output", "controls", "flash", "tests"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.output, args.controls, args.flash, args.tests))
