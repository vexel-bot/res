from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VERIFIER = REPOSITORY_ROOT / "backend/scripts/verify_preflight_oci.py"


def _blob(root: Path, payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "blobs" / "sha256" / digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return f"sha256:{digest}"


def _write_fixture(
    tmp_path: Path,
    *,
    provider_label: str = "none",
    nested_index: bool = False,
    descriptor_binding: bool = False,
) -> Path:
    root = tmp_path / "layout"
    (root / "blobs" / "sha256").mkdir(parents=True)
    (root / "oci-layout").write_text(json.dumps({"imageLayoutVersion": "1.0.0"}), encoding="utf-8")

    config = {
        "config": {
            "Labels": {
                "org.opencontainers.image.title": "Clicko speech CPU preflight",
                "io.clicko.providers": provider_label,
            }
        }
    }
    config_digest = _blob(root, json.dumps(config).encode())
    image = {
        "schemaVersion": 2,
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": config_digest,
            "size": 1,
        },
        "layers": [],
    }
    image_digest = _blob(root, json.dumps(image).encode())

    image_sha256 = image_digest.removeprefix("sha256:")
    provenance_digest = _blob(
        root,
        json.dumps(
            {
                "_type": "https://in-toto.io/Statement/v1",
                "subject": (
                    []
                    if descriptor_binding
                    else [{"name": "fixture", "digest": {"sha256": image_sha256}}]
                ),
                "predicateType": "https://slsa.dev/provenance/v1",
                "predicate": {"buildDefinition": {}, "runDetails": {}},
            }
        ).encode(),
    )
    sbom_digest = _blob(
        root,
        json.dumps(
            {
                "_type": "https://in-toto.io/Statement/v1",
                "subject": (
                    []
                    if descriptor_binding
                    else [{"name": "fixture", "digest": {"sha256": image_sha256}}]
                ),
                "predicateType": "https://spdx.dev/Document",
                "predicate": {"spdxVersion": "SPDX-2.3"},
            }
        ).encode(),
    )
    attestation = {
        "schemaVersion": 2,
        "layers": [
            {"mediaType": "application/vnd.in-toto+json", "digest": provenance_digest, "size": 1},
            {"mediaType": "application/vnd.in-toto+json", "digest": sbom_digest, "size": 1},
        ],
    }
    attestation_digest = _blob(root, json.dumps(attestation).encode())
    index = {
        "schemaVersion": 2,
        "manifests": [
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": image_digest,
                "size": 1,
                "platform": {"architecture": "amd64", "os": "linux"},
            },
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": attestation_digest,
                "size": 1,
                "annotations": {
                    "vnd.docker.reference.type": "attestation-manifest",
                    **(
                        {"vnd.docker.reference.digest": image_digest}
                        if descriptor_binding
                        else {}
                    ),
                },
            },
        ],
    }
    if nested_index:
        nested_digest = _blob(root, json.dumps(index).encode())
        index = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "manifests": [
                {
                    "mediaType": "application/vnd.oci.image.index.v1+json",
                    "digest": nested_digest,
                    "size": 1,
                }
            ],
        }
    (root / "index.json").write_text(json.dumps(index), encoding="utf-8")
    archive = tmp_path / "preflight.oci.tar"
    with tarfile.open(archive, "w") as tar:
        for path in root.rglob("*"):
            if path.is_file():
                tar.add(path, arcname=path.relative_to(root))
    return archive


def _run(archive: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), str(archive), "--title", "Clicko speech CPU preflight"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_preflight_oci_verifier_accepts_linux_amd64_with_attestations(tmp_path: Path) -> None:
    archive = _write_fixture(tmp_path)
    completed = _run(archive)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {
        "architecture": "amd64",
        "attestationCount": 1,
        "attestationBindingMethods": ["statement_subject"],
        "imageDigest": result["imageDigest"],
        "providerLabel": "none",
        "status": "preflight-oci-verified",
        "title": "Clicko speech CPU preflight",
    }
    assert result["imageDigest"].startswith("sha256:")


def test_preflight_oci_verifier_accepts_buildkit_nested_index(tmp_path: Path) -> None:
    completed = _run(_write_fixture(tmp_path, nested_index=True))
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "preflight-oci-verified"
    assert result["attestationCount"] == 1
    assert result["attestationBindingMethods"] == ["statement_subject"]
    assert result["imageDigest"].startswith("sha256:")


def test_preflight_oci_verifier_accepts_buildkit_descriptor_binding(tmp_path: Path) -> None:
    completed = _run(
        _write_fixture(tmp_path, nested_index=True, descriptor_binding=True)
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["attestationBindingMethods"] == ["oci_reference_digest"]


def test_preflight_oci_verifier_rejects_provider_label(tmp_path: Path) -> None:
    completed = _run(_write_fixture(tmp_path, provider_label="kokoro"))
    assert completed.returncode != 0
    assert "oci_provider_label_mismatch" in completed.stderr


def test_preflight_oci_verifier_rejects_missing_attestation(tmp_path: Path) -> None:
    archive = _write_fixture(tmp_path)
    rewritten = tmp_path / "no-attestation.oci.tar"
    with tarfile.open(archive, "r") as source, tarfile.open(rewritten, "w") as target:
        for member in source.getmembers():
            if member.name == "index.json":
                payload = json.loads(source.extractfile(member).read())
                payload["manifests"] = payload["manifests"][:1]
                data = json.dumps(payload).encode()
                info = tarfile.TarInfo(member.name)
                info.size = len(data)
                target.addfile(info, fileobj=io.BytesIO(data))
            else:
                target.addfile(member, source.extractfile(member) if member.isfile() else None)
    completed = _run(rewritten)
    assert completed.returncode != 0
    assert "oci_attestation_missing" in completed.stderr


def test_preflight_oci_verifier_rejects_unbound_attestation(tmp_path: Path) -> None:
    archive = _write_fixture(tmp_path)
    unpacked = tmp_path / "unbound-layout"
    with tarfile.open(archive, "r") as source:
        source.extractall(unpacked)
    index = json.loads((unpacked / "index.json").read_text(encoding="utf-8"))
    attestation_descriptor = index["manifests"][1]
    attestation_path = (
        unpacked
        / "blobs"
        / "sha256"
        / attestation_descriptor["digest"].removeprefix("sha256:")
    )
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    layer = attestation["layers"][0]
    statement_path = (
        unpacked / "blobs" / "sha256" / layer["digest"].removeprefix("sha256:")
    )
    statement = json.loads(statement_path.read_text(encoding="utf-8"))
    statement["subject"][0]["digest"]["sha256"] = "0" * 64
    payload = json.dumps(statement).encode()
    new_statement_digest = hashlib.sha256(payload).hexdigest()
    new_statement_path = unpacked / "blobs" / "sha256" / new_statement_digest
    new_statement_path.write_bytes(payload)
    layer["digest"] = f"sha256:{new_statement_digest}"
    attestation_payload = json.dumps(attestation).encode()
    new_attestation_digest = hashlib.sha256(attestation_payload).hexdigest()
    (unpacked / "blobs" / "sha256" / new_attestation_digest).write_bytes(
        attestation_payload
    )
    attestation_descriptor["digest"] = f"sha256:{new_attestation_digest}"
    (unpacked / "index.json").write_text(json.dumps(index), encoding="utf-8")
    rewritten = tmp_path / "unbound.oci.tar"
    with tarfile.open(rewritten, "w") as target:
        for path in unpacked.rglob("*"):
            if path.is_file():
                target.add(path, arcname=path.relative_to(unpacked))

    completed = _run(rewritten)
    assert completed.returncode != 0
    assert "oci_attestation_subject_binding_missing" in completed.stderr
