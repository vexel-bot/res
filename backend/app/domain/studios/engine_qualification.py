"""Engine experiments are independent of commercial project qualification."""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

CASE_LANGUAGES = ("action_product", "kinetic_type", "interface_service")
Language = Literal["action_product", "kinetic_type", "interface_service"]


class CreateEngineCampaignV1(StudioContract):
    title: str = Field(default="Alight Motion · qualificação", min_length=1, max_length=200)


class BindEngineCaseV1(StudioContract):
    language: Language
    document_id: str = Field(min_length=1, max_length=120)
    expected_document_revision: int = Field(ge=1)
    expected_campaign_revision: int = Field(ge=1)


class EngineRenderReferenceV1(StudioContract):
    document_id: str = Field(min_length=1, max_length=120)
    document_revision: int = Field(ge=1)
    asset_id: str = Field(min_length=1, max_length=120)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")


class CreateEngineComparisonV1(StudioContract):
    language: Language
    mode: Literal["technical_fidelity", "editorial_result"]
    variants: list[EngineRenderReferenceV1] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def variant_count(self):
        expected = 2 if self.mode == "technical_fidelity" else 3
        if len(self.variants) != expected or len({v.asset_id for v in self.variants}) != expected:
            raise ValueError("engine_comparison_variant_count_invalid")
        return self


class EngineComparisonReviewV1(StudioContract):
    preferred_label: str = Field(pattern=r"^[ABC]$")
    full_video_inspected: bool
    mobile_inspected: bool
    blind_review_completed: bool
    unrecorded_manual_corrections: bool
    notes: str = Field(min_length=1, max_length=4000)
    action_seconds: float | None = Field(default=None, ge=0, le=15, allow_inf_nan=False)
    executable_findings: list[str] = Field(default_factory=list, max_length=30)
    control_simplicity_confirmed: bool = False
    technical_fidelity_confirmed: bool = False


class RegisterEngineTrialV1(StudioContract):
    language: Language
    job_id: str = Field(min_length=1, max_length=120)
