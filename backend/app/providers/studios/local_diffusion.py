from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ...config import get_settings
from ...domain.studios.scene_generation import LOCAL_VIDEO_PROFILE_IDS


def worker_root():
    return Path(__file__).resolve().parents[4] / "workers" / "media-generation-local"


def worker_python():
    root = worker_root()
    candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    )
    return next((str(candidate) for candidate in candidates if candidate.is_file()), sys.executable)


def preflight(*, profile_id="wan21-t2v-local-experimental-v1"):
    completed = subprocess.run(
        [
            worker_python(),
            str(worker_root() / "preflight.py"),
            "--profile-id",
            profile_id,
            "--phase",
            "execution",
            "--check-environment",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return json.loads(completed.stdout)


def capability():
    settings = get_settings()
    worker_profiles = None
    parsed = urlparse(settings.studio_local_diffusion_url)
    if (
        settings.studio_local_diffusion_enabled
        and parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and settings.studio_local_diffusion_token
    ):
        try:
            response = httpx.get(
                settings.studio_local_diffusion_url.rstrip("/") + "/api/v1/capabilities",
                headers={
                    "Authorization": "Bearer "
                    + settings.studio_local_diffusion_token.get_secret_value()
                },
                timeout=20,
            )
            response.raise_for_status()
            worker_profiles = response.json().get("profiles")
        except (httpx.HTTPError, ValueError, AttributeError):
            worker_profiles = None
    profiles = []
    if worker_profiles is not None:
        profiles = worker_profiles
    else:
        for profile_id in sorted(LOCAL_VIDEO_PROFILE_IDS):
            try:
                admission = preflight(profile_id=profile_id)
            except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as error:
                admission = {
                    "profileId": profile_id,
                    "status": "unavailable",
                    "reasons": [type(error).__name__],
                }
            profiles.append(
                {
                    **admission,
                    "resourceAdmission": admission.get("status", "unavailable"),
                    "modelReadiness": "unknown",
                    "adapterSupport": "unknown",
                    "qualificationState": "experimental"
                    if profile_id.startswith("animatediff-lightning")
                    else "unavailable",
                    "usableNow": False,
                }
            )
    eligible = [
        item
        for item in profiles
        if item.get("modelReadiness") == "ready"
        and item.get("adapterSupport") == "available"
        and item.get("qualificationState") in {"experimental", "qualified"}
    ]
    available = [item for item in eligible if item.get("usableNow")]
    selected = (available or eligible or profiles)[0]
    return {
        "schemaVersion": "studio.scene-generation-capability.v1",
        "state": selected.get("qualificationState", "unavailable")
        if settings.studio_local_diffusion_enabled and eligible
        else "unavailable",
        "profileId": selected.get("profileId", "animatediff-lightning-sd15-a-v1"),
        "operation": "text_to_video",
        "preflight": selected,
        "serviceAccessible": worker_profiles is not None,
        "modelReadiness": selected.get("modelReadiness", "unknown"),
        "resourceAdmission": selected.get("resourceAdmission", selected.get("status", "unknown")),
        "adapterSupport": selected.get("adapterSupport", "unknown"),
        "qualificationState": selected.get("qualificationState", "unavailable"),
        "profiles": profiles,
        "paidFallbackEnabled": False,
    }


def submit_or_resume(execution_id, payload, is_cancelled):
    settings = get_settings()
    if not settings.studio_local_diffusion_enabled:
        return {"status": "unavailable", "reason": "local_diffusion_not_enabled"}
    parsed = urlparse(settings.studio_local_diffusion_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        return {"status": "unavailable", "reason": "local_diffusion_loopback_required"}
    if not settings.studio_local_diffusion_token:
        return {"status": "unavailable", "reason": "local_diffusion_token_missing"}
    token = settings.studio_local_diffusion_token.get_secret_value()
    headers = {"Authorization": "Bearer " + token}
    base = settings.studio_local_diffusion_url.rstrip("/")
    with httpx.Client(timeout=httpx.Timeout(30, read=60)) as client:
        known = client.get(f"{base}/api/v1/executions/{execution_id}", headers=headers)
        if known.status_code == 200:
            response = known.json()
            if response.get("status") != "running":
                return response
            submitted = known
        elif known.status_code != 404:
            known.raise_for_status()
        else:
            try:
                submitted = client.post(
                    f"{base}/api/v1/generate-scene",
                    headers=headers,
                    json={**payload, "executionId": execution_id},
                )
            except httpx.TimeoutException:
                return {"status": "submission_unknown", "executionId": execution_id}
            if submitted.status_code == 409:
                detail = submitted.json().get("detail", submitted.json())
                return detail if isinstance(detail, dict) else {"status": "unavailable", "reason": str(detail)}
            submitted.raise_for_status()
        for _ in range(186):
            if is_cancelled():
                try:
                    client.post(
                        f"{base}/api/v1/executions/{execution_id}/cancel",
                        headers=headers,
                    )
                except httpx.HTTPError:
                    pass
                return {"cancelled": True, "executionId": execution_id}
            import time

            time.sleep(10)
            response = client.get(f"{base}/api/v1/executions/{execution_id}", headers=headers)
            response.raise_for_status()
            receipt = response.json()
            if receipt.get("status") != "running":
                return receipt
        try:
            client.post(f"{base}/api/v1/executions/{execution_id}/cancel", headers=headers)
        except httpx.HTTPError:
            pass
    return {"status": "timeout", "executionId": execution_id}


def verify_artifact(execution_id, path, checksum):
    candidate = Path(path).resolve()
    expected_directory = (worker_root() / ".runs" / execution_id).resolve()
    if candidate.parent != expected_directory or candidate.name != "candidate.mp4" or not candidate.is_file():
        raise ValueError("scene_generation_artifact_path_invalid")
    actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if actual != checksum:
        raise ValueError("scene_generation_artifact_checksum_mismatch")
    return candidate
