"""One bounded Opus run per arm over the same native EffectCraft project."""
import argparse
import base64
import hashlib
import io
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

MODEL = "claude-opus-5-5"
BUDGET = 1.50
KEY = "orbita-reference-mcp-20261112-clicko-opus"
ROOT = Path(__file__).resolve().parents[2]
MCP_TOOLS = {"command_list", "command_run", "command_batch", "doc_inspect", "render_preview",
             "get_comp", "get_layer", "list_layers"}
SYSTEM = ("You are the director and editor of an editable vertical advertisement. "
          "Use the native EffectCraft MCP tools. Inspect the active comp and use command_run with "
          "script.run and params.code to build multi-layer edits when helpful. "
          "The timeline initially contains each material as an independent layer. "
          "Use the source durations and inventory. Review actual renders and revise. "
          "For delivery call finish_project. Respond in Brazilian Portuguese.")


def write(path, result):
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


class NativeMcp:
    def __init__(self, directory):
        self.directory = directory
        self.responses = queue.Queue()
        self.serial = 0
        self.error = (directory / "mcp-stderr.log").open("w", encoding="utf-8")
        portable = os.environ.get("CLICKO_BENCHMARK_MCP_BINARY")
        distribution = os.environ.get("CLICKO_BENCHMARK_MCP_DIST")
        self.native_directory = directory.as_posix() if portable else "/job"
        binary_mount = (["--mount", f"type=bind,source={distribution},target=/upstream,readonly"] if distribution
                        else ["--mount", "type=volume,source=clicko-craft-target,target=/target,readonly"])
        cli = "/upstream/effectcraft-cli" if distribution else "/target/effect/release/effectcraft-cli"
        executable = [portable] if portable else [
            "docker", "run", "--rm", "-i", "--network", "none", "--memory", "2g", "--cpus", "2",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", *binary_mount,
            "--mount", f"type=bind,source={directory},target=/job",
            "-w", "/job", "--entrypoint", cli, "clicko-craft-runtime:local",
        ]
        confinement = ["--automation-read-root", self.native_directory, "--automation-write-root", self.native_directory] if portable else []
        self.process = subprocess.Popen([*executable, "mcp", "--project", self.native_path("001.ecproj"), *confinement],
            cwd=directory, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.error, text=True, encoding="utf-8")

        def receive():
            for line in self.process.stdout:
                self.responses.put(json.loads(line))
            self.responses.put(None)

        threading.Thread(target=receive, daemon=True).start()

    def __enter__(self):
        return self

    def native_path(self, filename):
        return f"{self.native_directory}/{filename}"

    def __exit__(self, *_):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.error.close()

    def rpc(self, method, params, timeout=130):
        self.serial += 1
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.serial, "method": method,
                                            "params": params}, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        while True:
            result = self.responses.get(timeout=timeout)
            if result is None:
                raise RuntimeError("Native MCP terminated. See mcp-stderr.log.")
            if result.get("id") == self.serial:
                if "error" in result:
                    raise RuntimeError(str(result["error"]))
                return result["result"]

    def call(self, name, params=None, timeout=130):
        return self.rpc("tools/call", {"name": name, "arguments": params or {}}, timeout)

    def command(self, name, params=None, timeout=130):
        result = self.call("command_run", {"id": name, "params": params or {}}, timeout)
        if result.get("isError"):
            raise ValueError(result["content"][0].get("text", "MCP command failed"))
        return result

    def tools(self):
        info = self.rpc("initialize", {"protocolVersion": "2025-06-18",
            "capabilities": {}, "clientInfo": {"name": "Clicko comparison", "version": "1"}})
        found = self.rpc("tools/list", {})["tools"]
        tools = [{"name": item["name"], "description": item.get("description", ""),
                  "input_schema": item["inputSchema"]} for item in found if item["name"] in MCP_TOOLS]
        return info["serverInfo"], tools

    def finish(self, project="orbita-opus-mcp.ecproj", video="orbita-opus-mcp.mp4"):
        self.command("file.saveAs", {"path": self.native_path(project)})
        self.command("renderQueue.add", {"output": self.native_path(video), "format": "mp4"})
        self.command("renderQueue.render", timeout=300)
        path = self.directory / video
        if not path.is_file() or not path.stat().st_size:
            raise ValueError("MCP render did not create the requested MP4")
        return path


def copy_seed(output, directory, expected):
    with ZipFile(output / "orbita-semente-comum.zip") as archive:
        archive.extractall(directory)
    native = directory / "001.ecproj"
    assert hashlib.sha256(native.read_bytes()).hexdigest() == expected


def local_mcp(output, receipt):
    import numpy as np
    from PIL import Image

    with tempfile.TemporaryDirectory(prefix="orbita-mcp-", dir=output) as temp:
        directory = Path(temp)
        copy_seed(output, directory, receipt["seedSha256"])
        with NativeMcp(directory) as mcp:
            info, tools = mcp.tools()
            assert MCP_TOOLS.intersection({"doc_inspect", "command_run", "render_preview"}) <= {t["name"] for t in tools}
            assert not mcp.call("doc_inspect").get("isError")
            # Keep the source intact. The proof edits a temporary seed copy.
            if os.environ.get("CLICKO_BENCHMARK_MCP_BINARY"):
                mcp.command("comp.new", {"name": "MCP smoke", "width": 180, "height": 320, "duration": .5})
                mcp.command("layer.newText", {"text": "MCP"})
            else:
                mcp.command("script.run", {"code": "var c=app.project.activeItem; c.duration=0.5; c.layers.addText('MCP');"})
            frame = mcp.call("render_preview", {"time": .25, "max_side": 534})
            assert any(item.get("type") == "image" for item in frame["content"])
            video = mcp.finish("smoke.ecproj", "smoke.mp4")
            shutil.copyfile(video, output / "mcp-prova-local.mp4")
    comparisons = []
    with tempfile.TemporaryDirectory(prefix="orbita-mcp-reference-", dir=output) as temp:
        directory = Path(temp)
        with ZipFile(output / "orbita-referencia-editavel.zip") as archive:
            archive.extractall(directory)
        with NativeMcp(directory) as mcp:
            for second in (2.75, 8.333, 15.5):
                frame = mcp.call("render_preview", {"time": second, "max_side": 534})
                image = next(item for item in frame["content"] if item.get("type") == "image")
                mcp_image = Image.open(io.BytesIO(base64.b64decode(image["data"]))).convert("RGB")
                native = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(second), "-i",
                    str(output / "orbita-referencia.mp4"), "-frames:v", "1", "-threads", "1",
                    "-vf", "scale=300:534", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
                    check=True, capture_output=True, timeout=45).stdout
                native_image = Image.open(io.BytesIO(native)).convert("RGB")
                same_size = mcp_image.resize(native_image.size)
                mae = np.abs(np.asarray(same_size, dtype=np.int16) - np.asarray(native_image, dtype=np.int16)).mean()
                comparisons.append({"seconds": second, "meanPixelDifference": round(float(mae), 3)})
                mcp_image.save(output / f"mcp-referencia-{second:g}.png")
    write(output / "mcp-local.json", {"server": info, "tools": [x["name"] for x in tools],
        "seedSha256": receipt["seedSha256"], "edited": True, "rendered": True, "referenceFrameComparison": comparisons,
        "apiSpendUsd": 0})
    print(json.dumps(comparisons), flush=True)


def scope_budget(db, settings, scope, committed, job_scope, model, budget):
    from sqlalchemy import select
    from app.models import StudioGenerationJob

    month = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    jobs = [j for j in db.scalars(select(StudioGenerationJob))
            if j.created_at.replace(tzinfo=UTC) >= month or (j.result_payload or {}).get("submissionStarted")]
    for field, rows in (
        ("studio_external_monthly_budget_usd", jobs),
        ("studio_external_workspace_monthly_budget_usd", [j for j in jobs if job_scope(j)["workspaceId"] == scope["workspaceId"]]),
        ("studio_external_user_monthly_budget_usd", [j for j in jobs if job_scope(j) == scope]),
    ):
        setattr(settings, field, max(getattr(settings, field), round(sum(committed(j) for j in rows) + budget, 8)))
    limit = round(sum(committed(j) for j in jobs if j.request_payload.get("model") == model) + budget, 8)
    settings.studio_external_model_monthly_budgets = {**settings.studio_external_model_monthly_budgets,
        model: max(settings.studio_external_model_monthly_budgets.get(model, 0), limit)}


def clicko_arm(output, receipt, db, document, user, connection, instruction):
    from app.config import get_settings
    from app.domain.studios.craft import CraftAICommandRequestV1
    from app.domain.studios.llm import LLMConnectionRequest
    from app.models import StudioGenerationJob, StudioLLMConnection
    from app.services.object_storage import get_object_storage
    from app.services.studios import craft, craft_agent, craft_ai, craft_drafts, llm_connections
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.external_policy import committed, job_scope

    path = output / "clicko-recibo.json"
    log = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    run_key = KEY
    budget = BUDGET
    existing = craft_drafts.session_job(db, document, run_key)
    if existing and existing.error_code == "llm_generation_budget_exceeded":
        previous = existing.result_payload or {}
        if previous.get("submissionOutcome") == "response_received" and not previous.get("draft") and not craft_agent.pending_exposure(existing):
            prior = previous["measuredCostUsd"]
            assert not previous.get("uncertainCostUpperBoundUsd") and prior < BUDGET
            budget = round(BUDGET - prior, 8)
            archive = output / "clicko-original-recibo.json"
            if not archive.exists():
                shutil.copyfile(path, archive)
            log.update(originalJobId=existing.id, originalMeasuredUsd=prior)
            run_key += "-capability-paged"
            existing = craft_drafts.session_job(db, document, run_key)
    expected = existing.request_payload["documentRevision"] if existing else document.revision
    if not existing:
        assert record_to_contract(document).native_editor_state.checksum_sha256 == receipt["seedSha256"]
        scope_budget(db, get_settings(), user._studio_billing_scope, committed, job_scope, MODEL, budget)
    if not log.get("connectionId"):
        config = {**connection.config, "budgetUsd": BUDGET, "maxOutputTokens": 12000,
                  "inputUsdPerMillion": 4, "outputUsdPerMillion": 20, "models": [MODEL],
                  "label": "Opus 5.5 · ÓRBITA comparação MCP", "provider": "anthropic",
                  "apiKey": llm_connections.decrypt(connection)}
        saved = llm_connections.save(db, document.workspace_id, LLMConnectionRequest.model_validate(config), user)
        log["connectionId"] = saved["id"]
        write(path, log)
    conn = db.get(StudioLLMConnection, log["connectionId"])
    request = CraftAICommandRequestV1(expectedRevision=expected, instruction=instruction,
        connectionId=conn.id, model=MODEL, directionEffort="deliberate")
    start = time.monotonic()
    try:
        answer = craft_ai.ai_commands(db, document, request, user, run_key, native_budget=budget)
        log.update(editReceiptId=answer["receiptId"], revision=answer["document"]["revision"])
        log.pop("runnerError", None)
    except (ValueError, OSError) as error:
        db.rollback()
        log["runnerError"] = str(error).split(":", 1)[0]
    job = craft_drafts.session_job(db, document, run_key)
    if job:
        state = job.result_payload or {}
        log.update(jobId=job.id, status=job.status, error=job.error_code, seedSha256=receipt["seedSha256"],
                   documentId=document.id, measuredUsd=state.get("measuredCostUsd", 0),
                   combinedUsd=round(log.get("originalMeasuredUsd", 0) + state.get("measuredCostUsd", 0), 8),
                   uncertainUsd=craft_agent.pending_exposure(job) + state.get("uncertainCostUpperBoundUsd", 0),
                   turns=state.get("turns", []), tools=state.get("tools", []),
                   exportRequested=state.get("exportRequested"), exportJobId=state.get("exportJobId"),
                   rationale=state.get("aiTrace", {}).get("rationale"))
        render = db.get(StudioGenerationJob, log["exportJobId"]) if log["exportJobId"] else None
        if render and render.status == "succeeded":
            artifact = render.result_payload["artifact"]
            asset = craft.scoped_asset(db, document.workspace_id, artifact["assetId"], artifact["checksumSha256"])
            with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as media:
                shutil.copyfile(media, output / "orbita-opus-clicko.mp4")
            with craft.native_bundle(db, document, record_to_contract(document).native_editor_state) as bundle:
                shutil.copyfile(bundle, output / "orbita-opus-clicko-editavel.zip")
            log["artifact"] = artifact
        elif state.get("draft"):
            with craft_drafts.bundle(db, document, job) as bundle:
                shutil.copyfile(bundle, output / "orbita-opus-clicko-rascunho.zip")
    log["lastAttemptSeconds"] = round(time.monotonic() - start, 3)
    write(path, log)
    print(json.dumps({k:log.get(k) for k in ("status", "error", "runnerError", "measuredUsd", "exportRequested", "exportJobId")}), flush=True)


def image_blocks(result):
    return [{"type": "image", "source": {"type": "base64", "media_type": block["mimeType"], "data": block["data"]}}
            if block["type"] == "image" else {"type": "text", "text": block["text"]}
            for block in result.get("content", []) if block["type"] in {"text", "image"}]


def import_mcp(output, receipt, db, user):
    from app.domain.studios.contracts import CreateStudioDocumentRequest
    from app.models import CreativeDocument
    from app.services.studios import craft
    from app.services.studios.compatibility import record_to_contract
    from app.services.studios.kernel import create_document

    seed = record_to_contract(db.get(CreativeDocument, receipt["seedId"]))
    branch = create_document(db, CreateStudioDocumentRequest.model_validate({
        "workspaceId": seed.workspace_id, "contentType": "video", "brandRevision": seed.brand_memory_ref.revision,
        "title": "ÓRBITA · corte autônomo Opus via MCP",
        "brief": seed.brief.model_dump(mode="json", by_alias=True),
        "composition": seed.composition.model_dump(mode="json", by_alias=True),
        "assets": [asset.model_dump(mode="json", by_alias=True) for asset in seed.assets],
    }), user, creation_key=KEY + "-mcp-import")
    state = seed.native_editor_state
    if branch.revision == 1:
        craft.save_native(db, branch, user, output / "projeto-mcp/orbita-opus-mcp.ecproj", engine="effectcraft",
            expected_revision=1, key=KEY + "-mcp-save", asset_manifest=state.asset_manifest, font_manifest=state.font_manifest)
    with craft.native_bundle(db, branch, record_to_contract(branch).native_editor_state) as bundle:
        shutil.copyfile(bundle, output / "orbita-opus-mcp-editavel.zip")
    write(output / "mcp-importado.json", {"documentId": branch.id, "revision": branch.revision,
        "sourceNativeSha256": hashlib.sha256((output / "projeto-mcp/orbita-opus-mcp.ecproj").read_bytes()).hexdigest(),
        "apiSpendUsd": 0})
    print(json.dumps({"mcpDocumentId": branch.id, "revision": branch.revision}), flush=True)


def mcp_arm(output, receipt, provider, instruction):
    directory = output / "projeto-mcp"
    directory.mkdir(exist_ok=True)
    copy_seed(output, directory, receipt["seedSha256"])
    path = output / "mcp-recibo.json"
    if path.exists():
        raise ValueError("Paid MCP attempt already recorded")
    log = {"model": MODEL, "seedSha256": receipt["seedSha256"], "measuredUsd": 0.0, "turns": [], "tools": []}
    start = time.monotonic()
    with NativeMcp(directory) as mcp:
        log["server"], tools = mcp.tools()
        tools.append({"name": "finish_project", "description": "Save the active draft and export the MP4. Ends the editing session.",
            "input_schema": {"type": "object", "properties": {"rationale": {"type": "string"}}, "required": ["rationale"]}})
        messages = [{"role": "user", "content": instruction}]
        try:
            for _ in range(30):
                seconds = 960 - (time.monotonic() - start)
                if seconds <= 0:
                    raise ValueError("mcp_deadline")
                count = provider.count_craft_tokens(MODEL, SYSTEM, messages, tools, seconds, prompt_cache=True)
                tokens = min(12000, int((BUDGET - log["measuredUsd"] - count * 5 / 1e6) * 1e6 / 20))
                if tokens < 256:
                    raise ValueError("mcp_budget_exhausted")
                log["pendingUsd"] = round((count * 5 + tokens * 20) / 1e6, 8)
                write(path, log)
                turn = provider.craft_turn(MODEL, SYSTEM, messages, tools, tokens, seconds, prompt_cache=True,
                                           **({"effort": "high"} if not log["turns"] else {}))
                use = turn["usage"]
                measured = (use.get("input_tokens", 0) * 4 + use.get("cache_creation_input_tokens", 0) * 5
                    + use.get("cache_read_input_tokens", 0) * .2 + use.get("output_tokens", 0) * 20) / 1e6
                log["pendingUsd"] = 0
                log["measuredUsd"] = round(log["measuredUsd"] + measured, 8)
                log["turns"].append({"usage": use, "costUsd": measured, "providerRequestId": turn.get("request_id"),
                                     "stopReason": turn["stop_reason"]})
                messages.append({"role": "assistant", "content": turn["content"]})
                responses = []
                for item in turn["content"]:
                    if item["type"] != "tool_use":
                        continue
                    name, args = item["name"], item["input"]
                    t0 = time.monotonic()
                    if name == "finish_project":
                        log.update(exportRequested=True, rationale=args.get("rationale"))
                        write(path, log)
                        rendered = mcp.finish()
                        shutil.copyfile(rendered, output / rendered.name)
                        log["exported"] = True
                        log["tools"].append({"name": name, "ok": True, "seconds": round(time.monotonic()-t0, 3)})
                        return
                    result = mcp.call(name, args)
                    blocks = image_blocks(result)
                    responses.append({"type": "tool_result", "tool_use_id": item["id"],
                                      "content": blocks, "is_error": bool(result.get("isError"))})
                    log["tools"].append({"name": name, "ok": not result.get("isError"),
                                         "seconds": round(time.monotonic()-t0, 3)})
                    if name in {"command_run", "command_batch"} and not result.get("isError"):
                        mcp.command("file.saveAs", {"path": mcp.native_path("rascunho.ecproj")})
                write(path, log)
                if not responses:
                    if turn["stop_reason"] == "end_turn":
                        messages.append({"role": "user", "content": "Conclua a entrega pedindo finish_project quando pronta."})
                        continue
                    raise ValueError("mcp_incomplete_turn")
                messages.append({"role": "user", "content": responses})
            raise ValueError("mcp_turn_limit")
        except (ValueError, RuntimeError, OSError, queue.Empty) as error:
            log["error"] = str(error)[:250]
        finally:
            log["elapsedSeconds"] = round(time.monotonic() - start, 3)
            write(path, log)
            print(json.dumps({k:log.get(k) for k in ("measuredUsd", "pendingUsd", "exported", "error")}), flush=True)


def main(output, arm):
    receipt = json.loads((output / "referencia-recibo.json").read_text(encoding="utf-8"))
    if arm == "smoke":
        return local_mcp(output, receipt)
    qa = json.loads((output / "referencia-validada.json").read_text(encoding="utf-8"))
    if not qa.get("verified"):
        raise ValueError("Local reference verification has not passed")
    if arm == "mcp" and not json.loads((output / "mcp-local.json").read_text(encoding="utf-8")).get("rendered"):
        raise ValueError("Native MCP has not rendered locally")
    runtime = ROOT / ".codex-runtime/clicko-dev"
    os.environ.update(ENVIRONMENT="development", DATABASE_URL="sqlite:///" + (runtime / "studios/records.sqlite").as_posix(),
        STORAGE_PATH=str(runtime / "studios/uploads"), STUDIO_LLM_CREDENTIAL_KEY=(runtime / "llm-credential-key").read_text().strip())
    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioGenerationJob, User
    from app.services.studios import llm_connections
    from app.services.studios.external_policy import job_scope

    inventory = json.loads((output / "materiais.json").read_text(encoding="utf-8"))
    instruction = (output / "briefing.txt").read_text(encoding="utf-8")
    instruction += ("\n\nAs fontes já estão na timeline em camadas separadas, com nomes baseados no ID do arquivo. "
                    "Da primeira camada até o fundo, a ordem é 09, 08, 07, 06, 05, 04, 03, 02, 01, Fundo. "
                    "Cada vídeo tem 3 s e as duas pistas têm 18 s.\n\nInventário comum:\n")
    instruction += "\n".join(f"- {r['file']} | {r['notes']} | ID Clicko {r['assetId']}" for r in inventory)
    with SessionLocal() as db:
        document = db.get(CreativeDocument, receipt["clickoId"])
        previous = db.get(StudioGenerationJob, "ade2bdf3-c30e-4b6a-90b4-4c99850ddc4c")
        user = db.get(User, previous.requested_by)
        assert previous.workspace_id == document.workspace_id
        user._studio_billing_scope = job_scope(previous)
        if arm == "import-mcp":
            return import_mcp(output, receipt, db, user)
        connection, provider, _, _ = llm_connections.planner(
            db, document.workspace_id, "9947192f-7acf-466c-b46b-a3eab369f618", MODEL)
        assert connection.provider == "anthropic" and connection.config["baseUrl"].rstrip("/") == "https://api.anthropic.com/v1"
        if arm == "clicko":
            clicko_arm(output, receipt, db, document, user, connection, instruction)
        else:
            mcp_arm(output, receipt, provider, instruction)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("arm", choices=["smoke", "clicko", "mcp", "import-mcp"])
    args = parser.parse_args()
    main(args.output.resolve(), args.arm)
