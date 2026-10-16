"""Run the immutable Rust adapter in a job-scoped, networkless container.

The API supplies JSON-lines on stdin. Only its materialized mediaRoot is mounted;
browser paths never become host paths. Native installations can configure their
adapter executable directly and bypass this development/Windows runner.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from uuid import UUID

ENGINES = frozenset({"photocraft", "filmcraft", "effectcraft"})
PATH_KEYS = frozenset(
    {
        "nativePath",
        "outputPath",
        "inputPath",
        "mediaRoot",
        "path",
        "filePath",
        "fontPath",
    }
)
MAX_LINE_BYTES = 8 * 1024 * 1024


def translate(value, root: Path, key: str = ""):
    if isinstance(value, dict):
        # Engine command "path" often names a property (transform.position),
        # never a host filename. Native command access is bounded by Workspace.
        return {
            name: item
            if name in {"commands", "params", "legacyDocument"}
            else translate(item, root, name)
            for name, item in value.items()
        }
    if isinstance(value, list):
        return [translate(item, root, key) for item in value]
    if isinstance(value, str) and key in PATH_KEYS:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("adapter path is outside the materialized job")
        return (
            "/job/" + candidate.relative_to(root).as_posix()
            if candidate != root
            else "/job"
        )
    return value


def error_reply(request, code: str, message: str):
    return {
        "protocolVersion": 1,
        "requestId": request.get("requestId"),
        "error": {"code": code, "message": message},
    }


def run(request: dict, engine: str):
    if request.get("protocolVersion") != 1 or request.get("engine", engine) != engine:
        return error_reply(
            request, "craft_protocol_invalid", "Invalid adapter version or engine"
        )
    params = request.get("params") or {}
    root_value = params.get("mediaRoot")
    if not isinstance(root_value, str):
        if request.get("method") in {"engine.capabilities", "engine.commands"}:
            with tempfile.TemporaryDirectory(
                prefix="clicko-craft-capabilities-"
            ) as directory:
                return run(
                    dict(request, params={**params, "mediaRoot": directory}), engine
                )
        return error_reply(
            request,
            "craft_job_root_required",
            "A materialized job directory is required",
        )
    root = Path(root_value).resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor):
        return error_reply(
            request, "craft_job_root_invalid", "Invalid materialized job directory"
        )
    payload = dict(request, params=translate(params, root))
    image = os.environ.get("CLICKO_CRAFT_RUNTIME_IMAGE", "clicko-craft-runtime:local")
    container_name = "clicko-craft-job-" + UUID(str(request.get("requestId"))).hex
    argv = [
        "docker",
        "run",
        "--name",
        container_name,
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--cpus",
        os.environ.get("CLICKO_CRAFT_CPUS", "2"),
        "--memory",
        os.environ.get("CLICKO_CRAFT_MEMORY", "4g"),
        "--tmpfs",
        "/tmp:rw,nosuid,size=512m",
        "--env",
        "CLICKO_CRAFT_ISOLATED=1",
        "--mount",
        f"type=bind,source={root},target=/job",
        image,
        f"/opt/clicko/bin/clicko-{engine}-adapter",
    ]
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        # Native Linux temporary directories are private (0700); execute with
        # the materializing worker's uid, while retaining all container limits.
        argv[argv.index(image) : argv.index(image)] = [
            "--user",
            f"{os.getuid()}:{os.getgid()}",
        ]
    process = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    def cancel(_signum, _frame):
        subprocess.run(
            ["docker", "kill", container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
        process.terminate()
        raise SystemExit(143)

    signal.signal(signal.SIGTERM, cancel)
    try:
        result, diagnostic = process.communicate(
            (json.dumps(payload, ensure_ascii=False) + "\n").encode(), timeout=3600
        )
    except subprocess.TimeoutExpired:
        cancel(signal.SIGTERM, None)
    if process.returncode:
        # Docker diagnostics contain no credential environment or project payload.
        detail = diagnostic.decode(errors="replace").strip()[-2000:]
        return error_reply(
            request,
            "craft_runtime_failed",
            detail or f"Adapter exited {process.returncode}",
        )
    for line in result.decode().splitlines():
        reply = json.loads(line)
        if reply.get("requestId") == request.get("requestId"):
            return restore_paths(reply, root)
    return error_reply(
        request, "craft_runtime_protocol_error", "Adapter returned no matching receipt"
    )


def restore_paths(value, root: Path, key: str = ""):
    if isinstance(value, dict):
        return {name: restore_paths(item, root, name) for name, item in value.items()}
    if isinstance(value, list):
        return [restore_paths(item, root, key) for item in value]
    if isinstance(value, str) and key in PATH_KEYS and value.startswith("/job/"):
        relative = value.removeprefix("/job/")
        destination = (root / relative).resolve()
        if not destination.is_relative_to(root):
            raise ValueError("returned adapter path leaves the materialized job")
        return str(destination)
    return value


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--cancel":
        name = "clicko-craft-job-" + UUID(sys.argv[2]).hex
        subprocess.run(
            ["docker", "kill", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
        return
    if len(sys.argv) != 2 or sys.argv[1] not in ENGINES:
        raise SystemExit("Usage: run_adapter.py photocraft|filmcraft|effectcraft")
    engine = sys.argv[1]
    for line in sys.stdin.buffer:
        request = {}
        try:
            if len(line) > MAX_LINE_BYTES:
                raise ValueError("Adapter request exceeds protocol limit")
            decoded = json.loads(line)
            if not isinstance(decoded, dict):
                raise ValueError("Adapter request must be an object")
            request = decoded
            reply = run(request, engine)
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            reply = error_reply(request, "craft_runtime_error", str(exc))
        # JSONL is UTF-8 regardless of the Windows console's locale/code page.
        sys.stdout.buffer.write(
            (json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8")
        )
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
