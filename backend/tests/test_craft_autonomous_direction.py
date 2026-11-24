"""Autonomous native sessions preserve audit, evidence and explicit request scope."""
import copy
from types import SimpleNamespace

import pytest

from app.domain.studios.craft import CraftAICommandRequestV1
from app.services.studios import craft_ai, craft_history, llm_connections
from app.services.studios.craft_agent import token_allowance


@pytest.fixture(autouse=True)
def clean_database():
    yield


@pytest.mark.parametrize('change', [
    {'generationBudgetUsd': 5}, {'directionEffort': 'standard'},
    {'executionTimeLimitSeconds': 60}, {'workflow': 'motion_swarm'},
])
def test_uncapped_mode_rejects_contradictory_request_before_provider(change):
    request = CraftAICommandRequestV1.model_validate({
        'expectedRevision': 1, 'instruction': 'Direção livre', 'directionEffort': 'open_ended',
        'unlimitedBudget': True, **change,
    })
    with pytest.raises(ValueError, match='craft_unlimited_native_requires_open_ended_without_cap'):
        craft_ai.ai_commands(None, None, request, None, 'same-task')


def test_uncapped_console_records_large_usage_and_uncertainty_without_imposing_cap(monkeypatch):
    from app.services.studios import external_policy
    monkeypatch.setattr(llm_connections, 'lock_editing_budget', lambda *_: None)
    monkeypatch.setattr(external_policy, 'assert_operation', lambda *_, **__: None)
    db = SimpleNamespace(refresh=lambda *_: None)
    connection = SimpleNamespace(workspace_id='workspace', revision=1, provider='anthropic', config={
        'enabled': True, 'billingMode': 'metered', 'budgetUsd': 0,
        'inputUsdPerMillion': 4, 'outputUsdPerMillion': 20, 'protocol': 'anthropic_messages',
        'baseUrl': 'https://api.anthropic.com/v1', 'models': ['claude-opus-5-5'],
        'maxOutputTokens': 32000,
    })
    original = copy.deepcopy(connection.config)
    job = SimpleNamespace(job_type='craft_ai', workspace_id='workspace', provider='llm.anthropic', request_payload={
        'llmConnectionRevision': 1, 'billingPolicy': 'anthropic_console_native', 'unlimitedNativeSession': True,
        'boundedNativeSession': False, 'generationBudgetUsd': None, 'motionExperiment': None,
        'directionEffort': 'open_ended', 'model': 'claude-opus-5-5',
        'pricing': {'inputUsdPerMillion': 4, 'outputUsdPerMillion': 20},
    }, result_payload={'measuredCostUsd': 123.4, 'uncertainCostUpperBoundUsd': 3})
    llm_connections.reserve_request(db, job, connection, 1000, 1000, provider_only=True)
    assert job.result_payload['financialReservationUsd'] == pytest.approx(126.424)
    assert connection.config == original
    _, tokens = token_allowance(connection, [], 123.4, None, input_tokens=100000, prompt_cache=True)
    assert tokens == 32000
    job.request_payload['generationBudgetUsd'] = 5
    with pytest.raises(ValueError, match='craft_provider_only_scope_invalid'):
        llm_connections.reserve_request(db, job, connection, 1000, 1000, provider_only=True)


def messages(text):
    return [{'role': 'user', 'content': text}, {'role': 'assistant', 'content': []},
            {'role': 'user', 'content': []}]


def test_larger_or_unhelpful_checkpoint_preserves_current_conversation():
    before = messages('evidence' * 20000)
    original = copy.deepcopy(before)
    candidate = messages('evidence' * 21000)
    result = craft_history.renewal_decision(before, candidate, before_tokens=65000, after_tokens=66000,
        reason='context_growth', batch=0, turn=1)
    assert not result['accepted'] and result['savedFraction'] < 0
    assert before == original


def test_token_count_takes_precedence_over_transport_byte_savings():
    result = craft_history.renewal_decision(messages('x' * 1000000), messages('x' * 200000),
        before_tokens=100000, after_tokens=98000, reason='context_growth', batch=1, turn=9)
    assert not result['accepted'] and result['comparisonBasis'] == 'counted_tokens'


def test_useful_renewal_has_complete_audit_for_every_trigger():
    for reason in ['context_growth', 'output_allowance']:
        result = craft_history.renewal_decision(messages('x' * 1000000), messages('x' * 600000),
            before_tokens=100000, after_tokens=60000, reason=reason, batch=2, turn=12)
        assert result['accepted'] and result['reason'] == reason
        assert result['beforeTokens'] == 100000 and result['retainedTokens'] == 60000
        assert result['turn'] == 12 and result['draftBatch'] == 2


def test_no_counts_uses_labelled_byte_comparison_without_claiming_token_savings():
    result = craft_history.renewal_decision(messages('x' * 1000000), messages('x' * 600000),
        reason='context_growth', batch=0, turn=2)
    assert result['accepted'] and result['comparisonBasis'] == 'serialized_bytes'
    assert result['beforeTokens'] is None and result['retainedTokens'] is None
