"""Read-only audit of existing session evidence. Never calls a model or renderer."""
import argparse
import json
from pathlib import Path


def audit(path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    result = value.get("result", value)
    turns, tools = result.get("turns", []), result.get("tools", [])
    delivery = result.get("deliveryReview", {})
    references = [t.get("input", {}).get("referenceId") for t in tools
                  if t.get("name") == "inspect_reference" and t.get("ok")]
    spans = delivery.get("nativeCoverage", [])
    return {"source": str(path.resolve()), "paidResponses": len(turns),
            "recordedCostUsd": round(sum(t.get("costUsd", 0) or 0 for t in turns), 8),
            "referencesInspected": references,
            "externalReferenceObserved": any(r and r != "orbita.quality.baseline" for r in references),
            "legacyTechnicalStatus": delivery.get("status"),
            "nativeSecondsCovered": round(sum(b-a for a, b in spans), 6),
            "perceptualListening": delivery.get("perceptualAudioListening", "not_established"),
            "searchMisses": [m["input"] for m in result.get("inspectionMemory", [])
                             if m.get("name") == "inspect_editor_capabilities"
                             and m.get("result", {}).get("totalCommands") == 0],
            "errors": [t.get("error") for t in tools if not t.get("ok")],
            "interpretation": "Coverage and process audit only; not an aesthetic score or human approval."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([audit(path) for path in args.evidence], ensure_ascii=False, indent=2))
