"""Bounded Claude refinement between local direction and the real editorial preview."""

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import Field

from ...domain.studios.agents import AgentOutput
from ...domain.studios.contracts import CreativeCompositionV1, StudioContract
from ...domain.studios.local_composition import LocalLayerStyle
from ...domain.studios.timeline_editor import MotionKey
from . import llm_connections, motion_editorial
from .craft import workspace_files
from .gemini_editing import measured_request_cost

MODEL = "claude-opus-5-5"
ENDPOINT = "https://api.anthropic.com/v1"
OUTPUT_TOKENS = 4096


def binding(db, workspace, connection_id):
    row, adapter, _, _ = llm_connections.planner(db, workspace, connection_id, MODEL)
    config = row.config
    if (
        row.provider != "anthropic" or config["protocol"] != "anthropic_messages"
        or config["baseUrl"] != ENDPOINT or config.get("requestPath") not in (None, "/messages")
        or config["authHeader"].lower() != "x-api-key" or config["authPrefix"]
        or config["billingMode"] != "metered"
        or not re.fullmatch(r"wrkspc_[A-Za-z0-9]{16,80}", config.get("extraHeaders", {}).get("anthropic-workspace-id", ""))
    ):
        raise ValueError("editorial_claude_connection_invalid")
    return row, adapter


class LayerEdit(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    x: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    y: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    width: float | None = Field(default=None, ge=2, allow_inf_nan=False)
    height: float | None = Field(default=None, ge=2, allow_inf_nan=False)
    font_size: int | None = Field(default=None, ge=14, le=160)
    align: Literal["left", "center", "right"] | None = None
    keyframes: list[MotionKey] | None = Field(default=None, max_length=12)


class MotionRefinement(StudioContract):
    edits: list[LayerEdit] = Field(min_length=1, max_length=12)
    rationale: str = Field(min_length=1, max_length=900)


def apply_refinement(comp, plan, roles):
    candidate = comp.model_copy(deep=True)
    page = candidate.pages[0]
    layers = {layer.id: layer for layer in page.layers if not layer.locked and layer.visible}
    seen = set()
    for edit in plan.edits:
        layer = layers.get(edit.id)
        if edit.id in seen or layer is None:
            raise ValueError("editorial_claude_layer_invalid")
        seen.add(edit.id)
        style = LocalLayerStyle.model_validate(layer.properties)
        protected = roles.get(style.asset_id) in {"logo", "interface"}
        for field in ("x", "y", "width", "height"):
            value = getattr(edit, field)
            if value is not None:
                setattr(layer, field, value)
        if layer.x + layer.width > page.width or layer.y + layer.height > page.height:
            raise ValueError("editorial_claude_layer_outside_canvas")
        if edit.font_size is not None or edit.align is not None:
            if layer.kind != "text":
                raise ValueError("editorial_claude_text_style_invalid")
            if edit.font_size is not None:
                style.font_size = edit.font_size
            if edit.align is not None:
                style.align = edit.align
        if edit.keyframes is not None:
            if any(k.property not in {"x", "y", "scale", "rotation", "opacity"} for k in edit.keyframes):
                raise ValueError("editorial_claude_keyframe_invalid")
            if protected and any(k.property != "opacity" for k in edit.keyframes):
                raise ValueError("editorial_claude_protected_asset_motion_invalid")
            style.keyframes = edit.keyframes
        layer.properties = style.model_dump(mode="json", by_alias=True, exclude_defaults=True)
        layer.properties["schemaVersion"] = style.schema_version
    return candidate


def refine(db, record, job, connection, adapter, local_output, evidence, instruction):
    from PIL import Image, ImageOps

    if not local_output.commands or local_output.commands[0].id != "composition.replace":
        raise ValueError("editorial_claude_local_candidate_required")
    comp = CreativeCompositionV1.model_validate(local_output.commands[0].params["composition"])
    page = comp.pages[0]
    roles = evidence["materialSnapshot"]["roles"]
    layers = [layer.model_dump(mode="json", by_alias=True, exclude_defaults=True) for layer in page.layers
              if layer.visible and not layer.locked]
    image_ids = list(dict.fromkeys(layer["properties"].get("assetId") for layer in layers if layer["kind"] == "image"))[:3]
    image_ids = [identifier for identifier in image_ids if identifier]
    cards = [card for card in motion_editorial.knowledge()["cards"] if card["id"] in evidence["cardIds"]]
    context = {
        "editorialMotion": True,
        "instruction": instruction,
        "canvas": {"width": page.width, "height": page.height, "background": page.background},
        "timelineFrames": comp.media_timeline.duration_frames,
        "direction": evidence["receipts"][0],
        "motionCards": cards,
        "layers": layers,
        "assetRoles": roles,
        "imageOrder": image_ids,
        "structuredPlanningInstruction": (
            "For this Clicko refinement only, return JSON {edits:[{id,x?,y?,width?,height?,fontSize?,align?,keyframes?}],rationale}. "
            "Use the supplied schema. Propose distinct motion for photo, subject and reveal. Improve visual hierarchy and framing. "
            "Respect the canvas and keep text readable at phone width. Keyframe values x/y are offsets relative to layer position "
            "and frames are relative to each existing layer. No text, source, color, timing, audio, new layer or asset changes. "
            "For logos and interface layers use opacity only. Leave room for safe margins at the maximum animated scale. "
            "Images are original stills only, not evidence of completed motion."
        ),
        "outputSchema": MotionRefinement.model_json_schema(by_alias=True),
        "maxPromptChars": 28000,
        "maxOutputTokens": min(OUTPUT_TOKENS, connection.config["maxOutputTokens"]),
    }
    prompt_bytes = len(json.dumps(context, ensure_ascii=False).encode())
    if prompt_bytes > 28000:
        raise ValueError("editing_ai_prompt_too_large")
    with workspace_files(db, record, None, extra_asset_ids=image_ids) as (directory, params, _):
        paths = {entry["assetId"]: entry["path"] for entry in params["media"]}
        media = []
        for index, identifier in enumerate(image_ids):
            sample = Path(directory) / f"editorial-source-{index}.jpg"
            with Image.open(paths[identifier]) as source:
                image = ImageOps.exif_transpose(source).convert("RGBA")
                image.thumbnail((448, 448))
                background = Image.new("RGBA", image.size, page.background)
                background.alpha_composite(image)
                background.convert("RGB").save(sample, quality=83)
            media.append((sample, "image/jpeg"))
        llm_connections.reserve_request(db, job, connection, prompt_bytes + 1024 + len(media) * 6000,
                                        context["maxOutputTokens"])
        job.result_payload = {**(job.result_payload or {}), "submissionStarted": True, "submissionOutcome": "unknown"}
        db.commit()
        response = adapter.plan(MODEL, context, media)
    usage = response["usage"]
    cost = measured_request_cost(job, usage)
    job.result_payload = {**job.result_payload, "submissionOutcome": "response_received",
                          "measuredCostUsd": cost, "usage": usage}
    db.commit()  # Usage remains available if the model output or preview is rejected.
    if adapter.credential and adapter.credential in response["text"]:
        raise ValueError("editorial_claude_response_credential_rejected")
    proposed = MotionRefinement.model_validate_json(response["text"])
    candidate = apply_refinement(comp, proposed, roles)
    motion_editorial._fit_proof_images(db, record, candidate, evidence["format"], roles)
    job.result_payload = {**job.result_payload, "claudeRefinement": proposed.model_dump(mode="json", by_alias=True)}
    db.commit()
    evidence["receipts"].append({"stage": "claude_refinement", "status": "complete", "layerIds": [e.id for e in proposed.edits]})
    evidence["claude"] = {"provider": "anthropic", "model": response.get("responseModel") or MODEL,
                          "usage": usage, "measuredCostUsd": cost, "imageEvidence": image_ids}
    return AgentOutput.model_validate({
        "commands": [{"id": "composition.replace", "params": {"composition": candidate.model_dump(mode="json", by_alias=True)}}],
        "rationale": proposed.rationale,
    })
