"""Compare an unchanged native checkpoint's previews with its cached video; no LLM or edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT / ".codex-runtime/clicko-dev")
    parser.add_argument("--job", required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--frames", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime, output = args.runtime.resolve(), args.output.resolve()
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
                      STORAGE_PATH=str(runtime / "studios/uploads"))
    sys.path.insert(0, str(ROOT / "backend"))
    from app.database import SessionLocal
    from app.domain.studios.contracts import NativeEditorStateV1
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.models import CreativeDocument, StudioGenerationJob
    from app.providers.studios.craft import require_capability
    from app.providers.studios.media_runtime import resolve_tool
    from app.services.studios import craft, craft_drafts
    from app.services.studios.craft_agent import Draft
    from app.services.studios.craft_direction import media_ids

    if output.exists():
        raise ValueError("Use a new qualification directory; existing results are preserved.")
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, args.job)
        if not job or job.status == "running":
            raise ValueError("Stop the director at a confirmed response before qualification.")
        result_before = json.dumps(job.result_payload, sort_keys=True)
        record = db.get(CreativeDocument, job.document_id)
        revision = record.revision
        state = NativeEditorStateV1.model_validate(job.request_payload["nativeEditorState"])
        capability = require_capability(state.engine)
        checkpoint = job.result_payload["draft"]
        identity = hashlib.sha256(f"{state.engine}:{capability['buildId']}:{checkpoint['batches']}:{checkpoint['checksumSha256']}".encode()).hexdigest()
        if args.video.name != f"draft-{identity}.mp4" or not args.video.is_file():
            raise ValueError("Video must match the current checkpoint's build, batch and native checksum.")
        output.mkdir(parents=True)
        video_sha = sha(args.video)
        report = {"status": "measuring", "jobId": job.id, "buildId": capability["buildId"],
                  "draftBatch": checkpoint["batches"], "nativeChecksumSha256": checkpoint["checksumSha256"],
                  "videoChecksumSha256": video_sha, "llmCalls": 0, "nativeEdits": 0, "frames": []}
        with craft_drafts.bundle(db, record, job) as bundle:
            shutil.copyfile(bundle, output / "checkpoint-editavel.zip")
        with craft.workspace_files(db, record, state, extra_asset_ids=media_ids(job)) as (directory, params, _):
            params, restored = craft_drafts.restore(job, state.engine, directory, params)
            draft = Draft(state, directory, params, capability,
                CraftAICommandRequestV1(expectedRevision=record.revision, instruction="Read-only preview/video parity qualification"), float("inf"))
            draft.batches = restored["batches"]
            frame_count = round(draft.project["durationMs"] / 1000 * draft.project["fps"])
            for frame in args.frames:
                if not 0 <= frame < frame_count:
                    raise ValueError("Frame outside the checkpoint.")
                paths = {}
                for side in (720, 1920):
                    target = directory / f"native-{frame}-{side}.png"
                    draft.call("render.frame", frame=frame, outputPath=str(target), format="png", maxSide=side)
                    paths[str(side)] = output / target.name
                    shutil.copyfile(target, paths[str(side)])
                decoded = output / f"video-{frame}.png"
                subprocess.run([resolve_tool("ffmpeg"), "-v", "error", "-nostdin", "-i", str(args.video),
                    "-vf", f"select=eq(n\\,{frame})", "-frames:v", "1", "-threads", "1", str(decoded)],
                    check=True, capture_output=True, timeout=60)
                native = Image.open(paths["1920"]).convert("RGB")
                video = Image.open(decoded).convert("RGB")
                if native.size != video.size:
                    raise ValueError("Preview and decoded video dimensions differ.")
                difference = ImageChops.difference(native, video)
                difference.save(output / f"difference-{frame}.png")
                values = ImageStat.Stat(difference)
                sheet = Image.new("RGB", (native.width * 3, native.height + 30), "#111111")
                draw = ImageDraw.Draw(sheet)
                for i, (label, im) in enumerate((("Native PNG", native), ("Decoded MP4", video), ("Absolute RGB difference", difference))):
                    sheet.paste(im, (i * native.width, 30)); draw.text((i * native.width + 8, 8), label, fill="white")
                sheet.save(output / f"comparison-{frame}.jpg", quality=95)
                report["frames"].append({"frame": frame, "timeSeconds": frame / draft.project["fps"],
                    "meanAbsoluteRgbDifference": values.mean, "rmsRgbDifference": values.rms,
                    "nativePreviewSha256": sha(paths["1920"]), "decodedVideoSha256": sha(decoded)})
            report["nativePreserved"] = sha(Path(draft.params["nativePath"])) == checkpoint["checksumSha256"]
        db.refresh(job); db.refresh(record)
        report.update(status="measured_requires_visual_interpretation", videoPreserved=sha(args.video) == video_sha,
                      jobPreserved=json.dumps(job.result_payload, sort_keys=True) == result_before,
                      documentPreserved=record.revision == revision,
                      interpretation="Lossy encoding and RGB/YUV conversion create differences. Metrics alone do not establish aesthetic quality or full-sequence parity.")
        assert all(report[k] for k in ("nativePreserved", "videoPreserved", "jobPreserved", "documentPreserved"))
        (output / "qualification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
