from types import SimpleNamespace

import pytest

from app.services.studios.craft_agent import token_allowance
from app.services.studios.craft_turn_policy import output_limit, reasoning_effort


def truncated(sent):
    return {"stopReason": "max_tokens", "effectiveRequestParameters": {"maxOutputTokens": sent}}


def test_received_truncation_increases_headroom_across_restarts_without_changing_other_models():
    history = [truncated(20000), {"stopReason": "tool_use"}, truncated(20000)]
    assert output_limit(20000, "claude-opus-5-5", history, direction_v2=True) == 40000
    assert output_limit(20000, "claude-opus-5-5", history + [truncated(40000)], direction_v2=True) == 80000
    assert output_limit(20000, "other", history, direction_v2=True) == 20000
    assert output_limit(20000, "claude-opus-5-5", history) == 20000
    assert output_limit(20000, "claude-opus-5-5", [{"stopReason": "tool_use"}], direction_v2=True) == 20000


def test_model_capacity_failure_does_not_restart_an_identical_paid_attempt():
    assert output_limit(20000, "claude-opus-5-5", [truncated(80000)], direction_v2=True) == 128000
    with pytest.raises(ValueError, match="craft_agent_output_capacity_exhausted"):
        output_limit(20000, "claude-opus-5-5", [truncated(128000)], direction_v2=True)


def test_escalated_response_still_respects_existing_financial_budget():
    connection = SimpleNamespace(config={"maxOutputTokens": 20000, "billingMode": "metered",
                                        "inputUsdPerMillion": 4, "outputUsdPerMillion": 20})
    size, tokens = token_allowance(connection, [], 0, 0.10, input_tokens=1000, output_tokens=80000)
    assert tokens == 4800
    assert (size * 4 + tokens * 20) / 1000000 <= 0.10
    assert token_allowance(connection, [], 0, None, input_tokens=1000, output_tokens=40000)[1] == 40000


def test_effort_tracks_execution_without_weakening_comparative_or_diagnostic_decisions():
    context = {"directorContext": {"autonomousCycle": {"stage": "experiment"}}}
    assert reasoning_effort(context, "conception") == "medium"
    assert reasoning_effort(context, "production") == "medium"
    for stage in ["diagnosis", "comparison", "review", "conclusion", "delivered"]:
        assert reasoning_effort(context, stage) == "high"
    assert reasoning_effort({}, "conception") == "high"
