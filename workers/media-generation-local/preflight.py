"""Read-only installation and execution admission for local diffusion."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

MODULE_ROOT = Path(__file__).resolve().parent
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))
from profile_registry import LEGACY_PROFILE, ROOT, get_profile  # noqa: E402

CACHE = ROOT / ".model-cache"
OFFLOAD = ROOT / ".offload"
LOCK = ROOT / "requirements.lock"


def _system_memory_details() -> dict:
    if hasattr(ctypes, "windll"):

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("memory_measurement_failed")
        unit = 1024 * 1024
        return {
            "totalPhysicalMiB": status.total_physical // unit,
            "availablePhysicalMiB": status.available_physical // unit,
            "totalCommitMiB": status.total_page_file // unit,
            "availableCommitMiB": status.available_page_file // unit,
        }
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        values[key] = int(value.strip().split()[0]) // 1024
    return {
        "totalPhysicalMiB": values.get("MemTotal", 0),
        "availablePhysicalMiB": values.get("MemAvailable", 0),
        "totalCommitMiB": values.get("CommitLimit", 0),
        "availableCommitMiB": max(0, values.get("CommitLimit", 0) - values.get("Committed_AS", 0)),
    }


def _system_memory_mib():
    details = _system_memory_details()
    return details["totalPhysicalMiB"], details["availablePhysicalMiB"]


def _gpu_memory_mib():
    try:
        completed = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return []
    result = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.rsplit(",", 3)]
        if len(parts) == 4:
            name, total, free, driver = parts
            result.append({"name": name, "totalMiB": int(total), "freeMiB": int(free), "driverVersion": driver})
    return result


def _lock_status() -> str:
    if not LOCK.is_file():
        return "missing"
    return "qualified" if "lockStatus: qualified" in LOCK.read_text(encoding="utf-8") else "unqualified"


def _locked_versions() -> dict[str, str]:
    if not LOCK.is_file():
        return {}
    text = LOCK.read_text(encoding="utf-8")
    versions = {
        name.casefold(): version
        for name, version in re.findall(
            r"(?m)^([A-Za-z0-9_.-]+)==([^\\\s]+)", text
        )
    }
    for name, url in re.findall(r"(?m)^([A-Za-z0-9_.-]+)\s*@\s*(\S+)", text):
        decoded = unquote(url)
        wheel = re.search(rf"/{re.escape(name)}-([0-9][A-Za-z0-9.+]*)-cp\d+", decoded, re.IGNORECASE)
        if wheel:
            versions[name.casefold()] = wheel.group(1)
    return versions


def _environment_status() -> dict:
    required = ("torch", "diffusers", "transformers", "accelerate", "safetensors", "huggingface-hub")
    versions, missing = {}, []
    for package in required:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)
    cuda_available = False
    if "torch" not in missing:
        try:
            probe = subprocess.run(
                [sys.executable, "-c", "import torch; print('1' if torch.cuda.is_available() else '0')"],
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            cuda_available = probe.returncode == 0 and probe.stdout.strip() == "1"
        except (OSError, subprocess.SubprocessError):
            cuda_available = False
    locked = _locked_versions()
    mismatches = {
        package: {"locked": locked.get(package), "installed": version}
        for package, version in versions.items()
        if locked.get(package) != version
    }
    lock_digest = hashlib.sha256(LOCK.read_bytes()).hexdigest() if LOCK.is_file() else None
    return {
        "lockStatus": "qualified" if _lock_status() == "qualified" and not mismatches else "unqualified",
        "lockDigestSha256": lock_digest,
        "lockedVersions": {package: locked.get(package) for package in required},
        "versionMismatches": mismatches,
        "missingPackages": missing,
        "versions": versions,
        "cudaAvailable": cuda_available,
    }


def _disk_usage(path: Path):
    probe = path.resolve()
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    return shutil.disk_usage(probe)


def inspect(
    profile_path=None,
    cache_path=None,
    *,
    profile_id=None,
    phase="all",
    check_environment=False,
    environment_status=None,
):
    manifest = json.loads(Path(profile_path).read_text(encoding="utf-8")) if profile_path else get_profile(profile_id)
    cache = Path(cache_path or CACHE).resolve()
    disk = _disk_usage(cache)
    try:
        memory = _system_memory_details()
    except OSError:
        total_ram, free_ram = _system_memory_mib()
        memory = {
            "totalPhysicalMiB": total_ram,
            "availablePhysicalMiB": free_ram,
            "totalCommitMiB": 0,
            "availableCommitMiB": 0,
        }
    gpus = _gpu_memory_mib()
    expected = int(manifest.get("expectedDownloadBytes", 0))
    reserve = int(manifest.get("minimumFreeBytesAfterInstall", manifest.get("minimumFreeBytesAfterDownload", 0)))
    scratch_multiplier = float(manifest.get("downloadScratchMultiplier", 0.5))
    download_scratch = int(expected * scratch_multiplier)
    required_disk = expected + download_scratch + reserve
    execution_disk = int(manifest.get("minimumExecutionDiskFreeBytes", 0))
    total_ram_min = int(manifest.get("minimumSystemRamTotalMiB", manifest.get("minimumSystemRamMiB", 0)))
    free_ram_min = int(manifest.get("minimumSystemRamFreeMiB", 0))
    free_commit_min = int(manifest.get("minimumCommitFreeMiB", 0))
    total_vram_min = int(manifest.get("minimumVramTotalMiB", manifest.get("minimumVramMiB", 0)))
    free_vram_min = int(manifest.get("minimumVramFreeMiB", 0))
    reasons = []
    if phase in {"all", "install"} and disk.free < required_disk:
        reasons.append("insufficient_disk_before_model_download")
    if phase == "execution" and disk.free < execution_disk:
        reasons.append("insufficient_disk_for_execution")
    if memory["totalPhysicalMiB"] < total_ram_min:
        reasons.append("insufficient_system_ram")
    if phase in {"all", "execution"} and memory["availablePhysicalMiB"] < free_ram_min:
        reasons.append("blocked_current_load")
    if phase in {"all", "execution"} and memory["availableCommitMiB"] < free_commit_min:
        reasons.append("insufficient_commit_for_execution")
    if not gpus:
        reasons.append("cuda_gpu_unavailable")
    else:
        if max(item["totalMiB"] for item in gpus) < total_vram_min:
            reasons.append("insufficient_vram")
        if phase in {"all", "execution"} and max(item["freeMiB"] for item in gpus) < free_vram_min:
            reasons.append("blocked_current_gpu_load")
    environment = (
        environment_status or _environment_status()
        if check_environment
        else {"lockStatus": _lock_status()}
    )
    if check_environment:
        if environment["lockStatus"] != "qualified":
            reasons.append("environment_lock_unqualified")
        if environment["missingPackages"]:
            reasons.append("environment_packages_missing")
        elif not environment.get("cudaAvailable"):
            reasons.append("environment_cuda_unavailable")
    reasons = list(dict.fromkeys(reasons))
    return {
        "schemaVersion": "res.local-video-preflight.v2",
        "profileId": manifest["profileId"],
        "phase": phase,
        "status": "blocked_resources" if reasons else "admitted",
        "reasons": reasons,
        "modelDownloadStarted": False,
        "resources": {
            "diskFreeBytes": disk.free,
            "requiredDiskFreeBytes": required_disk,
            "minimumExecutionDiskFreeBytes": execution_disk,
            "expectedDownloadBytes": expected,
            "downloadScratchBytes": download_scratch,
            "minimumFreeBytesAfterInstall": reserve,
            "systemRamTotalMiB": memory["totalPhysicalMiB"],
            "systemRamFreeMiB": memory["availablePhysicalMiB"],
            "minimumSystemRamTotalMiB": total_ram_min,
            "minimumSystemRamFreeMiB": free_ram_min,
            "systemCommitTotalMiB": memory["totalCommitMiB"],
            "systemCommitFreeMiB": memory["availableCommitMiB"],
            "minimumCommitFreeMiB": free_commit_min,
            "gpus": gpus,
            "cachePath": str(cache),
            "offloadPath": str(OFFLOAD.resolve()),
        },
        "environment": environment,
        "model": {"adapter": manifest.get("adapter", "wan21"), "expectedDownloadBytes": expected},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile")
    parser.add_argument("--profile-id", default=LEGACY_PROFILE)
    parser.add_argument("--cache")
    parser.add_argument("--phase", choices=("install", "execution", "all"), default="all")
    parser.add_argument("--check-environment", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            inspect(
                args.profile,
                args.cache,
                profile_id=args.profile_id,
                phase=args.phase,
                check_environment=args.check_environment,
            ),
            separators=(",", ":"),
        )
    )
