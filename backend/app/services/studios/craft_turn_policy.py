"""Recover output truncation without replaying an incomplete native operation."""


def output_limit(configured, model, turns, *, direction_v2=False):
    """Increase per-response headroom after confirmed truncation, not session spend.

    Opus 5.5 always thinks; thinking and tool JSON share its output allowance.
    Only a received max_tokens result justifies escalation. Financial guards
    still apply in token_allowance. Unknown submissions are never retried here.
    """
    if not direction_v2 or model != "claude-opus-5-5":
        return configured
    limit = configured
    for turn in turns:
        if turn.get("stopReason") != "max_tokens":
            continue
        sent = turn.get("effectiveRequestParameters", {}).get("maxOutputTokens", configured)
        if not isinstance(sent, int) or sent < 1:
            sent = configured
        if sent >= 128000:
            raise ValueError("craft_agent_output_capacity_exhausted")
        limit = max(limit, min(128000, sent * 2))
    return limit


TRUNCATION_GUIDANCE = (
    "The last response reached its output limit before a complete action. "
    "No operation from that incomplete response was executed. The saved native draft and your "
    "direction remain authoritative. Use the additional output headroom to execute the next "
    "concrete production step in a focused tool call, rather than redesigning the entire film at once. "
    "You retain all creative decisions."
)


def reasoning_effort(context, stage):
    """Keep diagnosis/comparison demanding; avoid deliberating every engine call.

    Opus 5.5's medium is its documented default for agentic execution. A plan
    revision must not accidentally label the entire later production conception.
    This controls compute, never the creative choices or available tools.
    """
    cycle_stage = context.get("directorContext", {}).get("autonomousCycle", {}).get("stage")
    if stage in {"comparison", "review", "conclusion", "delivered", "diagnosis"}:
        return "high"
    if cycle_stage in {"experiment", "production"} or stage in {"experiment", "production", "revision"}:
        return "medium"
    return "high"
