"""Create an isolated actual-API project; private login data stays in ignored tmp."""
# ruff: noqa: E402
import ast
import hashlib
import json
import secrets
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.motion_recipes import TemporalExposureV1

PRIVATE = ROOT / "tmp/editor-spatial-inspection-20261003"
EVIDENCE = ROOT / "docs/studios/research/editor-oss-20261002/spatial-inspection-browser"
PRIVATE.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)
credentials_path = PRIVATE / "credentials.json"
token = ""


def api(path, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request("http://127.0.0.1:8000" + path, headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"local_api:{exc.code}:{exc.read().decode()}") from None


if credentials_path.exists():
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    token = api("/api/v1/auth/login", credentials)["accessToken"]
    fixture = json.loads((EVIDENCE / "fixture.json").read_text(encoding="utf-8"))
    if "--run-job" in sys.argv:
        from app.database import SessionLocal
        from app.models import LibraryAsset, StudioGenerationJob
        from app.providers.studios.heavy_media_lease import _active, _read, lease_path
        from app.services.object_storage import get_object_storage
        from app.services.studios.jobs import execute_job_once

        jobs = api("/api/v1/studios/v1/jobs?workspace_id=" + fixture["workspaceId"]
                   + "&document_id=" + fixture["documentId"] + "&job_type=video_render&limit=1")
        assert isinstance(jobs, list) and len(jobs) == 1, "UI must submit the job first"
        with SessionLocal() as db:
            job = db.get(StudioGenerationJob, jobs[0]["id"])
            assert job and job.workspace_id == fixture["workspaceId"] and job.job_type == "video_render"
            request = job.request_payload["renderRequest"]
            snapshot = job.request_payload["documentSnapshot"]
            assert job.provider == "remotion.contextual-v2" and request["output"]["quality"] == "draft"
            assert snapshot["documentId"] == fixture["documentId"]
            if job.status in {"queued", "retrying"}:
                assert not _active(_read(lease_path())), "A live operation owns heavy-media capacity"
                execute_job_once(db, job)
                db.refresh(job)
            assert job.status == "succeeded", {"status": job.status, "error": job.error_message}
            result = job.result_payload
            assert result["documentRevision"] == snapshot["revision"]
            assert result["providerVersion"] == "4.0.527-native.12"
            assert result["qualityEvaluation"]["status"] == "passed"
            asset = db.get(LibraryAsset, result["artifact"]["assetId"])
            output = EVIDENCE / f"preview-revision-{snapshot['revision']}.mp4"
            with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
                shutil.copy2(source, output)
            assert hashlib.sha256(output.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
            (EVIDENCE / f"render-revision-{snapshot['revision']}.json").write_text(json.dumps({
                "scope": "actual_UI_submitted_job_existing_pipeline_no_mock",
                "renderResult": result, "renderMetadata": asset.object_metadata,
                "requestOutput": request["output"], "snapshotRevision": snapshot["revision"],
                "humanReview": "pending"}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"status": "succeeded", "revision": snapshot["revision"], "checksum": result["artifact"]["checksumSha256"]}))
    elif "--capture" in sys.argv:
        for frame in [0, 1, 4]:
            inspection = api(f"/api/v1/studios/v1/documents/{fixture['documentId']}/editor/inspection?frame={frame}")
            (EVIDENCE / f"inspection-frame-{frame}.json").write_text(json.dumps(inspection, ensure_ascii=False, indent=2),
                                                                   encoding="utf-8")
        print(json.dumps({"status": "captured", "revision": inspection["document"]["revision"]}))
    else:
        print(json.dumps({"status": "existing", "documentId": fixture["documentId"]}))
    sys.exit(0)

credentials = {"email": f"spatial-inspection-{uuid4().hex[:12]}@example.com", "password": secrets.token_urlsafe(32)}
account = api("/api/v1/auth/register", {**credentials, "name": "Inspeção local de efeitos",
                                       "workspaceName": "Laboratório espacial 03-10"})
token = account["accessToken"]
credentials_path.write_text(json.dumps(credentials), encoding="utf-8")
workspace = api("/api/v1/bootstrap")["workspaces"][0]["id"]
document = api("/api/v1/studios/v1/documents", {
    "workspaceId": workspace, "title": "Efeitos espaciais — inspeção real", "contentType": "video",
    "brief": {"objective": "Conferir autoria e avaliação de sombra e desfoque", "audience": "Equipe do editor"},
    "composition": {"pages": [{"id": "spatial-page", "width": 320, "height": 320, "safeArea": 0}]}})

# Reuse exact pure fixture definitions; never import test modules or a test database.
namespace = {"ContextualPlanRequestV2": ContextualPlanRequestV2, "TemporalExposureV1": TemporalExposureV1}
sources = {}
for relative, names in [("backend/tests/test_remotion_native.py", {"native_direction"}),
                        ("backend/tests/test_spatial_effects_render.py", {"BOXES", "SHADOWS", "spatial_direction"})]:
    source = (ROOT / relative).read_bytes()
    tree = ast.parse(source)
    selected = [node for node in tree.body if (isinstance(node, ast.FunctionDef) and node.name in names)
                or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets))]
    exec(compile(ast.Module(body=selected, type_ignores=[]), relative, "exec"), namespace)
    sources[relative] = hashlib.sha256(source).hexdigest()
direction = namespace["spatial_direction"]("exposure")
scene = direction["scenes"][0]
# Identity choreography supplies an actual granular command to test later in this same scene.
scene["motionRecipes"].append({"id": "inspect-sharp", "technique": "motion_choreography", "targetIds": ["sharp"],
    "startFrame": 0, "endFrameExclusive": 30, "intent": "Conferir ajuste rastreável no inspetor",
    "continuityAnchor": "Mesma forma branca", "verification": ["Revisão e render correspondem"],
    "parameters": {"pivot": [.5, .5], "tracks": [{"targetId": "sharp", "property": "x",
        "keyframes": [{"frame": 0, "value": 0}, {"frame": 29, "value": 0}]}]}})
plan = api(f"/api/v1/studios/v1/documents/{document['documentId']}/editing-plans", direction,
           key="spatial-inspection-plan")
assert plan["status"] == "ready", plan["blockers"]
document = api(f"/api/v1/studios/v1/documents/{document['documentId']}/editing-plans/{plan['id']}/apply",
               {"expectedPlanRevision": plan["revision"]})
inspection = api(f"/api/v1/studios/v1/documents/{document['documentId']}/editor/inspection?frame=0")
(EVIDENCE / "fixture.json").write_text(json.dumps({"scope": "real_local_API_isolated_workspace_no_UI_mock",
    "documentId": document["documentId"], "workspaceId": workspace, "planId": plan["id"],
    "inspection": inspection, "sources": sources, "humanReview": "pending"}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": "created", "documentId": document["documentId"], "workspaceId": workspace}))
