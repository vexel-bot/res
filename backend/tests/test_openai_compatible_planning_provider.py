from __future__ import annotations

import json

import httpx
import pytest

from app.domain.studios.intelligence import PlanningCopyRequestV1
from app.providers.studios.openai_compatible_planning import (
    GENERATION_SCHEMA_MAX_ITEMS,
    GENERATION_SCHEMA_MAX_SCRIPT,
    GENERATION_SCHEMA_MAX_TEXT,
    OpenAICompatiblePlanningCopyProvider,
    _canonicalize_storyboard_order,
    _constrain_generation_schema,
)


def planning_request() -> PlanningCopyRequestV1:
    return PlanningCopyRequestV1.model_validate(
        {
            "requestId": "planning-1",
            "workspaceId": "workspace-1",
            "brandMemoryRef": {"id": "brand-1", "revision": 7},
            "objective": "Gerar anúncio UGC de quinze segundos",
            "audience": "Gestores de social media",
            "product": "Clicko Studios",
            "offer": "Teste privado",
            "restrictions": ["Não prometer resultado garantido"],
            "evidence": [
                {
                    "id": "evidence-1",
                    "version": "v1",
                    "sourceUrl": "https://example.invalid/evidence/1",
                    "confidence": 0.9,
                }
            ],
        }
    )


def valid_draft() -> dict[str, object]:
    return {
        "schemaVersion": "studio.planning-copy-draft.v1",
        "brief": {
            "objective": "Gerar anúncio UGC de quinze segundos",
            "audience": "Gestores de social media",
            "angle": "Da ideia ao anúncio editável",
            "promise": "Organizar a produção em uma única linha de trabalho",
            "hook": "Sua próxima ideia pode virar um anúncio revisável.",
            "cta": "Entre no teste privado.",
            "channel": "instagram",
            "format": "short-video",
            "tone": "direto",
            "restrictions": ["Não prometer resultado garantido"],
            "evidence": [
                {
                    "id": "evidence-1",
                    "version": "v1",
                    "sourceUrl": "https://example.invalid/evidence/1",
                    "confidence": 0.9,
                }
            ],
        },
        "script": "Sua próxima ideia pode virar um anúncio revisável.",
        "claims": [
            {
                "claimId": "claim-evidence",
                "text": "A evidência fornecida sustenta este ponto.",
                "evidenceIds": ["evidence-1"],
                "requiresHumanReview": False,
            },
            {
                "claimId": "claim-review",
                "text": "Resultado estimado a confirmar.",
                "evidenceIds": [],
                "requiresHumanReview": True,
            },
        ],
        "alternatives": ["Da pauta ao vídeo, com revisão."],
        "abstentions": [],
    }


def provider_for(
    draft: dict[str, object],
    *,
    seen: list[httpx.Request] | None = None,
) -> OpenAICompatiblePlanningCopyProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(draft)}}]},
        )

    return OpenAICompatiblePlanningCopyProvider(
        base_url="https://qwen-worker.example.invalid",
        model="Qwen/Qwen3-4B-Instruct-2507",
        model_revision="cdbee75f17c01a7cc42f958dc650907174af0554",
        api_key="secret-not-serialized",
        transport=httpx.MockTransport(handler),
    )


def test_qwen_compatible_adapter_wraps_structured_output_in_trusted_lineage() -> None:
    seen: list[httpx.Request] = []
    progress: list[int] = []
    with provider_for(valid_draft(), seen=seen) as provider:
        result = provider.plan(planning_request(), progress.append, lambda: False)

    assert progress == [5, 20, 80, 100]
    assert result.status == "complete"
    assert result.workspace_id == "workspace-1"
    assert result.lineage.provider == "evaluation.qwen-openai-compatible"
    assert result.lineage.model_revision == "cdbee75f17c01a7cc42f958dc650907174af0554"
    assert len(result.lineage.parameters_digest_sha256) == 64
    assert seen[0].url.path == "/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer secret-not-serialized"
    body = json.loads(seen[0].content)
    assert body["response_format"]["type"] == "json_schema"
    assert "secret-not-serialized" not in json.dumps(result.model_dump(mode="json"))


def test_generation_schema_is_bounded_without_narrowing_the_domain_contract() -> None:
    from app.domain.studios.intelligence import PlanningCopyDraftV1

    source = PlanningCopyDraftV1.model_json_schema(by_alias=True)
    constrained = _constrain_generation_schema(source)

    assert source["properties"]["script"]["maxLength"] == 20_000
    assert constrained["properties"]["script"]["maxLength"] == GENERATION_SCHEMA_MAX_SCRIPT
    assert constrained["properties"]["storyboard"]["maxItems"] == GENERATION_SCHEMA_MAX_ITEMS
    brief = constrained["$defs"]["CreativeBriefV1"]["properties"]
    assert brief["audience"]["maxLength"] == GENERATION_SCHEMA_MAX_TEXT


def test_storyboard_order_is_canonicalized_from_array_position_only() -> None:
    draft = valid_draft()
    draft["storyboard"] = [
        {
            "beatId": "beat-b",
            "order": 8,
            "narrativeRole": "demo",
            "durationSeconds": 3,
            "visualDirection": "Mostrar produto.",
        },
        {
            "beatId": "beat-a",
            "order": 4,
            "narrativeRole": "cta",
            "durationSeconds": 2,
            "visualDirection": "Mostrar CTA.",
        },
    ]
    normalized = _canonicalize_storyboard_order(draft)

    assert [beat["beatId"] for beat in normalized["storyboard"]] == ["beat-b", "beat-a"]
    assert [beat["order"] for beat in normalized["storyboard"]] == [0, 1]


def test_truncated_completion_is_rejected_even_when_json_is_parseable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": json.dumps(valid_draft())},
                    }
                ]
            },
        )

    with (
        OpenAICompatiblePlanningCopyProvider(
            base_url="http://localhost:18080",
            model="test",
            model_revision="test",
            transport=httpx.MockTransport(handler),
        ) as provider,
        pytest.raises(RuntimeError, match="truncated_output"),
    ):
        provider.plan(planning_request(), lambda _: None, lambda: False)


def test_compact_decoding_schema_does_not_force_mid_word_cutoff() -> None:
    from app.providers.studios.openai_compatible_planning import _ugc_generation_schema, _UgcWorkerDraft

    domain_schema = _UgcWorkerDraft.model_json_schema(by_alias=True)
    decoding_schema = _ugc_generation_schema(domain_schema)
    assert domain_schema["properties"]["hook"]["maxLength"] == 100
    assert "maxLength" not in json.dumps(decoding_schema)
    assert decoding_schema["properties"]["beats"]["maxItems"] == 5


def test_adapter_rejects_model_output_that_drops_a_locked_restriction() -> None:
    draft = valid_draft()
    draft["brief"]["restrictions"] = []  # type: ignore[index]

    with provider_for(draft) as provider, pytest.raises(ValueError, match="dropped restrictions"):
        provider.plan(planning_request(), lambda _: None, lambda: False)


def test_adapter_rejects_unreviewed_claim_without_evidence() -> None:
    draft = valid_draft()
    draft["claims"][1]["requiresHumanReview"] = False  # type: ignore[index]

    with provider_for(draft) as provider, pytest.raises(RuntimeError, match="invalid_structured_output"):
        provider.plan(planning_request(), lambda _: None, lambda: False)


def test_adapter_rejects_invented_evidence_reference() -> None:
    draft = valid_draft()
    draft["claims"][0]["evidenceIds"] = ["invented"]  # type: ignore[index]

    with provider_for(draft) as provider, pytest.raises(ValueError, match="unknown evidence"):
        provider.plan(planning_request(), lambda _: None, lambda: False)


def test_adapter_rejects_dropped_request_evidence() -> None:
    draft = valid_draft()
    draft["brief"]["evidence"] = []  # type: ignore[index]

    with provider_for(draft) as provider, pytest.raises(ValueError, match="dropped evidence"):
        provider.plan(planning_request(), lambda _: None, lambda: False)


def test_adapter_rejects_invented_storyboard_evidence() -> None:
    draft = valid_draft()
    draft["storyboard"] = [
        {
            "beatId": "beat-1",
            "order": 0,
            "narrativeRole": "demo",
            "durationSeconds": 3,
            "visualDirection": "Mostrar a interface sintética.",
            "evidenceIds": ["invented-storyboard-evidence"],
        }
    ]

    with provider_for(draft) as provider, pytest.raises(ValueError, match="unknown evidence"):
        provider.plan(planning_request(), lambda _: None, lambda: False)


def test_adapter_cancellation_prevents_network_request() -> None:
    seen: list[httpx.Request] = []
    with provider_for(valid_draft(), seen=seen) as provider, pytest.raises(RuntimeError, match="cancelled_before"):
        provider.plan(planning_request(), lambda _: None, lambda: True)

    assert seen == []


@pytest.mark.parametrize(
    "url",
    ["qwen-worker", "file:///tmp/worker", "https://user:pass@example.invalid"],
)
def test_adapter_rejects_invalid_or_credential_bearing_urls(url: str) -> None:
    with pytest.raises(ValueError):
        OpenAICompatiblePlanningCopyProvider(
            base_url=url,
            model="Qwen/Qwen3-4B-Instruct-2507",
            model_revision="immutable-revision",
        )
