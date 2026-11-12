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
    direction_effort: Literal["standard", "deliberate"] = "standard"
    workflow: Literal["native", "motion_swarm"] = "native"


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


class CraftClipReviewRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    start_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)
    duration_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    fps: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    page: int = Field(default=0, ge=0)
    page_size: int = Field(default=12, ge=1, le=12)
    asset_id: str | None = Field(default=None, max_length=120)


class CraftEditorialLessonV1(StudioContract):
    id: str | None = Field(default=None, max_length=120)
    situation: str = Field(min_length=1, max_length=2000)
    correction: str = Field(min_length=1, max_length=4000)
    use_when: list[str] = Field(min_length=1, max_length=20)
    avoid_when: list[str] = Field(default_factory=list, max_length=20)
    source_feedback: str | None = Field(default=None, max_length=4000)
    source_url: str | None = Field(default=None, max_length=2000)


class CraftEditorialLessonRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    expected_version: int = Field(ge=0)
    scope: Literal["workspace", "document"] = "document"
    lesson: CraftEditorialLessonV1


class CraftEditorialFeedbackRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    job_id: str = Field(min_length=1, max_length=120)
    comment: str = Field(min_length=1, max_length=4000)


class CraftLinkRequestV1(StudioContract):
    expected_revision: int = Field(ge=1)
    composition_document_id: str = Field(min_length=1, max_length=120)


class CraftNativeManifestV1(StudioContract):
    asset_manifest: list[NativeMediaReferenceV1] = Field(default_factory=list, max_length=10000)
    font_manifest: list[NativeMediaReferenceV1] = Field(default_factory=list, max_length=1000)
