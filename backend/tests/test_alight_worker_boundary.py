"""Driver simulations audit the worker boundary, never qualify the Android app."""

import json

import pytest

from app.domain.studios.contextual_editing import digest

DRIVER = """
from pathlib import Path
from app.providers.studios.alight_worker import file_hash, TransientAlightError
class Driver:
    def __init__(self, worker, profile):
        self.worker, self.profile = worker, profile
    def confirm_resume(self, previous, bundle):
        return self.profile.get("allowResume", False)
    def execute(self, stage, bundle, root, destination, remaining, is_cancelled):
        mode = self.profile.get("fixtureMode")
        if stage == "compile":
            if mode == "unknown": raise ValueError("fixture_unknown_ui")
            if mode == "no_space": raise ValueError("fixture_device_storage_full")
            if mode == "unconfirmed": return {"confirmed": False}
            if mode == "transient":
                marker = self.worker.state_dir / "first-transient"
                if not marker.exists():
                    marker.write_text("attempt")
                    raise TransientAlightError("temporary_io_failure")
        if stage == "validate" and Path(destination).exists():
            raise ValueError("fixture_stale_host_output")
        observation = Path(root) / (stage + ".txt")
        observation.write_text("SIMULATED UI - " + bundle["jobId"])
        if stage == "retrieve": Path(destination).write_bytes(b"SIMULATED OUTPUT")
        return {"confirmed": True, "observationPath": observation.name,
                "observationSha256": "0" * 64 if mode == "corrupt" else file_hash(observation)}
    def receipt(self, bundle, destination):
        return {"jobId": "OLD-JOB" if self.profile.get("fixtureMode") == "old_job" else bundle["jobId"],
                "packageDigest": bundle["packageDigest"], "videoSha256": file_hash(destination),
                "evidenceKind": "real_device", "manualInterventions": [],
                "watermarkVerifiedAbsent": self.profile.get("fixtureMode") != "watermark"}
    def cancel(self):
        return self.profile.get("cancelConfirmed", False)
"""
