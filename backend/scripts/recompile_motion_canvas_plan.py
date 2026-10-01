"""Recompile a persisted res direction with the current semantic components.

This harness keeps the director's stored direction and materials. It does not
invent scenes, select assets, call an LLM, or mutate the source pilot. The
result is a versioned derived composition that can be compared with an older
render from the same plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.domain.studios.motion import MotionGraphV1, evaluate_motion_graph, project_motion_graph
from app.providers.studios.motion_canvas_projection import compile_motion_canvas_composition
from app.providers.studios.motion_canvas_render import MotionCanvasGraphicsProvider
from app.services.object_storage import sha256_file
from app.services.studios.scene_compiler import compile_scenes, current_execution_versions


def _asset_bindings(pilot_dir: Path, document: CreativeDocumentV1) -> dict[str, Path]:
    database_path = pilot_dir / "pilot.sqlite"
    storage_root = (pilot_dir / "storage").resolve(strict=True)
    result: dict[str, Path] = {}
    with sqlite3.connect(f"file:{database_path.resolve().as_posix()}?mode=ro", uri=True) as db:
        for asset in document.assets:
            row = db.execute(
                "SELECT storage_key, checksum_sha256 FROM library_assets WHERE id=? AND workspace_id=?",
                (asset.id, document.workspace_id),
            ).fetchone()
            if not row or row[1] != asset.checksum or not asset.checksum:
                raise ValueError("motion_canvas_recompile_asset_binding_missing:" + asset.id)
            source = (storage_root / row[0]).resolve(strict=True)
            if not source.is_relative_to(storage_root) or sha256_file(source) != asset.checksum:
                raise ValueError("motion_canvas_recompile_asset_checksum_conflict:" + asset.id)
            result[asset.id] = source
    return result


def _normalize_legacy_direction(payload: dict) -> dict:
    """Make pre-v2.20 persisted directions readable without redesigning them.

    Older pilots used an empty path element as a generic accent and allowed a
    scene keyword to be supplied without a bound text span.  The current
    contracts correctly reject both cases for new production.  A recompile of
    a historical artifact must still be possible, so we remove only the
    invalid legacy claims and leave its scenes, timings and asset choices
    intact.  New API requests never pass through this function.
    """
    import copy

    result = copy.deepcopy(payload)
    for scene in result.get("scenes", []):
        for element in scene.get("elements", []):
            points = element.get("points") or []
            if element.get("pathMode") in {"polyline", "quadratic"} and not points:
                # Persisted V2 elements inherited the default path mode even
                # when they were ordinary rectangles. Keep the field valid
                # while giving the unused path a degenerate geometry.
                element["points"] = [{"x": 0.0, "y": 0.0}, {"x": 0.0, "y": 0.0}]
        for cue in scene.get("keywordCues", []):
            # Legacy cues were scene annotations, not source-bound spans. The
            # legacy policy permits materializing them as their own layer.
            cue["sourceExcerpt"] = cue.get("text", "")
    return result


def _visual_strategy_fingerprint(direction: dict) -> str:
    """Fingerprint the director's visual language, excluding layout math.

    A renderer swap or a compiler fit can change pixels while leaving the
    editorial strategy unchanged. Recording this separately prevents a new
    MP4 from being reported as a creative improvement when it only reused the
    same icon/path plan.
    """
    strategy = {
        "artDirection": direction.get("artDirection"),
        "scenes": [],
    }
    for scene in direction.get("scenes", []):
        strategy["scenes"].append({
            "id": scene.get("id"),
            "family": scene.get("family"),
            "compositions": [
                {
                    key: value
                    for key, value in composition.items()
                    if key in {"family", "purpose", "targetIds", "materialIds", "formatNames"}
                }
                for composition in scene.get("compositions", [])
            ],
            "elements": [
                {
                    key: element.get(key)
                    for key in (
                        "kind", "assetId", "text", "visualRole", "contentPartId",
                        "contentIdentity", "purpose", "pathMode",
                    )
                }
                for element in scene.get("elements", [])
            ],
            "materialNeeds": [
                {
                    key: need.get(key)
                    for key in ("kind", "required", "sourceClass", "purpose", "targetId")
                }
                for need in scene.get("materialNeeds", [])
            ],
        })
    canonical = json.dumps(strategy, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def recompile(pilot_dir: Path, output: Path) -> dict:
    pilot_dir = pilot_dir.resolve(strict=True)
    source_plan_path = pilot_dir / "plan.json"
    source_bytes = source_plan_path.read_bytes()
    source = json.loads(source_bytes)
    source_strategy_fingerprint = _visual_strategy_fingerprint(source["direction"])
    document = CreativeDocumentV1.model_validate(source["draftDocument"])
    # Historical pilots were created before the canonical-content assertion
    # gate. Keep their direction readable for a versioned recompile while
    # leaving the stored plan untouched; new production still uses the strict
    # policy at the API boundary.
    direction_payload = _normalize_legacy_direction(source["direction"])
    direction_payload["semanticVerificationPolicy"] = "legacy_execution_v1"
    direction_payload["executionVersions"] = current_execution_versions().model_dump(mode="json", by_alias=True)
    direction = ContextualPlanRequestV2.model_validate(direction_payload)
    derived_strategy_fingerprint = _visual_strategy_fingerprint(
        direction.model_dump(mode="json", by_alias=True)
    )
    if direction.expected_document_revision != document.revision:
        raise ValueError("motion_canvas_recompile_document_revision_conflict")
    derived_document, graph, operations, manifest = compile_scenes(
        document, direction, user_id="recompile-motion-canvas", plan_id=source["id"] + "-recompiled"
    )
    evaluation = evaluate_motion_graph(derived_document, graph)
    if not evaluation.eligible_for_reviewed_projection:
        raise ValueError("motion_canvas_recompile_graph_ineligible")
    projection = project_motion_graph(graph, "motion_canvas", evaluation)
    bindings = _asset_bindings(pilot_dir, document)
    binding_payload = {
        asset_id: {
            "path": str(path),
            "sha256": sha256_file(path),
            "mime": next(item.media_type for item in document.assets if item.id == asset_id),
        }
        for asset_id, path in bindings.items()
    }
    executable_manifest = compile_motion_canvas_composition(derived_document, projection, binding_payload)
    page = derived_document.composition.pages[0]
    timeline = derived_document.composition.media_timeline
    assert timeline is not None
    request = VideoRenderRequestV1(
        workspace_id=derived_document.workspace_id,
        document_id=derived_document.document_id,
        document_revision=derived_document.revision,
        document_version=derived_document.version,
        page_ids=[page.id],
        asset_ids=list(bindings),
        correlation_id="motion-canvas-recompile-" + source["id"],
        output={
            "width": page.width,
            "height": page.height,
            "fps": timeline.frame_rate.numerator / timeline.frame_rate.denominator,
            "audioCodec": "none",
        },
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    result = MotionCanvasGraphicsProvider("node", "ffmpeg", 600).render(
        derived_document,
        request,
        bindings,
        output,
        lambda _: None,
        lambda: False,
        motion_projection=projection,
        automatic_draft=True,
    )
    receipt = {
        "schemaVersion": "res.motion-canvas-plan-recompile.v1",
        "sourcePlanId": source["id"],
        "sourcePlanRevision": source["revision"],
        "sourcePlanSha256": hashlib.sha256(source_bytes).hexdigest(),
        "derivedDirectionSha256": hashlib.sha256(
            json.dumps(direction.model_dump(mode="json", by_alias=True), sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "compilerVersion": manifest["compilerVersion"],
        "componentLibraryVersion": manifest["componentLibraryVersion"],
        "runtimeVersion": manifest["runtimeVersion"],
        "documentId": derived_document.document_id,
        "documentRevision": derived_document.revision,
        "sourceAssets": {key: sha256_file(value) for key, value in bindings.items()},
        "renderer": result.provider,
        "rendererVersion": result.provider_version,
        "durationMs": result.duration_ms,
        "renderDurationMs": result.render_duration_ms,
        "outputSha256": sha256_file(output),
        "replanned": False,
        "recompiled": True,
        "newAssetSelection": False,
        "sourceVisualStrategyFingerprint": source_strategy_fingerprint,
        "derivedVisualStrategyFingerprint": derived_strategy_fingerprint,
        "visualStrategyChanged": source_strategy_fingerprint != derived_strategy_fingerprint,
        "paidApiCalls": 0,
        "audioIncluded": False,
        "humanVisualReview": "pending",
        "operationCount": len(operations),
        "rendererChecks": result.renderer_checks,
        "manifest": executable_manifest,
    }
    (output.parent / (output.stem + ".receipt.json")).write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output.parent / (output.stem + ".direction.json")).write_text(
        json.dumps(direction.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = recompile(args.pilot_dir, args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "manifest"}, ensure_ascii=False))
