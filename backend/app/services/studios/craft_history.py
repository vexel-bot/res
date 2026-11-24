"""Deterministic context renewal over durable native draft state."""

import copy
import json
from . import craft_observations

CHECKPOINT_FIELDS = ("continuation", "draftSummary", "previousPreviewSamples", "savedEditorialPlan", "shortContinuation",
                     "recentActions", "reviewState", "specialistContributions", "specialistDeliveryUpdate",
                     "continuationPreviewError", "registeredAssets", "projectFeedback", "nativeInspection", "nativeToolObservation",
                     "inspectionMemory", "deliveryReview", "directorContext", "nativeObservationIndex", "reviewArtifactIndex",
                     "materialSearches", "materialSearchAttempts", "availableMotionVariants")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def review_artifact_index(result):
    return [{**{k: item.get(k) for k in ("assetId", "checksumSha256", "draftBatch", "jobId", "documentRevision")},
             "interval": item.get("report", {}).get("interval"),
             "nativeChecksumSha256": item.get("report", {}).get("source", {}).get("nativeChecksumSha256")}
            for item in result.get("reviewArtifacts", [])]


def has_checkpoint_review(result, checkpoint):
    return bool(checkpoint and any(item.get("draftBatch") == checkpoint.get("batches")
        and item.get("nativeChecksumSha256") == checkpoint.get("checksumSha256")
        for item in review_artifact_index(result)))


def recoverable_contract(value):
    if not isinstance(value, dict):
        return value
    result = {k: recoverable_contract(v) for k, v in value.items()}
    if result.get("name") == "describe_commands" and len(encoded(result.get("result"))) > 4000:
        result["result"] = {identifier: {"required": schema.get("inputSchema", schema).get("required", []),
            "details": "Full schema is recoverable with describe_commands and this id."}
            for identifier, schema in (result.get("result") or {}).items() if isinstance(schema, dict)}
    if isinstance(result.get("nativeCommands"), list):
        result["nativeCommands"] = [{"id": c["id"], "label": c.get("label", c["id"]),
            "details": "describe_commands returns the full schema"} for c in result["nativeCommands"]]
    return result


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


def should_compact(messages, counted_tokens=None, *, checkpoint_tokens=0, checkpoint_bytes=0,
                   turns_since_attempt=None, serialized_bytes=None):
    if len(messages) <= 2:
        return False
    size = len(encoded(messages).encode()) if serialized_bytes is None else serialized_bytes
    if turns_since_attempt is not None and turns_since_attempt < 8:
        # A cache rewrite after a single exchange often costs more than retaining
        # that exchange. Large-input pressure and output-allowance recovery bypass this guard.
        return (counted_tokens or 0) >= 240_000 or size >= 12_000_000
    return (
        (counted_tokens is not None and counted_tokens > max(48000, checkpoint_tokens + 8192))
        or size > max(2_000_000, checkpoint_bytes + 512_000)
        or len(messages) > 72
    )


def renewal_decision(messages, candidate, *, before_tokens=None, after_tokens=None, reason, batch, turn):
    """Measure a proposed checkpoint before discarding a paid cached conversation."""
    before_bytes, after_bytes = (len(encoded(value).encode()) for value in (messages, candidate))
    counted = before_tokens is not None and after_tokens is not None
    before, after = (before_tokens, after_tokens) if counted else (before_bytes, after_bytes)
    saved = before - after
    # Policies for useful renewal, not provider context-window limits.
    useful = saved >= (4096 if counted else 65536) and saved >= before * .20
    return {"reason": reason, "draftBatch": batch, "turn": turn, "accepted": useful,
            "beforeBytes": before_bytes, "afterBytes": after_bytes,
            "beforeTokens": before_tokens, "retainedTokens": after_tokens,
            "comparisonBasis": "counted_tokens" if counted else "serialized_bytes",
            "savedFraction": round(saved / max(before, 1), 6)}


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


def recent_actions(tools, count=8):
    fields = ("name", "ok", "draftBatch", "error", "toolUseId", "inputDigest", "contributionId")
    return [{key: entry[key] for key in fields if key in entry} for entry in tools[-count:]]


def material_search_index(searches):
    return [{"query": item["query"], "origin": item["origin"],
             "status": item["result"].get("searchStatus"),
             "sourceIds": [source.get("id") for source in item["result"]["sources"]]}
            for item in searches]


def inspection_checkpoint(inspection, recoverable):
    if not inspection or not recoverable:
        return inspection
    return {"draftBatch": inspection["draftBatch"], "request": inspection["request"],
            "recovery": "inspect_project accepts the same request; use layerIds or limit for a focused reply."}


def retain_visible_inspections(inspection_ids, messages):
    """A previous tool ID is useful only while its actual result is visible."""
    visible = {block.get("tool_use_id") for message in messages if message.get("role") == "user"
               and isinstance(message.get("content"), list) for block in message["content"]
               if block.get("type") == "tool_result" and not block.get("is_error")}
    for key, identifier in list(inspection_ids.items()):
        if identifier not in visible:
            del inspection_ids[key]


def compact_messages(context, draft_summary, draft_batch, job_result, *, messages=(), prompt_cache=False):
    """Keep the stable briefing prefix and rebuild state without incomplete tool pairs."""
    tail = recent_tool_exchanges(messages) if context.get("retainRecentExchanges") else []
    source_calls = {}
    source_samples = {}
    retained_preview = None
    for message in messages:
        blocks = message.get("content")
        if not isinstance(blocks, list):
            continue
        # A previous renewal has no tool pairs. Recover its explicitly labelled
        # evidence too, so a second renewal does not silently discard pixels.
        if message.get("role") == "user":
            retained_source = None
            checkpoint_batch = None
            for index, block in enumerate(blocks):
                text = block.get("text") if block.get("type") == "text" else None
                if text == "Latest completed draft preview, sampled evidence.":
                    retained_source = None
                    if checkpoint_batch == draft_batch:
                        retained_preview = blocks[index + 1:]
                    break
                try:
                    header = json.loads(text) if text else None
                except (TypeError, ValueError):
                    header = None
                if isinstance(header, dict):
                    if "instruction" in header and "reviewedSamples" in header:
                        checkpoint_batch = header.get("draftBatch")
                    identifier = header.get("registeredSource") or header.get("registeredReference")
                    args = header.get("sample")
                    if (isinstance(identifier, str) and isinstance(args, dict)
                            and identifier in {args.get("assetId"), args.get("referenceId")}):
                        source_samples[identifier] = (args, [])
                        retained_source = identifier
                        continue
                if retained_source:
                    source_samples[retained_source][1].append(block)
        if message.get("role") == "assistant":
            for block in blocks:
                args = block.get("input") or {}
                if (block.get("type") == "tool_use" and (
                    (args.get("assetId") and block.get("name") in {"inspect_source_media", "view_image_asset", "review_clip"})
                    or (args.get("referenceId") and block.get("name") in {"inspect_reference", "review_reference"})
                )):
                    source_calls[block["id"]] = args
        if message.get("role") == "user":
            for block in blocks:
                args = source_calls.get(block.get("tool_use_id"))
                evidence = block.get("content")
                if (args and not block.get("is_error") and isinstance(evidence, list)
                        and any(item.get("type") == "image" for item in evidence)):
                    source_samples[args.get("assetId") or args["referenceId"]] = (args, evidence)
    previews = [
        entry["sample"] for entry in draft_reviews(job_result.get("tools", []), draft_batch) if "sample" in entry
    ][-3:]
    checkpoint = {
        "instruction": ("Continue from the saved native draft. The checkpoint is authoritative for current state. "
                        "Reviewed samples are already inspected on this exact revision. Use them before requesting another preview."),
        "draftBatch": draft_batch, "draft": draft_summary, "editorialPlan": job_result.get("editorialPlan"),
        "availableMotionVariants": context.get("availableMotionVariants", []),
        "registeredAssets": context.get("registeredAssets", []),
        "inspectedSources": [args for args, _ in source_samples.values() if args.get("assetId")],
        "inspectedReferences": [args for args, _ in source_samples.values() if args.get("referenceId")],
        "nativeToolObservation": recoverable_contract(job_result.get("nativeToolObservation")),
        "inspectionMemory": inspection_memory(job_result, draft_batch),
        "nativeObservationIndex": craft_observations.index(job_result.get("observationArchive", {})),
        "reviewArtifactIndex": review_artifact_index(job_result),
        "executionCheckIndex": [{"toolUseId": t.get("toolUseId"), "draftBatch": t.get("draftBatch"),
            "status": t.get("verification", t.get("executionReceipt", {}).get("configuration", {})).get("status")}
            for t in job_result.get("tools", []) if t.get("verification") or t.get("executionReceipt")][-24:],
        "executionDetailsAvailableVia": {"tool": "inspect_direction", "payload": {"kind": "execution"}},
        "deliveryReview": job_result.get("deliveryReview"),
        "directorContext": job_result.get("directorContext", context.get("directorContext")),
        "projectFeedback": context.get("projectFeedback", []),
        "acquiredMaterials": list(job_result.get("acquiredSources", {}).values()), "reviewedSamples": previews,
        "recentActions": recent_actions(job_result.get("tools", [])),
        "materialSearches": material_search_index(job_result.get("materialSearches", [])),
        "materialSearchAttempts": [{"query": t.get("input", {}).get("query"),
            "origin": t.get("input", {}).get("origin", "workspace"), "ok": t.get("ok"),
            "toolUseId": t.get("toolUseId"), "meaning": "Attempt history; consult retained results, do not infer matches."}
            for t in job_result.get("tools", []) if t.get("name") == "find_material_sources"],
        "reviewState": reviewed_draft(job_result.get("tools", []), draft_batch),
        "recentFailures": recent_actions([entry for entry in job_result.get("tools", []) if not entry.get("ok")], 3),
        "specialistContributions": [
            {field: item[field] for field in ("id", "scope", "status", "summary", "baseBatch") if field in item}
            for item in job_result.get("motionSwarm", {}).get("contributions", {}).values()
        ],
    }
    inspection = job_result.get("nativeInspection")
    if inspection and inspection.get("draftBatch") == draft_batch:
        checkpoint["nativeInspection"] = inspection_checkpoint(inspection, context.get("recoverableEvidenceMode"))
    content = [brief_block(context, prompt_cache), {"type": "text", "text": encoded(checkpoint)}]
    for asset_id, (args, evidence) in source_samples.items():
        content.append({"type": "text", "text": encoded({
            ("registeredReference" if args.get("referenceId") else "registeredSource"): asset_id,
            "sample": args,
            "interpretation": "Analysis evidence retained from this session. These pixels are not the edited draft.",
        })})
        if not context.get("recoverableEvidenceMode"):
            content.extend(copy.deepcopy(evidence))
        else:
            content.append({"type": "text", "text": "Source/reference pixels remain recoverable with their inspection tools; request them when needed."})
    # Preserve pixels from the last completed preview of this exact saved batch.
    preview_ids = set()
    unchanged_ids = {t.get("toolUseId") for t in job_result.get("tools", []) if t.get("unchanged")}
    for message in messages:
        if message.get("role") == "assistant" and isinstance(message.get("content"), list):
            for block in message["content"]:
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") in {"edit_project", "run_motion_script", "apply_contribution"} and block.get("id") not in unchanged_ids:
                    preview_ids.clear()
                if (block.get("name") in {"preview_frame", "preview_sequence", "review_clip"}
                        and not (block.get("input") or {}).get("assetId")):
                    preview_ids.add(block["id"])
    if previews:
        found = None
        for message in reversed(messages):
            blocks = message.get("content")
            if message.get("role") != "user" or not isinstance(blocks, list):
                continue
            found = next((
                block for block in reversed(blocks)
                if block.get("tool_use_id") in preview_ids and not block.get("is_error") and isinstance(block.get("content"), list)
                and any(item.get("type") == "image" for item in block["content"])
            ), None)
            if found:
                break
        evidence = found["content"] if found else retained_preview
        already_retained = found and any(b.get("tool_use_id") == found.get("tool_use_id")
            for message in tail if message.get("role") == "user" for b in message.get("content", []))
        if evidence and not already_retained:
            content.append({"type": "text", "text": "Latest completed draft preview, sampled evidence."})
            content.extend(copy.deepcopy(evidence))
    return [{"role": "user", "content": content}, *tail]


def inspection_memory(result, batch):
    """Keep useful contracts and focused properties, without carrying stale revisions."""
    return [recoverable_contract(item) for item in result.get("inspectionMemory", [])
            if item.get("draftBatch") in {None, batch}][-8:]


def recent_tool_exchanges(messages, keep=2):
    """Retain complete public tool exchanges; never move signed thinking to a new prefix."""
    pairs = []
    for assistant, user in zip(messages, messages[1:]):
        if assistant.get("role") != "assistant" or user.get("role") != "user":
            continue
        if not isinstance(assistant.get("content"), list) or not isinstance(user.get("content"), list):
            continue
        public = [b for b in assistant["content"] if b.get("type") in {"text", "tool_use"}]
        calls = {b["id"] for b in public if b.get("type") == "tool_use"}
        results = {b["tool_use_id"] for b in user["content"] if b.get("type") == "tool_result"}
        if calls and calls == results:
            pairs.append([{"role": "assistant", "content": copy.deepcopy(public)}, copy.deepcopy(user)])
    return [message for pair in pairs[-keep:] for message in pair]
