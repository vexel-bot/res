"""Versioned JSON-lines bridge to the genuine Rust engines. No rendering fallback."""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from ...config import get_settings

ENGINES = ("photocraft", "filmcraft", "effectcraft")
EXTENSIONS = {"photocraft": ".pcraft", "filmcraft": ".fcproj", "effectcraft": ".ecproj"}
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
HOST_COMMANDS = [
    {
        "id": "host.history.undo",
        "label": "Desfazer",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "id": "host.history.redo",
        "label": "Refazer",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
]
PAGE_COMMANDS = [
    {
        "id": "host.pages.add",
        "label": "Adicionar página",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pageId": {"type": "string", "minLength": 1, "maxLength": 160},
                "title": {"type": "string", "minLength": 1, "maxLength": 240},
                "width": {"type": "integer", "minimum": 1, "maximum": 8192},
                "height": {"type": "integer", "minimum": 1, "maximum": 8192},
            },
            "required": ["pageId", "title", "width", "height"],
            "additionalProperties": False,
        },
    },
    {
        "id": "host.pages.delete",
        "label": "Remover página",
        "inputSchema": {
            "type": "object",
            "properties": {"pageId": {"type": "string"}},
            "required": ["pageId"],
            "additionalProperties": False,
        },
    },
    {
        "id": "host.pages.move",
        "label": "Mover página",
        "inputSchema": {
            "type": "object",
            "properties": {"pageId": {"type": "string"}, "index": {"type": "integer", "minimum": 0, "maximum": 99}},
            "required": ["pageId", "index"],
            "additionalProperties": False,
        },
    },
]


class CraftRuntimeError(ValueError):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        self.message = message or code
        super().__init__(code)


def runtime_argv(engine: str) -> list[str]:
    if engine not in ENGINES:
        raise CraftRuntimeError("craft_engine_invalid")
    configured = getattr(get_settings(), f"studio_craft_{engine}_binary")
    if configured:
        executable = Path(configured).expanduser().resolve()
        if not executable.is_file():
            raise CraftRuntimeError("craft_runtime_binary_unavailable")
        return [str(executable)]
    wrapper = REPOSITORY_ROOT / "workers" / "craft" / "run_adapter.py"
    if wrapper.is_file():
        return [sys.executable, str(wrapper), engine]
    suffix = ".exe" if os.name == "nt" else ""
    adapter = REPOSITORY_ROOT / "workers" / "craft" / "bin" / f"clicko-{engine}-adapter{suffix}"
    if adapter.is_file():
        return [str(adapter)]
    raise CraftRuntimeError("craft_runtime_not_built")


def call_engine(engine: str, method: str, params: dict | None = None, *, cancelled=None) -> dict:
    if not params or not params.get("mediaRoot"):
        with tempfile.TemporaryDirectory(prefix="craft-runtime-probe-") as directory:
            return call_engine(
                engine, method, {**(params or {}), "mediaRoot": str(Path(directory).resolve())}, cancelled=cancelled
            )
    request_id = str(uuid4())
    request = {
        "protocolVersion": 1,
        "requestId": request_id,
        "engine": engine,
        "method": method,
        "params": params or {},
    }
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "TMPDIR",
            "HOME",
            "USERPROFILE",
            "DOCKER_HOST",
            "DOCKER_CONFIG",
            "CLICKO_CRAFT_RUNTIME_IMAGE",
        }
    }
    environment["PHOTOCRAFT_NO_SYSTEM_FONTS"] = "1"
    kwargs = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": environment,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        process = subprocess.Popen(runtime_argv(engine), **kwargs)
    except OSError as exc:
        raise CraftRuntimeError("craft_runtime_unavailable") from exc
    started = time.monotonic()
    first_input = json.dumps(request, ensure_ascii=False) + "\n"

    def stop_process():
        wrapper = REPOSITORY_ROOT / "workers" / "craft" / "run_adapter.py"
        if not getattr(get_settings(), f"studio_craft_{engine}_binary") and wrapper.is_file():
            try:
                subprocess.run(
                    [sys.executable, str(wrapper), "--cancel", request_id],
                    capture_output=True,
                    timeout=15,
                    env=environment,
                    check=False,
                    **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
        if process.poll() is None:
            process.kill()
        process.communicate()

    try:
        while True:
            if cancelled and cancelled():
                stop_process()
                raise CraftRuntimeError("craft_execution_cancelled")
            if time.monotonic() - started > get_settings().studio_craft_timeout_seconds:
                stop_process()
                raise CraftRuntimeError("craft_execution_timeout")
            try:
                output, _stderr = process.communicate(first_input, timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                first_input = None
        if len(output) > 32 * 1024**2:
            raise CraftRuntimeError("craft_runtime_response_too_large")
        envelopes = []
        for line in output.splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and value.get("requestId") == request_id:
                envelopes.append(value)
        if len(envelopes) != 1 or envelopes[0].get("protocolVersion") != 1:
            raise CraftRuntimeError("craft_runtime_protocol_invalid")
        response = envelopes[0]
        if response.get("error"):
            error = response["error"]
            raise CraftRuntimeError(str(error.get("code", "craft_engine_error")), str(error.get("message", "")))
        if process.returncode or not isinstance(response.get("result"), dict):
            raise CraftRuntimeError("craft_runtime_failed")
        return response["result"]
    finally:
        if process.poll() is None:
            stop_process()


def engine_capability(engine: str) -> dict:
    try:
        result = call_engine(engine, "engine.capabilities")
        if result.get("engine") != engine:
            raise CraftRuntimeError("craft_runtime_engine_mismatch")
        for key in ("buildId", "upstreamRevision", "formatVersion"):
            if not result.get(key):
                raise CraftRuntimeError("craft_runtime_identity_missing")
            result[key] = str(result[key])
        commands = result.get("commands")
        if not isinstance(commands, list):
            raise CraftRuntimeError("craft_runtime_command_schema_missing")
        return {
            **result,
            "available": True,
            "commands": [*commands, *HOST_COMMANDS, *(PAGE_COMMANDS if engine == "photocraft" else [])],
            "formats": list(
                dict.fromkeys(
                    [
                        *(
                            {
                                "jpg": "jpeg",
                                "h264": "mp4",
                                "prores": "mov",
                                "mxf-op1a": "mxf_op1a",
                                "mxf-opatom": "mxf_opatom",
                            }.get(item, item)
                            for item in result.get("formats", [])
                            if item not in {"pcraft", "fcproj", "ecproj"}
                        ),
                        *(["png_set"] if engine == "photocraft" else []),
                    ]
                )
            ),
        }
    except CraftRuntimeError as exc:
        return {"engine": engine, "available": False, "reason": exc.code, "commands": [], "formats": []}


def require_capability(engine: str) -> dict:
    result = engine_capability(engine)
    if not result["available"]:
        raise CraftRuntimeError(result["reason"])
    return result
