from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.studios.speech_assets import (
    ESPEAK_REQUIRED_RUNTIME_FILES,
    EspeakRuntimeManifestV1,
    espeak_runtime_manifest_digest,
    verify_espeak_runtime,
)
from scripts.generate_espeak_runtime_manifest import build_manifest
from scripts.install_espeak_runtime_replacement import install_replacement

SOURCE_REVISION = "7d426728fe146f4168fa716e29d8e276c7da33f2"
BUNDLED_REVISION = "4870adfa25b1a32b4361592f1be8a40337c58d6c"


def _fixture(tmp_path: Path):
    runtime = tmp_path / "espeak-runtime"
    for index, relative in enumerate(sorted(ESPEAK_REQUIRED_RUNTIME_FILES), start=1):
        destination = runtime / Path(*relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(f"runtime-{index}-{relative}".encode())
    (runtime / "build" / "source-revision.txt").write_text(
        SOURCE_REVISION,
        encoding="utf-8",
    )
    (runtime / "build" / "base-image-digest.txt").write_text(
        f"sha256:{'b' * 64}",
        encoding="utf-8",
    )
    (runtime / "build" / "compiler.txt").write_text("gcc 14.2.0", encoding="utf-8")
    (runtime / "build" / "cmake.txt").write_text("3.31.6", encoding="utf-8")
    (runtime / "build" / "flags.txt").write_text(
        "BUILD_SHARED_LIBS=ON\n"
        "USE_LIBSONIC=OFF\n"
        "USE_MBROLA=OFF\n"
        "USE_SPEECHPLAYER=OFF\n",
        encoding="utf-8",
    )
    extra = runtime / "share" / "espeak-ng-data" / "voices" / "mb" / "mb-br1"
    extra.parent.mkdir(parents=True, exist_ok=True)
    extra.write_bytes(b"pt-BR-voice-data")
    recipe = tmp_path / "Dockerfile.espeak-runtime"
    recipe.write_text("FROM scratch\n", encoding="utf-8")
    manifest = build_manifest(
        runtime,
        build_recipe=recipe,
        loader_wheel_digest_sha256="a" * 64,
        bundled_espeak_revision=BUNDLED_REVISION,
        generated_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    return runtime, manifest


def test_espeak_runtime_manifest_binds_all_runtime_source_and_license_bytes(tmp_path):
    runtime, manifest = _fixture(tmp_path)

    assert manifest.replacement_performed is True
    assert manifest.source_revision == SOURCE_REVISION
    assert len(manifest.files) == len(ESPEAK_REQUIRED_RUNTIME_FILES) + 1
    assert verify_espeak_runtime(manifest, runtime) == espeak_runtime_manifest_digest(manifest)


def test_espeak_runtime_verifier_rejects_tampering_and_unmanifested_files(tmp_path):
    runtime, manifest = _fixture(tmp_path)
    (runtime / "share" / "espeak-ng-data" / "pt_dict").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="espeak_runtime_asset_(size|checksum)_mismatch"):
        verify_espeak_runtime(manifest, runtime)

    runtime, manifest = _fixture(tmp_path / "second")
    (runtime / "share" / "espeak-ng-data" / "unexpected").write_bytes(b"extra")
    with pytest.raises(ValueError, match="espeak_runtime_file_set_mismatch"):
        verify_espeak_runtime(manifest, runtime)


def test_espeak_runtime_manifest_requires_library_data_license_and_source(tmp_path):
    runtime, manifest = _fixture(tmp_path)
    payload = manifest.model_dump(mode="json", by_alias=True)
    payload["files"] = [
        item
        for item in payload["files"]
        if item["relativePath"] != "source/espeak-ng.tar.gz"
    ]

    with pytest.raises(ValueError, match="missing required files: source/espeak-ng.tar.gz"):
        EspeakRuntimeManifestV1.model_validate(payload)


def test_manifested_runtime_replaces_and_verifies_loader_payload(tmp_path):
    runtime, manifest = _fixture(tmp_path)
    loader = tmp_path / "site-packages" / "espeakng_loader"
    (loader / "espeak-ng-data").mkdir(parents=True)
    (loader / "libespeak-ng.so.1.52.0").write_bytes(b"old-library")
    (loader / "espeak-ng-data" / "pt_dict").write_bytes(b"old-data")

    digest = install_replacement(
        manifest,
        runtime_root=runtime,
        loader_root=loader,
    )

    assert digest == espeak_runtime_manifest_digest(manifest)
    assert not (loader / "libespeak-ng.so.1.52.0").exists()
    assert (loader / "libespeak-ng.so").read_bytes() == (
        runtime / "lib" / "libespeak-ng.so"
    ).read_bytes()
    assert (loader / "espeak-ng-data" / "pt_dict").read_bytes() == (
        runtime / "share" / "espeak-ng-data" / "pt_dict"
    ).read_bytes()


def test_loader_replacement_preserves_unrelated_loader_module_files(tmp_path):
    runtime, manifest = _fixture(tmp_path)
    loader = tmp_path / "site-packages" / "espeakng_loader"
    loader.mkdir(parents=True)
    (loader / "unrelated.py").write_text("kept", encoding="utf-8")

    digest = install_replacement(
        manifest,
        runtime_root=runtime,
        loader_root=loader,
    )

    assert digest == espeak_runtime_manifest_digest(manifest)
    assert (loader / "unrelated.py").read_text(encoding="utf-8") == "kept"


def test_installer_runs_without_site_packages_or_backend_imports(tmp_path):
    runtime, manifest = _fixture(tmp_path)
    loader = tmp_path / "site-packages" / "espeakng_loader"
    loader.mkdir(parents=True)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        manifest.model_dump_json(by_alias=True),
        encoding="utf-8",
    )
    expected_digest = espeak_runtime_manifest_digest(manifest)

    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            str(Path(__file__).parents[1] / "scripts/install_espeak_runtime_replacement.py"),
            "--manifest",
            str(manifest_path),
            "--runtime-root",
            str(runtime),
            "--loader-root",
            str(loader),
            "--expected-manifest-digest",
            expected_digest,
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert expected_digest in completed.stdout
