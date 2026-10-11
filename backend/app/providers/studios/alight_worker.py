"""Android admission and auditable execution. No inferred XML exporter.

A local driver is admitted only with pinned files and real-device calibration.
No driver, compiler or calibration is bundled: the absent device stays pending.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from ...domain.studios.contextual_editing import digest

STAGES = ("validate", "compile", "transfer", "import", "export", "retrieve", "verify")
NAME = "alight-motion.contextual-v1"
APP_PACKAGE = "com.alightcreative.motion"


class TransientAlightError(RuntimeError):
    """Only explicitly classified, audited device errors may be retried."""

    def __init__(self, code):
        if code not in {"device_disconnected", "temporary_io_failure"}:
            raise ValueError("alight_unknown_transient_code")
        super().__init__(code)


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _local_file(root, value, checksum):
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file() or file_hash(path) != checksum:
        raise ValueError("alight_profile_file_binding_invalid")
    return path


def load_profile(path):
    root = Path(path).resolve().parent
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for field in ("serial", "package", "appVersion", "androidVersion", "locale", "compilerVersion", "profileId"):
        if not isinstance(data.get(field), str) or not data[field]:
            raise ValueError("alight_profile_incomplete")
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", data["serial"]) or not re.fullmatch(r"[A-Za-z0-9_.]+", data["package"]):
        raise ValueError("alight_device_identifier_invalid")
    if not re.fullmatch(r"[1-9][0-9]*x[1-9][0-9]*", data.get("resolution", "")) or not isinstance(
        data.get("enabledFeatures"), list
    ):
        raise ValueError("alight_device_resources_missing")
    driver = _local_file(root, data["driverFile"], data["driverSha256"])
    calibration = json.loads(
        _local_file(root, data["calibrationFile"], data["calibrationSha256"]).read_text(encoding="utf-8")
    )
    execution_mode = data.get("executionMode", "physical_android_ui")
    if execution_mode not in {"physical_android_ui", "android_emulator_ui"}:
        raise ValueError("alight_execution_mode_invalid")
    evidence_kind = "real_emulator" if execution_mode == "android_emulator_ui" else "real_device"
    if execution_mode == "android_emulator_ui":
        runtime = data.get("emulatorRuntime", {})
        if (
            not all(
                isinstance(runtime.get(key), str) and runtime[key]
                for key in ("vendor", "version", "binaryPath", "binarySha256", "androidHardware")
            )
            or calibration.get("emulatorRuntime") != runtime
            or not Path(runtime["binaryPath"]).is_absolute()
            or not Path(runtime["binaryPath"]).is_file()
            or file_hash(runtime["binaryPath"]) != runtime["binarySha256"]
        ):
            raise ValueError("alight_emulator_runtime_unqualified")
    if (
        calibration.get("evidenceKind") != evidence_kind
        or calibration.get("automated") is not True
        or calibration.get("profileId") != data["profileId"]
        or calibration.get("appVersion") != data["appVersion"]
        or calibration.get("compilerVersion") != data["compilerVersion"]
        or calibration.get("driverSha256") != data["driverSha256"]
        or calibration.get("testedCapabilities") != data.get("testedCapabilities", [])
        or not all(
            calibration.get("checks", {}).get(key) is True
            for key in (
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
            )
        )
    ):
        raise ValueError("alight_real_calibration_required")
    if not {
        "composition.video",
        "composition.image",
        "composition.text",
        "composition.mask",
        "composition.trim",
        "composition.constant_speed",
    }.issubset(data.get("testedCapabilities", [])):
        raise ValueError("alight_basic_capabilities_unqualified")
    samples = calibration.get("samples") or []
    if len(samples) < 2:
        raise ValueError("alight_golden_samples_required")
    for sample in samples:
        _local_file(root, sample["path"], sample["sha256"])
    data["driverPath"] = driver
    data["profileSha256"] = file_hash(path)
    data["calibration"] = calibration
    data["executionMode"] = execution_mode
    return data


class PhysicalAlightWorker:
    def __init__(self, adb="adb", profile_path=None, state_dir=None, timeout=900, execution_mode="physical_android_ui"):
        if execution_mode not in {"physical_android_ui", "android_emulator_ui"}:
            raise ValueError("alight_execution_mode_invalid")
        self.execution_mode = execution_mode
        self.adb = adb
        self.profile_path = profile_path
        self.state_dir = Path(state_dir or Path(__file__).resolve().parents[3] / "storage/alight-worker")
        self.timeout = min(timeout, 900)

    def command(self, *args):
        result = subprocess.run([self.adb, *args], capture_output=True, timeout=10, shell=False)
        if result.returncode:
            raise ValueError("alight_adb_command_failed")
        return result.stdout.decode("utf-8", errors="replace").strip()

    def status(self):
        blockers, profile = [], None
        application_probe = None
        try:
            devices = self.command("devices", "-l")
        except (OSError, subprocess.SubprocessError, ValueError):
            devices = ""
            blockers.append("adb_unavailable")
        serials = {line.split()[0]: line.split()[1] for line in devices.splitlines()[1:] if len(line.split()) >= 2}
        physical = {serial: state for serial, state in serials.items() if not serial.startswith("emulator-")}
        candidates = serials if self.execution_mode == "android_emulator_ui" else physical
        if not candidates and self.execution_mode == "android_emulator_ui":
            blockers.append("emulator_missing")
        if not candidates and self.execution_mode == "physical_android_ui":
            blockers.append("physical_device_missing")
        if not self.profile_path:
            blockers.extend(["validated_import_missing", "validated_compiler_missing", "device_profile_missing"])
            connected = [serial for serial, state in candidates.items() if state == "device"]
            application_probe = {
                "package": APP_PACKAGE,
                "installed": None,
                "version": None,
                "installer": None,
                "connectedDevices": len(connected),
                "observationKind": "adb_package_probe",
                "observedAtUnix": time.time(),
            }
            if len(connected) > 1:
                blockers.append("device_selection_required")
            elif len(connected) == 1:
                serial = connected[0]
                # Discovery is read-only and never grants rendering capabilities.
                # The planner cannot choose a package or inject an ADB command.
                if not re.fullmatch(r"[A-Za-z0-9._:-]+", serial):
                    blockers.append("alight_application_probe_failed")
                else:
                    try:
                        package = self.command("-s", serial, "shell", "dumpsys", "package", APP_PACKAGE)
                        version = re.search(r"^\s*versionName=(\S+)\s*$", package, re.MULTILINE)
                        installer = re.search(r"^\s*installerPackageName=(\S+)\s*$", package, re.MULTILINE)
                        application_probe.update(
                            installed=version is not None,
                            version=version.group(1) if version else None,
                            installer=installer.group(1) if installer else None,
                        )
                        if not version:
                            blockers.append("alight_app_missing")
                    except (OSError, subprocess.SubprocessError, ValueError):
                        blockers.append("alight_application_probe_failed")
            elif candidates:
                blockers.append("device_not_authorized_or_connected")
        else:
            try:
                profile = load_profile(self.profile_path)
                if profile["executionMode"] != self.execution_mode:
                    blockers.append("execution_mode_profile_conflict")
                if profile["serial"].startswith("emulator-") and self.execution_mode == "physical_android_ui":
                    blockers.append("emulator_excluded")
                if candidates.get(profile["serial"]) != "device":
                    blockers.append("device_not_authorized_or_connected")
                else:
                    serial = profile["serial"]
                    package = self.command("-s", serial, "shell", "dumpsys", "package", profile["package"])
                    if f"versionName={profile['appVersion']}" not in package.split():
                        blockers.append("app_version_changed")
                    if (
                        self.command("-s", serial, "shell", "getprop", "ro.kernel.qemu") == "1"
                        and self.execution_mode == "physical_android_ui"
                    ):
                        blockers.append("emulator_excluded")
                    if self.execution_mode == "android_emulator_ui" and (
                        self.command("-s", serial, "shell", "getprop", "ro.hardware")
                        != profile["emulatorRuntime"]["androidHardware"]
                    ):
                        blockers.append("emulator_runtime_changed")
                    if (
                        self.command("-s", serial, "shell", "getprop", "ro.build.version.release")
                        != profile["androidVersion"]
                    ):
                        blockers.append("android_version_changed")
                    locale = self.command("-s", serial, "shell", "getprop", "persist.sys.locale")
                    if locale != profile["locale"]:
                        blockers.append("device_locale_changed")
                    resolution = self.command("-s", serial, "shell", "wm", "size").splitlines()
                    if not resolution or resolution[-1].split(": ")[-1] != profile["resolution"]:
                        blockers.append("device_resolution_changed")
                key = digest(profile["serial"])
                if (self.state_dir / (key + ".quarantine")).exists():
                    blockers.append("device_quarantined")
                if (self.state_dir / (key + ".lock")).exists():
                    blockers.append("device_busy")
            except (KeyError, OSError, ValueError, subprocess.SubprocessError):
                blockers.append("profile_or_calibration_invalid")
        return {
            "provider": NAME,
            "available": not blockers,
            "profileId": profile["profileId"] if profile else None,
            "providerVersion": profile["appVersion"] if profile else "unqualified",
            "compilerVersion": profile["compilerVersion"] if profile else None,
            "profileSha256": profile["profileSha256"] if profile else None,
            "capabilities": profile.get("testedCapabilities", []) if profile and not blockers else [],
            "blockers": sorted(set(blockers)),
            "executionMode": self.execution_mode,
            "officialApi": "not_identified",
            "commercialQualified": False,
            "emulatorRuntime": profile.get("emulatorRuntime") if profile else None,
            "applicationProbe": application_probe,
        }

    def render(self, bundle, root, destination, progress, is_cancelled):
        try:
            return self._render_once(bundle, root, destination, progress, is_cancelled)
        except TransientAlightError:
            failure = self.state_dir / (digest(bundle["jobId"]) + ".failure.json")
            evidence = json.loads(failure.read_text(encoding="utf-8")) if failure.is_file() else {}
            if evidence.get("interruptionConfirmed") is not True or is_cancelled():
                raise
            # The next attempt must re-probe the pinned profile and prove its
            # resume state; it cannot simply collect an existing export.
            Path(destination).unlink(missing_ok=True)
            result = self._render_once(bundle, root, destination, progress, is_cancelled)
            result["attempts"] = 2
            result["journal"] = [{**stage, "attempt": 1} for stage in evidence.get("journal", [])] + [
                {**stage, "attempt": 2} for stage in result["journal"]
            ]
            result["transientRecoveryVerified"] = True
            return result

    def _render_once(self, bundle, root, destination, progress, is_cancelled):
        status = self.status()
        if not status["available"]:
            raise ValueError("alight_unavailable:" + ",".join(status["blockers"]))
        profile = load_profile(self.profile_path)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        key = digest(profile["serial"])
        lock = self.state_dir / (key + ".lock")
        quarantine = self.state_dir / (key + ".quarantine")
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ValueError("alight_device_busy") from exc
        os.close(descriptor)
        journal = []
        checkpoint = self.state_dir / (digest(bundle["jobId"]) + ".json")
        started = time.monotonic()
        driver = None
        succeeded = False
        failure_code = None
        try:
            (self.state_dir / (digest(bundle["jobId"]) + ".running.json")).write_text(
                json.dumps({"jobId": bundle["jobId"], "deadlineUnix": time.time() + self.timeout}), encoding="utf-8"
            )
            # Export must be produced during this attempt; an existing host file
            # is never accepted as its output.
            Path(destination).unlink(missing_ok=True)
            spec = importlib.util.spec_from_file_location("res_alight_calibrated_driver", profile["driverPath"])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            driver = module.Driver(self, profile)
            # The driver is trusted, server-installed, hashed code. The planner
            # never supplies module names, executable commands or XML.
            if checkpoint.exists():
                previous = json.loads(checkpoint.read_text(encoding="utf-8"))
                if previous.get("packageDigest") != bundle["packageDigest"]:
                    raise ValueError("alight_checkpoint_package_mismatch")
                if previous.get("profileSha256") != profile["profileSha256"]:
                    raise ValueError("alight_checkpoint_profile_changed")
                if not driver.confirm_resume(previous, bundle):
                    raise ValueError("alight_resume_state_unproven")
            for index, stage in enumerate(STAGES):
                if is_cancelled():
                    raise InterruptedError("alight_render_cancelled")
                if time.monotonic() - started > self.timeout:
                    raise TimeoutError("alight_render_timeout")
                step_started = time.monotonic()
                evidence = driver.execute(
                    stage, bundle, root, destination, self.timeout - (step_started - started), is_cancelled
                )
                if not evidence or evidence.get("confirmed") is not True:
                    raise ValueError("alight_stage_unconfirmed:" + stage)
                observation = _local_file(
                    Path(root).resolve(), evidence.get("observationPath", ""), evidence.get("observationSha256")
                )
                retained = self.state_dir / digest(bundle["jobId"]) / "observations"
                retained.mkdir(parents=True, exist_ok=True)
                observed_name = stage + "-" + evidence["observationSha256"] + observation.suffix
                shutil.copyfile(observation, retained / observed_name)
                evidence = {**evidence, "observationPath": str((retained / observed_name).relative_to(self.state_dir))}
                journal.append(
                    {
                        "stage": stage,
                        "durationMs": round((time.monotonic() - step_started) * 1000),
                        "evidence": evidence,
                    }
                )
                value = {
                    "jobId": bundle["jobId"],
                    "packageDigest": bundle["packageDigest"],
                    "profileSha256": profile["profileSha256"],
                    "journal": journal,
                }
                temporary = checkpoint.with_suffix(".pending")
                temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                temporary.replace(checkpoint)
                progress(round((index + 1) / len(STAGES) * 95))
            receipt = driver.receipt(bundle, destination)
            if (
                receipt.get("jobId") != bundle["jobId"]
                or receipt.get("packageDigest") != bundle["packageDigest"]
                or receipt.get("videoSha256") != file_hash(destination)
                or receipt.get("evidenceKind")
                != ("real_emulator" if self.execution_mode == "android_emulator_ui" else "real_device")
                or receipt.get("manualInterventions") != []
                or receipt.get("watermarkVerifiedAbsent") is not True
            ):
                raise ValueError("alight_receipt_binding_invalid")
            succeeded = True
            return {
                **receipt,
                "journal": journal,
                "profileSha256": profile["profileSha256"],
                "profileId": profile["profileId"],
                "appVersion": profile["appVersion"],
                "compilerVersion": profile["compilerVersion"],
                "attempts": 1,
                "executionMode": self.execution_mode,
                "emulatorRuntime": profile.get("emulatorRuntime"),
                "apiCostUsd": 0,
                "geometryObservation": "unavailable",
                "sourceTimesBasis": "declared_plan",
            }
        except BaseException as exc:
            failure_code = str(exc)
            raise
        finally:
            if not succeeded:
                confirmed = False
                if driver:
                    try:
                        confirmed = driver.cancel() is True
                    except Exception:
                        confirmed = False
                if not confirmed:
                    quarantine.write_text(
                        "Interruption not confirmed; inspect logs and device before recovery.", encoding="utf-8"
                    )
                checkpoint.with_suffix(".failure.json").write_text(
                    json.dumps(
                        {
                            "journal": journal,
                            "interruptionConfirmed": confirmed,
                            "packageDigest": bundle["packageDigest"],
                            "jobId": bundle["jobId"],
                            "error": failure_code,
                            "failedAtUnix": time.time(),
                        }
                    ),
                    encoding="utf-8",
                )
            (self.state_dir / (digest(bundle["jobId"]) + ".running.json")).unlink(missing_ok=True)
            lock.unlink(missing_ok=True)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["probe", "render"])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--profile")
    parser.add_argument("--state")
    parser.add_argument("--bundle")
    parser.add_argument("--output")
    parser.add_argument("--receipt")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument(
        "--execution-mode", choices=["physical_android_ui", "android_emulator_ui"], default="physical_android_ui"
    )
    args = parser.parse_args()
    if args.operation == "render" and not all((args.profile, args.bundle, args.output, args.receipt)):
        parser.error("render requires --profile, --bundle, --output and --receipt")
    worker = PhysicalAlightWorker(args.adb, args.profile, args.state, args.timeout, args.execution_mode)
    if args.operation == "probe":
        print(json.dumps(worker.status()))
        return
    root = Path(args.bundle).resolve()
    bundle = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    expected = bundle.pop("packageDigest")
    if digest(bundle) != expected:
        raise ValueError("alight_manifest_digest_invalid")
    bundle["packageDigest"] = expected
    for value in bundle["assets"].values():
        _local_file(root, value["path"], value["sha256"])
    receipt = worker.render(
        bundle, root, Path(args.output), lambda value: print(json.dumps({"progress": value}), flush=True), lambda: False
    )
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
