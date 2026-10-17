"""Real HTTP/Redis/Celery exports and cancellation in disposable Linux QA storage.

Run after acceptance.py and the media-cpu image build. SQLite is kept on a
Docker volume: Windows and Linux SQLite locking must not share an NTFS bind.
Only a backup of the QA database is used; no external provider is invoked.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"


def docker(*args, timeout=30):
    return subprocess.check_output(
        ["docker", *args], text=True, stderr=subprocess.STDOUT, timeout=timeout
    ).strip()


def main():
    suffix = uuid4().hex[:12]
    network, volume, broker, worker, api = [
        "clicko-craft-qa-" + part + "-" + suffix
        for part in ("network", "database", "redis", "worker", "api")
    ]
    directory = OUTPUT / ("queue-qa-" + suffix)
    directory.mkdir(parents=True)
    with (
        sqlite3.connect(OUTPUT / "qa.sqlite") as source,
        sqlite3.connect(directory / "qa.sqlite") as target,
    ):
        source.backup(target)
    storage = Path(os.environ.get("STORAGE_PATH", ROOT / "data/uploads")).resolve()
    fixtures = json.loads((OUTPUT / "acceptance-results.json").read_text())
    film = next(item for item in fixtures if item["engine"] == "filmcraft")
    image = json.loads(docker("image", "inspect", "clicko-media-cpu:craft"))[0]["Id"]
    redis_image = json.loads(docker("image", "inspect", "redis:8.2.1-alpine"))[0]["Id"]
    started = []
    network_created = volume_created = False
    try:
        docker("network", "create", "--internal", network)
        network_created = True
        docker("volume", "create", volume)
        volume_created = True
        docker(
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--user",
            "0",
            "--mount",
            f"type=bind,source={directory},target=/seed,readonly",
            "--mount",
            f"type=volume,source={volume},target=/qa",
            image,
            "sh",
            "-c",
            "cp /seed/qa.sqlite /qa/qa.sqlite && chown 10001:10001 /qa /qa/qa.sqlite",
        )
        docker(
            "run",
            "--detach",
            "--name",
            broker,
            "--network",
            network,
            redis_image,
            "redis-server",
            "--save",
            "",
            "--appendonly",
            "no",
        )
        started.append(broker)
        common = [
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            "1g",
            "--cpus",
            "2",
            "--tmpfs",
            "/tmp/clicko-craft:rw,nosuid,size=4g,mode=1777",
            "--mount",
            f"type=volume,source={volume},target=/qa",
            "--mount",
            f"type=bind,source={storage},target=/storage",
        ]
        for value in (
            "DATABASE_URL=sqlite:////qa/qa.sqlite",
            "STORAGE_PATH=/storage",
            "OBJECT_STORAGE_BACKEND=local",
            "ENVIRONMENT=development",
            "REDIS_URL=redis://" + broker + ":6379/0",
            "CELERY_TASK_ALWAYS_EAGER=false",
            "OPENAI_OUTBOUND_ENABLED=false",
            "STUDIO_WORKER_IMAGE_DIGEST=" + image,
        ):
            common.extend(["-e", value])
        docker(
            "run", "--detach", "--name", worker, "--network", network, *common, image
        )
        started.append(worker)
        docker(
            "run",
            "--detach",
            "--name",
            api,
            "--network",
            "bridge",
            "--publish",
            "127.0.0.1::8000",
            "--no-healthcheck",
            *common,
            "-e",
            "STUDIO_WORKER_CAPABILITY=",
            "-e",
            "STUDIO_WORKER_MANIFEST_PATH=",
            image,
            "python",
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        )
        started.append(api)
        docker("network", "connect", network, api)
        origin = "http://127.0.0.1:" + docker("port", api, "8000/tcp").rsplit(":", 1)[1]
        session = requests.Session()
        token = json.loads((OUTPUT / "frontend-qa-auth.json").read_text())["token"]
        session.headers["Authorization"] = "Bearer " + token

        def call(method, path, body=None, expected=200):
            response = session.request(
                method,
                origin + path,
                json=body,
                headers={"Idempotency-Key": str(uuid4())},
                timeout=120,
            )
            assert response.status_code == expected, (
                method,
                path,
                response.status_code,
                response.text[:1200],
            )
            return response.json()

        for _ in range(60):
            try:
                response = session.get(origin + "/api/v1/bootstrap", timeout=2)
                if response.status_code == 200 and "ready." in docker("logs", worker):
                    workspace = response.json()["workspaces"][0]["id"]
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("Disposable QA API/worker startup timed out")

        def enqueue(document_id, revision):
            return call(
                "POST",
                "/api/v1/studios/v1/documents/" + document_id + "/craft/render-jobs",
                {"expectedRevision": revision, "format": "mp4"},
                201,
            )["id"]

        def status(job_id):
            return call("GET", "/api/v1/studios/v1/jobs/" + job_id)

        def terminal(job_id):
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                job = status(job_id)
                if job["status"] in {"succeeded", "failed", "cancelled"}:
                    return job
                time.sleep(0.25)
            raise RuntimeError("Worker job timed out")

        job_id = enqueue(film["documentId"], film["revision"])
        job = terminal(job_id)
        assert job["status"] == "succeeded", job
        context = job["workerExecutionContext"]
        assert (
            context["mode"] == "isolated"
            and context["attested"]
            and context["imageDigest"] == image
        ), context
        artifact = job["result"]["artifact"]
        response = session.get(origin + artifact["downloadUrl"], timeout=30)
        response.raise_for_status()
        assert response.content[4:8] == b"ftyp"
        assert (
            hashlib.sha256(response.content).hexdigest() == artifact["checksumSha256"]
        )
        print(
            "Passed real HTTP/Redis/Celery export with attested native worker and verified MP4",
            flush=True,
        )

        document = call(
            "POST",
            "/api/v1/studios/v1/documents",
            {
                "workspaceId": workspace,
                "title": "Queued native cancellation QA",
                "contentType": "video",
                "engine": "effectcraft",
                "brandRevision": 1,
                "brief": {
                    "objective": "Cancel an actual long native export",
                    "audience": "QA",
                },
                "composition": {
                    "pages": [
                        {
                            "id": "cancel-page",
                            "width": 1280,
                            "height": 720,
                            "durationMs": 60000,
                            "background": "#223344",
                            "layers": [
                                {
                                    "id": "square",
                                    "kind": "shape",
                                    "name": "Square",
                                    "x": 100,
                                    "y": 100,
                                    "width": 400,
                                    "height": 400,
                                    "properties": {"fill": "#ff0000"},
                                }
                            ],
                        }
                    ]
                },
            },
            201,
        )
        native = call(
            "POST",
            "/api/v1/studios/v1/documents/" + document["documentId"] + "/craft/migrate",
            {"engine": "effectcraft", "expectedRevision": document["revision"]},
        )
        cancel_job_id = enqueue(document["documentId"], native["revision"])
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            job = status(cancel_job_id)
            # Process names only, never arguments potentially containing credentials.
            if job["status"] == "running" and "clicko-effect" in docker(
                "exec",
                worker,
                "python",
                "-c",
                "from pathlib import Path; print([p.read_text().strip() for p in Path('/proc').glob('[0-9]*/comm') if p.exists()])",
            ):
                time.sleep(0.5)
                break
            if job["status"] in {"succeeded", "failed", "cancelled"}:
                raise RuntimeError("Export completed before native cancellation check")
            time.sleep(0.1)
        else:
            raise RuntimeError("Native rendering process never started")
        started_cancel = time.monotonic()
        call(
            "POST",
            "/api/v1/studios/v1/jobs/" + cancel_job_id + "/cancel",
            {"reason": "Cancel actual running native export"},
        )
        job = terminal(cancel_job_id)
        assert job["status"] == "cancelled" and not (job.get("result") or {}).get(
            "artifact"
        ), job
        assert job["workerExecutionContext"]["attested"]
        evidence = {
            "schemaVersion": "clicko.craft-queue-acceptance.v1",
            "imageId": image,
            "redisImageId": redis_image,
            "nativeExport": True,
            "workerAttested": True,
            "runningNativeCancellation": True,
            "databaseStorage": "disposable-linux-volume",
            "cancellationSeconds": round(time.monotonic() - started_cancel, 3),
            "exportJobId": job_id,
            "cancelJobId": cancel_job_id,
        }
        (OUTPUT / "queue-acceptance-results.json").write_text(
            json.dumps(evidence, indent=2) + "\n"
        )
        print(
            "Passed running native export cancellation without publishing a partial artifact",
            flush=True,
        )
    finally:
        for name in (worker, api):
            if name in started:
                log = subprocess.run(
                    ["docker", "logs", name], capture_output=True, text=True, timeout=20
                )
                (
                    directory / ("worker.log" if name == worker else "api.log")
                ).write_text(log.stdout + log.stderr, encoding="utf-8")
        resources = [("rm", "--force", name) for name in reversed(started)]
        if network_created:
            resources.append(("network", "rm", network))
        if volume_created:
            resources.append(("volume", "rm", volume))
        for args in resources:
            subprocess.run(
                ["docker", *args], capture_output=True, timeout=20, check=True
            )


if __name__ == "__main__":
    main()
