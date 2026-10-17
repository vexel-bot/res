"""Verify the loopback-only Qwen evaluation API without printing its key."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _env_value(path: Path, name: str) -> str:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith(f"{name}="):
            return raw_line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError(f"missing_env_value:{name}")


def _request(url: str, *, key: str | None, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    data = None
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    request = Request(url, headers=headers, data=data, method="POST" if data else "GET")
    try:
        with urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read() or b"{}")
    except URLError:
        return 503, {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18080/v1")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--startup-timeout-seconds", type=int, default=90)
    args = parser.parse_args()
    key = _env_value(args.env_file, "AI_API_KEY")
    if len(key) < 32:
        raise SystemExit("api_key_too_short")

    deadline = time.monotonic() + args.startup_timeout_seconds
    authorized_status = 503
    models: dict = {}
    while authorized_status == 503 and time.monotonic() < deadline:
        authorized_status, models = _request(f"{args.base_url}/models", key=key)
        if authorized_status == 503:
            time.sleep(2)
    unauthorized_status, _ = _request(f"{args.base_url}/models", key=None)
    chat_status, completion = _request(
        f"{args.base_url}/chat/completions",
        key=key,
        body={
            "model": "clicko-qwen3-4b-q4-k-m",
            "messages": [{"role": "user", "content": "Responda somente OK. /no_think"}],
            "temperature": 0,
            "max_tokens": 16,
        },
    )
    content = completion.get("choices", [{}])[0].get("message", {}).get("content")
    model_ids = [item.get("id") for item in models.get("data", [])]
    if unauthorized_status != 401:
        raise SystemExit(f"unauthorized_gate_failed:{unauthorized_status}")
    if authorized_status != 200 or chat_status != 200:
        raise SystemExit(f"authorized_api_failed:{authorized_status}:{chat_status}")
    if "clicko-qwen3-4b-q4-k-m" not in model_ids or content != "OK.":
        raise SystemExit("model_or_completion_mismatch")
    print(
        json.dumps(
            {
                "status": "local-qwen-api-verified",
                "baseUrl": args.base_url,
                "model": "clicko-qwen3-4b-q4-k-m",
                "unauthorizedStatus": unauthorized_status,
                "completion": content,
                "usage": completion.get("usage"),
                "timings": completion.get("timings"),
                "apiKeyExposed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
