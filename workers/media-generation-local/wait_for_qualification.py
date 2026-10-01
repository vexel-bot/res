"""Wait for safe host admission, then run the bounded qualification matrix.

This helper is intentionally separate from the worker API. It lets an operator
close the desktop client that launched the qualification without weakening the
profile's memory thresholds or losing the requested run.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import httpx

from execution_store import atomic_json
from qualify_profile import run


def _append_observation(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as target:
        target.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def wait_and_run(
    *,
    base_url: str,
    token: str,
    output: Path,
    profile_id: str,
    maximum_wait_seconds: int,
    poll_seconds: int,
    launch_margin_mib: int,
    maximum_samples: int | None = None,
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    status_path = output / "watch-status.json"
    history_path = output / "watch-history.jsonl"
    started = time.monotonic()
    headers = {"Authorization": "Bearer " + token}

    while time.monotonic() - started < maximum_wait_seconds:
        try:
            with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=30) as client:
                response = client.get("/api/v1/capabilities")
                response.raise_for_status()
                profile = next(
                    (
                        item
                        for item in response.json().get("profiles", [])
                        if item.get("profileId") == profile_id
                    ),
                    None,
                )
            resources = (profile or {}).get("resources", {})
            free_ram = int(resources.get("systemRamFreeMiB", 0))
            required_ram = int(resources.get("minimumSystemRamFreeMiB", 0))
            safely_admitted = bool(
                profile
                and profile.get("usableNow")
                and free_ram >= required_ram + launch_margin_mib
            )
            snapshot = {
                "schemaVersion": "res.local-video-qualification-watch.v1",
                "profileId": profile_id,
                "status": "ready" if safely_admitted else "waiting_for_resources",
                "capability": profile,
                "launchMarginMiB": launch_margin_mib,
                "elapsedSeconds": round(time.monotonic() - started, 3),
            }
            atomic_json(status_path, snapshot)
            _append_observation(
                history_path,
                {
                    "elapsedSeconds": snapshot["elapsedSeconds"],
                    "status": snapshot["status"],
                    "profileId": profile_id,
                    "systemRamFreeMiB": free_ram,
                    "minimumSystemRamFreeMiB": required_ram,
                    "launchMarginMiB": launch_margin_mib,
                    "resourceAdmission": (profile or {}).get("resourceAdmission"),
                    "reasons": (profile or {}).get("reasons", []),
                },
            )
            if safely_admitted:
                result = run(base_url, token, output, profile_id, maximum_samples)
                if result.get("status") in {"blocked_resources", "partial_blocked_resources"}:
                    atomic_json(
                        status_path,
                        {
                            **snapshot,
                            "status": "waiting_after_transient_resource_block",
                            "resultStatus": result.get("status"),
                            "elapsedSeconds": round(time.monotonic() - started, 3),
                        },
                    )
                    time.sleep(poll_seconds)
                    continue
                atomic_json(
                    status_path,
                    {
                        **snapshot,
                        "status": "completed",
                        "resultStatus": result.get("status"),
                        "elapsedSeconds": round(time.monotonic() - started, 3),
                    },
                )
                return result
        except (httpx.HTTPError, ValueError, KeyError) as error:
            failure = {
                    "schemaVersion": "res.local-video-qualification-watch.v1",
                    "profileId": profile_id,
                    "status": "worker_unreachable",
                    "errorCode": type(error).__name__,
                    "elapsedSeconds": round(time.monotonic() - started, 3),
                }
            atomic_json(status_path, failure)
            _append_observation(history_path, failure)
        time.sleep(poll_seconds)

    result = {
        "schemaVersion": "res.local-video-qualification-watch.v1",
        "profileId": profile_id,
        "status": "wait_deadline_exceeded",
        "elapsedSeconds": round(time.monotonic() - started, 3),
    }
    atomic_json(status_path, result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8094")
    parser.add_argument("--profile-id", default="animatediff-lightning-sd15-a-v1")
    parser.add_argument("--output", required=True)
    parser.add_argument("--maximum-wait-seconds", type=int, default=3600)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--launch-margin-mib", type=int, default=256)
    parser.add_argument("--maximum-samples", type=int)
    args = parser.parse_args()
    secret = os.environ.get("RES_LOCAL_DIFFUSION_TOKEN", "")
    if len(secret) < 32:
        raise SystemExit("RES_LOCAL_DIFFUSION_TOKEN is required")
    value = wait_and_run(
        base_url=args.base_url,
        token=secret,
        output=Path(args.output),
        profile_id=args.profile_id,
        maximum_wait_seconds=max(1, args.maximum_wait_seconds),
        poll_seconds=max(1, args.poll_seconds),
        launch_margin_mib=max(0, args.launch_margin_mib),
        maximum_samples=max(1, args.maximum_samples) if args.maximum_samples is not None else None,
    )
    print(json.dumps(value, separators=(",", ":")))
