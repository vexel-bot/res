"""Opt-in pilot: an operator grants one motion insert to a specific document."""
import json
import os
import subprocess
import sys
from pathlib import Path

from ...domain.studios.editing_resources import ResourceMetadataV1
from ...providers.studios.higgsfield import LTX
from .craft_direction import stage_material
from .editing_resources import store_resource


def enabled(document_id):
    return (os.environ.get("CLICKO_MOTION_PILOT_DOCUMENT") == str(document_id)
            and bool(os.environ.get("CLICKO_MOTION_PILOT_DIR")))


def generate(db, record, job, user, draft, manifests, args):
    if not enabled(record.id) or not draft.batches:
        raise ValueError("motion_insert_requires_a_native_draft")
    directory = Path(os.environ["CLICKO_MOTION_PILOT_DIR"]) / str(record.id)
    directory.mkdir(parents=True, exist_ok=True)
    spec = directory / "input.json"
    if not spec.exists():
        frame = args["frame"]
        if type(frame) is not int or not 0 <= frame < draft.project["durationMs"] * draft.project["fps"] / 1000:
            raise ValueError("motion_insert_frame_out_of_range")
        still = draft.directory / "motion-insert-start.png"
        draft.call("render.frame", outputPath=str(still), frame=frame, format="png", maxSide=1920)
        (directory / "frame.png").write_bytes(still.read_bytes())
        spec.write_text(json.dumps(dict(model=LTX, image_files=["frame.png"], prompt=args["prompt"],
                                        duration=8, resolution="4k", aspect_ratio="9:16",
                                        generate_audio=False)), encoding="utf8")
    source = directory / "shot.mp4"
    if not source.exists():
        runner = Path(__file__).resolve().parents[4] / "scripts/studios/higgsfield_shot.py"
        result = subprocess.run([sys.executable, str(runner), str(directory), "--max-usd", "3"],
                                capture_output=True, text=True, timeout=900)
        if result.returncode:
            raise ValueError("motion_insert_provider_failed_check_operator_connection_and_quote")
    asset = store_resource(db, record.workspace_id, "Motion Higgsfield " + str(record.id), source,
                           ResourceMetadataV1(kind="video", description="Animação do quadro original da Clicko",
                                              usageEvidence="Filme produzido a partir do quadro original deste projeto."), user.id)
    receipt = json.loads((directory / "receipt.json").read_text())
    info = dict(assetId=asset.id, title=asset.title, mediaType=asset.media_type,
                requestId=receipt["receipt"]["request_id"], provider="higgsfield", model=LTX)
    return stage_material(db, job, draft, manifests, asset, "higgsfield-motion", info)
