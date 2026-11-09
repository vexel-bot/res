"""Canonical timeline commands for the existing audited LLM planning pipeline."""

from ...domain.studios.contracts import MediaTimelineV1
from ...domain.studios.timeline_editor import MotionKey, TimelineEditRequest, VisualMotion
from . import timeline_editor


def capability(contract):
    timeline_editor.validate(contract)
    schema = MediaTimelineV1.model_json_schema(by_alias=True)
    definitions = schema.pop("$defs", {})
    # The general document contract intentionally permits native-editor data.
    # The canonical renderer accepts a smaller, executable subset: tell the
    # planner its actual keyframe shape rather than an unconstrained object.
    key_schema = MotionKey.model_json_schema(by_alias=True)
    motion_schema = VisualMotion.model_json_schema(by_alias=True)
    definitions.update(motion_schema.pop("$defs", {}))
    for definition in definitions.values():
        properties = definition.get("properties", {})
        if "keyframes" in properties:
            properties["keyframes"] = {"type": "array", "items": key_schema, "maxItems": 32}
        for name in ("transform", "motion"):
            if name in properties:
                properties[name] = motion_schema
    return {
        "buildId": "ffmpeg.timeline-v1",
        "commands": [
            {
                "id": "timeline.replace",
                "inputSchema": {
                    "type": "object",
                    "properties": {"timeline": schema},
                    "required": ["timeline"],
                    "additionalProperties": False,
                    "$defs": definitions,
                },
            },
            {
                "id": "timeline.patch",
                "inputSchema": {
                    "$defs": definitions,
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["updates"],
                    "properties": {
                        "updates": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 32,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["trackId", "itemId", "changes"],
                                "properties": {
                                    "trackId": {"type": "string"},
                                    "itemId": {"type": "string"},
                                    "changes": {
                                        "type": "object",
                                        "minProperties": 1,
                                        "additionalProperties": False,
                                        "properties": {
                                            "timeline": {"type": "object"},
                                            "source": {"type": "object"},
                                            "transform": motion_schema,
                                            "motion": motion_schema,
                                            "keyframes": {"type": "array", "items": key_schema, "maxItems": 32},
                                            "text": {"type": "string"},
                                            "gainDb": {"type": "number"},
                                            "fadeInFrames": {"type": "integer"},
                                            "fadeOutFrames": {"type": "integer"},
                                        },
                                    },
                                },
                            },
                        }
                    },
                },
            },
        ],
    }


def normalize_commands(commands):
    """Expand only unambiguous per-frame motion shorthand, then validate normally.

    Older planner responses used {frame, scale, y}; no execution semantics are
    changed by expanding these into the renderer's per-property keyframes.
    Unknown properties and malformed values still fail closed.
    """
    from copy import deepcopy

    result = deepcopy(commands)
    for command in result:
        if command.get("id") != "timeline.replace":
            continue
        timeline = command.get("params", {}).get("timeline", {})
        for track in timeline.get("tracks", []):
            for item in [*track.get("clips", []), *track.get("cues", [])]:
                keys = []
                for key in item.get("keyframes", []):
                    if "property" in key:
                        keys.append(key)
                        continue
                    properties = set(key) - {"frame", "easing"}
                    if not properties or not properties <= {"x", "y", "scale", "opacity", "rotation"}:
                        raise ValueError("timeline_keyframes_invalid")
                    for prop in sorted(properties):
                        expanded = {"property": prop, "frame": key.get("frame"), "value": key[prop]}
                        if "easing" in key:
                            expanded["easing"] = key["easing"]
                        keys.append(MotionKey.model_validate(expanded).model_dump(mode="json", by_alias=True))
                item["keyframes"] = keys
    return result


def patch_timeline(timeline, updates):
    """Bounded edits preserve every unspecified item and field, including audio."""
    from copy import deepcopy

    result = deepcopy(timeline)
    if not isinstance(updates, list) or not 1 <= len(updates) <= 32:
        raise ValueError("timeline_patch_updates_invalid")
    seen = set()
    allowed = {
        "timeline",
        "source",
        "transform",
        "motion",
        "keyframes",
        "text",
        "gainDb",
        "fadeInFrames",
        "fadeOutFrames",
    }
    for update in updates:
        if set(update) != {"trackId", "itemId", "changes"}:
            raise ValueError("timeline_patch_update_invalid")
        identity = (update["trackId"], update["itemId"])
        if identity in seen:
            raise ValueError("timeline_patch_duplicate_item")
        seen.add(identity)
        track = next((t for t in result["tracks"] if t["id"] == identity[0]), None)
        item = next(
            (
                i
                for i in (
                    (track.get("cues", []) if track.get("kind") == "caption" else track.get("clips", []))
                    if track
                    else []
                )
                if i["id"] == identity[1]
            ),
            None,
        )
        changes = update["changes"]
        if not item or track.get("locked") or item.get("locked"):
            raise ValueError("timeline_patch_item_unavailable")
        if not isinstance(changes, dict) or not changes or not set(changes) <= allowed:
            raise ValueError("timeline_patch_changes_invalid")
        for name, value in changes.items():
            if name in {"timeline", "source", "transform", "motion"}:
                if not isinstance(value, dict):
                    raise ValueError("timeline_patch_object_required")
                item[name] = {**(item.get(name) or {}), **value}
            else:
                item[name] = deepcopy(value)
    return result


def apply(db, record, request, user, key, digest, command_request, output, job):
    if len(command_request.commands) != 1 or command_request.commands[0].id not in {
        "timeline.replace",
        "timeline.patch",
    }:
        raise ValueError("timeline_ai_single_validated_timeline_required")
    # No implicit acquisition or invented IDs: the planner can only edit bound materials.
    from .compatibility import record_to_contract

    contract = record_to_contract(record)
    command = command_request.commands[0]
    value = (
        patch_timeline(
            contract.composition.media_timeline.model_dump(mode="json", by_alias=True), command.params.get("updates")
        )
        if command.id == "timeline.patch"
        else command.params["timeline"]
    )
    timeline = MediaTimelineV1.model_validate(value)
    available = {asset.id for asset in contract.assets}
    proposed = contract.model_copy(
        update={"composition": contract.composition.model_copy(update={"media_timeline": timeline})}
    )
    if not timeline_editor.validate(proposed) <= available:
        raise ValueError("timeline_ai_asset_not_bound")
    operation = {"idempotencyKey": key, "payloadHash": digest, "aiTrace": output.get("aiTrace", {}), "aiJobId": job.id}
    document = timeline_editor.save(
        db,
        record,
        TimelineEditRequest(expected_revision=request.expected_revision, timeline=timeline),
        user,
        key,
        operation=operation,
    )
    from .craft import receipt

    return receipt(db, record, key, digest) or {"document": document.model_dump(mode="json", by_alias=True)}
