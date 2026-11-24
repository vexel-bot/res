"""Collect live editor coverage, contiguous review and reference comparison on a local EffectCraft build."""

import argparse
import base64
import json
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.providers.studios.craft import call_engine, require_capability
from app.services.object_storage import sha256_file
from app.services.studios import craft_agent, craft_effectcraft_controls, craft_motion_reference, craft_review


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    reference = options.reference.resolve(strict=True)
    capability = require_capability("effectcraft")
    native = output / "control-proof.ecproj"
    params = {"mediaRoot": str(output), "media": []}
    call_engine("effectcraft", "project.new", {
        **params, "outputPath": str(native), "title": "EffectCraft control proof",
        "width": 540, "height": 960, "fps": 30, "durationMs": 3000,
    })
    draft = craft_agent.Draft(SimpleNamespace(engine="effectcraft", migration_warnings=[]), output,
        {**params, "nativePath": str(native)}, capability, SimpleNamespace(expected_revision=1), time.monotonic() + 360)
    names = {entry["name"] for entry in [*craft_agent.TOOLS, *craft_agent.SOURCE_MEDIA, *craft_agent.DIRECTION, *craft_agent.EDITORIAL]}
    draft.available_tools = {*names, craft_agent.FINISH["name"]}
    offset = 0
    pages = []
    while offset is not None:
        page = craft_effectcraft_controls.controls(capability, draft.available_tools, offset=offset)
        pages.append(page)
        offset = page["nextOffset"]
    (output / "inventory.json").write_text(json.dumps(pages, indent=2, ensure_ascii=False), encoding="utf-8")

    draft.run("run_motion_script", {"code": """
var comp=app.project.activeItem;
comp.layers.addSolid([0.08,0.1,0.16],"Background",540,960,1,3);
var subject=comp.layers.addSolid([1,0.35,0.15],"Product placeholder",140,180,1,3);
var position=subject.property("ADBE Transform Group").property("ADBE Position");
position.setValueAtTime(0,[135,480,0]);
position.setValueAtTime(2.5,[405,480,0]);
"""})
    review = craft_review.review_draft(draft, {"startSeconds": .5, "durationSeconds": 1})
    report = review["report"]
    window = report["source"].get("reviewWindow")
    if capability.get("temporalReview", {}).get("frameRange"):
        assert window and window["firstFrame"] == 15 and window["endFrameExclusive"] == 45
    assert report["visual"]["sampledSeconds"][0] == .5
    assert report["visual"]["sampledSeconds"][-1] == .866667
    (output / "review.mp4").write_bytes(review["path"].read_bytes())
    (output / "review-sheet.jpg").write_bytes(base64.b64decode(review["blocks"][1]["source"]["data"]))
    staged_reference = output / "reference.mp4"
    shutil.copyfile(reference, staged_reference)
    draft.params["media"] = [{"assetId": "comparison", "path": str(staged_reference), "mediaType": "video/mp4",
                              "checksumSha256": sha256_file(reference)}]
    comparison = craft_motion_reference.compare(draft, {"assetId": "comparison", "referenceStartSeconds": 0,
        "draftStartSeconds": .5, "offsets": [0, .4, .9]}, None)
    (output / "comparison.jpg").write_bytes(base64.b64decode(comparison[1]["source"]["data"]))
    result = {"buildId": capability["buildId"], "coverage": pages[0]["coverage"],
              "review": report, "rangeVerified": bool(window), "comparison": json.loads(comparison[0]["text"]), "paidCalls": 0}
    (output / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"build": result["buildId"], **result["coverage"]}))


if __name__ == "__main__":
    main()
