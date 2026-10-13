"""Host contracts for native Craft projects; engine command schemas come from Rust."""

from typing import Any, Literal

from pydantic import Field

from .contracts import CraftEngine, NativeMediaReferenceV1, StudioContract


class CraftCommandV1(StudioContract):
    id: str = Field(min_length=1, max_length=160)
    params: dict[str, Any] = Field(default_factory=dict)


class CraftCommandRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    commands: list[CraftCommandV1] = Field(min_length=1, max_length=100)
    label: str = Field(default="Edição no Studio", min_length=1, max_length=240)
    page_id: str | None = Field(default=None, max_length=160)


class CraftAICommandRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    instruction: str = Field(min_length=1, max_length=10000)
    page_id: str | None = Field(default=None, max_length=160)
    connection_id: str | None = Field(default=None, max_length=36)
    model: str | None = Field(default=None, min_length=1, max_length=240)


class CraftMigrationRequestV1(StudioContract):
    engine: CraftEngine
    expected_revision: int = Field(ge=1)


class CraftRecoverEffectsRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)


class CraftUpgradeRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    target_build_id: str = Field(min_length=1, max_length=160)


class CraftRenderRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    format: str = Field(default="png", pattern=r"^[a-z0-9_]{2,12}$")
    frame: int = Field(default=0, ge=0)
    quality: Literal["draft", "standard", "high"] = "standard"
    page_id: str | None = Field(default=None, max_length=160)


class CraftPreviewRequestV1(StudioContract):
    frame: int = Field(default=0, ge=0)
    page_id: str | None = Field(default=None, max_length=160)


class CraftLinkRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    composition_document_id: str = Field(min_length=1, max_length=120)


class CraftNativeManifestV1(StudioContract):
    asset_manifest: list[NativeMediaReferenceV1] = Field(default_factory=list, max_length=10000)
    font_manifest: list[NativeMediaReferenceV1] = Field(default_factory=list, max_length=1000)
