from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import httpx


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def _write_token(path: Path, token: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    updated = [
        f'CLICKO_TEST_ACCESS_TOKEN="{token}"'
        if line.startswith("CLICKO_TEST_ACCESS_TOKEN=")
        else line
        for line in lines
    ]
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def _expect(response: httpx.Response, status: int) -> dict:
    if response.status_code != status:
        raise RuntimeError(
            f"HTTP {response.status_code}, expected {status}: {response.text[:1000]}"
        )
    return response.json()


def _authenticated_client(credentials: Path) -> tuple[httpx.Client, dict[str, str]]:
    values = _read_env(credentials)
    base_url = values.get("CLICKO_TEST_API_ORIGIN", "http://127.0.0.1:8000")
    client = httpx.Client(base_url=base_url, timeout=120)
    token = values.get("CLICKO_TEST_ACCESS_TOKEN", "")
    if token:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 200:
            return client, {"Authorization": f"Bearer {token}"}
    login = _expect(
        client.post(
            "/api/v1/auth/login",
            json={
                "email": values["CLICKO_TEST_EMAIL"],
                "password": values["CLICKO_TEST_PASSWORD"],
            },
        ),
        200,
    )
    token = login["accessToken"]
    _write_token(credentials, token)
    return client, {"Authorization": f"Bearer {token}"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an authenticated local upload -> FFprobe smoke without Redis."
    )
    parser.add_argument("--credentials", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    credentials = args.credentials.resolve()
    client, headers = _authenticated_client(credentials)
    try:
        bootstrap = _expect(client.get("/api/v1/bootstrap", headers=headers), 200)
        workspace_id = bootstrap["workspaces"][0]["id"]
        with tempfile.TemporaryDirectory(prefix="clicko-video-api-smoke-") as temporary:
            fixture = Path(temporary) / "synthetic-portrait-2s.mp4"
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
                    "2",
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
            digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
            with fixture.open("rb") as media:
                asset = _expect(
                    client.post(
                        "/api/v1/assets/upload",
                        headers=headers,
                        data={
                            "workspace_id": workspace_id,
                            "title": "Synthetic portrait API smoke",
                            "tags": "video-api-smoke",
                        },
                        files={"file": (fixture.name, media, "video/mp4")},
                    ),
                    201,
                )
        ingest = _expect(
            client.post(
                "/api/v1/studios/v1/media-ingests",
                headers={
                    **headers,
                    "Idempotency-Key": (
                        "video-api-smoke-"
                        + hashlib.sha256(f"{digest}:{asset['id']}".encode()).hexdigest()[:16]
                    ),
                },
                json={"workspaceId": workspace_id, "assetId": asset["id"]},
            ),
            202,
        )
        final = _expect(
            client.get(f"/api/v1/studios/v1/media-ingests/{ingest['id']}", headers=headers),
            200,
        )
        job = _expect(
            client.get(
                f"/api/v1/studios/v1/jobs/{ingest['generationJobId']}",
                headers=headers,
            ),
            200,
        )
        if job["status"] != "succeeded" or final["status"] != "ready":
            raise RuntimeError(f"Video API smoke did not complete: job={job} ingest={final}")
        media_info = final["mediaInfo"]
        report = {
            "schemaVersion": "studio.video-api-eager-smoke.v1",
            "status": "passed",
            "authenticated": True,
            "workspaceCount": len(bootstrap["workspaces"]),
            "jobStatus": job["status"],
            "ingestStatus": final["status"],
            "fixtureSha256": digest,
            "durationMs": round(media_info["durationMicroseconds"] / 1000),
            "videoStreams": len(media_info["videoStreams"]),
            "audioStreams": len(media_info["audioStreams"]),
            "executionMode": (job.get("workerExecutionContext") or {}).get("mode"),
        }
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        print(rendered, end="")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
