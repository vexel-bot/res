"""Replay an existing res editorial plan through Motion Canvas, without replanning.

This engineering harness reads the exact draft document and graph persisted by
the res. It does not choose scenes, create assets, call an LLM, or update the DB.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.domain.studios.motion import MotionGraphV1, evaluate_motion_graph, project_motion_graph
from app.providers.studios.motion_canvas_projection import compile_motion_canvas_composition
from app.providers.studios.motion_canvas_render import MotionCanvasGraphicsProvider
from app.services.object_storage import sha256_file


def replay(pilot_dir: Path, output: Path) -> dict:
    pilot_dir = pilot_dir.resolve(strict=True)
    plan_path = pilot_dir / "plan.json"
    database_path = pilot_dir / "pilot.sqlite"
    storage_root = (pilot_dir / "storage").resolve(strict=True)
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    document = CreativeDocumentV1.model_validate(plan["draftDocument"])
    graph = MotionGraphV1.model_validate(plan["motionGraph"])
    if plan["documentId"] != document.document_id or graph.document_id != document.document_id:
        raise ValueError("motion_canvas_replay_document_binding_conflict")
    evaluation = evaluate_motion_graph(document, graph)
    if not evaluation.eligible_for_reviewed_projection:
        raise ValueError("motion_canvas_replay_graph_ineligible")
    projection = project_motion_graph(graph, "motion_canvas", evaluation)

    bindings: dict[str, Path] = {}
    with sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True) as db:
        for asset in document.assets:
            row = db.execute(
                "SELECT storage_key, checksum_sha256 FROM library_assets WHERE id=? AND workspace_id=?",
                (asset.id, document.workspace_id),
            ).fetchone()
            if not row or not row[0] or not asset.checksum or row[1] != asset.checksum:
                raise ValueError("motion_canvas_replay_asset_binding_missing:" + asset.id)
            source = (storage_root / row[0]).resolve(strict=True)
            if not source.is_relative_to(storage_root) or sha256_file(source) != asset.checksum:
                raise ValueError("motion_canvas_replay_asset_checksum_conflict:" + asset.id)
            bindings[asset.id] = source

    manifest = compile_motion_canvas_composition(
        document, projection,
        {asset_id: {"path": str(path), "sha256": sha256_file(path),
                    "mime": next(a.media_type for a in document.assets if a.id == asset_id)}
         for asset_id, path in bindings.items()},
    )
    page = document.composition.pages[0]
    timeline = document.composition.media_timeline
    request = VideoRenderRequestV1(
        workspace_id=document.workspace_id,
        document_id=document.document_id,
        document_revision=document.revision,
        document_version=document.version,
        page_ids=[page.id],
        asset_ids=list(bindings),
        correlation_id="motion-canvas-replay-" + plan["id"],
        output={"width": page.width, "height": page.height,
                "fps": timeline.frame_rate.numerator / timeline.frame_rate.denominator,
                "audioCodec": "none"},
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    result = MotionCanvasGraphicsProvider("node", "ffmpeg", 600).render(
        document, request, bindings, output, lambda _: None, lambda: False,
        motion_projection=projection, automatic_draft=True,
    )
    renderer_receipt = result.renderer_checks["motionCanvasReceipt"]
    geometry_path = output.parent / (output.stem + ".geometry.json")
    geometry_path.write_text(
        json.dumps({"geometrySchemaVersion": renderer_receipt.get("geometrySchemaVersion"),
                    "geometrySamples": renderer_receipt.get("geometrySamples", [])}, ensure_ascii=False),
        encoding="utf-8",
    )
    receipt = {
        "schemaVersion": "res.motion-canvas-plan-replay.v1",
        "sourcePlanId": plan["id"],
        "sourcePlanRevision": plan["revision"],
        "sourcePlanSha256": hashlib.sha256(plan_bytes).hexdigest(),
        "documentId": document.document_id,
        "documentRevision": document.revision,
        "sourceAssets": {key: sha256_file(value) for key, value in bindings.items()},
        "renderer": result.provider,
        "rendererVersion": result.provider_version,
        "durationMs": result.duration_ms,
        "renderDurationMs": result.render_duration_ms,
        "outputSha256": sha256_file(output),
        "replanned": False,
        "newAssetSelection": False,
        "paidApiCalls": 0,
        "audioIncluded": False,
        "humanVisualReview": "pending",
        "layoutDiagnostics": renderer_receipt.get("layoutDiagnostics", []),
        "geometrySampleCount": len(renderer_receipt.get("geometrySamples", [])),
        "geometrySha256": sha256_file(geometry_path),
        "manifest": manifest,
    }
    (output.parent / (output.stem + ".receipt.json")).write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = replay(args.pilot_dir, args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "manifest"}, ensure_ascii=False))
