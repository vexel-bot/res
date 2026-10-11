"""Driver simulations audit the worker boundary, never qualify the Android app."""

import json

import pytest

from app.domain.studios.contextual_editing import digest
from app.providers.studios.alight_worker import PhysicalAlightWorker, file_hash, load_profile

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


@pytest.fixture
def simulated_worker(tmp_path, monkeypatch):
    driver = tmp_path / "driver.py"
    driver.write_text(DRIVER, encoding="utf-8")
    profile = {
        "serial": "PHYSICAL-FIXTURE",
        "driverPath": driver,
        "profileSha256": "a" * 64,
        "profileId": "software-test",
        "appVersion": "fixture",
        "compilerVersion": "fixture",
    }
    monkeypatch.setattr("app.providers.studios.alight_worker.load_profile", lambda _: profile)
    worker = PhysicalAlightWorker(profile_path=tmp_path / "profile.json", state_dir=tmp_path / "state")
    monkeypatch.setattr(worker, "status", lambda: {"available": True})
    return worker, profile, tmp_path


@pytest.mark.parametrize("mode", ["unknown", "no_space", "unconfirmed", "corrupt", "old_job", "watermark"])
def test_unknown_or_invalid_output_is_audited_and_quarantined(simulated_worker, mode):
    worker, profile, root = simulated_worker
    profile["fixtureMode"] = mode
    bundle = {"jobId": "job-1", "packageDigest": "b" * 64}
    with pytest.raises(ValueError):
        worker.render(bundle, root, root / "output.mp4", lambda _: None, lambda: False)
    assert (worker.state_dir / (digest(profile["serial"]) + ".quarantine")).is_file()
    failure = json.loads((worker.state_dir / (digest("job-1") + ".failure.json")).read_text())
    assert failure["error"] and failure["jobId"] == "job-1"
    assert failure["interruptionConfirmed"] is False
    assert not list(worker.state_dir.glob("*.lock"))


def test_cancel_blocks_delivery_and_releases_lock_with_audited_interruption(simulated_worker):
    worker, profile, root = simulated_worker
    profile["cancelConfirmed"] = True
    with pytest.raises(InterruptedError):
        worker.render(
            {"jobId": "cancelled", "packageDigest": "b" * 64}, root, root / "output", lambda _: None, lambda: True
        )
    failure = json.loads((worker.state_dir / (digest("cancelled") + ".failure.json")).read_text())
    assert failure["interruptionConfirmed"] and "cancelled" in failure["error"]
    assert not list(worker.state_dir.glob("*.quarantine"))
    assert not (root / "output").exists()


def test_worker_timeout_has_error_evidence(simulated_worker):
    worker, profile, root = simulated_worker
    worker.timeout = -1  # Force the elapsed-time branch without sleeping.
    profile["cancelConfirmed"] = True
    with pytest.raises(TimeoutError):
        worker.render(
            {"jobId": "timeout", "packageDigest": "b" * 64}, root, root / "output", lambda _: None, lambda: False
        )
    evidence = json.loads((worker.state_dir / (digest("timeout") + ".failure.json")).read_text())
    assert evidence["error"] == "alight_render_timeout"


@pytest.mark.parametrize("changed", ["packageDigest", "profileSha256", "resumeState"])
def test_restart_requires_same_package_profile_and_proven_state(simulated_worker, changed):
    worker, profile, root = simulated_worker
    profile["cancelConfirmed"] = True
    worker.state_dir.mkdir()
    previous = {"packageDigest": "b" * 64, "profileSha256": profile["profileSha256"]}
    if changed != "resumeState":
        previous[changed] = "c" * 64
    (worker.state_dir / (digest("restart") + ".json")).write_text(json.dumps(previous))
    with pytest.raises(ValueError, match="checkpoint|resume_state"):
        worker.render(
            {"jobId": "restart", "packageDigest": "b" * 64}, root, root / "output", lambda _: None, lambda: False
        )


def test_single_transient_retry_retains_evidence_and_never_uses_prior_host_file(simulated_worker):
    worker, profile, root = simulated_worker
    profile.update(fixtureMode="transient", cancelConfirmed=True, allowResume=True)
    destination = root / "output"
    destination.write_bytes(b"OLD HOST FILE")
    result = worker.render(
        {"jobId": "retry", "packageDigest": "b" * 64}, root, destination, lambda _: None, lambda: False
    )
    assert result["attempts"] == 2 and result["transientRecoveryVerified"]
    assert {entry["attempt"] for entry in result["journal"]} == {1, 2}
    for entry in result["journal"]:
        observed = worker.state_dir / entry["evidence"]["observationPath"]
        assert file_hash(observed) == entry["evidence"]["observationSha256"]
    assert destination.read_bytes() == b"SIMULATED OUTPUT"


def test_exclusive_device_lock_rejects_another_job(simulated_worker):
    worker, profile, root = simulated_worker
    worker.state_dir.mkdir()
    lock = worker.state_dir / (digest(profile["serial"]) + ".lock")
    lock.write_text("another job")
    with pytest.raises(ValueError, match="device_busy"):
        worker.render(
            {"jobId": "parallel", "packageDigest": "b" * 64}, root, root / "output", lambda _: None, lambda: False
        )
    assert lock.read_text() == "another job"


def test_emulator_mode_does_not_claim_a_missing_phone(tmp_path, monkeypatch):
    worker = PhysicalAlightWorker(state_dir=tmp_path, execution_mode="android_emulator_ui")
    monkeypatch.setattr(worker, "command", lambda *args: "List of devices attached\n")
    status = worker.status()
    assert not status["available"] and "emulator_missing" in status["blockers"]
    assert "physical_device_missing" not in status["blockers"]
    assert status["executionMode"] == "android_emulator_ui"


def test_installed_application_is_observed_without_admitting_render(tmp_path, monkeypatch):
    worker = PhysicalAlightWorker(state_dir=tmp_path, execution_mode="android_emulator_ui")
    calls = []

    def command(*args):
        calls.append(args)
        if args == ("devices", "-l"):
            return "List of devices attached\nemulator-5554 device\n"
        assert args == ("-s", "emulator-5554", "shell", "dumpsys", "package", "com.alightcreative.motion")
        return "  versionName=5.0.273.1028425\n  installerPackageName=com.android.vending\nPRIVATE_ACCOUNT_DATA"

    monkeypatch.setattr(worker, "command", command)
    status = worker.status()
    assert status["applicationProbe"]["installed"] is True
    assert status["applicationProbe"]["version"] == "5.0.273.1028425"
    assert status["applicationProbe"]["installer"] == "com.android.vending"
    assert "PRIVATE_ACCOUNT_DATA" not in json.dumps(status)
    assert not status["available"] and not status["capabilities"]
    assert "validated_import_missing" in status["blockers"]
    assert len(calls) == 2


@pytest.mark.parametrize("state", ["ambiguous", "offline", "failed", "missing"])
def test_application_discovery_does_not_guess_device_or_success(tmp_path, monkeypatch, state):
    worker = PhysicalAlightWorker(state_dir=tmp_path, execution_mode="android_emulator_ui")
    calls = []

    def command(*args):
        calls.append(args)
        if args == ("devices", "-l"):
            devices = {
                "ambiguous": "emulator-5554 device\nemulator-5556 device",
                "offline": "emulator-5554 offline",
            }.get(state, "emulator-5554 device")
            return "List of devices attached\n" + devices
        if state == "failed":
            raise ValueError("alight_adb_command_failed")
        return "Unable to find package: com.alightcreative.motion"

    monkeypatch.setattr(worker, "command", command)
    status = worker.status()
    expected = {
        "ambiguous": "device_selection_required", "offline": "device_not_authorized_or_connected",
        "failed": "alight_application_probe_failed", "missing": "alight_app_missing",
    }[state]
    assert expected in status["blockers"] and not status["available"]
    assert status["applicationProbe"]["installed"] is (False if state == "missing" else None)
    if state in {"ambiguous", "offline"}:
        assert len(calls) == 1


def test_emulator_job_rejects_a_receipt_claiming_physical_device(simulated_worker):
    worker, profile, root = simulated_worker
    worker.execution_mode = "android_emulator_ui"
    with pytest.raises(ValueError, match="receipt_binding_invalid"):
        worker.render(
            {"jobId": "emulator-test", "packageDigest": "b" * 64},
            root,
            root / "output.mp4",
            lambda _: None,
            lambda: False,
        )


@pytest.mark.parametrize("execution_mode", ["physical_android_ui", "android_emulator_ui"])
def test_profile_pins_driver_calibration_resources_and_capabilities(tmp_path, execution_mode):
    # These files are software fixtures; their labels never enter a real campaign.
    (tmp_path / "driver.py").write_text(DRIVER)
    (tmp_path / "original.project").write_bytes(b"fixture original")
    (tmp_path / "changed.project").write_bytes(b"fixture changed")
    capabilities = ["composition." + v for v in ["video", "image", "text", "mask", "trim", "constant_speed"]]
    data = {
        "serial": "fixture",
        "package": "fixture.app",
        "appVersion": "fixture",
        "androidVersion": "fixture",
        "locale": "pt-BR",
        "resolution": "1080x1920",
        "enabledFeatures": [],
        "compilerVersion": "fixture",
        "profileId": "fixture",
        "driverFile": "driver.py",
        "driverSha256": file_hash(tmp_path / "driver.py"),
        "calibrationFile": "calibration.json",
        "testedCapabilities": capabilities,
    }
    data["executionMode"] = execution_mode
    if execution_mode == "android_emulator_ui":
        runtime_binary = tmp_path / "runtime.fixture"
        runtime_binary.write_bytes(b"SOFTWARE FIXTURE ONLY")
        data["emulatorRuntime"] = {
            "vendor": "SOFTWARE FIXTURE",
            "version": "fixture",
            "binaryPath": str(runtime_binary.resolve()),
            "binarySha256": file_hash(runtime_binary),
            "androidHardware": "fixture",
        }
    calibration = {
        "evidenceKind": "real_emulator" if execution_mode == "android_emulator_ui" else "real_device",
        "automated": True,
        "profileId": "fixture",
        "appVersion": "fixture",
        "compilerVersion": "fixture",
        "driverSha256": data["driverSha256"],
        "testedCapabilities": capabilities,
        "checks": {
            key: True
            for key in [
                "editableImport",
                "assetBindings",
                "fontBindings",
                "textChange",
                "assetChange",
                "durationChange",
                "silentExport",
                "basicComposition",
                "mixedSourceFpsTrim",
                "constantSpeed",
                "aspectPreservation",
                "maskOverlap",
            ]
        },
        "samples": [
            {"path": name, "sha256": file_hash(tmp_path / name)} for name in ["original.project", "changed.project"]
        ],
    }
    if execution_mode == "android_emulator_ui":
        calibration["emulatorRuntime"] = data["emulatorRuntime"]
    (tmp_path / "calibration.json").write_text(json.dumps(calibration))
    data["calibrationSha256"] = file_hash(tmp_path / "calibration.json")
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(data))
    assert load_profile(path)["profileSha256"] == file_hash(path)
    data["testedCapabilities"].append("recipe.displacement")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="real_calibration"):
        load_profile(path)
    path.write_text(json.dumps({**data, "testedCapabilities": capabilities[:-1]}))
    (tmp_path / "driver.py").write_text("changed")
    with pytest.raises(ValueError, match="file_binding"):
        load_profile(path)
