"""Real protocol HTTP + API + Rust persistence; deterministic local endpoint, no real LLM."""

import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

from PIL import Image
import requests

OUTPUT = Path(__file__).resolve().parents[2] / ".codex-runtime/craft"


def main():
    submissions = []
    command = {"id": "shape.create", "params": {"kind": "rect", "rect": [0, 0, 160, 160], "fill": "#0000ff"}}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.path == "/v1/chat/completions"
            assert self.headers["Authorization"] == "Bearer local-test-only-credential"
            context = json.loads(payload["messages"][1]["content"])
            assert "raw" not in context["project"]
            assert "shape.create" in {item["id"] for item in context["commands"]}
            submissions.append(payload["model"])
            result = {"model": "deterministic-qa", "choices": [{"finish_reason": "stop", "message": {
                "content": json.dumps({"commands": [command], "rationale": "Fixture de transporte HTTP"}),
            }}], "usage": {"prompt_tokens": 10, "completion_tokens": 20}}
            encoded = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]

    def call(method, path, body=None, expected=200, key=None, binary=False):
        response = session.request(method, "http://127.0.0.1:8018" + path, json=body,
                                   headers={"Idempotency-Key": key or str(uuid4())}, timeout=600)
        assert response.status_code == expected, (response.status_code, response.text[:1000])
        return response.content if binary else response.json()

    try:
        workspace = call("GET", "/api/v1/bootstrap")["workspaces"][0]["id"]
        connection = call("POST", "/api/v1/studios/v1/craft/llm-connections?workspace_id=" + workspace, {
            "label": "Local deterministic protocol qualification", "provider": "custom", "protocol": "openai_chat",
            "baseUrl": f"http://127.0.0.1:{server.server_port}/v1", "models": ["deterministic-qa"],
            "apiKey": "local-test-only-credential", "enabled": True, "billingMode": "local_free",
        }, expected=201)
        assert "local-test-only-credential" not in json.dumps(connection)
        document = call("POST", "/api/v1/studios/v1/documents", {
            "workspaceId": workspace, "title": "Native AI transport qualification", "contentType": "visual",
            "brief": {"objective": "Validate one HTTP request and native undo", "audience": "QA"},
            "composition": {"pages": [{"id": "page", "width": 320, "height": 320, "background": "#ffffff", "layers": []}]},
        }, expected=201)
        base = "/api/v1/studios/v1/documents/" + document["documentId"]
        migrated = call("POST", base + "/craft/migrate", {"engine": "photocraft", "expectedRevision": document["revision"]})
        before = call("POST", base + "/craft/preview", {"frame": 0}, binary=True)
        request = {"expectedRevision": migrated["revision"], "instruction": "Adicione um quadrado azul",
                   "connectionId": connection["id"], "model": "deterministic-qa"}
        key = str(uuid4())
        edited = call("POST", base + "/craft/ai-commands", request, key=key)
        replay = call("POST", base + "/craft/ai-commands", request, key=key)
        assert replay["receiptId"] == edited["receiptId"] and submissions == ["deterministic-qa"]
        outcome = call("GET", base + "/craft/ai-requests/" + key)
        assert outcome["status"] == "committed" and outcome["receipt"]["receiptId"] == edited["receiptId"]
        image_bytes = call("POST", base + "/craft/preview", {"frame": 0}, binary=True)
        with Image.open(io.BytesIO(image_bytes)) as image:
            assert image.convert("RGBA").getpixel((40, 40)) == (0, 0, 255, 255)
        undo = call("POST", base + "/craft/commands", {"expectedRevision": edited["document"]["revision"],
                    "commands": [{"id": "host.history.undo", "params": {}}]})
        assert call("POST", base + "/craft/preview", {"frame": 0}, binary=True) == before
        call("GET", base + "/craft/inspection")
        call("DELETE", f"/api/v1/studios/v1/craft/llm-connections/{connection['id']}?workspace_id={workspace}&expected_revision=1")
        result = {"realLLM": False, "endpoint": "local deterministic HTTP fixture", "nativeEngine": "photocraft",
                  "providerSubmissions": len(submissions), "receiptReplay": True, "reconciliation": True,
                  "nativePixels": True, "nativeUndo": True, "revisionAfterUndo": undo["document"]["revision"]}
        (OUTPUT / "llm-http-native-results.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
