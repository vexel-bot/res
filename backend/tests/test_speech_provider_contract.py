from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from app.domain.studios.contracts import (
    SpeechProvenanceV1,
    SpeechSynthesisRequestV1,
    SpeechSynthesisResultV1,
)
from app.domain.studios.providers import SPEECH_PROVIDERS


def test_speech_port_is_typed_and_registry_stays_empty_until_promotion() -> None:
    text = "Café Aurora: uma pausa boa começa aqui."
    request = SpeechSynthesisRequestV1(
        locale="pt-BR",
        text=text,
        script_digest_sha256=hashlib.sha256(text.encode()).hexdigest(),
        voice_key="kokoro.pt-br.female-01",
    )
    result = SpeechSynthesisResultV1(
        provider="example",
        provider_version="0.0.0",
        audio_format=request.audio_format,
        sample_rate=request.sample_rate,
        duration_ms=1200,
        artifact_checksum_sha256="b" * 64,
        provenance=SpeechProvenanceV1(
            source_revision="abcdef1",
            model_digest_sha256="c" * 64,
            worker_manifest_digest_sha256="d" * 64,
            worker_image_digest=f"sha256:{'e' * 64}",
            provenance_mode="test",
        ),
    )

    assert request.schema_version == "studio.speech-synthesis-request.v1"
    assert result.schema_version == "studio.speech-synthesis-result.v1"
    assert SPEECH_PROVIDERS == {}


def test_speech_result_rejects_unverifiable_checksum() -> None:
    with pytest.raises(ValidationError):
        SpeechSynthesisResultV1(
            provider="example",
            provider_version="0.0.0",
            audio_format="wav",
            sample_rate=24_000,
            duration_ms=1200,
            artifact_checksum_sha256="not-a-digest",
            provenance={
                "sourceRevision": "abcdef1",
                "modelDigestSha256": "c" * 64,
                "workerManifestDigestSha256": "d" * 64,
                "workerImageDigest": f"sha256:{'e' * 64}",
                "provenanceMode": "test",
            },
        )
