from typing import Any

from ..config import get_settings


class AIProviderUnavailable(RuntimeError):
    pass


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = (settings.ai_base_url or "").rstrip("/")
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)

    def generate_json(self, system: str, prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
        # Retained legacy adapter has no authenticated billing scope/reservation.
        # Do not allow it to bypass the canonical, budgeted Studios LLM service.
        raise AIProviderUnavailable("Use the budgeted Studios LLM connection service")
