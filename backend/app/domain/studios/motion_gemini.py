"""DEV-only settings; the API never accepts a browser assertion of free billing."""

from pydantic import Field, SecretStr

from .agents import AgentOutput
from .contracts import StudioContract


class MotionGeminiKey(StudioContract):
    api_key: SecretStr


class MotionGeminiSettings(StudioContract):
    enabled: bool = False
    model: str | None = Field(default=None, max_length=160)


class MotionGeminiCancel(StudioContract):
    request_key: str = Field(min_length=8, max_length=128)


class MotionFreeTierEvidence(StudioContract):
    credential_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    workspace_id: str
    user_id: str
    model: str
    project_id: str = Field(min_length=3, max_length=120)
    tier: str = Field(pattern=r"^free$")
    billing_disabled: bool
    inference_authorized: bool
    structured_output_verified: bool
    evidence_reference: str = Field(min_length=10, max_length=300)
    verified_at: str
    expires_at: str
    requests_per_minute: int = Field(ge=1, le=10)
    requests_per_day: int = Field(ge=1, le=50)
    max_output_tokens: int = Field(ge=128, le=8000)
    input_tokens_per_minute: int = Field(ge=24000, le=1000000)


class MotionSceneDirection(StudioContract):
    title: str = Field(max_length=120)
    duration_seconds: float = Field(gt=0, le=120)
    description: str = Field(max_length=800)


class MotionCreativeDirection(StudioContract):
    concept: str = Field(max_length=1000)
    narrative: str = Field(max_length=1500)
    scenes: list[MotionSceneDirection] = Field(min_length=1, max_length=12)
    palette: list[str] = Field(min_length=1, max_length=8)
    typography: str = Field(max_length=500)
    motion_and_transitions: str = Field(max_length=1000)
    rhythm: str = Field(max_length=500)
    audio_recommendations: str = Field(max_length=600)


class MotionAgentOutput(AgentOutput):
    direction: MotionCreativeDirection
