"""Deterministic context renewal over durable native draft state."""

import copy
import json

CHECKPOINT_FIELDS = ("continuation", "draftSummary", "previousPreviewSamples", "savedEditorialPlan", "shortContinuation",
                     "recentActions", "reviewState", "specialistContributions", "specialistDeliveryUpdate",
                     "continuationPreviewError", "registeredAssets", "projectFeedback")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def brief_block(context, prompt_cache):
    stable = {key: value for key, value in context.items() if key not in CHECKPOINT_FIELDS}
    prefix = {"type": "text", "text": encoded(stable)}
    if prompt_cache:
        prefix["cache_control"] = {"type": "ephemeral"}
    return prefix


def start_message(context, *, prompt_cache=False, evidence=()):
    current = {key: context[key] for key in CHECKPOINT_FIELDS if key in context}
    content = [brief_block(context, prompt_cache)]
    if current:
        content.append({"type": "text", "text": encoded(current)})
    content.extend(evidence)
    return [{"role": "user", "content": content}]


def should_count_tokens(messages):
    if len(messages) <= 1 or len(messages) % 8 == 1:
        return True
    recent = messages[-1].get("content", [])
    return isinstance(recent, list) and any(
        isinstance(block.get("content"), list) or len(encoded(block)) > 12000 for block in recent
    )


def should_compact(messages, counted_tokens=None):
    return len(messages) > 2 and (
        (counted_tokens is not None and counted_tokens > 48000)
        or len(encoded(messages).encode()) > 2_000_000
        or len(messages) > 72
    )


def draft_reviews(tools, batch):
    if batch is None:
        return []
    return [entry for entry in tools if entry.get("ok") and entry.get("draftBatch") == batch
            and not entry.get("reusedToolUseId") and not (entry.get("sample") or {}).get("assetId")
            and entry.get("name") in {"preview_frame", "preview_sequence", "inspect_transition", "review_clip"}]


def reviewed_draft(tools, batch):
    samples = draft_reviews(tools, batch)
    if len(samples) < 2:
        return None
    return {
        "draftBatch": batch, "completedReviews": len(samples), "latestSamples": samples[-6:],
        "nextDecision": ("The draft is unchanged across these reviews. If ready, call finish_project. "
                         "If you see a concrete problem, make the focused edit or request the evidence still needed."),
    }


def compact_messages(context, draft_summary, draft_batch, job_result, *, messages=(), prompt_cache=False):
    """Keep the stable briefing prefix and rebuild state without incomplete tool pairs."""
    previews = [
        entry["sample"] for entry in draft_reviews(job_result.get("tools", []), draft_batch) if "sample" in entry
    ][-3:]
    checkpoint = {
        "instruction": ("Continue from the saved native draft. The checkpoint is authoritative for current state. "
                        "Reviewed samples are already inspected on this exact revision. Use them before requesting another preview."),
        "draftBatch": draft_batch, "draft": draft_summary, "editorialPlan": job_result.get("editorialPlan"),
        "registeredAssets": context.get("registeredAssets", []),
        "projectFeedback": context.get("projectFeedback", []),
        "acquiredMaterials": list(job_result.get("acquiredSources", {}).values()), "reviewedSamples": previews,
        "recentActions": job_result.get("tools", [])[-8:],
        "reviewState": reviewed_draft(job_result.get("tools", []), draft_batch),
        "recentFailures": [entry for entry in job_result.get("tools", []) if not entry.get("ok")][-3:],
        "specialistContributions": [
            {field: item[field] for field in ("id", "scope", "status", "summary", "baseBatch") if field in item}
            for item in job_result.get("motionSwarm", {}).get("contributions", {}).values()
        ],
    }
    content = [brief_block(context, prompt_cache), {"type": "text", "text": encoded(checkpoint)}]
    # Preserve pixels from the last completed preview of this exact saved batch.
    preview_ids = set()
    for message in messages:
        if message.get("role") == "assistant" and isinstance(message.get("content"), list):
            for block in message["content"]:
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") in {"edit_project", "run_motion_script", "apply_contribution"}:
                    preview_ids.clear()
                if (block.get("name") in {"preview_frame", "preview_sequence", "review_clip"}
                        and not (block.get("input") or {}).get("assetId")):
                    preview_ids.add(block["id"])
    if previews:
        for message in reversed(messages):
            blocks = message.get("content")
            if message.get("role") != "user" or not isinstance(blocks, list):
                continue
            found = next((
                block for block in reversed(blocks)
                if block.get("tool_use_id") in preview_ids and isinstance(block.get("content"), list)
                and any(item.get("type") == "image" for item in block["content"])
            ), None)
            if found:
                content.append({"type": "text", "text": "Latest completed draft preview, sampled evidence."})
                content.extend(copy.deepcopy(found["content"]))
                break
    return [{"role": "user", "content": content}]
