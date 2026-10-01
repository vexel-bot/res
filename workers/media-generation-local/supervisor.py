"""Owns the inference deadline and always publishes a durable receipt."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from execution_store import atomic_json
from preflight import _gpu_memory_mib, _system_memory_details
from profile_registry import get_profile


def _terminate(process):
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        process.kill()
    process.wait(timeout=15)


def main(request_path: Path, output_path: Path, receipt_path: Path):
    request = json.loads(request_path.read_text(encoding="utf-8"))
    profile = request.get("profileSnapshot") or get_profile(request["profileId"])
    envelope = {
        "schemaVersion": "studio.scene-generation-receipt.v2",
        "executionId": request.get("executionId"),
        "profileId": request.get("profileId"),
        "profileDigestSha256": request.get("profileDigestSha256"),
        "requestDigestSha256": request.get("requestDigest"),
        "runtimeDigests": request.get("runtimeDigests", {}),
    }
    process = subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).with_name("runner.py")),
            str(request_path),
            str(output_path),
            str(receipt_path),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    deadline = time.monotonic() + int(profile["maximumRuntimeSeconds"])
    initial_memory = _system_memory_details()
    initial_ram = int(initial_memory["availablePhysicalMiB"])
    initial_gpus = _gpu_memory_mib()
    initial_vram = max((int(gpu["freeMiB"]) for gpu in initial_gpus), default=0)
    minimum_ram = None
    minimum_vram = None
    resource_failure = None
    consecutive_ram_breaches = 0
    while process.poll() is None and time.monotonic() < deadline:
        try:
            ram = int(_system_memory_details()["availablePhysicalMiB"])
            gpus = _gpu_memory_mib()
            vram = max((int(gpu["freeMiB"]) for gpu in gpus), default=0)
            minimum_ram = ram if minimum_ram is None else min(minimum_ram, ram)
            minimum_vram = vram if minimum_vram is None else min(minimum_vram, vram)
            ram_reserve = int(profile.get("watchdogSystemRamFreeMiB", 0))
            emergency_ram_reserve = int(profile.get("watchdogEmergencySystemRamFreeMiB", 32))
            required_breaches = int(profile.get("watchdogConsecutiveRamBreaches", 1))
            consecutive_ram_breaches = consecutive_ram_breaches + 1 if ram < ram_reserve else 0
            if ram < emergency_ram_reserve:
                resource_failure = "system_ram_reserve_exhausted"
            elif consecutive_ram_breaches >= required_breaches:
                resource_failure = "system_ram_reserve_exhausted"
            elif vram < int(profile.get("watchdogVramFreeMiB", 0)):
                resource_failure = "vram_reserve_exhausted"
        except (OSError, ValueError):
            resource_failure = "resource_measurement_failed"
        if resource_failure:
            _terminate(process)
            atomic_json(
                receipt_path,
                {
                    **envelope,
                    "status": "blocked_resources",
                    "stage": "inference",
                    "reason": resource_failure,
                    "minimumAvailableSystemRamMiB": minimum_ram,
                    "minimumAvailableVramMiB": minimum_vram,
                    "consecutiveRamBreaches": consecutive_ram_breaches,
                },
            )
            return
        time.sleep(1)
    if process.poll() is None:
        _terminate(process)
        atomic_json(
            receipt_path,
            {
                **envelope,
                "status": "deadline_exceeded",
                "stage": "inference",
            },
        )
    elif not receipt_path.is_file() or receipt_path.stat().st_size == 0:
        atomic_json(
            receipt_path,
            {
                **envelope,
                "status": "failed",
                "stage": "runner",
                "errorCode": "runner_exited_without_receipt",
                "returnCode": process.returncode,
            },
        )
    else:
        result = json.loads(receipt_path.read_text(encoding="utf-8"))
        result = {**envelope, **result}
        result["minimumAvailableSystemRamMiB"] = minimum_ram
        result["minimumAvailableVramMiB"] = minimum_vram
        result["observedSystemRamDeltaPeakMiB"] = max(0, initial_ram - (minimum_ram or initial_ram))
        result["observedVramDeltaPeakMiB"] = max(0, initial_vram - (minimum_vram or initial_vram))
        atomic_json(receipt_path, result)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
