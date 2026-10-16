"""Create a real, isolated local API project for inspecting the editor in the browser."""
import json
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "tmp" / "editor-kernel-browser-20261002"
EVIDENCE = ROOT / "docs" / "studios" / "research" / "editor-oss-20261002" / "editor-browser"
ORIGIN = "http://127.0.0.1:8000"
token = ""


def api(path, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request(ORIGIN + path, headers=headers,
                                     data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"local_api:{exc.code}:{exc.read().decode()}") from None


PRIVATE.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)
state_path = PRIVATE / "browser-state.json"
if state_path.exists():
    state = json.loads(state_path.read_text(encoding="utf-8"))
    values = {v["name"]: v["value"] for v in state["origins"][0]["localStorage"]}
    token = values["nexus_access_token"]
    if "--capture-inspection" in sys.argv:
        fixture = json.loads((EVIDENCE / "fixture.json").read_text(encoding="utf-8"))
        inspection = api(f"/api/v1/studios/v1/documents/{fixture['documentId']}/editor/inspection")
        (EVIDENCE / "after-browser.json").write_text(json.dumps({"inspection": inspection,
            "scope": "canonical-state-after-browser-edit", "humanReview": "pending"},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "captured", "revision": inspection["document"]["revision"]}))
        sys.exit(0)
    print(json.dumps({"status": "existing_fixture", "statePath": str(state_path)}))
    sys.exit(0)
account = api("/api/v1/auth/register", {"email": f"editor-kernel-{uuid4().hex[:12]}@example.com",
               "name": "Validação local do editor", "password": secrets.token_urlsafe(32),
               "workspaceName": "Laboratório do núcleo de edição 02-10"})
token = account["accessToken"]
workspace_id = api("/api/v1/bootstrap")["workspaces"][0]["id"]
document = api("/api/v1/studios/v1/documents", {
    "workspaceId": workspace_id, "title": "Comandos canônicos — estudo local", "contentType": "video",
    "brief": {"objective": "Inspecionar o movimento e salvar ajustes rastreáveis", "audience": "Equipe do editor"},
    "composition": {"pages": [{"id": "editor-page", "width": 320, "height": 320, "safeArea": 16}]},
})
plan = api(f"/api/v1/studios/v1/documents/{document['documentId']}/editing-plans", {
    "expectedDocumentRevision": 1, "intent": {"objective": "Inspecionar uma acomodação de forma original"},
    "scenes": [{"id": "settle", "purpose": "A forma se acomoda, preservando identidade", "durationFrames": 90,
                "background": "#10212c", "verification": ["Movimento contínuo e pausa final"], "elements": [
                    {"id": "hero", "kind": "shape", "purpose": "Mostrar a acomodação", "x": 120, "y": 130,
                     "width": 80, "height": 80, "durationFrames": 90, "fill": "#32cde5", "visualRole": "hero"},
                    {"id": "title", "kind": "text", "purpose": "Identificar o estudo", "x": 24, "y": 24,
                     "width": 272, "height": 70, "durationFrames": 90, "fontSize": 24,
                     "text": "Estudo de movimento", "visualRole": "text"}],
                "motionRecipes": [{"id": "settle-motion", "technique": "motion_choreography", "targetIds": ["hero"],
                    "startFrame": 0, "endFrameExclusive": 90, "intent": "Acomodar e permanecer",
                    "continuityAnchor": "Mesma forma e cor", "verification": ["Sem salto na chegada"],
                    "parameters": {"pivot": [.5, .5], "tracks": [{"targetId": "hero", "property": "y",
                        "keyframes": [{"frame": 0, "value": 48, "curve": [.22, .75, .25, 1]},
                                      {"frame": 24, "value": 0}, {"frame": 89, "value": 0}]}]}}]}],
}, key="editor-kernel-browser-plan")
if plan["status"] != "ready":
    raise RuntimeError("fixture_plan_not_ready:" + json.dumps(plan["blockers"]))
document = api(f"/api/v1/studios/v1/documents/{document['documentId']}/editing-plans/{plan['id']}/apply",
               {"expectedPlanRevision": plan["revision"]})
inspection = api(f"/api/v1/studios/v1/documents/{document['documentId']}/editor/inspection")
state_path.write_text(json.dumps({"cookies": [], "origins": [{"origin": "http://127.0.0.1:3000", "localStorage": [
    {"name": "nexus_access_token", "value": token}, {"name": "clicko:active-workspace", "value": workspace_id}]}]}),
    encoding="utf-8")
(EVIDENCE / "fixture.json").write_text(json.dumps({"workspaceId": workspace_id, "documentId": document["documentId"],
    "inspection": inspection, "scope": "real-local-api-isolated-test-workspace", "humanReview": "pending"},
    ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": "created", "documentId": document["documentId"],
                  "statePath": str(state_path)}, ensure_ascii=False))
