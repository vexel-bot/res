"""Three roles coordinate through validated documents and operations, not separate chats."""

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

AgentRole = Literal["audiovisual", "image"]


class EditingReference(StudioContract):
    asset_id: str = Field(min_length=1, max_length=120)
    start_seconds: float = Field(default=0, ge=0, le=1800, allow_inf_nan=False)
    duration_seconds: float = Field(default=6, ge=.2, le=15, allow_inf_nan=False)
    source_url: str | None = Field(default=None, max_length=500)


class EditorialExperiment(StudioContract):
    variant: Literal["baseline", "knowledge", "orchestrated"] = "orchestrated"
    format: Literal["auto", "motion", "hybrid", "footage", "interface"] = "auto"
    objective: str | None = Field(default=None, min_length=1, max_length=240)
    connection_id: str | None = Field(default=None, min_length=1, max_length=36)
    cut_effort: Literal["medium", "high", "xhigh"] | None = None
    creative_cut: Literal[True] | None = None
    scene_direction: Literal[True] | None = None
    open_edit: Literal[True] | None = None
    purpose: Literal["advertisement", "reference_study"] | None = None
    references: list[EditingReference] | None = Field(default=None, min_length=1, max_length=2)
    timeline_proof_asset_id: str | None = Field(default=None, min_length=36, max_length=36)
    creative_replay_task_id: str | None = Field(default=None, min_length=36, max_length=36)

    @model_validator(mode="after")
    def connection_requires_review(self):
        if self.open_edit:
            if not self.connection_id or not self.cut_effort or not self.references:
                raise ValueError("open_edit_requires_claude_effort_and_visual_reference")
            if (self.scene_direction or self.creative_cut or self.creative_replay_task_id
                    or self.timeline_proof_asset_id):
                raise ValueError("open_edit_cannot_use_legacy_template")
        elif self.purpose or self.references:
            raise ValueError("editing_references_require_open_edit")
        if self.cut_effort == "xhigh" and not self.open_edit:
            raise ValueError("editorial_xhigh_requires_open_edit")
        if self.connection_id and self.variant != "orchestrated":
            raise ValueError("editorial_claude_requires_render_review")
        if self.cut_effort and not self.connection_id:
            raise ValueError("editorial_cut_requires_claude")
        if self.creative_cut and not self.cut_effort:
            raise ValueError("editorial_creative_cut_requires_effort")
        if self.timeline_proof_asset_id and not self.scene_direction:
            raise ValueError("editorial_timeline_proof_requires_scene_direction")
        if self.scene_direction and not self.creative_cut:
            raise ValueError("editorial_scene_direction_requires_creative_cut")
        if self.creative_replay_task_id and not self.creative_cut:
            raise ValueError("editorial_replay_requires_creative_cut")
        return self


class EditorialVerdictRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    render_checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    verdict: Literal["approved", "needs_revision"]
    notes: str = Field(min_length=10, max_length=2000)
    criteria: dict[Literal["hook", "product", "continuity", "legibility", "reference", "cta"],
                   Literal["passed", "failed", "not_observed"]]

    @model_validator(mode="after")
    def approval_requires_observed_criteria(self):
        if set(self.criteria) != {"hook", "product", "continuity", "legibility", "reference", "cta"}:
            raise ValueError("open_edit_editorial_criteria_required")
        return self


class LocalProjectRequest(StudioContract):
    workspace_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=120)
    content_type: Literal["visual", "video"]
    width: int = Field(default=1280, ge=320, le=1920)
    height: int = Field(default=720, ge=320, le=1920)


class RoleBinding(StudioContract):
    mode: Literal["local_tools", "local_model"] = "local_tools"
    connection_id: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def configured_model(self):
        if self.mode == "local_model" and not (self.connection_id and self.model):
            raise ValueError("agent_local_model_binding_required")
        if self.mode == "local_tools" and (self.connection_id or self.model):
            raise ValueError("agent_tools_do_not_use_model")
        return self


class RoleConfiguration(StudioContract):
    expected_revision: int = Field(ge=0)
    audiovisual: RoleBinding = Field(default_factory=RoleBinding)
    image: RoleBinding = Field(default_factory=RoleBinding)


class AgentTaskRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    instruction: str = Field(min_length=1, max_length=8000)
    role: Literal["auto", "audiovisual", "image"] = "auto"
    planner: Literal["current", "deterministic", "gemini_experimental", "editorial_experimental"] = "current"
    editorial: EditorialExperiment | None = None
    duration_seconds: int | None = Field(default=None, ge=3, le=120)
    probe: bool = False
    selected_layer_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list, max_length=24
    )

    @model_validator(mode="after")
    def unique_selection(self):
        if self.probe and self.planner != "gemini_experimental":
            raise ValueError("motion_gemini_probe_requires_experiment")
        if len(set(self.selected_layer_ids)) != len(self.selected_layer_ids):
            raise ValueError("agent_duplicate_selected_layer")
        if (self.planner == "editorial_experimental") != (self.editorial is not None):
            raise ValueError("editorial_experiment_configuration_required")
        if self.editorial and self.selected_layer_ids:
            raise ValueError("editorial_experiment_requires_project_scope")
        return self


class AgentOperation(StudioContract):
    id: Literal[
        "composition.replace",
        "layer.upsert",
        "layer.remove",
        "project.duration",
        "project.background",
        "timeline.replace",
        "asset.attach",
    ]
    params: dict[str, Any] = Field(default_factory=dict, max_length=3)


class AgentOutput(StudioContract):
    commands: list[AgentOperation] = Field(default_factory=list, max_length=32)
    rationale: str = Field(max_length=2000)


class LocalCommandsRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    commands: list[AgentOperation] = Field(min_length=1, max_length=32)


class ApplyAgentTaskRequest(StudioContract):
    expected_revision: int = Field(ge=1)
