"""Read-only production diagnosis using isolated native copies and one rendered frame."""
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True)
    parser.add_argument("--layer", required=True)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime = ROOT / ".codex-runtime/clicko-dev"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import NativeEditorStateV1
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.models import CreativeDocument, StudioGenerationJob
    from app.providers.studios.craft import require_capability
    from app.services.studios import craft, craft_drafts
    from app.services.studios.craft_agent import Draft
    from app.services.studios.craft_direction import media_ids

    out = args.output.resolve()
    if out.exists():
        raise ValueError("Existing qualification is preserved; choose a new directory.")
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, args.job)
        if not job or job.status == "running":
            raise ValueError("Stop the director at a confirmed response first.")
        before = json.dumps(job.result_payload, sort_keys=True)
        record = db.get(CreativeDocument, job.document_id)
        revision = record.revision
        native = NativeEditorStateV1.model_validate(job.request_payload["nativeEditorState"])
        capability = require_capability(native.engine)
        out.mkdir(parents=True)
        report = {"jobId": job.id, "draftBatch": job.result_payload["draft"]["batches"], "frame": args.frame,
                  "nativeChecksumSha256": job.result_payload["draft"]["checksumSha256"],
                  "productionEdits": 0, "llmCalls": 0, "diagnosticCopiesModified": [], "formalQualityAssessment": False}
        with craft.workspace_files(db, record, native, extra_asset_ids=media_ids(job)) as (directory, params, _):
            params, checkpoint = craft_drafts.restore(job, native.engine, directory, params)
            original_path = Path(params["nativePath"])
            original = json.loads(original_path.read_text(encoding="utf-8"))
            request = CraftAICommandRequestV1(expectedRevision=record.revision, instruction="Isolated technical ablation, never a replacement edit")
            crops = []
            for variant in ("unchanged", "source-only", "without-exposure", "without-mask"):
                value = copy.deepcopy(original)
                layers = value["items"][str(value["clickoActiveComp"])]["kind"]["layers"]
                target = next(l for l in layers if l["name"] == args.layer)
                effects = next(g for g in target["props"]["children"] if g["match"] == "effects")
                masks = next(g for g in target["props"]["children"] if g["match"] == "masks")
                if variant == "source-only":
                    for layer in layers:
                        layer["switches"]["video"] = layer["id"] == target["id"]
                    target["switches"]["effects"] = False
                    for group in masks["children"]:
                        group["enabled"] = False
                elif variant == "without-exposure":
                    effect = next(g for g in effects["children"] if g["name"] == "Exposure")
                    effect["enabled"] = False
                elif variant == "without-mask":
                    for group in masks["children"]:
                        group["enabled"] = False
                path = directory / (variant + ".ecproj")
                path.write_text(json.dumps(value), encoding="utf-8")
                draft = Draft(native, directory, {**params, "nativePath": str(path)}, capability, request, float("inf"))
                draft.batches = checkpoint["batches"]
                frame = directory / (variant + ".png")
                draft.call("render.frame", outputPath=str(frame), frame=args.frame, format="png", maxSide=1920)
                shutil.copy2(frame, out / frame.name)
                with Image.open(frame) as image:
                    box = (int(image.width * .35), int(image.height * .45), int(image.width * .75), int(image.height * .85))
                    crops.append((variant, image.crop(box)))
                if variant == "unchanged":
                    blocks = draft.run("preview_frame", {"frame": args.frame, "maximumSide": 1920, "crop": [.35, .45, .4, .4]})
                    (out / "detail-tool-submitted.jpg").write_bytes(base64.b64decode(blocks[0]["source"]["data"]))
                    report["detailToolObservation"] = json.loads(blocks[1]["text"])
                else:
                    report["diagnosticCopiesModified"].append(variant)
            sheet = Image.new("RGB", (sum(im.width for _, im in crops), max(im.height for _, im in crops) + 25), "#111111")
            draw = ImageDraw.Draw(sheet)
            x = 0
            for label, image in crops:
                sheet.paste(image, (x, 25)); draw.text((x + 5, 5), label, fill="white"); x += image.width
            sheet.save(out / "ablation-comparison.jpg", quality=95)
            report["nativePreserved"] = hashlib.sha256(original_path.read_bytes()).hexdigest() == checkpoint["checksumSha256"]
        db.refresh(job); db.refresh(record)
        report.update(jobPreserved=json.dumps(job.result_payload, sort_keys=True) == before, documentPreserved=record.revision == revision,
                      status="measured_requires_visual_interpretation")
        assert all(report[k] for k in ("nativePreserved", "jobPreserved", "documentPreserved"))
        (out / "qualification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))


if __name__ == "__main__":
    main()
