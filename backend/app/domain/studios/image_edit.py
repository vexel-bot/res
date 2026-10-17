from __future__ import annotations

import hashlib
import json
from typing import Literal, Protocol

from pydantic import Field, model_validator

from .contracts import StudioContract


class NormalizedRegionV1(StudioContract):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> "NormalizedRegionV1":
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("image_region_exceeds_canvas")
        return self


class ImageEditMaskV1(NormalizedRegionV1):
    shape: Literal["rectangle", "ellipse"] = "rectangle"


class ImageProtectedRegionV1(NormalizedRegionV1):
    kind: Literal["face", "product", "logo"]
    label: str = Field(min_length=1, max_length=120)


class ImageDerivationRequestV1(StudioContract):
    workspace_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    brightness: float = Field(default=1, ge=0.25, le=2)
    contrast: float = Field(default=1, ge=0.25, le=2)
    edit_mask: ImageEditMaskV1 | None = None
    protected_regions: list[ImageProtectedRegionV1] = Field(default_factory=list, max_length=30)
    expected_source_checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    idempotency_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")


class ImageEditExecutionV1(StudioContract):
    brightness: float
    contrast: float
    edit_mask: ImageEditMaskV1 | None = None
    protected_regions: list[ImageProtectedRegionV1] = Field(default_factory=list)


class ImageEditResultV1(StudioContract):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    media_type: Literal["image/png"] = "image/png"
    provider: str
    provider_version: str


class ImageEditProvider(Protocol):
    name: str
    version: str

    def derive(
        self,
        source_path: str,
        output_path: str,
        request: ImageEditExecutionV1,
    ) -> ImageEditResultV1: ...


def image_derivation_digest(source_checksum: str, request: ImageDerivationRequestV1) -> str:
    payload = {
        "sourceChecksumSha256": source_checksum.lower(),
        "brightness": request.brightness,
        "contrast": request.contrast,
        "editMask": request.edit_mask.model_dump(mode="json", by_alias=True)
        if request.edit_mask
        else None,
        "protectedRegions": [
            item.model_dump(mode="json", by_alias=True) for item in request.protected_regions
        ],
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
