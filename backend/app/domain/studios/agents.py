"""Three roles coordinate through validated documents and operations, not separate chats."""

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from .contracts import StudioContract

AgentRole = Literal["audiovisual", "image"]


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
    selected_layer_ids: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list, max_length=24
    )

    @model_validator(mode="after")
    def unique_selection(self):
        if len(set(self.selected_layer_ids)) != len(self.selected_layer_ids):
            raise ValueError("agent_duplicate_selected_layer")
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
