"""Read-only prerequisites and artifacts. Never downloads or substitutes a renderer."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    lock = json.loads((ROOT / "workers/craft/sources.lock.json").read_text())
    docker = shutil.which("docker")
    daemon = None
    if docker:
        try:
            process = subprocess.run([docker, "info", "--format", "{{.OSType}}"], timeout=15,
                                     capture_output=True, text=True, check=False)
            daemon = process.stdout.strip() if process.returncode == 0 else "unavailable"
        except (OSError, subprocess.TimeoutExpired):
            daemon = "unavailable"
    engines = {}
    for name in ("photocraft", "filmcraft", "effectcraft"):
        source = next(value for value in lock["sources"] if value["name"] == name)
        browser = ROOT / "public/craft" / name
        native = ROOT / "workers/craft/bin" / ("clicko-" + name + "-adapter")
        wasm = all((browser / filename).is_file() for filename in (
            "clicko_" + name + "_adapter.js", "clicko_" + name + "_adapter_bg.wasm", "manifest.json"))
        engines[name] = {"sourceRevision": source["commit"], "sourceVersion": source["version"],
            "nativeArtifactPresent": native.is_file(), "browserArtifactsPresent": wasm,
            "qualification": "present-not-yet-tested" if wasm or native.is_file() else "blocked-missing-build",
            "requiredValidation": "commands, preview, native round-trip, export, provenance and licenses"}
    result = {"schemaVersion": "clicko.craft-preflight.v1", "dockerExecutable": bool(docker),
        "dockerLinuxDaemon": daemon == "linux", "rustToolchainRequired": lock["rustToolchain"],
        "wasmBindgenRequired": lock["wasmBindgenVersion"], "engines": engines,
        "buildAvailable": daemon == "linux", "doesNotQualifyEngines": True}
    print(json.dumps(result, indent=2))
    return 0 if result["buildAvailable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
