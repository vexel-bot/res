"""Appearance-conditioned images; contracts do not imply identity qualification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .contracts import IdentityVersionReferenceV1, StudioContract

PROVIDER = "candidate.qwen-image-edit-2511"
MODEL_REPOSITORY = "Qwen/Qwen-Image-Edit-2511"
MODEL_REVISION = "6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9"
SOURCE_REVISION = "6b5e1f5cec987d404be5ac6657db3b9aacb56a89"
DIFFUSERS_VERSION = "0.42.0"
DIFFUSERS_REVISION = "95f9b8925c34469ccac829866d7ad4e3fca1bd89"
PROVIDER_VERSION = f"0.1.0+qwen-{MODEL_REVISION[:12]}.diffusers-{DIFFUSERS_VERSION}"
SHA256 = r"^[a-f0-9]{64}$"


def canonical_digest(value: StudioContract) -> str:
    encoded = json.dumps(
        value.model_dump(mode="json", by_alias=True), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AppearanceImageRequestV1(StudioContract):
    schema_version: Literal["studio.appearance-image-request.v1"] = "studio.appearance-image-request.v1"
    identity_ref: IdentityVersionReferenceV1
    reference_asset_id: str = Field(min_length=1, max_length=120)
    reference_checksum_sha256: str = Field(pattern=SHA256)
    source_asset_id: str | None = Field(default=None, min_length=1, max_length=120)
    source_checksum_sha256: str | None = Field(default=None, pattern=SHA256)
    direction: str = Field(min_length=3, max_length=4000)
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    seed: int = Field(default=0, ge=0, lt=2**32)
    inference_steps: int = Field(default=40, ge=1, le=50)

    @field_validator("direction", mode="before")
    @classmethod
    def trim_direction(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_binding(self):
        if bool(self.source_asset_id) != bool(self.source_checksum_sha256):
            raise ValueError("appearance_source_binding_incomplete")
        if self.identity_ref.version is None:
            raise ValueError("appearance_identity_version_required")
        if self.width % 16 or self.height % 16 or self.width * self.height > 2048**2:
            raise ValueError("appearance_dimensions_invalid")
        return self


class AppearanceModelFileV1(StudioContract):
    path: str = Field(min_length=1, max_length=500)
    size_bytes: int = Field(gt=0, le=12 * 1024**3)
    checksum_sha256: str = Field(pattern=SHA256)

    @field_validator("path")
    @classmethod
    def normalized_path(cls, value):
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or str(path) != value or "\\" in value or ":" in value:
            raise ValueError("appearance_model_path_invalid")
        return value


class AppearanceModelManifestV1(StudioContract):
    schema_version: Literal["studio.appearance-model-assets.v1"] = "studio.appearance-model-assets.v1"
    repository: Literal["Qwen/Qwen-Image-Edit-2511"] = MODEL_REPOSITORY
    model_revision: Literal["6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9"] = MODEL_REVISION
    source_revision: Literal["6b5e1f5cec987d404be5ac6657db3b9aacb56a89"] = SOURCE_REVISION
    diffusers_version: Literal["0.42.0"] = DIFFUSERS_VERSION
    diffusers_revision: Literal["95f9b8925c34469ccac829866d7ad4e3fca1bd89"] = DIFFUSERS_REVISION
    model_license: Literal["Apache-2.0"] = "Apache-2.0"
    files: list[AppearanceModelFileV1] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def complete_inventory(self):
        paths = {entry.path for entry in self.files}
        if len(paths) != len(self.files):
            raise ValueError("appearance_model_duplicate_path")
        required = {
            "model_index.json",
            "README.md",
            "processor/tokenizer.json",
            "processor/preprocessor_config.json",
            "scheduler/scheduler_config.json",
            "text_encoder/config.json",
            "text_encoder/model.safetensors.index.json",
            "tokenizer/tokenizer_config.json",
            "transformer/config.json",
            "transformer/diffusion_pytorch_model.safetensors.index.json",
            "vae/config.json",
            "vae/diffusion_pytorch_model.safetensors",
            *(f"text_encoder/model-{i:05d}-of-00004.safetensors" for i in range(1, 5)),
            *(f"transformer/diffusion_pytorch_model-{i:05d}-of-00005.safetensors" for i in range(1, 6)),
        }
        if not required.issubset(paths):
            raise ValueError("appearance_model_inventory_incomplete")
        return self


def verify_model_assets(manifest: AppearanceModelManifestV1, model_root: Path, cancelled=lambda: False) -> str:
    if model_root.is_symlink() or not model_root.is_dir():
        raise ValueError("appearance_model_root_unavailable")
    root = model_root.resolve()
    expected = {entry.path for entry in manifest.files}
    for candidate in root.rglob("*"):
        if (
            candidate.is_symlink()
            or not candidate.resolve().is_relative_to(root)
            or (hasattr(candidate, "is_junction") and candidate.is_junction())
        ):
            raise ValueError("appearance_model_symlink_forbidden")
        if candidate.is_file() and candidate.relative_to(root).as_posix() not in expected:
            raise ValueError("appearance_model_unmanifested_file")
    for entry in manifest.files:
        if cancelled():
            raise InterruptedError("appearance_cancelled_during_asset_verification")
        path = root / entry.path
        if not path.is_file() or path.stat().st_size != entry.size_bytes or file_digest(path) != entry.checksum_sha256:
            raise ValueError("appearance_model_asset_mismatch")
    return canonical_digest(manifest)


class AppearanceImageResultV1(StudioContract):
    schema_version: Literal["studio.appearance-image-result.v1"] = "studio.appearance-image-result.v1"
    provider: Literal["candidate.qwen-image-edit-2511"] = PROVIDER
    provider_version: str = Field(min_length=1, max_length=180)
    request_digest_sha256: str = Field(pattern=SHA256)
    model_manifest_digest_sha256: str = Field(pattern=SHA256)
    identity_ref: IdentityVersionReferenceV1
    reference_checksum_sha256: str = Field(pattern=SHA256)
    source_checksum_sha256: str | None = Field(default=None, pattern=SHA256)
    artifact_checksum_sha256: str = Field(pattern=SHA256)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    synthetic_content_disclosed: Literal[True] = True
    review_required: Literal[True] = True
    quality_qualified: Literal[False] = False
    wall_seconds: float = Field(gt=0, allow_inf_nan=False)
