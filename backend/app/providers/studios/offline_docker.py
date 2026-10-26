"""Local Docker control shared by isolated speech adapters; never invokes a shell."""

import subprocess
from pathlib import Path


class OfflineDockerControl:
    def __init__(self, docker_executable: Path):
        if not docker_executable.is_absolute() or not docker_executable.is_file():
            raise ValueError("speech_docker_absolute_executable_required")
        self.docker_executable = str(docker_executable)

    def _docker(self, arguments, timeout=20):
        try:
            return subprocess.run(
                [self.docker_executable, *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("speech_docker_control_unavailable") from exc

    def _remove(self, name):
        # Stop the daemon-owned process, then verify deletion independently of client exit.
        self._docker(["container", "rm", "--force", name])
        inventory = self._docker(
            [
                "container",
                "ls",
                "--all",
                "--filter",
                f"name=^/{name}$",
                "--format",
                "{{.Names}}",
            ]
        )
        if inventory.returncode != 0 or inventory.stdout.strip():
            raise RuntimeError("speech_docker_cleanup_unverified")
