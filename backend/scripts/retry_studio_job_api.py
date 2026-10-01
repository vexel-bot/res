from __future__ import annotations

import argparse
import json
import time

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry a failed Studio job and verify its worker attestation.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=30.0) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": args.email, "password": args.password},
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
        before = client.get(f"/api/v1/studios/v1/jobs/{args.job_id}", headers=headers)
        before.raise_for_status()
        before_payload = before.json()
        if before_payload["status"] not in {"failed", "cancelled"}:
            raise RuntimeError(f"Job is not retryable: {before_payload}")
        response = client.post(
            f"/api/v1/studios/v1/jobs/{args.job_id}/retry", headers=headers
        )
        if response.status_code != 202:
            raise RuntimeError(f"Retry rejected: {response.status_code} {response.text}")
        deadline = time.monotonic() + args.timeout
        job: dict = {}
        while time.monotonic() < deadline:
            current = client.get(
                f"/api/v1/studios/v1/jobs/{args.job_id}", headers=headers
            )
            current.raise_for_status()
            job = current.json()
            if job["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.5)
        context = job.get("workerExecutionContext") or {}
        if (
            job.get("status") != "succeeded"
            or job.get("attempts", 0) <= before_payload.get("attempts", 0)
            or context.get("mode") != "isolated"
            or context.get("attested") is not True
        ):
            raise RuntimeError(f"Retried job did not recover on an attested worker: {job}")
        print(
            json.dumps(
                {
                    "schemaVersion": "studio.job-retry-smoke-result.v1",
                    "status": "passed",
                    "jobId": job["id"],
                    "attemptsBefore": before_payload["attempts"],
                    "attemptsAfter": job["attempts"],
                    "workerExecutionContext": context,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
