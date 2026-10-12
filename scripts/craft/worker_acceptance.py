"""Validate actual tools/binary hashes in the built, isolated media worker image.

Produces local attestation and a CycloneDX inventory of installed Python/Debian
packages and locked Rust dependencies. No broker, paid provider or secret is used.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import tomllib
from urllib.parse import quote
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".codex-runtime/craft"
PROBE = """
import hashlib, json, os, socket, subprocess
from pathlib import Path
from app.config import Settings
from app.services.studios.worker_runtime import load_worker_manifest, validate_worker_manifest, manifest_digest
assert os.getuid() == 10001, 'Worker must run as Clicko non-root user'
assert socket.if_nameindex() == [(1, 'lo')], 'Unexpected network interface'
mount = next(line.split() for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1] == '/')
assert 'ro' in mount[3].split(','), 'Worker root filesystem must be read-only'
Path(os.environ['TMPDIR']).mkdir(parents=True, exist_ok=True)
manifest = load_worker_manifest('/opt/clicko/worker-manifest.json')
versions = validate_worker_manifest(manifest, Settings(_env_file=None))
native = json.loads(Path('/opt/clicko/runtime-manifest.json').read_text())
for engine, build in native['engines'].items():
    binary = Path('/opt/clicko/bin') / ('clicko-' + engine + '-adapter')
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == build['sha256'], engine
freeze = subprocess.check_output(['python', '-m', 'pip', 'freeze'], text=True).splitlines()
debian = subprocess.check_output(['dpkg-query', '-W', '-f=${binary:Package}\\t${Version}\\t${Architecture}\\n'], text=True).splitlines()
print(json.dumps({'schemaVersion': 'clicko.craft-worker-attestation.v1',
    'uid': os.getuid(), 'network': 'none', 'readOnly': True, 'tools': versions,
    'workerManifestSha256': manifest_digest(manifest), 'nativeRuntime': native,
    'pipFreeze': freeze, 'debianPackages': debian}))
"""


def inventory(attestation):
    components = {}

    def add(name, version, ecosystem, *, checksum=None, reference=None):
        purl = f"pkg:{ecosystem}/{quote(name, safe='')}@{quote(version, safe='')}"
        component = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": purl,
            "bom-ref": purl,
        }
        if checksum:
            component["hashes"] = [{"alg": "SHA-256", "content": checksum}]
        if reference:
            component["externalReferences"] = [{"type": "vcs", "url": reference}]
        components[purl] = component

    for line in attestation["pipFreeze"]:
        if "==" in line:
            name, version = line.split("==", 1)
            add(name.lower().replace("_", "-"), version, "pypi")
    for line in attestation["debianPackages"]:
        name, version, _architecture = line.split("\t")
        add(name, version, "deb/debian")
    for adapter in ("photo", "film", "effect"):
        lock = tomllib.loads(
            (ROOT / f"workers/craft/adapters/{adapter}/Cargo.lock").read_text(
                encoding="utf-8"
            )
        )
        for package in lock["package"]:
            add(
                package["name"],
                package["version"],
                "cargo",
                checksum=package.get("checksum"),
                reference=package.get("source", "").removeprefix("git+")
                if package.get("source", "").startswith("git+")
                else None,
            )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "serialNumber": "urn:uuid:" + str(uuid4()),
        "metadata": {
            "timestamp": attestation["verifiedAt"],
            "component": {
                "type": "container",
                "name": "clicko-media-cpu",
                "version": attestation["imageId"],
                "hashes": [
                    {
                        "alg": "SHA-256",
                        "content": attestation["imageId"].removeprefix("sha256:"),
                    }
                ],
            },
        },
        "components": sorted(components.values(), key=lambda item: item["purl"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="clicko-media-cpu:craft")
    args = parser.parse_args()
    image = json.loads(
        subprocess.check_output(["docker", "image", "inspect", args.image], text=True)
    )[0]
    name = "clicko-craft-worker-probe-" + uuid4().hex
    command = [
        "docker",
        "run",
        "--rm",
        "-i",
        "--name",
        name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "512m",
        "--cpus",
        "2",
        "--tmpfs",
        "/tmp:rw,nosuid,size=128m,mode=1777",
        "-e",
        "DATABASE_URL=sqlite:////tmp/clicko-craft/probe.sqlite",
        "-e",
        "REDIS_URL=redis://127.0.0.1:6379/0",
        "-e",
        "ENVIRONMENT=development",
        image["Id"],
        "python",
        "-",
    ]
    try:
        result = subprocess.run(
            command, input=PROBE, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["docker", "rm", "--force", name],
            capture_output=True,
            timeout=20,
            check=False,
        )
        raise
    if result.returncode:
        raise RuntimeError("Worker validation failed: " + result.stderr[-3000:])
    attestation = json.loads(result.stdout)
    attestation["imageId"] = image["Id"]
    attestation["repoDigests"] = image.get("RepoDigests", [])
    attestation["verifiedAt"] = datetime.now(UTC).isoformat()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "media-worker-attestation.json").write_text(
        json.dumps(attestation, indent=2) + "\n", encoding="utf-8"
    )
    bom = inventory(attestation)
    (OUTPUT / "media-worker-sbom.cdx.json").write_text(
        json.dumps(bom, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Worker attested: {image['Id']}; non-root, read-only, no network; {len(attestation['tools'])} tools verified."
    )
    print(
        f"Recorded {len(bom['components'])} installed/locked dependency components in the CycloneDX inventory."
    )


if __name__ == "__main__":
    main()
