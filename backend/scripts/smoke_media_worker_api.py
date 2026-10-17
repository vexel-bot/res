from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

import httpx


def expect(response: httpx.Response, status: int) -> dict:
    if response.status_code != status:
        raise RuntimeError(
            f"HTTP {response.status_code}, expected {status}: {response.text[:1000]}"
        )
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prove upload -> Redis queue -> isolated media worker -> FFprobe."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8013")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--fixture-seconds", type=int, default=1)
    parser.add_argument("--cancel-proxy", action="store_true")
    args = parser.parse_args()

    suffix = uuid4().hex[:12]
    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        registration = expect(
            client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"media-worker-smoke-{suffix}@example.com",
                    "name": "Media Worker Smoke",
                    "password": "media-worker-smoke-123",
                    "workspaceName": f"Media Worker {suffix}",
                },
            ),
            201,
        )
        headers = {"Authorization": f"Bearer {registration['accessToken']}"}
        bootstrap = expect(client.get("/api/v1/bootstrap", headers=headers), 200)
        workspace_id = bootstrap["workspaces"][0]["id"]

        with tempfile.TemporaryDirectory(prefix="clicko-worker-smoke-") as temporary:
            fixture = Path(temporary) / "worker-smoke.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=0x201a36:s=360x640:r=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000",
                    "-t",
                    str(args.fixture_seconds),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(fixture),
                ],
                check=True,
                timeout=30,
            )
            with fixture.open("rb") as media:
                asset = expect(
                    client.post(
                        "/api/v1/assets/upload",
                        headers=headers,
                        data={
                            "workspace_id": workspace_id,
                            "title": "Worker smoke source",
                            "tags": "worker-smoke",
                        },
                        files={"file": (fixture.name, media, "video/mp4")},
                    ),
                    201,
                )

        ingest = expect(
            client.post(
                "/api/v1/studios/v1/media-ingests",
                headers={**headers, "Idempotency-Key": f"worker-smoke-{suffix}"},
                json={"workspaceId": workspace_id, "assetId": asset["id"]},
            ),
            202,
        )
        deadline = time.monotonic() + args.timeout
        job: dict = {}
        while time.monotonic() < deadline:
            job = expect(
                client.get(
                    f"/api/v1/studios/v1/jobs/{ingest['generationJobId']}",
                    headers=headers,
                ),
                200,
            )
            if job["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.5)
        if job.get("status") != "succeeded":
            raise RuntimeError(f"Media worker job did not succeed: {job}")
        context = job.get("workerExecutionContext") or {}
        if (
            context.get("mode") != "isolated"
            or context.get("attested") is not True
            or context.get("capability") != "media_cpu"
            or context.get("queueName") != "studio.media.cpu"
            or not context.get("manifestDigestSha256")
        ):
            raise RuntimeError(f"Media worker execution was not attested: {context}")
        final_ingest = expect(
            client.get(
                f"/api/v1/studios/v1/media-ingests/{ingest['id']}", headers=headers
            ),
            200,
        )
        if final_ingest["status"] != "ready":
            raise RuntimeError(f"Media ingest did not become ready: {final_ingest}")
        proxy_cancellation = None
        if args.cancel_proxy:
            proxy = expect(
                client.post(
                    f"/api/v1/studios/v1/media-ingests/{ingest['id']}/proxy",
                    headers={
                        **headers,
                        "Idempotency-Key": f"worker-proxy-cancel-{suffix}",
                    },
                    json={"workspaceId": workspace_id, "spec": {}},
                ),
                202,
            )
            proxy_deadline = time.monotonic() + args.timeout
            proxy_job = proxy
            while time.monotonic() < proxy_deadline:
                proxy_job = expect(
                    client.get(
                        f"/api/v1/studios/v1/jobs/{proxy['id']}", headers=headers
                    ),
                    200,
                )
                if proxy_job["status"] == "running":
                    break
                if proxy_job["status"] in {"succeeded", "failed", "cancelled"}:
                    raise RuntimeError(
                        f"Proxy reached terminal state before cancellation: {proxy_job}"
                    )
                time.sleep(0.05)
            if proxy_job.get("status") != "running":
                raise RuntimeError(f"Proxy never started: {proxy_job}")
            cancelled = expect(
                client.post(
                    f"/api/v1/studios/v1/jobs/{proxy['id']}/cancel",
                    headers=headers,
                    json={"reason": "isolated-worker-cancellation-smoke"},
                ),
                200,
            )
            if cancelled["status"] not in {"cancelRequested", "cancel_requested"}:
                raise RuntimeError(f"Running proxy did not accept cancellation: {cancelled}")
            while time.monotonic() < proxy_deadline:
                proxy_job = expect(
                    client.get(
                        f"/api/v1/studios/v1/jobs/{proxy['id']}", headers=headers
                    ),
                    200,
                )
                if proxy_job["status"] == "cancelled":
                    break
                if proxy_job["status"] in {"succeeded", "failed"}:
                    raise RuntimeError(f"Cancelled proxy completed incorrectly: {proxy_job}")
                time.sleep(0.1)
            final_ingest = expect(
                client.get(
                    f"/api/v1/studios/v1/media-ingests/{ingest['id']}",
                    headers=headers,
                ),
                200,
            )
            assets = expect(
                client.get(
                    "/api/v1/assets",
                    headers=headers,
                    params={"workspace_id": workspace_id},
                ),
                200,
            )
            leaked = [
                item["id"]
                for item in assets
                if (item.get("metadata") or {}).get("generationJobId") == proxy["id"]
            ]
            if (
                proxy_job.get("status") != "cancelled"
                or final_ingest.get("proxyAssetId") is not None
                or leaked
            ):
                raise RuntimeError(
                    "Cancelled proxy leaked a publishable artifact: "
                    f"job={proxy_job} ingest={final_ingest} assets={leaked}"
                )
            proxy_cancellation = {
                "jobId": proxy["id"],
                "status": proxy_job["status"],
                "attempts": proxy_job["attempts"],
                "workerExecutionContext": proxy_job.get("workerExecutionContext"),
                "leakedAssetIds": leaked,
            }
        print(
            json.dumps(
                {
                    "schemaVersion": "studio.media-worker-smoke-result.v1",
                    "status": "passed",
                    "jobId": job["id"],
                    "workerExecutionContext": context,
                    "media": final_ingest["mediaInfo"],
                    "proxyCancellation": proxy_cancellation,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
