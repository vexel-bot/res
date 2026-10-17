"""Transport boundary tests; simulated HTTP, not a real generation benchmark."""
import hashlib
import json
import time
from dataclasses import replace
from decimal import Decimal

import httpx
import pytest

from app.providers.studios.higgsfield import (
    BASE,
    I2V,
    IMAGE,
    TTV,
    GenerationQuote,
    GenerationReceipt,
    HiggsfieldError,
    HiggsfieldProvider,
    PreparedGeneration,
)

RID = "d7e6c0f3-6699-4f6c-bb45-2ad7fd9158ff"
KEY = "explicit-persisted-intent-1"


@pytest.fixture(autouse=True)
def clean_database():
    # Override the inherited DB-reset fixture for this transport-only module.
    # No test here reads/writes the DB or starts the app/client.
    yield


def intent(model=TTV, **parameters):
    return PreparedGeneration.prepare(model, {"prompt": "Produto real, câmera fixa", **parameters}, KEY)


def receipt(status="queued", **fields):
    return {"request_id": RID, "status": status, "status_url": f"{BASE}/requests/{RID}/status",
            "cancel_url": f"{BASE}/requests/{RID}/cancel", **fields}


def quote(prepared, **fields):
    return GenerationQuote(prepared.digest_sha256, Decimal("0.420"), Decimal("7.000"), time.monotonic(),
                           hashlib.sha256(b"Key test-key-id:test-secret").hexdigest(), **fields)


def provider(handler, *, enabled=True):
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    return HiggsfieldProvider("test-key-id", "test-secret", client=client, submission_enabled=enabled)


def test_disabled_submission_makes_no_http_request():
    calls = []
    p = provider(lambda request: calls.append(request), enabled=False)
    prepared = intent()
    with pytest.raises(HiggsfieldError, match="submission_disabled"):
        p.submit(prepared, quote(prepared), maximum_cost_usd="1")
    assert calls == []


def test_estimate_and_submit_use_identical_body_and_exact_decimal_price():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Key test-key-id:test-secret"
        if request.url.path.startswith("/estimate/"):
            assert "Idempotency-Key" not in request.headers
            return httpx.Response(200, json={"usd": "0.420001", "credits": "7.000"})
        return httpx.Response(200, json=receipt())

    p = provider(handler)
    prepared = intent(duration=5, sound="off", aspect_ratio="9:16")
    estimated = p.estimate(prepared)
    assert estimated.usd == Decimal("0.420001")
    with pytest.raises(HiggsfieldError, match="budget_exceeded"):
        p.submit(prepared, estimated, maximum_cost_usd="0.420000")
    result = p.submit(prepared, estimated, maximum_cost_usd="0.420001")
    assert result.status == "queued" and not result.terminal
    assert result.output_kind == "video" and result.candidate_urls == ()
    assert calls[0].content == calls[1].content == prepared.payload_json.encode()
    assert calls[1].headers["Idempotency-Key"] == KEY
    assert calls[1].url.path == "/" + TTV


def test_persisted_intent_replay_after_ambiguous_timeout_keeps_body_and_key():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("private prompt and key must not escape", request=request)
        return httpx.Response(200, json=receipt())

    p = provider(handler)
    original = intent(sound="off")
    estimated = quote(original)
    with pytest.raises(HiggsfieldError) as failure:
        p.submit(original, estimated, maximum_cost_usd="1")
    assert failure.value.outcome_unknown
    assert "private" not in str(failure.value)
    assert len(calls) == 1  # No automatic POST retry.
    restored = PreparedGeneration.model_validate_json(original.model_dump_json())
    result = p.submit(restored, estimated, maximum_cost_usd="1")
    assert result.request_id == RID
    assert calls[0].content == calls[1].content
    assert calls[0].headers["Idempotency-Key"] == calls[1].headers["Idempotency-Key"] == KEY


def test_mutated_input_and_new_key_cannot_reuse_quote():
    parameters = {"prompt": "Material original", "duration": 5}
    original = PreparedGeneration.prepare(TTV, parameters, KEY)
    parameters["duration"] = 10
    assert json.loads(original.payload_json)["duration"] == 5
    calls = []
    p = provider(lambda request: calls.append(request))
    for changed in [PreparedGeneration.prepare(TTV, parameters, KEY),
                    PreparedGeneration.prepare(TTV, {"prompt": "Material original", "duration": 5}, "new-intent")]:
        with pytest.raises(HiggsfieldError, match="binding_conflict"):
            p.submit(changed, quote(original), maximum_cost_usd="1")
    assert calls == []


def test_field_order_canonical_but_omitted_and_null_remain_distinct():
    a = PreparedGeneration.prepare(IMAGE, {"prompt": "Imagem original", "image_url": None}, KEY)
    b = PreparedGeneration.prepare(IMAGE, {"image_url": None, "prompt": "Imagem original"}, KEY)
    c = PreparedGeneration.prepare(IMAGE, {"prompt": "Imagem original"}, KEY)
    assert a.payload_json == b.payload_json and a.digest_sha256 == b.digest_sha256
    assert c.digest_sha256 != a.digest_sha256
    assert "Imagem" not in repr(a) and KEY not in repr(a)


@pytest.mark.parametrize("model,parameters", [
    (TTV, {"duration": 60}), (TTV, {"duration": True}), (TTV, {"duration": 5.0}),
    (TTV, {"cfg_scale": float("nan")}), (TTV, {"sound": "disabled"}),
    (TTV, {"multi_shots": True}), (TTV, {"unknown": "private data"}),
    (I2V, {}), (I2V, {"image_url": "http://host/image.jpg"}),
    (I2V, {"image_url": "https://cdn.example/image.jpg", "aspect_ratio": "9:16"}),
    (IMAGE, {"image_weight": 101}),
])
def test_invalid_model_parameters_rejected_before_transport(model, parameters):
    with pytest.raises(HiggsfieldError, match="intent_invalid"):
        intent(model, **parameters)


def test_image_reference_and_image_edit_preserve_signed_urls_and_model():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=receipt())

    p = provider(handler)
    for model in [I2V, IMAGE]:
        prepared = intent(model, image_url="https://cdn.example/asset.jpg?signature=opaque")
        result = p.submit(prepared, quote(prepared), maximum_cost_usd="1")
        assert result.output_kind == ("image" if model == IMAGE else "video")
        assert json.loads(calls[-1].content)["image_url"].endswith("?signature=opaque")
        assert calls[-1].url.path == "/" + model


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1", None, True, "oops"])
def test_estimate_rejects_unusable_money(amount):
    p = provider(lambda request: httpx.Response(200, json={"usd": amount, "credits": "1"}))
    with pytest.raises(HiggsfieldError, match="amount_invalid"):
        p.estimate(intent())


def test_expired_quote_cannot_submit():
    calls = []
    prepared = intent()
    expired = replace(quote(prepared), observed_monotonic=time.monotonic() - 301)
    p = provider(lambda request: calls.append(request))
    with pytest.raises(HiggsfieldError, match="quote_expired"):
        p.submit(prepared, expired, maximum_cost_usd="1")
    assert calls == []


def test_quote_from_other_credentials_is_not_a_valid_account_price():
    calls = []
    p = HiggsfieldProvider("other-account-key", "other-secret", submission_enabled=True,
                          client=httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request))))
    prepared = intent()
    with pytest.raises(HiggsfieldError, match="credentials_changed"):
        p.submit(prepared, quote(prepared), maximum_cost_usd="1")
    assert calls == []


def test_json_number_estimate_retains_precision_without_float_rounding():
    p = provider(lambda request: httpx.Response(200, content=b'{"usd":0.1234567890123456789,"credits":"1"}'))
    assert p.estimate(intent()).usd == Decimal("0.1234567890123456789")


@pytest.mark.parametrize("http_status,unknown", [(422, False), (429, False), (408, True), (500, True), (503, True)])
def test_submission_http_failure_is_sanitized_without_retry(http_status, unknown):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(http_status, json={"detail": "private prompt key image"})

    prepared = intent()
    with pytest.raises(HiggsfieldError) as failure:
        provider(handler).submit(prepared, quote(prepared), maximum_cost_usd="1")
    assert str(failure.value) == f"higgsfield_http_{http_status}"
    assert failure.value.outcome_unknown is unknown and len(calls) == 1


def test_redirect_does_not_send_credentials_or_claim_acceptance():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(307, headers={"Location": "https://other.example/steal"})

    prepared = intent()
    with pytest.raises(HiggsfieldError) as failure:
        provider(handler).submit(prepared, quote(prepared), maximum_cost_usd="1")
    assert failure.value.outcome_unknown and len(calls) == 1
    assert calls[0].url.host == "api.higgsfield.ai"


@pytest.mark.parametrize("bad_url", ["https://other.example/status", f"{BASE}/requests/{RID}/status?key=leak",
                                     f"http://api.higgsfield.ai/requests/{RID}/status"])
def test_control_urls_cannot_redirect_authenticated_polling(bad_url):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=receipt(status_url=bad_url))

    prepared = intent()
    with pytest.raises(HiggsfieldError) as failure:
        provider(handler).submit(prepared, quote(prepared), maximum_cost_usd="1")
    assert failure.value.outcome_unknown and len(calls) == 1


def test_poll_preserves_request_identity_and_only_completed_has_candidates():
    responses = [receipt(), receipt("in_progress"), receipt("completed", video={"url": "https://cdn.example/output.mp4"})]
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=responses.pop(0))

    p = provider(handler)
    prepared = intent()
    current = p.submit(prepared, quote(prepared), maximum_cost_usd="1")
    current = p.retrieve(current)
    assert current.status == "in_progress" and not current.terminal and current.candidate_urls == ()
    current = p.retrieve(current)
    assert current.terminal and current.candidate_urls == ("https://cdn.example/output.mp4",)
    assert [c.method for c in calls] == ["POST", "GET", "GET"]


def test_wrong_request_or_wrong_media_kind_is_not_admitted():
    current = GenerationReceipt(RID, "queued", "video", f"{BASE}/requests/{RID}/status")
    for value in [receipt(request_id="c7816ea4-eaad-4091-9c84-d8d8e6e8b2b3"),
                  receipt("completed", images=[{"url": "https://cdn.example/photo.jpg"}])]:
        p = provider(lambda request, value=value: httpx.Response(200, json=value))
        with pytest.raises((HiggsfieldError, ValueError)):
            p.retrieve(current)


@pytest.mark.parametrize("state", ["failed", "nsfw", "canceled"])
def test_unsuccessful_terminal_states_are_not_completed_candidates(state):
    current = GenerationReceipt(RID, "queued", "video", f"{BASE}/requests/{RID}/status")
    result = provider(lambda request: httpx.Response(200, json=receipt(state, error="private"))).retrieve(current)
    assert result.status == state and result.terminal and result.candidate_urls == ()
    assert "private" not in repr(result)


def test_cancel_acceptance_is_not_terminal_and_started_work_is_not_canceled():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(202)

    p = provider(handler)
    current = GenerationReceipt(RID, "queued", "video", f"{BASE}/requests/{RID}/status",
                                f"{BASE}/requests/{RID}/cancel")
    assert p.cancel_queued(current) is True
    assert not current.terminal and current.status == "queued"
    assert p.cancel_queued(replace(current, status="in_progress")) is False
    assert len(calls) == 1
    p = provider(lambda request: httpx.Response(400, json={"detail": "processing started"}))
    assert p.cancel_queued(current) is False


def test_forged_control_handle_cannot_traverse_authenticated_routes():
    calls = []
    p = provider(lambda request: calls.append(request))
    forged = GenerationReceipt("../../unexpected", "queued", "video", f"{BASE}/requests/../../unexpected/status")
    with pytest.raises(HiggsfieldError, match="request_id_invalid"):
        p.retrieve(forged)
    assert calls == []


def test_only_documented_cancel_acceptance_returns_true():
    current = GenerationReceipt(RID, "queued", "video", f"{BASE}/requests/{RID}/status",
                                f"{BASE}/requests/{RID}/cancel")
    p = provider(lambda request: httpx.Response(200, json={"status": "ok"}))
    with pytest.raises(HiggsfieldError, match="cancel_response_invalid"):
        p.cancel_queued(current)


def test_unparseable_acceptance_is_unknown_not_a_rejected_generation():
    prepared = intent()
    for response in [httpx.Response(200, content=b"not json"),
                     httpx.Response(200, json=receipt(status="unexpected")),
                     httpx.Response(200, json=receipt("completed"))]:
        with pytest.raises(HiggsfieldError) as failure:
            provider(lambda request, response=response: response).submit(
                prepared, quote(prepared), maximum_cost_usd="1")
        assert failure.value.outcome_unknown
