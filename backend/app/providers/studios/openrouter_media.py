"""OpenRouter media transport. Fixed origin, bounded downloads, no POST retries."""

import re

import httpx

BASE = "https://openrouter.ai/api/v1"


class OpenRouterMediaProvider:
    def __init__(self, key, client=None):
        self.key, self.client = key, client

    def request(self, method, path, body=None, *, binary=False):
        def call(client):
            try:
                with client.stream(
                    method, BASE + path, json=body, headers={"Authorization": "Bearer " + self.key}
                ) as response:
                    if response.status_code >= 400:
                        raise ValueError(f"openrouter_media_http_{response.status_code}")
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > (256 * 1024 * 1024 if binary else 4 * 1024 * 1024):
                            raise ValueError("openrouter_media_response_too_large")
                        chunks.append(chunk)
                    data = b"".join(chunks)
                    if binary:
                        return data, response.headers.get("x-generation-id")
                    import json

                    return json.loads(data)
            except httpx.HTTPError as error:
                raise ValueError("openrouter_media_transport_outcome_unknown") from error

        if self.client:
            return call(self.client)
        with httpx.Client(timeout=120, follow_redirects=False, trust_env=False) as client:
            return call(client)

    def models(self):
        return self.request("GET", "/videos/models")["data"], self.request("GET", "/models?output_modalities=speech")[
            "data"
        ]

    def balance(self):
        data = self.request("GET", "/credits")["data"]
        return max(0.0, float(data["total_credits"]) - float(data["total_usage"]))

    @staticmethod
    def job_path(identifier):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", identifier or ""):
            raise ValueError("openrouter_media_invalid_job_id")
        return "/videos/" + identifier
