"""Canonical timeline commands for the existing audited LLM planning pipeline."""

from ...domain.studios.contracts import MediaTimelineV1
from ...domain.studios.timeline_editor import TimelineEditRequest
from . import timeline_editor


def capability(contract):
    timeline_editor.validate(contract)
    schema = MediaTimelineV1.model_json_schema(by_alias=True)
    definitions = schema.pop("$defs", {})
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
            }
        ],
    }


def apply(db, record, request, user, key, digest, command_request, output, job):
    if len(command_request.commands) != 1 or command_request.commands[0].id != "timeline.replace":
        raise ValueError("timeline_ai_single_validated_timeline_required")
    timeline = MediaTimelineV1.model_validate(command_request.commands[0].params["timeline"])
    # No implicit acquisition or invented IDs: the planner can only edit bound materials.
    from .compatibility import record_to_contract

    contract = record_to_contract(record)
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
