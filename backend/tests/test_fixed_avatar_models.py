from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.domain.studios.avatar_models import (
    AvatarVisualSourceV1,
    FixedAvatarCastV1,
    SingleAvatarPilotV1,
)
from scripts.admit_single_avatar_video import validate_probe_payload


def test_gemini_keys_are_loaded_as_secrets_and_calls_default_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_1", "first-secret")
    monkeypatch.setenv("API_2", "second-secret")
    settings = Settings(_env_file=None)

    assert settings.gemini_api_key_1 is not None
    assert settings.gemini_api_key_2 is not None
    assert settings.gemini_api_key_1.get_secret_value() == "first-secret"
    assert settings.gemini_api_key_2.get_secret_value() == "second-secret"
    assert "first-secret" not in repr(settings)
    assert settings.gemini_outbound_enabled is False
    assert settings.gemini_video_generation_enabled is False
    assert settings.gemini_max_external_spend_usd == 0


def test_video_generation_requires_explicit_positive_spend_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_1", "first-secret")
    settings = Settings(
        _env_file=None,
        gemini_outbound_enabled=True,
        gemini_video_generation_enabled=True,
        gemini_max_external_spend_usd=0,
    )
    with pytest.raises(RuntimeError, match="positive external spend limit"):
        settings.validate_for_startup()


def test_openai_key_is_secret_and_video_calls_default_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-secret")
    settings = Settings(_env_file=None)

    assert settings.openai_api_key is not None
    assert settings.openai_api_key.get_secret_value() == "openai-test-secret"
    assert "openai-test-secret" not in repr(settings)
    assert settings.openai_outbound_enabled is False
    assert settings.openai_video_generation_enabled is False
    assert settings.openai_max_external_spend_usd == 0


def test_openai_video_generation_requires_explicit_outbound_and_spend_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-secret")
    disabled = Settings(
        _env_file=None,
        openai_video_generation_enabled=True,
        openai_max_external_spend_usd=1.5,
    )
    with pytest.raises(RuntimeError, match="OPENAI_OUTBOUND_ENABLED"):
        disabled.validate_for_startup()

    zero_spend = Settings(
        _env_file=None,
        openai_outbound_enabled=True,
        openai_video_generation_enabled=True,
        openai_max_external_spend_usd=0,
    )
    with pytest.raises(RuntimeError, match="positive external spend limit"):
        zero_spend.validate_for_startup()


def test_heygem_visual_source_cannot_train_voice_or_skip_consent() -> None:
    with pytest.raises(ValidationError, match="consent grant"):
        AvatarVisualSourceV1.model_validate(
            {
                "sourceKind": "authorized_performer_video",
                "assetId": "asset-1",
                "checksumSha256": "a" * 64,
                "durationMilliseconds": 8000,
                "width": 1280,
                "height": 720,
                "exactlyOnePerson": True,
                "faceVisibleAndUnobstructed": True,
                "neutralCaptureApproved": True,
                "rightsStatus": "rights_verified",
                "voiceTrainingAllowed": False,
            }
        )

    with pytest.raises(ValidationError):
        AvatarVisualSourceV1.model_validate(
            {
                "sourceKind": "synthetic_original_video",
                "assetId": "asset-2",
                "checksumSha256": "b" * 64,
                "durationMilliseconds": 8000,
                "width": 1280,
                "height": 720,
                "exactlyOnePerson": True,
                "faceVisibleAndUnobstructed": True,
                "neutralCaptureApproved": True,
                "rightsStatus": "rights_verified",
                "voiceTrainingAllowed": True,
            }
        )


def test_fixed_cast_manifest_is_valid_and_blocked_without_source_video() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "studios"
        / "knowledge"
        / "ledgers"
        / "fixed-avatar-cast-2026-09-02.json"
    )
    cast = FixedAvatarCastV1.model_validate(json.loads(path.read_text(encoding="utf-8")))

    assert len(cast.models) == 6
    assert sum(model.gender_presentation == "man" for model in cast.models) == 3
    assert sum(model.gender_presentation == "woman" for model in cast.models) == 3
    caio = next(model for model in cast.models if model.avatar_id == "avatar-caio-vale")
    assert caio.visual_source is not None
    assert caio.provider_status == "pending_benchmark"
    assert caio.provider_candidate == "musetalk-v1.5-local"
    assert all(model.visual_source is None for model in cast.models if model is not caio)
    assert all(model.provider_status == "pending_source_video" for model in cast.models if model is not caio)
    assert all(model.local_voice_only for model in cast.models)


def test_single_avatar_pilot_enforces_one_video_and_explicit_spend_gate() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "studios"
        / "knowledge"
        / "ledgers"
        / "single-avatar-pilot-caio-vale-2026-09-02.json"
    )
    pilot = SingleAvatarPilotV1.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )

    assert pilot.avatar_id == "avatar-caio-vale"
    assert pilot.base_video_count == 1
    assert pilot.source_video is not None
    assert pilot.source_video.duration_milliseconds == 12000
    assert pilot.production_state in {"avatar_pending_benchmark", "avatar_rendered_private_review"}
    assert pilot.external_spend_limit_usd == 1.5
    assert pilot.video_generation_provider == "openai-sora-2"
    assert pilot.source_video_specification.duration_milliseconds == 12000
    assert pilot.visual_provider == "musetalk-v1.5-local"
    assert pilot.voice_route == "local-only"
    assert pilot.verification.generation_attempt_count == 1
    assert pilot.verification.external_request_sent is True

    with pytest.raises(ValidationError, match="must remain blocked"):
        SingleAvatarPilotV1.model_validate(
            {
                **pilot.model_dump(by_alias=True),
                "videoGenerationProvider": "gemini-omni-1.1-flash",
                "providerFreeTierVerified": False,
                "externalSpendLimitUsd": 0,
                "productionState": "avatar_pending_benchmark",
                "sourceVideo": {
                    "sourceKind": "synthetic_original_video",
                    "assetId": "caio-base-video-v1",
                    "checksumSha256": "c" * 64,
                    "durationMilliseconds": 8000,
                    "width": 1080,
                    "height": 1920,
                    "exactlyOnePerson": True,
                    "faceVisibleAndUnobstructed": True,
                    "neutralCaptureApproved": True,
                    "rightsStatus": "rights_verified",
                    "voiceTrainingAllowed": False,
                },
            }
        )


def test_single_avatar_video_probe_rejects_short_or_multiple_streams() -> None:
    valid = {
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "duration": "8.0"}
        ],
        "format": {"duration": "8.0"},
    }
    assert validate_probe_payload(valid) == (8000, 1080, 1920)

    short = {**valid, "format": {"duration": "7.999"}}
    with pytest.raises(ValueError, match="at_least_8_seconds"):
        validate_probe_payload(short)

    multiple = {
        **valid,
        "streams": [*valid["streams"], {**valid["streams"][0], "width": 720}],
    }
    with pytest.raises(ValueError, match="exactly_one_video_stream"):
        validate_probe_payload(multiple)
