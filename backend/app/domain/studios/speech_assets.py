from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
KOKORO_REQUIRED_MODEL_FILES = frozenset(
    {
        "config.json",
        "kokoro-v1_0.pth",
        "voices/pf_dora.pt",
        "voices/pm_alex.pt",
        "voices/pm_santa.pt",
    }
)
ESPEAK_REQUIRED_RUNTIME_FILES = frozenset(
    {
        "build/base-image-digest.txt",
        "build/cmake.txt",
        "build/compiler.txt",
        "build/flags.txt",
        "build/source-revision.txt",
        "lib/libespeak-ng.so",
        "licenses/espeak-ng-COPYING",
        "share/espeak-ng-data/phondata",
        "share/espeak-ng-data/phonindex",
        "share/espeak-ng-data/phontab",
        "share/espeak-ng-data/pt_dict",
        "source/espeak-ng.tar.gz",
    }
)
ESPEAK_ALLOWED_RUNTIME_PREFIXES = (
    "build/",
    "lib/",
    "licenses/",
    "share/espeak-ng-data/",
    "source/",
)
CHATTERBOX_VARIANT_RUNTIME_FILES = {
    "chatterbox-multilingual-v3": frozenset(
        {
            "grapheme_mtl_merged_expanded_v1.json",
            "s3gen.pt",
            "t3_mtl23ls_v3.safetensors",
            "ve.pt",
        }
    ),
    "chatterbox-pt-br": frozenset(
        {
            "grapheme_mtl_merged_expanded_v1.json",
            "s3gen.pt",
            "t3_pt_br.safetensors",
            "ve.pt",
        }
    ),
}
OPENVOICE_REQUIRED_RUNTIME_FILES = frozenset(
    {
        "converter/checkpoint.pth",
        "converter/config.json",
        "watermark/wavmark.model.pkl",
    }
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class KokoroModelAssetFileV1(StudioContract):
    relative_path: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(gt=0, le=10 * 1024**3)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_relative_path(self) -> KokoroModelAssetFileV1:
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts or str(path) != self.relative_path:
            raise ValueError("Kokoro model manifest paths must be normalized and relative")
        return self


class KokoroModelAssetManifestV1(StudioContract):
    schema_version: Literal["studio.kokoro-model-assets.v1"] = "studio.kokoro-model-assets.v1"
    repository_id: Literal["hexgrad/Kokoro-82M"] = "hexgrad/Kokoro-82M"
    source_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    generated_at: datetime
    model_card_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    files: list[KokoroModelAssetFileV1] = Field(min_length=5, max_length=100)

    @model_validator(mode="after")
    def validate_files(self) -> KokoroModelAssetManifestV1:
        paths = [item.relative_path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Kokoro model manifest file paths must be unique")
        if set(paths) != KOKORO_REQUIRED_MODEL_FILES:
            raise ValueError("Kokoro model manifest must contain exactly the approved runtime files")
        return self


def kokoro_model_asset_manifest_digest(manifest: KokoroModelAssetManifestV1) -> str:
    canonical = json.dumps(
        manifest.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_kokoro_model_snapshot(
    manifest: KokoroModelAssetManifestV1,
    snapshot_root: Path,
) -> str:
    root = snapshot_root.resolve()
    if not snapshot_root.is_dir() or snapshot_root.is_symlink():
        raise ValueError("kokoro_model_snapshot_missing_or_symlinked")
    if snapshot_root.name.lower() != manifest.source_revision.lower():
        raise ValueError("kokoro_model_snapshot_revision_mismatch")
    model_cache_root = root.parent.parent.resolve()
    reference = model_cache_root / "refs" / "main"
    try:
        referenced_revision = reference.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise ValueError("kokoro_model_cache_reference_unreadable") from error
    if referenced_revision.lower() != manifest.source_revision.lower():
        raise ValueError("kokoro_model_cache_reference_mismatch")
    for entry in manifest.files:
        source = snapshot_root / Path(*PurePosixPath(entry.relative_path).parts)
        if not source.is_file():
            raise ValueError(f"kokoro_model_asset_missing:{entry.relative_path}")
        resolved_source = source.resolve()
        if not resolved_source.is_relative_to(model_cache_root):
            raise ValueError(f"kokoro_model_asset_escaped_cache:{entry.relative_path}")
        if source.stat().st_size != entry.size_bytes:
            raise ValueError(f"kokoro_model_asset_size_mismatch:{entry.relative_path}")
        checksum = _sha256_file(source)
        if checksum != entry.checksum_sha256.lower():
            raise ValueError(f"kokoro_model_asset_checksum_mismatch:{entry.relative_path}")
    return kokoro_model_asset_manifest_digest(manifest)


class EspeakRuntimeAssetFileV1(StudioContract):
    relative_path: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(gt=0, le=2 * 1024**3)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_relative_path(self) -> EspeakRuntimeAssetFileV1:
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts or str(path) != self.relative_path:
            raise ValueError("eSpeak runtime manifest paths must be normalized and relative")
        if not self.relative_path.startswith(ESPEAK_ALLOWED_RUNTIME_PREFIXES):
            raise ValueError("eSpeak runtime manifest path is outside approved prefixes")
        return self


class EspeakRuntimeManifestV1(StudioContract):
    schema_version: Literal["studio.espeak-runtime-assets.v1"] = (
        "studio.espeak-runtime-assets.v1"
    )
    repository_id: Literal["espeak-ng/espeak-ng"] = "espeak-ng/espeak-ng"
    source_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    platform: Literal["linux-amd64"] = "linux-amd64"
    generated_at: datetime
    builder_image_digest: str = Field(pattern=r"^sha256:[0-9a-fA-F]{64}$")
    compiler: str = Field(min_length=1, max_length=160)
    cmake_version: str = Field(min_length=1, max_length=80)
    build_flags: list[str] = Field(min_length=1, max_length=100)
    build_recipe_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    loader_wheel_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    bundled_espeak_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    replacement_performed: Literal[True] = True
    files: list[EspeakRuntimeAssetFileV1] = Field(min_length=7, max_length=10000)

    @model_validator(mode="after")
    def validate_files(self) -> EspeakRuntimeManifestV1:
        paths = [item.relative_path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("eSpeak runtime manifest file paths must be unique")
        missing = sorted(ESPEAK_REQUIRED_RUNTIME_FILES - set(paths))
        if missing:
            raise ValueError(
                f"eSpeak runtime manifest is missing required files: {','.join(missing)}"
            )
        if len(self.build_flags) != len(set(self.build_flags)):
            raise ValueError("eSpeak runtime build flags must be unique")
        return self


def espeak_runtime_manifest_digest(manifest: EspeakRuntimeManifestV1) -> str:
    canonical = json.dumps(
        manifest.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_espeak_runtime(
    manifest: EspeakRuntimeManifestV1,
    runtime_root: Path,
) -> str:
    root = runtime_root.resolve()
    if not runtime_root.is_dir() or runtime_root.is_symlink():
        raise ValueError("espeak_runtime_root_missing_or_symlinked")
    disk_files: dict[str, Path] = {}
    for source in runtime_root.rglob("*"):
        if source.is_symlink():
            raise ValueError("espeak_runtime_symlinks_forbidden")
        if not source.is_file():
            continue
        resolved_source = source.resolve()
        if not resolved_source.is_relative_to(root):
            raise ValueError("espeak_runtime_file_escaped_root")
        relative = source.relative_to(runtime_root).as_posix()
        if not relative.startswith(ESPEAK_ALLOWED_RUNTIME_PREFIXES):
            raise ValueError(f"espeak_runtime_unapproved_path:{relative}")
        disk_files[relative] = source
    manifest_paths = {item.relative_path for item in manifest.files}
    if set(disk_files) != manifest_paths:
        raise ValueError("espeak_runtime_file_set_mismatch")
    for entry in manifest.files:
        source = disk_files[entry.relative_path]
        if source.stat().st_size != entry.size_bytes:
            raise ValueError(f"espeak_runtime_asset_size_mismatch:{entry.relative_path}")
        if _sha256_file(source) != entry.checksum_sha256.lower():
            raise ValueError(f"espeak_runtime_asset_checksum_mismatch:{entry.relative_path}")
    return espeak_runtime_manifest_digest(manifest)


class ChatterboxModelAssetFileV1(StudioContract):
    source_repository_id: Literal[
        "ResembleAI/chatterbox",
        "ResembleAI/Chatterbox-Multilingual-pt-br",
    ]
    source_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    source_path: str = Field(min_length=1, max_length=500)
    runtime_path: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(gt=0, le=10 * 1024**3)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_paths(self) -> ChatterboxModelAssetFileV1:
        for label, value in (
            ("source", self.source_path),
            ("runtime", self.runtime_path),
        ):
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or str(path) != value:
                raise ValueError(
                    f"Chatterbox {label} paths must be normalized and relative"
                )
        return self


class ChatterboxModelVariantV1(StudioContract):
    candidate_id: Literal[
        "chatterbox-multilingual-v3",
        "chatterbox-pt-br",
    ]
    language_id: Literal["pt"] = "pt"
    loader_contract: Literal[
        "chatterbox.multilingual.from-local.v1",
        "clicko.chatterbox.pt-br-from-local.v1",
    ]
    files: list[ChatterboxModelAssetFileV1] = Field(min_length=4, max_length=20)

    @model_validator(mode="after")
    def validate_files(self) -> ChatterboxModelVariantV1:
        paths = [item.runtime_path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("Chatterbox runtime paths must be unique per variant")
        if set(paths) != CHATTERBOX_VARIANT_RUNTIME_FILES[self.candidate_id]:
            raise ValueError(
                "Chatterbox variant must contain exactly the approved runtime files"
            )
        expected_loader = (
            "chatterbox.multilingual.from-local.v1"
            if self.candidate_id == "chatterbox-multilingual-v3"
            else "clicko.chatterbox.pt-br-from-local.v1"
        )
        if self.loader_contract != expected_loader:
            raise ValueError("Chatterbox candidate uses the wrong loader contract")
        return self


class ChatterboxModelAssetManifestV1(StudioContract):
    schema_version: Literal["studio.chatterbox-model-assets.v1"] = (
        "studio.chatterbox-model-assets.v1"
    )
    generated_at: datetime
    chatterbox_code_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    perth_code_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    model_card_digests_sha256: dict[str, str] = Field(min_length=2, max_length=2)
    variants: list[ChatterboxModelVariantV1] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def validate_variants(self) -> ChatterboxModelAssetManifestV1:
        candidate_ids = [item.candidate_id for item in self.variants]
        if len(candidate_ids) != len(set(candidate_ids)) or set(candidate_ids) != set(
            CHATTERBOX_VARIANT_RUNTIME_FILES
        ):
            raise ValueError("Chatterbox manifest must contain both approved candidates")
        if set(self.model_card_digests_sha256) != {
            "ResembleAI/chatterbox",
            "ResembleAI/Chatterbox-Multilingual-pt-br",
        } or any(
            len(value) != 64
            or any(character not in "0123456789abcdefABCDEF" for character in value)
            for value in self.model_card_digests_sha256.values()
        ):
            raise ValueError("Chatterbox model card digests must cover both repositories")
        return self


def chatterbox_model_asset_manifest_digest(
    manifest: ChatterboxModelAssetManifestV1,
) -> str:
    canonical = json.dumps(
        manifest.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_chatterbox_model_assets(
    manifest: ChatterboxModelAssetManifestV1,
    asset_root: Path,
) -> str:
    root = asset_root.resolve()
    if not asset_root.is_dir() or asset_root.is_symlink():
        raise ValueError("chatterbox_model_asset_root_missing_or_symlinked")
    expected: dict[str, ChatterboxModelAssetFileV1] = {}
    for variant in manifest.variants:
        for entry in variant.files:
            relative = f"{variant.candidate_id}/{entry.runtime_path}"
            expected[relative] = entry
    disk_files: dict[str, Path] = {}
    for source in asset_root.rglob("*"):
        if source.is_symlink():
            raise ValueError("chatterbox_model_asset_symlinks_forbidden")
        if not source.is_file():
            continue
        resolved_source = source.resolve()
        if not resolved_source.is_relative_to(root):
            raise ValueError("chatterbox_model_asset_escaped_root")
        disk_files[source.relative_to(asset_root).as_posix()] = source
    if set(disk_files) != set(expected):
        raise ValueError("chatterbox_model_asset_file_set_mismatch")
    for relative, entry in expected.items():
        source = disk_files[relative]
        if source.stat().st_size != entry.size_bytes:
            raise ValueError(f"chatterbox_model_asset_size_mismatch:{relative}")
        if _sha256_file(source) != entry.checksum_sha256.lower():
            raise ValueError(f"chatterbox_model_asset_checksum_mismatch:{relative}")
    return chatterbox_model_asset_manifest_digest(manifest)


class OpenVoiceModelAssetFileV1(StudioContract):
    source_repository_id: Literal["myshell-ai/OpenVoiceV2", "M4869/WavMark"]
    source_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    source_path: str = Field(min_length=1, max_length=500)
    runtime_path: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(gt=0, le=10 * 1024**3)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_paths(self) -> OpenVoiceModelAssetFileV1:
        for label, value in (
            ("source", self.source_path),
            ("runtime", self.runtime_path),
        ):
            path = PurePosixPath(value)
            if path.is_absolute() or ".." in path.parts or str(path) != value:
                raise ValueError(
                    f"OpenVoice {label} paths must be normalized and relative"
                )
        return self


class OpenVoiceModelAssetManifestV1(StudioContract):
    schema_version: Literal["studio.openvoice-model-assets.v1"] = (
        "studio.openvoice-model-assets.v1"
    )
    candidate_id: Literal["kokoro-openvoice-v2"] = "kokoro-openvoice-v2"
    generated_at: datetime
    openvoice_code_revision: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    wavmark_wheel_version: Literal["0.0.3"] = "0.0.3"
    wavmark_wheel_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    pipeline_contract: Literal["clicko.kokoro-openvoice-v2.pt-br.v1"] = (
        "clicko.kokoro-openvoice-v2.pt-br.v1"
    )
    base_voice_strategy: Literal["kokoro-pt-br-extract-source-se"] = (
        "kokoro-pt-br-extract-source-se"
    )
    reference_strategy: Literal["normalized-consented-wav-extract-target-se"] = (
        "normalized-consented-wav-extract-target-se"
    )
    files: list[OpenVoiceModelAssetFileV1] = Field(min_length=3, max_length=10)

    @model_validator(mode="after")
    def validate_files(self) -> OpenVoiceModelAssetManifestV1:
        paths = [item.runtime_path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("OpenVoice runtime paths must be unique")
        if set(paths) != OPENVOICE_REQUIRED_RUNTIME_FILES:
            raise ValueError(
                "OpenVoice manifest must contain exactly the approved runtime files"
            )
        repositories = {item.source_repository_id for item in self.files}
        if repositories != {"myshell-ai/OpenVoiceV2", "M4869/WavMark"}:
            raise ValueError("OpenVoice manifest must bind converter and WavMark assets")
        return self


def openvoice_model_asset_manifest_digest(
    manifest: OpenVoiceModelAssetManifestV1,
) -> str:
    canonical = json.dumps(
        manifest.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_openvoice_model_assets(
    manifest: OpenVoiceModelAssetManifestV1,
    asset_root: Path,
) -> str:
    root = asset_root.resolve()
    if not asset_root.is_dir() or asset_root.is_symlink():
        raise ValueError("openvoice_model_asset_root_missing_or_symlinked")
    disk_files: dict[str, Path] = {}
    for source in asset_root.rglob("*"):
        if source.is_symlink():
            raise ValueError("openvoice_model_asset_symlinks_forbidden")
        if not source.is_file():
            continue
        resolved_source = source.resolve()
        if not resolved_source.is_relative_to(root):
            raise ValueError("openvoice_model_asset_escaped_root")
        disk_files[source.relative_to(asset_root).as_posix()] = source
    expected = {item.runtime_path: item for item in manifest.files}
    if set(disk_files) != set(expected):
        raise ValueError("openvoice_model_asset_file_set_mismatch")
    for relative, entry in expected.items():
        source = disk_files[relative]
        if source.stat().st_size != entry.size_bytes:
            raise ValueError(f"openvoice_model_asset_size_mismatch:{relative}")
        if _sha256_file(source) != entry.checksum_sha256.lower():
            raise ValueError(f"openvoice_model_asset_checksum_mismatch:{relative}")
    return openvoice_model_asset_manifest_digest(manifest)
