import json
import time
from typing import Any

import httpx

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
        if not self.configured:
            raise AIProviderUnavailable("No AI provider is configured")
        started = time.perf_counter()
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                },
            )
            response.raise_for_status()
            payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        trace = {
            "provider": "openai-compatible",
            "model": self.model,
            "latencyMs": round((time.perf_counter() - started) * 1000),
            "usage": payload.get("usage", {}),
        }
        return json.loads(content), trace
