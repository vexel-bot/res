"""Runway native video adapter. HTTP contract checked against runwayml/sdk-python.

Models are fixed, no model router or third-party model substitution. Qualification
requires real outputs; transport tests are not a quality certification.
"""

import base64
import json
import re

import httpx

from .resource_download import download_resource

PROVIDER = "runway.editing-video"
VERSION = "2024-11-06"


def runway_binding(settings, operation):
    key = (
        settings.studio_runway_production_key
        if settings.environment == "production"
        else settings.studio_runway_test_key
    )
    if not settings.studio_runway_enabled or not key:
        raise ValueError("editing_runway_not_configured")
    if operation not in {"generate_video", "edit_video"}:
        raise ValueError("editing_ai_operation_unsupported")
    return ("aleph2" if operation == "edit_video" else "gen4.5"), key.get_secret_value()


class RunwayEditingProvider:
    def __init__(self, key, *, ratio="1280:720", output_hosts=(), client=None):
        self.key, self.ratio, self.output_hosts, self.client = key, ratio, list(output_hosts), client

    def request(self, method, path, body=None):
        def call(client):
            try:
                with client.stream(
                    method,
                    "https://api.dev.runwayml.com/v1" + path,
                    headers={"Authorization": f"Bearer {self.key}", "X-Runway-Version": VERSION},
                    json=body,
                ) as response:
                    if response.status_code not in (200, 201, 204):
                        raise ValueError(f"runway_http_{response.status_code}")
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 2 * 1024 * 1024:
                            raise ValueError("runway_response_too_large")
                return json.loads(data) if data else {}
            except httpx.HTTPError as error:
                raise ValueError("runway_transport_outcome_unknown") from error

        if self.client:
            return call(self.client)
        with httpx.Client(timeout=120, trust_env=False, follow_redirects=False) as client:
            return call(client)

    def validate_model(self, model):
        if model not in {"gen4.5", "aleph2"}:
            raise ValueError("runway_model_unsupported")
        return {"name": model, "qualification": "pending_real_media_validation", "apiVersion": VERSION}

    @staticmethod
    def inline(path, mime):
        if mime not in {"image/png", "image/jpeg", "image/webp", "video/mp4"}:
            raise ValueError("runway_input_format_unsupported")
        if path.stat().st_size > 3_700_000:
            raise ValueError("runway_input_requires_upload_adapter")
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")

    def prepare_video(self, model, prompt, media, duration):
        self.validate_model(model)
        if not 2 <= duration <= 10 or len(prompt.encode("utf-16-le")) // 2 > 1000:
            raise ValueError("runway_request_limits_invalid")
        videos = [(p, m) for p, m in media if m.startswith("video/")]
        images = [(p, m) for p, m in media if m.startswith("image/")]
        # More images require an explicit first/last-frame or timed-keyframe contract.
        if len(images) > 1 or len(videos) > 1 or len(images) + len(videos) != len(media):
            raise ValueError("runway_reference_layout_required")
        body = {"model": model, "promptText": prompt, "outputFormat": "mp4"}
        if model == "aleph2":
            if len(videos) != 1:
                raise ValueError("runway_source_video_required")
            body["videoUri"] = self.inline(*videos[0])
            if images:
                body["keyframes"] = [{"at": 0, "uri": self.inline(*images[0])}]
            path = "/video_to_video"
        else:
            if videos:
                raise ValueError("runway_generation_video_reference_unsupported")
            body.update(duration=duration, ratio=self.ratio)
            if images:
                body["promptImage"] = self.inline(*images[0])
                path = "/image_to_video"
            else:
                if self.ratio not in {"1280:720", "720:1280"}:
                    raise ValueError("runway_text_generation_ratio_unsupported")
                path = "/text_to_video"
        return path, body

    def video(self, model, prompt, media, duration):
        path, body = self.prepare_video(model, prompt, media, duration)
        return self.submit_video(path, body)

    def submit_video(self, path, body):
        result = self.request("POST", path, body)
        identifier = result.get("id")
        self.validate_id(identifier)
        return {"id": identifier, "status": "pending"}

    @staticmethod
    def validate_id(identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,160}", identifier):
            raise ValueError("runway_operation_id_invalid")

    def retrieve(self, identifier):
        self.validate_id(identifier)
        raw = self.request("GET", "/tasks/" + identifier)
        if raw.get("id") != identifier:
            raise ValueError("runway_operation_id_mismatch")
        status = raw.get("status")
        if status in {"PENDING", "THROTTLED", "RUNNING"}:
            return {"id": identifier, "status": "pending"}
        if status != "SUCCEEDED":
            raise ValueError("runway_task_" + (status.lower() if status in {"FAILED", "CANCELLED"} else "invalid"))
        outputs = raw.get("output", [])
        if len(outputs) != 1 or not isinstance(outputs[0], str):
            raise ValueError("runway_output_invalid")
        return {"id": identifier, "status": "completed", "output_video": {"uri": outputs[0]}}

    def cancel(self, identifier):
        self.validate_id(identifier)
        self.request("DELETE", "/tasks/" + identifier)

    def download(self, uri, destination):
        # Do not send the API credential to the media CDN; validate public addresses independently.
        download_resource(uri, destination, self.output_hosts)

    def verify(self, *args):
        return {
            "text": json.dumps(
                {
                    "passed": False,
                    "confidence": 0,
                    "issues": ["Revisar visualmente o candidato Runway e as partes preservadas."],
                }
            )
        }
