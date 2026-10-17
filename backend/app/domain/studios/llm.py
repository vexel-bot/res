"""Explicit endpoint protocols; a text model plans native operations, not media generation."""

from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator

from .contracts import StudioContract

LLMProtocol = Literal[
    "openai_chat", "openai_responses", "anthropic_messages", "gemini_generate",
    "cohere_chat", "ollama_chat", "custom_json",
]


class LLMConnectionRequest(StudioContract):
    label: str = Field(min_length=1, max_length=120)
    provider: str = Field(default="custom", pattern=r"^[a-z0-9_-]{1,80}$")
    protocol: LLMProtocol = "openai_chat"
    base_url: str = Field(min_length=1, max_length=1000)
    models: list[str] = Field(min_length=1, max_length=100)
    api_key: SecretStr | None = None
    auth_header: str = Field(default="Authorization", pattern=r"^[A-Za-z0-9-]{1,80}$")
    auth_prefix: str = Field(default="Bearer", pattern=r"^[A-Za-z0-9._-]{0,40}$")
    extra_headers: dict[str, str] = Field(default_factory=dict, max_length=20)
    request_path: str | None = Field(default=None, max_length=400)
    request_template: dict[str, Any] | None = None
    response_text_path: str | None = Field(default=None, max_length=240)
    enabled: bool = False
    billing_mode: Literal["metered", "local_free"] = "metered"
    budget_usd: float = Field(default=0, ge=0, le=10000)
    input_usd_per_million: float = Field(default=0, ge=0, le=10000)
    output_usd_per_million: float = Field(default=0, ge=0, le=10000)
    max_output_tokens: int = Field(default=4000, ge=128, le=32000)
    expected_revision: int | None = Field(default=None, ge=1)

    @field_validator("models")
    @classmethod
    def validate_models(cls, models):
        if len(set(models)) != len(models) or any(
            not model or len(model) > 240 or any(c.isspace() or ord(c) < 32 for c in model)
            for model in models
        ):
            raise ValueError("llm_model_ids_invalid")
        return models
