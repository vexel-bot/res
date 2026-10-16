"""Extend only the isolated real-API workspace; UI submits the actual render."""
# ruff: noqa: E402
import ast
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.motion_recipes import TemporalExposureV1

OLD = ROOT / "docs/studios/research/editor-oss-20261002/temporal-matte-inspection-browser"
OUT = ROOT / "docs/studios/research/editor-oss-20261002/temporal-matte-composition-preview"
fixture = json.loads((OLD / "fixture.json").read_text(encoding="utf-8"))
credentials = json.loads((ROOT / "tmp/editor-temporal-matte-inspection-native14/credentials.json").read_text(encoding="utf-8"))
token = ""


def api(path, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request("http://127.0.0.1:8000" + path, headers=headers,
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


token = api("/api/v1/auth/login", credentials)["accessToken"]
base = f"/api/v1/studios/v1/documents/{fixture['documentId']}"
if "--prepare-rig" in sys.argv:
    assert not (OUT / "rig-plan.json").exists(), "Do not repeat the applied plan"
    inspection = api(base + "/editor/inspection?frame=0")
    assert inspection["document"]["revision"] == 3
    assert inspection["document"]["workspaceId"] == fixture["workspaceId"]
    namespace = {"ContextualPlanRequestV2": ContextualPlanRequestV2, "TemporalExposureV1": TemporalExposureV1,
                 "Image": Image, "ImageDraw": ImageDraw}
    for relative, names in [("backend/tests/test_remotion_native.py", {"native_direction"}),
                           ("backend/tests/temporal_matte_kernel_diagnostic.py", {"GEOMETRY", "direction_for"})]:
        tree = ast.parse((ROOT / relative).read_bytes())
        selected = [node for node in tree.body if (isinstance(node, ast.FunctionDef) and node.name in names)
            or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets))]
        exec(compile(ast.Module(body=selected, type_ignores=[]), relative, "exec"), namespace)
    direction = namespace["direction_for"](fixture["matteAssetId"], "rig", "external", "alpha", True)
    direction["expectedDocumentRevision"] = 3
    hero = next(r for r in direction["scenes"][0]["motionRecipes"] if r["id"] == "hero-move")
    next(t for t in hero["parameters"]["tracks"] if t["property"] == "x")["keyframes"][0]["value"] = 12
    ContextualPlanRequestV2.model_validate(direction)
    plan = api(base + "/editing-plans", direction, key="matte-native14-rig-composition-preview")
    assert plan["status"] == "ready", plan["blockers"]
    document = api(base + f"/editing-plans/{plan['id']}/apply", {"expectedPlanRevision": plan["revision"]})
    assert document["revision"] == 4
    (OUT / "rig-plan.json").write_text(json.dumps({"scope": "real_API_typed_plan_not_UI_command",
        "fixture": fixture, "request": direction, "plan": plan, "document": document}, ensure_ascii=False, indent=2), encoding="utf-8")
    for frame in [0, 4, 10, 15]:
        observed = api(base + f"/editor/inspection?frame={frame}")
        assert observed["document"]["revision"] == 4
        (OUT / f"inspection-revision-4-frame-{frame}.json").write_text(json.dumps(observed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "applied", "revision": 4, "exposureTarget": "rig"}))
else:
    jobs = api("/api/v1/studios/v1/jobs?workspace_id=" + fixture["workspaceId"]
        + "&document_id=" + fixture["documentId"] + "&job_type=video_render&limit=1")
    assert len(jobs) == 1
    if "--collect" not in sys.argv:
        print(json.dumps({"id": jobs[0]["id"], "status": jobs[0]["status"]}))
        sys.exit(0)
    from app.database import SessionLocal
    from app.models import LibraryAsset, StudioGenerationJob
    from app.services.object_storage import get_object_storage
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, jobs[0]["id"])
        snapshot = job.request_payload["documentSnapshot"]
        assert job.workspace_id == fixture["workspaceId"] and snapshot["revision"] == 4, "UI must submit revision 4"
        if job.status in {"queued", "running", "retrying"}:
            print(json.dumps({"id": job.id, "status": job.status, "action": "wait_for_existing_worker"}))
            sys.exit(0)
        assert job.status == "succeeded", job.error_message
        result = job.result_payload
        assert result["documentRevision"] == 4 and result["providerVersion"] == "4.0.527-native.14"
        assert result["qualityEvaluation"]["status"] == "passed"
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        target = OUT / "preview-revision-4.mp4"
        assert not target.exists(), "Preserve retained MP4"
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
            shutil.copy2(source, target)
        assert hashlib.sha256(target.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
        (OUT / "render-revision-4.json").write_text(json.dumps({"scope": "actual_UI_submitted_job_existing_worker",
            "renderResult": result, "renderMetadata": asset.object_metadata, "snapshot": snapshot,
            "requestOutput": job.request_payload["renderRequest"]["output"], "humanReview": "pending"},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "collected", "revision": 4, "checksum": result["artifact"]["checksumSha256"]}))
