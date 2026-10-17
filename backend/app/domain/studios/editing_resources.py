"""Resources are stored assets, never executable instructions retrieved from the web."""

from typing import Literal

from pydantic import Field, model_validator

from .contextual_editing import ContextualPlanRequestV1
from .contextual_editing_v2 import ContextualPlanRequestV2
from .contracts import StudioContract, UgcTextLayerPropertiesV1
from .editorial_production import EditorialDirectionV1, ProductionRequestV1
from .material_inspection import MaterialInspectionRequestV1

ResourceKind = Literal["font", "logo", "image", "video", "wardrobe", "sound_effect", "music"]


class ResourceMetadataV1(StudioContract):
    kind: ResourceKind
    asset_role: Literal["product", "package", "logo", "brand", "action", "environment", "support"] | None = None
    description: str = Field(default="", max_length=4000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    source_url: str | None = Field(default=None, max_length=4000)
    usage_evidence: str = Field(min_length=1, max_length=4000)
    family: str | None = Field(default=None, max_length=120)
    variant: str | None = Field(default=None, max_length=80)
    version: str = Field(default="1", max_length=120)
    official: bool = False
    framing: str = Field(default="", max_length=500)
    focal_point: str = Field(default="", max_length=500)
    negative_space: str = Field(default="", max_length=500)
    motion_description: str = Field(default="", max_length=1000)
    editorial_function: str = Field(default="", max_length=1000)
    energy: Literal["low", "medium", "high"] | None = None


class ImportResourceV1(ResourceMetadataV1):
    title: str = Field(min_length=1, max_length=240)
    url: str = Field(min_length=1, max_length=4000)


class RegisteredEditingSourceV1(ImportResourceV1):
    auto_acquire: bool = False


class ResolveResourceV1(StudioContract):
    query: str = Field(min_length=1, max_length=500)
    kind: ResourceKind
    document_id: str | None = None
    exact: bool = False


class AttachResourceV1(StudioContract):
    expected_document_revision: int = Field(ge=1)
    asset_id: str


class ApplyGeneratedResourceV1(AttachResourceV1):
    target_clip_id: str = Field(min_length=1, max_length=120)


class ReviewGeneratedResourceV1(StudioContract):
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    result: Literal["passed", "failed"]
    observation: str = Field(min_length=1, max_length=4000)


class ContextualTextStyleV1(UgcTextLayerPropertiesV1):
    font_family: str = Field(default="Liberation Sans", min_length=1, max_length=120)
    font_asset_id: str | None = Field(default=None, max_length=120)


class EditorialInspectionIntervalV1(StudioContract):
    asset_id: str = Field(min_length=1, max_length=120)
    start_seconds: float = Field(ge=0, le=86400)
    end_seconds: float = Field(gt=0, le=86400)

    @model_validator(mode="after")
    def interval(self):
        if self.end_seconds <= self.start_seconds:
            raise ValueError("editing_inspection_interval_invalid")
        return self


class EditingAIRequestV1(StudioContract):
    material_inspection: MaterialInspectionRequestV1 | None = None
    revision_plan: ContextualPlanRequestV2 | None = None
    revision_scene_ids: list[str] = Field(default_factory=list, max_length=50)
    revision_instruction: str = Field(default="", max_length=4000)
    narration_beats: dict[str, str] = Field(default_factory=dict, max_length=50)
    production_stage: Literal["direction", "composition", "critique"] | None = None
    critique_render_job_id: str | None = None
    production_request: ProductionRequestV1 | None = None
    editorial_direction: EditorialDirectionV1 | None = None
    preliminary_material_inventory: list[dict] = Field(default_factory=list, max_length=100)
    inspection_intervals: list[EditorialInspectionIntervalV1] = Field(default_factory=list, max_length=10)
    plan_version: Literal[1, 2] = 1
    schema_version: Literal["studio.editing-ai-request.v1"] = "studio.editing-ai-request.v1"
    expected_document_revision: int = Field(ge=1)
    operation: Literal["plan", "generate_image", "edit_image", "generate_video", "edit_video"]
    prompt: str = Field(min_length=1, max_length=12000)
    source_asset_id: str | None = None
    reference_asset_ids: list[str] = Field(default_factory=list, max_length=3)
    source_start_seconds: float = Field(default=0, ge=0)
    duration_seconds: int = Field(default=8, ge=1, le=3600)
    preserve: list[str] = Field(default_factory=list, max_length=30)
    direction: ContextualPlanRequestV1 | None = None

    @model_validator(mode="after")
    def required_inputs(self):
        if self.material_inspection and (self.operation != "plan" or self.production_stage):
            raise ValueError("material_inspection_requires_independent_planning_job")
        if self.production_stage:
            if self.operation != "plan" or self.plan_version != 2 or self.production_request is None:
                raise ValueError("production_stage_requires_v2_planning")
            if self.direction != self.production_request.direction:
                raise ValueError("production_direction_binding_conflict")
            if self.production_stage == "composition" and self.editorial_direction is None:
                raise ValueError("production_storyboard_required")
            if self.production_stage == "critique" and (not self.critique_render_job_id or not self.revision_plan):
                raise ValueError("production_critique_render_required")
        if self.operation.startswith("edit_") and not self.source_asset_id:
            raise ValueError("editing_source_required")
        if self.operation == "plan" and self.direction is None:
            raise ValueError("editing_direction_required")
        return self


class GeminiEditingRequestV1(EditingAIRequestV1):
    """Compatibility name retained for existing clients and stored jobs."""

    schema_version: Literal["studio.editing-ai-request.v1"] = Field(
        default="studio.editing-ai-request.v1", exclude=True
    )
    duration_seconds: int = Field(default=8, ge=3, le=10)
