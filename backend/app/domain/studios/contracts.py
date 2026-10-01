from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class StudioContract(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True, extra="forbid")


class EntityReferenceV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    version: str | int | None = None


class BrandMemoryReferenceV1(EntityReferenceV1):
    revision: int = Field(ge=1)


class OpportunityEvidenceReferenceV1(EntityReferenceV1):
    source_url: str | None = Field(default=None, max_length=4000)
    observed_at: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class AssetReferenceV1(EntityReferenceV1):
    media_type: str = Field(default="application/octet-stream", max_length=160)
    checksum: str | None = Field(default=None, max_length=160)
    origin: str = Field(default="workspace", max_length=80)
    rights_status: Literal["verified", "restricted", "unknown"] = "unknown"
    provenance: dict[str, Any] = Field(default_factory=dict)


class ConsentGrantReferenceV1(EntityReferenceV1):
    policy_version: str = Field(min_length=1, max_length=120)


class IdentityVersionReferenceV1(EntityReferenceV1):
    consent_grant_id: str | None = Field(default=None, max_length=120)


class VoiceVersionReferenceV1(EntityReferenceV1):
    consent_grant_id: str | None = Field(default=None, max_length=120)


class CreativeBriefV1(StudioContract):
    schema_version: Literal["studio.creative-brief.v1"] = "studio.creative-brief.v1"
    objective: str = Field(min_length=1, max_length=1000)
    audience: str = Field(min_length=1, max_length=2000)
    angle: str = Field(default="", max_length=1000)
    promise: str = Field(default="", max_length=1000)
    hook: str = Field(default="", max_length=2000)
    cta: str = Field(default="", max_length=500)
    channel: str = Field(default="instagram", max_length=80)
    format: str = Field(default="post", max_length=80)
    tone: str = Field(default="", max_length=1000)
    restrictions: list[str] = Field(default_factory=list, max_length=100)
    hypotheses: list[str] = Field(default_factory=list, max_length=100)
    evidence: list[OpportunityEvidenceReferenceV1] = Field(default_factory=list, max_length=100)


class CreativeLayerV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    kind: Literal["text", "shape", "image", "video", "audio", "group"]
    name: str = Field(default="Layer", min_length=1, max_length=240)
    x: float = Field(default=0, ge=-16384, le=32768)
    y: float = Field(default=0, ge=-16384, le=32768)
    width: float = Field(gt=0, le=16384)
    height: float = Field(gt=0, le=16384)
    rotation: float = Field(default=0, ge=-360, le=360)
    opacity: float = Field(default=1, ge=0, le=1)
    visible: bool = True
    locked: bool = False
    z_index: int = Field(default=0, ge=0, le=10000)
    properties: dict[str, Any] = Field(default_factory=dict)


class UgcShapeLayerPropertiesV1(StudioContract):
    """Supported provider-neutral subset for the first UGC compositor."""

    schema_version: Literal["studio.ugc-shape-layer-properties.v1"] = "studio.ugc-shape-layer-properties.v1"
    type: Literal["shape"] = "shape"
    shape: Literal["rectangle"] = "rectangle"
    fill: str = Field(default="#6c5ce7", pattern=r"^#[0-9a-fA-F]{6}$")
    radius: int = Field(default=0, ge=0, le=512)


class UgcTextLayerPropertiesV1(StudioContract):
    schema_version: Literal["studio.ugc-text-layer-properties.v1"] = "studio.ugc-text-layer-properties.v1"
    type: Literal["text"] = "text"
    text: str = Field(min_length=1, max_length=4000)
    font_size: int = Field(default=48, ge=16, le=320)
    min_font_size: int = Field(default=24, ge=8, le=320)
    font_family: Literal["Liberation Sans"] = "Liberation Sans"
    font_weight: Literal["bold"] = "bold"
    color: str = Field(default="#ffffff", pattern=r"^#[0-9a-fA-F]{6}$")
    align: Literal["left", "center", "right"] = "center"
    line_height: float = Field(default=1.05, ge=0.8, le=3)

    @model_validator(mode="after")
    def validate_font_bounds(self) -> UgcTextLayerPropertiesV1:
        if self.min_font_size > self.font_size:
            raise ValueError("Text min font size cannot exceed font size")
        return self


class CreativePageV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    role: str = Field(default="content", max_length=120)
    width: int = Field(ge=320, le=8192)
    height: int = Field(ge=320, le=8192)
    safe_area: int = Field(default=48, ge=0, le=1000)
    background: str = Field(default="#10181c", pattern=r"^#[0-9a-fA-F]{6}$")
    duration_ms: int | None = Field(default=None, ge=1, le=86_400_000)
    layers: list[CreativeLayerV1] = Field(default_factory=list, max_length=1000)


class FrameRateV1(StudioContract):
    numerator: int = Field(default=30, ge=1, le=240_000)
    denominator: int = Field(default=1, ge=1, le=1001)


class StreamTimeBaseV1(StudioContract):
    """Seconds represented by one native stream timestamp tick."""

    numerator: int = Field(ge=1, le=1_000_000_000)
    denominator: int = Field(ge=1, le=1_000_000_000)


class VideoStreamV1(StudioContract):
    index: int = Field(ge=0)
    codec: str = Field(min_length=1, max_length=120)
    width: int = Field(ge=1, le=100_000)
    height: int = Field(ge=1, le=100_000)
    pixel_format: str | None = Field(default=None, max_length=120)
    frame_rate: FrameRateV1
    real_frame_rate: FrameRateV1 | None = None
    time_base: StreamTimeBaseV1 | None = None
    start_pts: int | None = None
    start_microseconds: int = Field(default=0, ge=-86_400_000_000, le=86_400_000_000)
    duration_ticks: int | None = Field(default=None, ge=0)
    duration_microseconds: int | None = Field(default=None, ge=0)
    bitrate: int | None = Field(default=None, ge=0)
    rotation_degrees: int = Field(default=0, ge=-360, le=360)


class AudioStreamV1(StudioContract):
    index: int = Field(ge=0)
    codec: str = Field(min_length=1, max_length=120)
    sample_rate: int | None = Field(default=None, ge=1, le=1_000_000)
    channels: int | None = Field(default=None, ge=1, le=128)
    channel_layout: str | None = Field(default=None, max_length=120)
    time_base: StreamTimeBaseV1 | None = None
    start_pts: int | None = None
    start_microseconds: int = Field(default=0, ge=-86_400_000_000, le=86_400_000_000)
    duration_ticks: int | None = Field(default=None, ge=0)
    duration_microseconds: int | None = Field(default=None, ge=0)
    bitrate: int | None = Field(default=None, ge=0)


class MediaProbeResultV1(StudioContract):
    schema_version: Literal["studio.media-probe.v1"] = "studio.media-probe.v1"
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=240)
    asset_id: str
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    container: str = Field(min_length=1, max_length=240)
    start_microseconds: int = Field(default=0, ge=-86_400_000_000, le=86_400_000_000)
    duration_microseconds: int = Field(ge=0)
    size_bytes: int = Field(ge=0)
    bitrate: int | None = Field(default=None, ge=0)
    video_streams: list[VideoStreamV1] = Field(default_factory=list, max_length=32)
    audio_streams: list[AudioStreamV1] = Field(default_factory=list, max_length=32)
    provider_trace: dict[str, Any] = Field(default_factory=dict)


class MediaIngestV1(StudioContract):
    schema_version: Literal["studio.media-ingest.v1"] = "studio.media-ingest.v1"
    id: str
    workspace_id: str
    asset_id: str
    status: Literal["pending", "probing", "ready", "rejected", "failed"]
    probe_provider: str
    media_info: MediaProbeResultV1 | None = None
    validation_errors: list[str] = Field(default_factory=list)
    proxy_asset_id: str | None = None
    waveform_asset_id: str | None = None
    proxy_time_map: MediaTimeMapV1 | None = None
    generation_job_id: str | None = None
    idempotency_key: str
    requested_by: str
    created_at: datetime
    updated_at: datetime


class CreateMediaIngestRequest(StudioContract):
    workspace_id: str
    asset_id: str


class MediaProxySpecV1(StudioContract):
    schema_version: Literal["studio.media-proxy-spec.v1"] = "studio.media-proxy-spec.v1"
    format: Literal["mp4"] = "mp4"
    max_width: int = Field(default=1080, ge=320, le=3840)
    max_height: int = Field(default=1920, ge=320, le=3840)
    target_fps: int = Field(default=30, ge=1, le=60)
    video_codec: Literal["h264"] = "h264"
    audio_codec: Literal["aac"] = "aac"
    quality: Literal["draft", "standard"] = "draft"


class MediaTimeMapSegmentV1(StudioContract):
    source_start_microseconds: int = Field(default=0, ge=0, le=86_400_000_000)
    representation_start_microseconds: int = Field(default=0, ge=0, le=86_400_000_000)
    duration_microseconds: int = Field(gt=0, le=86_400_000_000)
    rate_numerator: Literal[1] = 1
    rate_denominator: Literal[1] = 1


class MediaTimeMapV1(StudioContract):
    """Validated identity mapping from a derivative clock back to its canonical source clock."""

    schema_version: Literal["studio.media-time-map.v1"] = "studio.media-time-map.v1"
    source_asset_id: str = Field(min_length=1, max_length=120)
    representation_asset_id: str = Field(min_length=1, max_length=120)
    source_checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    representation_checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    source_frame_rate: FrameRateV1
    representation_frame_rate: FrameRateV1
    source_video_start_microseconds: int = Field(ge=-86_400_000_000, le=86_400_000_000)
    representation_video_start_microseconds: int = Field(
        ge=-86_400_000_000,
        le=86_400_000_000,
    )
    source_audio_start_microseconds: int | None = Field(
        default=None,
        ge=-86_400_000_000,
        le=86_400_000_000,
    )
    representation_audio_start_microseconds: int | None = Field(
        default=None,
        ge=-86_400_000_000,
        le=86_400_000_000,
    )
    source_duration_microseconds: int = Field(gt=0, le=86_400_000_000)
    representation_duration_microseconds: int = Field(gt=0, le=86_400_000_000)
    max_drift_microseconds: int = Field(ge=0, le=60_000_000)
    max_stream_offset_drift_microseconds: int = Field(ge=0, le=60_000_000)
    allowed_drift_microseconds: int = Field(ge=0, le=60_000_000)
    segments: list[MediaTimeMapSegmentV1] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def validate_identity_mapping(self) -> MediaTimeMapV1:
        if self.source_asset_id == self.representation_asset_id:
            raise ValueError("Media time map representation must differ from source")
        if self.max_drift_microseconds != abs(
            self.source_duration_microseconds - self.representation_duration_microseconds
        ):
            raise ValueError("Media time map drift does not match durations")
        if self.max_drift_microseconds > self.allowed_drift_microseconds:
            raise ValueError("Media time map drift exceeds allowed limit")
        if (self.source_audio_start_microseconds is None) != (self.representation_audio_start_microseconds is None):
            raise ValueError("Media time map audio stream presence differs")
        source_audio_offset = (
            None
            if self.source_audio_start_microseconds is None
            else self.source_audio_start_microseconds - self.source_video_start_microseconds
        )
        representation_audio_offset = (
            None
            if self.representation_audio_start_microseconds is None
            else self.representation_audio_start_microseconds - self.representation_video_start_microseconds
        )
        expected_stream_drift = (
            0
            if source_audio_offset is None or representation_audio_offset is None
            else abs(source_audio_offset - representation_audio_offset)
        )
        if self.max_stream_offset_drift_microseconds != expected_stream_drift:
            raise ValueError("Media time map stream offset drift is inconsistent")
        if self.max_stream_offset_drift_microseconds > self.allowed_drift_microseconds:
            raise ValueError("Media time map stream offset drift exceeds allowed limit")
        segment = self.segments[0]
        if segment.source_start_microseconds != 0 or segment.representation_start_microseconds != 0:
            raise ValueError("Media time map v1 must normalize both clocks to zero")
        if segment.duration_microseconds != min(
            self.source_duration_microseconds,
            self.representation_duration_microseconds,
        ):
            raise ValueError("Media time map segment must cover the shared duration")
        return self


class AudioWaveformSpecV1(StudioContract):
    schema_version: Literal["studio.audio-waveform-spec.v1"] = "studio.audio-waveform-spec.v1"
    audio_stream_index: int | None = Field(default=None, ge=0, le=255)
    sample_rate: int = Field(default=48_000, ge=8_000, le=192_000)
    points_per_second: int = Field(default=100, ge=10, le=1000)
    channel_mode: Literal["mono"] = "mono"
    include_rms: bool = True

    @model_validator(mode="after")
    def validate_bucket_size(self) -> AudioWaveformSpecV1:
        if self.sample_rate % self.points_per_second:
            raise ValueError("Waveform sampleRate must be divisible by pointsPerSecond")
        return self


class AudioWaveformBucketV1(StudioContract):
    minimum: int = Field(ge=-32_768, le=32_767)
    maximum: int = Field(ge=-32_768, le=32_767)
    rms: int | None = Field(default=None, ge=0, le=32_768)

    @model_validator(mode="after")
    def validate_peaks(self) -> AudioWaveformBucketV1:
        if self.minimum > self.maximum:
            raise ValueError("Waveform bucket minimum must not exceed maximum")
        return self


class AudioWaveformManifestV1(StudioContract):
    schema_version: Literal["studio.audio-waveform-manifest.v1"] = "studio.audio-waveform-manifest.v1"
    media_ingest_id: str = Field(min_length=1, max_length=120)
    source_asset_id: str = Field(min_length=1, max_length=120)
    source_checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    audio_stream_index: int = Field(ge=0, le=255)
    clock_unit: Literal["microseconds"] = "microseconds"
    start_microseconds: int = Field(ge=-86_400_000_000, le=86_400_000_000)
    duration_microseconds: int = Field(ge=0, le=86_400_000_000)
    sample_rate: int = Field(ge=8_000, le=192_000)
    channel_count: Literal[1] = 1
    samples_per_bucket: int = Field(ge=1)
    total_samples: int = Field(ge=0)
    bucket_count: int = Field(ge=0)
    buckets: list[AudioWaveformBucketV1] = Field(default_factory=list, max_length=5_000_000)
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=240)
    spec: AudioWaveformSpecV1
    spec_digest: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    @model_validator(mode="after")
    def validate_counts(self) -> AudioWaveformManifestV1:
        if self.bucket_count != len(self.buckets):
            raise ValueError("Waveform bucket count does not match payload")
        expected = (self.total_samples + self.samples_per_bucket - 1) // self.samples_per_bucket
        if self.bucket_count != expected:
            raise ValueError("Waveform buckets do not cover all decoded samples")
        return self


class CreateAudioWaveformRequest(StudioContract):
    workspace_id: str
    spec: AudioWaveformSpecV1 = Field(default_factory=AudioWaveformSpecV1)


class AudioWaveformResultV1(StudioContract):
    schema_version: Literal["studio.audio-waveform-result.v1"] = "studio.audio-waveform-result.v1"
    media_ingest_id: str
    source_asset_id: str
    waveform_asset_id: str
    provider: str
    provider_version: str
    storage_backend: str
    media_type: Literal["application/vnd.clicko.audio-waveform+json"] = "application/vnd.clicko.audio-waveform+json"
    size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    source_checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    spec_digest: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    start_microseconds: int = Field(ge=-86_400_000_000, le=86_400_000_000)
    duration_microseconds: int = Field(ge=0, le=86_400_000_000)
    sample_rate: int = Field(ge=8_000, le=192_000)
    bucket_count: int = Field(ge=0)


class CreateMediaProxyRequest(StudioContract):
    workspace_id: str
    spec: MediaProxySpecV1 = Field(default_factory=MediaProxySpecV1)


class MediaProxyEncodeResultV1(StudioContract):
    schema_version: Literal["studio.media-proxy-encode-result.v1"] = "studio.media-proxy-encode-result.v1"
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=240)
    width: int = Field(ge=1, le=8192)
    height: int = Field(ge=1, le=8192)
    frame_rate: FrameRateV1
    video_start_microseconds: int = Field(default=0, ge=-86_400_000_000, le=86_400_000_000)
    audio_start_microseconds: int = Field(default=0, ge=-86_400_000_000, le=86_400_000_000)
    duration_microseconds: int = Field(gt=0, le=86_400_000_000)
    video_codec: str = Field(min_length=1, max_length=80)
    audio_codec: str | None = Field(default=None, max_length=80)
    warnings: list[str] = Field(default_factory=list, max_length=100)


class MediaProxyResultV1(StudioContract):
    schema_version: Literal["studio.media-proxy-result.v1"] = "studio.media-proxy-result.v1"
    media_ingest_id: str
    source_asset_id: str
    proxy_asset_id: str
    provider: str
    provider_version: str
    storage_backend: str
    media_type: Literal["video/mp4"] = "video/mp4"
    size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    width: int = Field(ge=1, le=8192)
    height: int = Field(ge=1, le=8192)
    frame_rate: FrameRateV1
    duration_microseconds: int = Field(gt=0, le=86_400_000_000)
    video_codec: str
    audio_codec: str | None = None
    warnings: list[str] = Field(default_factory=list, max_length=100)
    time_map: MediaTimeMapV1


class TranscriptWordV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    start_microseconds: int = Field(ge=0, le=86_400_000_000)
    end_microseconds: int = Field(gt=0, le=86_400_000_000)
    text: str = Field(min_length=1, max_length=500)
    confidence: float | None = Field(default=None, ge=0, le=1)
    speaker: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def validate_word_range(self) -> TranscriptWordV1:
        if self.end_microseconds <= self.start_microseconds:
            raise ValueError("Transcript word end must be after start")
        return self


class TranscriptSegmentV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    start_microseconds: int = Field(ge=0, le=86_400_000_000)
    end_microseconds: int = Field(gt=0, le=86_400_000_000)
    text: str = Field(min_length=1, max_length=4000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    speaker: str | None = Field(default=None, max_length=240)
    words: list[TranscriptWordV1] = Field(default_factory=list, max_length=10_000)

    @model_validator(mode="after")
    def validate_segment_range(self) -> TranscriptSegmentV1:
        if self.end_microseconds <= self.start_microseconds:
            raise ValueError("Transcript segment end must be after start")
        previous_end = self.start_microseconds
        for word in self.words:
            if word.start_microseconds < self.start_microseconds or word.end_microseconds > self.end_microseconds:
                raise ValueError("Transcript word must stay inside its segment")
            if word.start_microseconds < previous_end:
                raise ValueError("Transcript words must be ordered and non-overlapping")
            previous_end = word.end_microseconds
        return self


class TranscriptDocumentV1(StudioContract):
    schema_version: Literal["studio.transcript.v1"] = "studio.transcript.v1"
    id: str
    workspace_id: str
    media_ingest_id: str
    asset_id: str
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    status: Literal["draft", "ready", "reviewed"] = "draft"
    revision: int = Field(default=1, ge=1)
    version: int = Field(default=1, ge=1)
    provider: str = Field(default="manual", min_length=1, max_length=120)
    provider_version: str | None = Field(default=None, max_length=240)
    segments: list[TranscriptSegmentV1] = Field(default_factory=list, max_length=100_000)
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_segments(self) -> TranscriptDocumentV1:
        previous_end = 0
        ids: set[str] = set()
        for segment in self.segments:
            if segment.id in ids:
                raise ValueError("Transcript segment ids must be unique")
            if segment.start_microseconds < previous_end:
                raise ValueError("Transcript segments must be ordered and non-overlapping")
            ids.add(segment.id)
            previous_end = segment.end_microseconds
        return self


class SpeechSynthesisRequestV1(StudioContract):
    """Provider-neutral request for stock or identity-bound speech synthesis."""

    schema_version: Literal["studio.speech-synthesis-request.v1"] = "studio.speech-synthesis-request.v1"
    locale: str = Field(min_length=2, max_length=32)
    text: str = Field(min_length=1, max_length=100_000)
    script_digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    voice_key: str = Field(min_length=1, max_length=240)
    audio_format: Literal["wav", "flac", "mp3"] = "wav"
    sample_rate: int = Field(default=24_000, ge=8_000, le=192_000)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)

    @model_validator(mode="after")
    def validate_script_digest(self) -> SpeechSynthesisRequestV1:
        digest = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if digest != self.script_digest_sha256.lower():
            raise ValueError("Speech script digest does not match text")
        return self


class VoiceCloneReferenceV1(StudioContract):
    """Private, consent-bound normalized audio handed to a clone provider."""

    schema_version: Literal["studio.voice-clone-reference.v1"] = "studio.voice-clone-reference.v1"
    voice_version_id: str = Field(min_length=1, max_length=120)
    consent_grant_id: str = Field(min_length=1, max_length=120)
    source_asset_id: str = Field(min_length=1, max_length=120)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    normalized_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    audio_format: Literal["wav"] = "wav"
    sample_rate: Literal[24_000] = 24_000
    channels: Literal[1] = 1
    duration_ms: int = Field(ge=3_000, le=30_000)
    retention_mode: Literal["job-ephemeral"] = "job-ephemeral"


class TranscriptionRequestV1(StudioContract):
    """Provider-neutral request for automatic transcript generation."""

    schema_version: Literal["studio.transcription-request.v1"] = "studio.transcription-request.v1"
    media_ingest_id: str = Field(min_length=1, max_length=120)
    source_asset_id: str = Field(min_length=1, max_length=120)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    word_timestamps: bool = True
    speaker_labels: bool = False


class TranscriptionProvenanceV1(StudioContract):
    """Runtime/model evidence required for an automatic transcript result."""

    schema_version: Literal["studio.transcription-provenance.v1"] = "studio.transcription-provenance.v1"
    source_revision: str = Field(min_length=7, max_length=160)
    model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_image_digest: str = Field(pattern=r"^sha256:[0-9a-fA-F]{64}$")


class TranscriptionResultV1(StudioContract):
    """Auditable transcript payload returned by a future transcription adapter."""

    schema_version: Literal["studio.transcription-result.v1"] = "studio.transcription-result.v1"
    media_ingest_id: str = Field(min_length=1, max_length=120)
    source_asset_id: str = Field(min_length=1, max_length=120)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    locale: str = Field(min_length=2, max_length=32)
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=160)
    segments: list[TranscriptSegmentV1] = Field(default_factory=list, max_length=100_000)
    provenance: TranscriptionProvenanceV1
    metrics: dict[str, float] = Field(default_factory=dict, max_length=100)


class TranscriptionJobResultV1(StudioContract):
    """Persisted binding from an ASR job to its versioned transcript."""

    schema_version: Literal["studio.transcription-job-result.v1"] = "studio.transcription-job-result.v1"
    generation_job_id: str = Field(min_length=1, max_length=120)
    workspace_id: str = Field(min_length=1, max_length=120)
    transcript_id: str = Field(min_length=1, max_length=120)
    media_ingest_id: str = Field(min_length=1, max_length=120)
    asset_id: str = Field(min_length=1, max_length=120)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    locale: str = Field(min_length=2, max_length=32)
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=160)
    transcript_revision: int = Field(ge=1)
    transcript_version: int = Field(ge=1)
    segment_count: int = Field(ge=0, le=100_000)
    transcription: TranscriptionResultV1


class SpeechProvenanceV1(StudioContract):
    schema_version: Literal["studio.speech-provenance.v1"] = "studio.speech-provenance.v1"
    source_revision: str = Field(min_length=7, max_length=160)
    model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_manifest_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    worker_image_digest: str = Field(pattern=r"^sha256:[0-9a-fA-F]{64}$")
    synthetic_content_disclosed: Literal[True] = True
    provenance_mode: str = Field(min_length=1, max_length=160)
    voice_version_id: str | None = Field(default=None, min_length=1, max_length=120)
    consent_grant_id: str | None = Field(default=None, min_length=1, max_length=120)
    voice_reference_checksum_sha256: str | None = Field(
        default=None,
        pattern=SHA256_PATTERN,
    )


class SpeechSynthesisResultV1(StudioContract):
    """Auditable result returned by a speech provider adapter."""

    schema_version: Literal["studio.speech-synthesis-result.v1"] = "studio.speech-synthesis-result.v1"
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=160)
    audio_format: Literal["wav", "flac", "mp3"]
    sample_rate: int = Field(ge=8_000, le=192_000)
    duration_ms: int = Field(ge=1, le=86_400_000)
    artifact_checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    provenance: SpeechProvenanceV1
    metrics: dict[str, float] = Field(default_factory=dict, max_length=100)


class SpeechSynthesisJobResultV1(StudioContract):
    schema_version: Literal["studio.speech-synthesis-job-result.v1"] = "studio.speech-synthesis-job-result.v1"
    generation_job_id: str
    job_type: Literal["stock_voice", "voice_clone"]
    asset_id: str
    storage_backend: str = Field(min_length=1, max_length=32)
    media_type: Literal["audio/wav", "audio/flac", "audio/mpeg"]
    size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    voice_reference: VoiceCloneReferenceV1 | None = None
    speech: SpeechSynthesisResultV1

    @model_validator(mode="after")
    def validate_output_binding(self) -> SpeechSynthesisJobResultV1:
        if self.speech.artifact_checksum_sha256.lower() != self.checksum_sha256.lower():
            raise ValueError("Speech provider checksum does not match stored artifact")
        if self.job_type == "voice_clone":
            if self.voice_reference is None:
                raise ValueError("Voice clone results require a reference binding")
            provenance = self.speech.provenance
            if (
                provenance.voice_version_id != self.voice_reference.voice_version_id
                or provenance.consent_grant_id != self.voice_reference.consent_grant_id
                or provenance.voice_reference_checksum_sha256 is None
                or provenance.voice_reference_checksum_sha256.lower()
                != self.voice_reference.normalized_checksum_sha256.lower()
            ):
                raise ValueError("Voice clone provenance does not match its reference")
        elif self.voice_reference is not None:
            raise ValueError("Stock speech results cannot carry a clone reference")
        return self


class AvatarVideoRequestV1(StudioContract):
    schema_version: Literal["studio.avatar-video-request.v1"] = "studio.avatar-video-request.v1"
    script: str = Field(min_length=1, max_length=20_000)
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    width: int = Field(default=1080, ge=128, le=4096)
    height: int = Field(default=1920, ge=128, le=4096)
    fps: int = Field(default=30, ge=12, le=60)
    disclosure_label: str = Field(default="Conteúdo sintético", min_length=1, max_length=240)


AvatarDrivingAudioOrigin = Literal[
    "uploaded_final_speech",
    "stock_voice_synthesis",
    "cloned_voice_synthesis",
    "recorded_final_speech",
]


class AvatarVideoRequestV2(StudioContract):
    """Identity-bound image + final-audio request for generative avatars.

    Unlike V1, this contract never infers the driving audio from voice enrollment
    samples.  Both media inputs are immutable catalog assets and are revalidated
    at admission and execution time.
    """

    schema_version: Literal["studio.avatar-video-request.v2"] = "studio.avatar-video-request.v2"
    expected_document_revision: int = Field(ge=1)
    scene_id: str = Field(min_length=1, max_length=120)
    requirement_id: str = Field(min_length=1, max_length=120)
    operation: Literal["image_audio_to_avatar"] = "image_audio_to_avatar"
    script: str = Field(min_length=1, max_length=20_000)
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    reference_image_asset_id: str = Field(min_length=1, max_length=120)
    reference_image_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    driving_audio_asset_id: str = Field(min_length=1, max_length=120)
    driving_audio_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    driving_audio_duration_ms: int = Field(gt=0, le=86_400_000)
    driving_audio_origin: AvatarDrivingAudioOrigin
    performance_direction: str = Field(min_length=1, max_length=2000)
    framing: Literal["close_up", "medium", "full_body"] = "medium"
    preserve: list[str] = Field(default_factory=list, max_length=40)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=40)
    profile_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,159}$")
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    width: int = Field(default=832, ge=128, le=4096)
    height: int = Field(default=480, ge=128, le=4096)
    fps: int = Field(default=25, ge=12, le=60)
    effective_parameters: dict[str, Any] = Field(default_factory=dict, max_length=80)
    disclosure_label: str = Field(default="Conteúdo sintético", min_length=1, max_length=240)


AvatarVideoRequest = AvatarVideoRequestV1 | AvatarVideoRequestV2


class AvatarVideoEncodeResultV1(StudioContract):
    schema_version: Literal["studio.avatar-video-encode-result.v1"] = "studio.avatar-video-encode-result.v1"
    provider: str = Field(min_length=1, max_length=160)
    provider_version: str = Field(min_length=1, max_length=160)
    width: int = Field(ge=128, le=4096)
    height: int = Field(ge=128, le=4096)
    fps: int = Field(ge=12, le=60)
    duration_ms: int = Field(gt=0, le=86_400_000)
    artifact_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    synthetic_content_disclosed: Literal[True] = True
    metrics: dict[str, float] = Field(default_factory=dict, max_length=100)


class AvatarVideoJobResultV1(StudioContract):
    schema_version: Literal["studio.avatar-video-job-result.v1"] = "studio.avatar-video-job-result.v1"
    generation_job_id: str
    asset_id: str
    storage_backend: str = Field(min_length=1, max_length=32)
    media_type: Literal["video/mp4"] = "video/mp4"
    size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    document_id: str
    identity_version_id: str
    voice_version_id: str
    consent_grant_id: str
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    avatar: AvatarVideoEncodeResultV1

    @model_validator(mode="after")
    def validate_avatar_output_binding(self) -> AvatarVideoJobResultV1:
        if self.avatar.artifact_checksum_sha256.lower() != self.checksum_sha256.lower():
            raise ValueError("Avatar provider checksum does not match stored artifact")
        return self


class AvatarVideoJobResultV2(StudioContract):
    schema_version: Literal["studio.avatar-video-job-result.v2"] = "studio.avatar-video-job-result.v2"
    generation_job_id: str
    asset_id: str
    storage_backend: str = Field(min_length=1, max_length=32)
    media_type: Literal["video/mp4"] = "video/mp4"
    size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    document_id: str
    document_revision: int = Field(ge=1)
    scene_id: str
    requirement_id: str
    identity_version_id: str
    voice_version_id: str
    consent_grant_id: str
    reference_image_asset_id: str
    reference_image_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    driving_audio_asset_id: str
    driving_audio_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    driving_audio_origin: AvatarDrivingAudioOrigin
    profile_id: str
    execution_binding_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    script_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    avatar: AvatarVideoEncodeResultV1

    @model_validator(mode="after")
    def validate_avatar_output_binding(self) -> AvatarVideoJobResultV2:
        if self.avatar.artifact_checksum_sha256.lower() != self.checksum_sha256.lower():
            raise ValueError("Avatar provider checksum does not match stored artifact")
        return self


class CreateTranscriptRequest(StudioContract):
    workspace_id: str
    media_ingest_id: str
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    status: Literal["draft", "ready", "reviewed"] = "draft"
    segments: list[TranscriptSegmentV1] = Field(default_factory=list, max_length=100_000)


class ReplaceTranscriptRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    transcript: TranscriptDocumentV1


class EditDecisionV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    operation: Literal["keep", "remove", "marker"]
    start_microseconds: int = Field(ge=0, le=86_400_000_000)
    end_microseconds: int = Field(gt=0, le=86_400_000_000)
    status: Literal["suggested", "accepted", "rejected"] = "suggested"
    reason: str = Field(default="", max_length=2000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str = Field(default="manual", min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_decision_range(self) -> EditDecisionV1:
        if self.end_microseconds <= self.start_microseconds:
            raise ValueError("Edit decision end must be after start")
        return self


class EditDecisionSetV1(StudioContract):
    schema_version: Literal["studio.edit-decision-set.v1"] = "studio.edit-decision-set.v1"
    id: str
    workspace_id: str
    media_ingest_id: str
    transcript_id: str | None = None
    document_id: str | None = None
    status: Literal["draft", "applied", "archived"] = "draft"
    revision: int = Field(default=1, ge=1)
    version: int = Field(default=1, ge=1)
    decisions: list[EditDecisionV1] = Field(default_factory=list, max_length=100_000)
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_decision_ids(self) -> EditDecisionSetV1:
        ids = [decision.id for decision in self.decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("Edit decision ids must be unique")
        return self


class CreateEditDecisionSetRequest(StudioContract):
    workspace_id: str
    media_ingest_id: str
    transcript_id: str | None = None
    document_id: str | None = None
    decisions: list[EditDecisionV1] = Field(default_factory=list, max_length=100_000)

    @model_validator(mode="after")
    def validate_decision_ids(self) -> CreateEditDecisionSetRequest:
        ids = [decision.id for decision in self.decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("Edit decision ids must be unique")
        return self


class ReplaceEditDecisionSetRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    decision_set: EditDecisionSetV1


class CaptionRenderStyleV1(StudioContract):
    font_asset_id: str | None = Field(default=None, max_length=120)
    schema_version: Literal["studio.caption-render-style.v1"] = "studio.caption-render-style.v1"
    preset: Literal["brand-bold"] | None = None
    position: Literal["lower-third"] = "lower-third"
    color: str = Field(default="#ffffff", pattern=r"^#[0-9a-fA-F]{6}$")
    font_size: int = Field(default=56, ge=16, le=240)
    font_family: Literal["Liberation Sans"] = "Liberation Sans"
    font_weight: Literal["bold"] = "bold"
    outline_color: str = Field(default="#000000", pattern=r"^#[0-9a-fA-F]{6}$")
    outline_width: int = Field(default=4, ge=0, le=24)
    max_lines: int = Field(default=3, ge=1, le=5)
    emphasis_color: str | None = Field(
        default=None,
        pattern=r"^#[0-9a-fA-F]{6}$",
    )


class ApplyTranscriptCaptionsRequest(StudioContract):
    document_id: str
    expected_document_revision: int = Field(ge=1)
    track_id: str = Field(default="captions-main", min_length=1, max_length=120)
    track_name: str = Field(default="Captions", min_length=1, max_length=240)
    style: CaptionRenderStyleV1 = Field(default_factory=CaptionRenderStyleV1)


class ApplyEditDecisionSetRequest(StudioContract):
    document_id: str
    expected_document_revision: int = Field(ge=1)
    expected_decision_revision: int = Field(ge=1)
    source_track_id: str = Field(default="video-main", min_length=1, max_length=120)


class TimelineFrameRangeV1(StudioContract):
    start_frame: int = Field(default=0, ge=0, le=2_073_600_000)
    duration_frames: int = Field(ge=1, le=2_073_600_000)


class SourceTimeRangeV1(StudioContract):
    start_microseconds: int = Field(default=0, ge=0, le=86_400_000_000)
    duration_microseconds: int = Field(ge=1, le=86_400_000_000)


class MediaClipV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    asset_id: str = Field(min_length=1, max_length=120)
    timeline: TimelineFrameRangeV1
    source: SourceTimeRangeV1 | None = None
    enabled: bool = True
    locked: bool = False
    label: str = Field(default="", max_length=240)
    playback_rate: float = Field(default=1, ge=0.5, le=2)
    transform: dict[str, Any] = Field(default_factory=dict)
    effects: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    keyframes: list[dict[str, Any]] = Field(default_factory=list, max_length=10_000)


class VideoTrackV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    kind: Literal["video"] = "video"
    name: str = Field(default="Video", min_length=1, max_length=240)
    muted: bool = False
    locked: bool = False
    clips: list[MediaClipV1] = Field(default_factory=list, max_length=10_000)


class AudioClipV1(MediaClipV1):
    gain_db: float = Field(default=0, ge=-96, le=24)
    pan: float = Field(default=0, ge=-1, le=1)
    fade_in_frames: int = Field(default=0, ge=0, le=2_073_600_000)
    fade_out_frames: int = Field(default=0, ge=0, le=2_073_600_000)


class AudioTrackV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    kind: Literal["audio"] = "audio"
    name: str = Field(default="Audio", min_length=1, max_length=240)
    muted: bool = False
    locked: bool = False
    clips: list[AudioClipV1] = Field(default_factory=list, max_length=10_000)


class CaptionCueV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    timeline: TimelineFrameRangeV1
    text: str = Field(min_length=1, max_length=4000)
    speaker: str | None = Field(default=None, max_length=240)
    source_segment_id: str | None = Field(default=None, max_length=120)
    confidence: float | None = Field(default=None, ge=0, le=1)
    style: CaptionRenderStyleV1 = Field(default_factory=CaptionRenderStyleV1)


class CaptionTrackV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    kind: Literal["caption"] = "caption"
    name: str = Field(default="Captions", min_length=1, max_length=240)
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    locked: bool = False
    cues: list[CaptionCueV1] = Field(default_factory=list, max_length=50_000)


class OverlayTrackV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    kind: Literal["overlay"] = "overlay"
    name: str = Field(default="Overlays", min_length=1, max_length=240)
    locked: bool = False
    clips: list[MediaClipV1] = Field(default_factory=list, max_length=10_000)


class MaskTrackV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    kind: Literal["mask"] = "mask"
    name: str = Field(default="Masks", min_length=1, max_length=240)
    target_track_id: str = Field(min_length=1, max_length=120)
    artifact_asset_id: str = Field(min_length=1, max_length=120)
    locked: bool = False


class MarkerV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    frame: int = Field(ge=0, le=2_073_600_000)
    label: str = Field(min_length=1, max_length=500)
    marker_type: str = Field(default="note", min_length=1, max_length=80)


class MarkerTrackV1(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    kind: Literal["marker"] = "marker"
    name: str = Field(default="Markers", min_length=1, max_length=240)
    markers: list[MarkerV1] = Field(default_factory=list, max_length=50_000)


TypedMediaTrackV1 = VideoTrackV1 | AudioTrackV1 | CaptionTrackV1 | OverlayTrackV1 | MaskTrackV1 | MarkerTrackV1


class MediaTimelineV1(StudioContract):
    schema_version: Literal["studio.media-timeline.v1"] = "studio.media-timeline.v1"
    frame_rate: FrameRateV1 = Field(default_factory=FrameRateV1)
    duration_frames: int = Field(ge=1, le=2_073_600_000)
    tracks: list[TypedMediaTrackV1] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_timeline(self) -> MediaTimelineV1:
        track_ids = [track.id for track in self.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("Media timeline track ids must be unique")
        known_tracks = set(track_ids)
        for track in self.tracks:
            if isinstance(track, MaskTrackV1) and track.target_track_id not in known_tracks:
                raise ValueError("Mask track target must exist in the same timeline")
            clips = getattr(track, "clips", [])
            for clip in clips:
                if clip.timeline.start_frame + clip.timeline.duration_frames > self.duration_frames:
                    raise ValueError("Media clip exceeds timeline duration")
        return self


class CreativeCompositionV1(StudioContract):
    pages: list[CreativePageV1] = Field(min_length=1, max_length=100)
    narrative: dict[str, Any] = Field(default_factory=dict)
    tracks: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    media_timeline: MediaTimelineV1 | None = None


class ProviderLineageV1(StudioContract):
    provider: str = Field(min_length=1, max_length=120)
    model: str | None = Field(default=None, max_length=240)
    provider_version: str | None = Field(default=None, max_length=120)
    parameters: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    job_id: str | None = Field(default=None, max_length=120)


class ReviewReferenceV1(StudioContract):
    status: Literal["draft", "requested", "approved", "changes_requested", "rejected"] = "draft"
    requested_version: int | None = Field(default=None, ge=1)
    approval_id: str | None = Field(default=None, max_length=120)


class ExportReferenceV1(StudioContract):
    asset_id: str = Field(min_length=1, max_length=120)
    document_version: int = Field(ge=1)
    target: str = Field(default="download", max_length=120)
    format: str = Field(max_length=80)
    created_at: datetime


class CreativeDocumentV1(StudioContract):
    schema_version: Literal["studio.creative-document.v1"] = "studio.creative-document.v1"
    document_id: str = Field(min_length=1, max_length=120)
    workspace_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    content_type: Literal["visual", "carousel", "video", "presenter"] = "visual"
    status: Literal["draft", "in_review", "approved", "archived"] = "draft"
    revision: int = Field(default=1, ge=1)
    version: int = Field(default=1, ge=1)
    actor_id: str | None = Field(default=None, max_length=120)
    correlation_id: str = Field(min_length=1, max_length=128)
    campaign_ref: EntityReferenceV1 | None = None
    post_ref: EntityReferenceV1 | None = None
    opportunity_ref: OpportunityEvidenceReferenceV1 | None = None
    brand_memory_ref: BrandMemoryReferenceV1
    brief: CreativeBriefV1
    composition: CreativeCompositionV1
    # Versioned canonical content is authored by contextual plan V2 and kept
    # with the document so derived layouts do not rely on renderer-only IDs.
    # The V2 plan owns the typed validation; V1 readers preserve this additive payload.
    content_references: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    assets: list[AssetReferenceV1] = Field(default_factory=list, max_length=1000)
    identity_ref: IdentityVersionReferenceV1 | None = None
    voice_ref: VoiceVersionReferenceV1 | None = None
    scene_ref: EntityReferenceV1 | None = None
    script_ref: EntityReferenceV1 | None = None
    shot_plan_ref: EntityReferenceV1 | None = None
    lineage: list[ProviderLineageV1] = Field(default_factory=list, max_length=1000)
    review: ReviewReferenceV1 = Field(default_factory=ReviewReferenceV1)
    exports: list[ExportReferenceV1] = Field(default_factory=list, max_length=1000)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def carousel_requires_pages(self) -> CreativeDocumentV1:
        if self.content_type == "carousel" and len(self.composition.pages) < 2:
            raise ValueError("Carousel documents require at least two pages")
        return self


class VideoRenderSpecV1(StudioContract):
    schema_version: Literal["studio.video-render-spec.v1"] = "studio.video-render-spec.v1"
    format: Literal["mp4", "webm"] = "mp4"
    width: int = Field(ge=320, le=8192)
    height: int = Field(ge=320, le=8192)
    fps: float = Field(default=30, gt=0, le=240)
    video_codec: Literal["h264", "vp9", "av1"] = "h264"
    audio_codec: Literal["aac", "opus", "none"] = "aac"
    quality: Literal["draft", "standard", "high"] = "standard"


class VideoRenderEncodeResultV1(StudioContract):
    renderer_checks: dict[str, Any] = Field(default_factory=dict)
    schema_version: Literal["studio.video-render-encode-result.v1"] = "studio.video-render-encode-result.v1"
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=240)
    width: int = Field(ge=320, le=8192)
    height: int = Field(ge=320, le=8192)
    duration_ms: int = Field(gt=0, le=86_400_000)
    fps: float = Field(gt=0, le=240)
    video_codec: str = Field(min_length=1, max_length=80)
    audio_codec: str | None = Field(default=None, max_length=80)
    render_duration_ms: int = Field(ge=0)
    frames_rendered: int = Field(gt=0)
    peak_rss_mb: float | None = Field(default=None, ge=0)
    rendered_layer_ids: list[str] = Field(default_factory=list, max_length=1000)
    rendered_caption_track_ids: list[str] = Field(default_factory=list, max_length=100)
    rendered_audio_clip_ids: list[str] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=100)


class VideoRenderRequestV1(StudioContract):
    schema_version: Literal["studio.video-render-request.v1"] = "studio.video-render-request.v1"
    workspace_id: str = Field(min_length=1, max_length=120)
    document_id: str = Field(min_length=1, max_length=120)
    document_revision: int = Field(ge=1)
    document_version: int = Field(ge=1)
    page_ids: list[str] = Field(min_length=1, max_length=100)
    asset_ids: list[str] = Field(default_factory=list, max_length=1000)
    output: VideoRenderSpecV1
    correlation_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def references_are_unique(self) -> VideoRenderRequestV1:
        if len(self.page_ids) != len(set(self.page_ids)):
            raise ValueError("pageIds must be unique")
        if len(self.asset_ids) != len(set(self.asset_ids)):
            raise ValueError("assetIds must be unique")
        return self


class CreateVideoRenderJobRequest(StudioContract):
    workspace_id: str
    document_id: str
    expected_document_revision: int = Field(ge=1)
    expected_document_version: int = Field(ge=1)
    page_ids: list[str] = Field(default_factory=list, max_length=100)
    output: VideoRenderSpecV1
    provider: Literal[
        "builtin.ffmpeg-ugc-v1", "hyperframes.cli", "builtin.ffmpeg-contextual-v1", "hyperframes.contextual-v2",
        "motion-canvas.contextual-v1", "remotion.contextual-v1", "remotion.contextual-v2",
    ] = "builtin.ffmpeg-ugc-v1"
    contextual_plan_id: str | None = Field(default=None, max_length=120)
    motion_graph_id: str | None = Field(default=None, max_length=120)
    motion_graph_digest_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    reduced_motion: bool = False
    correlation_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_motion_graph_binding(self) -> CreateVideoRenderJobRequest:
        if (self.provider in {"builtin.ffmpeg-contextual-v1", "hyperframes.contextual-v2", "motion-canvas.contextual-v1", "remotion.contextual-v1", "remotion.contextual-v2"}) != bool(
            self.contextual_plan_id
        ):
            raise ValueError("Contextual renders require a bound contextual plan")
        if bool(self.motion_graph_id) != bool(self.motion_graph_digest_sha256):
            raise ValueError("Motion graph id and digest must be supplied together")
        if self.motion_graph_id and self.provider != "hyperframes.cli":
            raise ValueError("Motion graph renders require the HyperFrames provider")
        if self.reduced_motion and not self.motion_graph_id:
            raise ValueError("Reduced motion renders require a bound motion graph")
        return self


class RenderedVideoArtifactV1(StudioContract):
    schema_version: Literal["studio.rendered-video-artifact.v1"] = "studio.rendered-video-artifact.v1"
    asset_id: str = Field(min_length=1, max_length=120)
    storage_uri: str = Field(min_length=1, max_length=4000)
    media_type: Literal["video/mp4", "video/webm"]
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    size_bytes: int = Field(gt=0)
    width: int = Field(ge=320, le=8192)
    height: int = Field(ge=320, le=8192)
    duration_ms: int = Field(gt=0, le=86_400_000)
    fps: float = Field(gt=0, le=240)
    video_codec: str = Field(min_length=1, max_length=80)
    audio_codec: str | None = Field(default=None, max_length=80)


class VideoTechnicalQualityPolicyV1(StudioContract):
    """Frozen thresholds for the first reviewable UGC technical gate."""

    schema_version: Literal["studio.video-technical-quality-policy.v1"] = "studio.video-technical-quality-policy.v1"
    policy_id: Literal["ugc-review-v1"] = "ugc-review-v1"
    max_duration_delta_ms: int = Field(default=80, ge=0, le=10_000)
    max_av_start_delta_ms: int = Field(default=80, ge=0, le=10_000)
    max_av_duration_delta_ms: int = Field(default=80, ge=0, le=10_000)
    max_black_frame_ratio: float = Field(default=0.05, ge=0, le=1)
    min_integrated_loudness_lufs: float = Field(default=-30, ge=-70, le=0)
    max_integrated_loudness_lufs: float = Field(default=-10, ge=-70, le=0)
    max_true_peak_dbfs: float = Field(default=-1, ge=-70, le=0)
    max_silence_ratio: float = Field(default=0.20, ge=0, le=1)
    black_min_duration_ms: int = Field(default=100, ge=50, le=10_000)
    silence_min_duration_ms: int = Field(default=250, ge=50, le=10_000)

    @model_validator(mode="after")
    def validate_loudness_window(self) -> VideoTechnicalQualityPolicyV1:
        if self.min_integrated_loudness_lufs >= self.max_integrated_loudness_lufs:
            raise ValueError("Minimum loudness must be lower than maximum loudness")
        return self


class VideoTechnicalQualityCheckV1(StudioContract):
    schema_version: Literal["studio.video-technical-quality-check.v1"] = "studio.video-technical-quality-check.v1"
    id: Literal[
        "video_stream_count",
        "audio_stream_count",
        "video_codec",
        "audio_codec",
        "dimensions",
        "frame_rate",
        "duration_delta",
        "av_start_delta",
        "av_duration_delta",
        "black_frame_ratio",
        "integrated_loudness",
        "true_peak",
        "silence_ratio",
    ]
    severity: Literal["blocker", "warning"]
    status: Literal["passed", "failed", "warning"]
    actual: float | str
    minimum: float | None = None
    maximum: float | None = None
    expected: str | None = Field(default=None, max_length=120)
    unit: str | None = Field(default=None, max_length=40)
    message: str = Field(min_length=1, max_length=500)


class VideoTechnicalQualityMetricsV1(StudioContract):
    schema_version: Literal["studio.video-technical-quality-metrics.v1"] = "studio.video-technical-quality-metrics.v1"
    video_duration_ms: float = Field(ge=0)
    audio_duration_ms: float = Field(ge=0)
    duration_delta_ms: float = Field(ge=0)
    av_start_delta_ms: float = Field(ge=0)
    av_duration_delta_ms: float = Field(ge=0)
    black_duration_ms: float = Field(ge=0)
    black_frame_ratio: float = Field(ge=0, le=1)
    integrated_loudness_lufs: float = Field(ge=-120, le=20)
    true_peak_dbfs: float = Field(ge=-120, le=20)
    silence_duration_ms: float = Field(ge=0)
    silence_ratio: float = Field(ge=0, le=1)


class VideoTechnicalQualityEvaluationV1(StudioContract):
    schema_version: Literal["studio.video-technical-quality-evaluation.v1"] = (
        "studio.video-technical-quality-evaluation.v1"
    )
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=240)
    policy: VideoTechnicalQualityPolicyV1
    status: Literal["passed", "failed"]
    metrics: VideoTechnicalQualityMetricsV1
    checks: list[VideoTechnicalQualityCheckV1] = Field(min_length=1, max_length=100)
    evaluated_at: datetime

    @model_validator(mode="after")
    def status_matches_blockers(self) -> VideoTechnicalQualityEvaluationV1:
        expected = (
            "failed"
            if any(check.severity == "blocker" and check.status == "failed" for check in self.checks)
            else "passed"
        )
        if self.status != expected:
            raise ValueError("Quality status must match blocker checks")
        return self


class WorkerToolRequirementV1(StudioContract):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,39}$")
    command: list[str] = Field(min_length=1, max_length=8)
    version_pattern: str = Field(min_length=1, max_length=240)


class WorkerIsolationPolicyV1(StudioContract):
    run_as_non_root: bool = True
    read_only_root_filesystem: bool = True
    allow_privilege_escalation: bool = False
    network_egress_policy: Literal["deny-all", "private-dependencies-only"] = "private-dependencies-only"
    max_concurrent_jobs: int = Field(default=1, ge=1, le=64)
    ephemeral_temp_path: str = Field(min_length=1, max_length=500)
    minimum_temp_bytes: int = Field(ge=64 * 1024 * 1024)


class WorkerAcceleratorRequirementV1(StudioContract):
    vendor: Literal["nvidia"]
    runtime: Literal["cuda"]
    minimum_devices: int = Field(default=1, ge=1, le=16)
    minimum_memory_mib: int = Field(ge=1024, le=1024 * 1024)
    minimum_compute_capability: float = Field(ge=1, le=20)
    driver_version_pattern: str = Field(min_length=1, max_length=240)
    inventory_command: list[str] = Field(min_length=1, max_length=8)


class StudioWorkerRuntimeManifestV1(StudioContract):
    schema_version: Literal["studio.worker-runtime-manifest.v1"] = "studio.worker-runtime-manifest.v1"
    runtime_name: str = Field(pattern=r"^[a-z][a-z0-9-]{2,79}$")
    runtime_version: str = Field(min_length=1, max_length=80)
    capability: Literal["media_cpu", "speech_cpu", "speech_gpu", "vision_gpu", "llm_gpu"]
    queues: list[str] = Field(min_length=1, max_length=20)
    resource_classes: list[str] = Field(min_length=1, max_length=20)
    job_types: list[str] = Field(min_length=1, max_length=40)
    providers: list[str] = Field(default_factory=list, max_length=100)
    required_environment: list[str] = Field(default_factory=list, max_length=100)
    required_paths: list[str] = Field(default_factory=list, max_length=100)
    tools: list[WorkerToolRequirementV1] = Field(min_length=1, max_length=40)
    accelerator: WorkerAcceleratorRequirementV1 | None = None
    isolation: WorkerIsolationPolicyV1

    @model_validator(mode="after")
    def collections_are_unique(self) -> StudioWorkerRuntimeManifestV1:
        for name in (
            "queues",
            "resource_classes",
            "job_types",
            "providers",
            "required_environment",
            "required_paths",
        ):
            values = getattr(self, name)
            if len(values) != len(set(values)):
                raise ValueError(f"Worker manifest {name} must be unique")
        tool_ids = [tool.id for tool in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ValueError("Worker manifest tool ids must be unique")
        gpu_capabilities = {"speech_gpu", "vision_gpu", "llm_gpu"}
        if self.capability in gpu_capabilities and self.accelerator is None:
            raise ValueError("GPU worker manifests require accelerator attestation")
        if self.capability not in gpu_capabilities and self.accelerator is not None:
            raise ValueError("CPU worker manifests cannot claim an accelerator")
        return self


class WorkerExecutionContextV1(StudioContract):
    schema_version: Literal["studio.worker-execution-context.v1"] = "studio.worker-execution-context.v1"
    mode: Literal["embedded", "isolated"]
    attested: bool
    job_type: str = Field(min_length=1, max_length=80)
    capability: Literal[
        "control",
        "media_cpu",
        "speech_cpu",
        "speech_gpu",
        "vision_gpu",
        "llm_gpu",
    ]
    queue_name: str = Field(min_length=1, max_length=80)
    runtime_name: str | None = Field(default=None, max_length=80)
    runtime_version: str | None = Field(default=None, max_length=80)
    manifest_digest_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    image_digest: str | None = Field(default=None, pattern=r"^sha256:[a-f0-9]{64}$")
    worker_instance_id: str | None = Field(default=None, max_length=160)
    hostname: str | None = Field(default=None, max_length=255)
    process_id: int | None = Field(default=None, ge=1)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    verified_at: datetime

    @model_validator(mode="after")
    def attestation_matches_mode(self) -> WorkerExecutionContextV1:
        required = (
            self.runtime_name,
            self.runtime_version,
            self.manifest_digest_sha256,
            self.worker_instance_id,
            self.hostname,
            self.process_id,
        )
        if self.mode == "isolated" and (not self.attested or not all(required)):
            raise ValueError("Isolated worker execution must be fully attested")
        if self.mode == "embedded" and self.attested:
            raise ValueError("Embedded execution cannot claim worker attestation")
        return self


class VideoRenderResultV1(StudioContract):
    schema_version: Literal["studio.video-render-result.v1"] = "studio.video-render-result.v1"
    job_id: str = Field(min_length=1, max_length=120)
    workspace_id: str = Field(min_length=1, max_length=120)
    document_id: str = Field(min_length=1, max_length=120)
    document_revision: int = Field(ge=1)
    document_version: int = Field(ge=1)
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=120)
    artifact: RenderedVideoArtifactV1
    render_duration_ms: int = Field(ge=0)
    frames_rendered: int = Field(gt=0)
    peak_rss_mb: float | None = Field(default=None, ge=0)
    rendered_layer_ids: list[str] = Field(default_factory=list, max_length=100)
    rendered_caption_track_ids: list[str] = Field(default_factory=list, max_length=100)
    quality_evaluation: VideoTechnicalQualityEvaluationV1 | None = None
    worker_execution_context: WorkerExecutionContextV1 | None = None
    warnings: list[str] = Field(default_factory=list, max_length=100)
    completed_at: datetime


class StudioDocumentVersionV1(StudioContract):
    schema_version: Literal["studio.document-version.v1"] = "studio.document-version.v1"
    document_id: str = Field(min_length=1, max_length=120)
    workspace_id: str = Field(min_length=1, max_length=120)
    number: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=240)
    created_at: datetime
    actor_id: str | None = Field(default=None, max_length=120)
    snapshot: CreativeDocumentV1


JobStatus = Literal[
    "queued",
    "running",
    "retrying",
    "cancel_requested",
    "cancelled",
    "succeeded",
    "failed",
]


class GenerationJobV1(StudioContract):
    schema_version: Literal["studio.generation-job.v1"] = "studio.generation-job.v1"
    id: str
    workspace_id: str
    requested_by: str | None = None
    document_id: str | None = None
    consent_grant_id: str | None = None
    identity_version_id: str | None = None
    voice_version_id: str | None = None
    job_type: str
    provider: str
    execution_capability: Literal[
        "control",
        "media_cpu",
        "speech_cpu",
        "speech_gpu",
        "vision_gpu",
        "llm_gpu",
    ]
    queue_name: str
    resource_class: str
    hard_time_limit_seconds: int = Field(ge=60, le=86_400)
    idempotency_key: str
    payload_hash: str
    correlation_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    attempts: int = Field(ge=0)
    max_attempts: int = Field(ge=1, le=20)
    request: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    cancel_reason: str | None = None
    worker_execution_context: WorkerExecutionContextV1 | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CreateStudioDocumentRequest(StudioContract):
    workspace_id: str
    title: str = Field(min_length=1, max_length=240)
    content_type: Literal["visual", "carousel", "video", "presenter"] = "visual"
    campaign_id: str | None = None
    post_id: str | None = None
    opportunity_id: str | None = None
    brand_revision: int = Field(default=1, ge=1)
    brief: CreativeBriefV1
    composition: CreativeCompositionV1
    assets: list[AssetReferenceV1] = Field(default_factory=list)
    correlation_id: str | None = Field(default=None, max_length=128)


class ReplaceStudioDocumentRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    document: CreativeDocumentV1


class StudioAssetRightsReviewRequestV1(StudioContract):
    expected_document_revision: int = Field(ge=1)
    asset_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["verified", "restricted"]
    basis: Literal["open-license", "owned", "written-permission"]
    source_reference: str = Field(min_length=3, max_length=2000)
    rights_reference: str = Field(min_length=3, max_length=2000)
    expires_at: datetime | None = None
    no_expiration_confirmed: bool = False
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def verified_rights_need_a_validity_window(self) -> StudioAssetRightsReviewRequestV1:
        if self.decision == "verified" and bool(self.expires_at) == self.no_expiration_confirmed:
            raise ValueError("Verified rights require either an expiration or explicit no-expiration confirmation")
        return self


class StudioAssetRightsReviewRecordV1(StudioContract):
    schema_version: Literal["studio.asset-rights-review.v1"] = "studio.asset-rights-review.v1"
    review_id: str
    workspace_id: str
    document_id: str
    document_revision: int = Field(ge=1)
    asset_id: str
    asset_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    decision: Literal["verified", "restricted"]
    basis: Literal["open-license", "owned", "written-permission"]
    publication_scope: Literal["commercial-saas"] = "commercial-saas"
    source_declaration: str = Field(min_length=1, max_length=1000)
    license_declaration: str = Field(min_length=1, max_length=1000)
    source_reference: str = Field(min_length=3, max_length=2000)
    rights_reference: str = Field(min_length=3, max_length=2000)
    expires_at: datetime | None = None
    no_expiration_confirmed: bool = False
    notes: str | None = Field(default=None, max_length=2000)
    reviewer_id: str
    reviewed_at: datetime


class StudioAssetRightsReviewResponseV1(StudioContract):
    schema_version: Literal["studio.asset-rights-review-response.v1"] = "studio.asset-rights-review-response.v1"
    review: StudioAssetRightsReviewRecordV1
    document: CreativeDocumentV1


class RestoreStudioDocumentVersionRequest(StudioContract):
    expected_revision: int = Field(ge=1)
    label: str | None = Field(default=None, max_length=240)


class CreateGenerationJobRequest(StudioContract):
    workspace_id: str
    document_id: str | None = None
    consent_grant_id: str | None = None
    identity_version_id: str | None = None
    voice_version_id: str | None = None
    job_type: Literal[
        "document_snapshot",
        "editing_gemini",
        "editing_ai",
        "media_probe",
        "video_proxy",
        "media_waveform",
        "video_render",
        "acoustic_analysis",
        "stock_voice",
        "transcription",
        "voice_clone",
        "avatar_video",
        "scene_generation",
    ] = "document_snapshot"
    provider: str = Field(default="builtin.snapshot", min_length=1, max_length=240)
    request: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_job_provider(self) -> CreateGenerationJobRequest:
        expected = {
            "editing_gemini": {"google.gemini-editing"},
            "editing_ai": {
                "compatible.editing-planner",
                "local.smolvlm-material-inspection",
                "runway.editing-video",
                "openai.sora-2",
            },
            "document_snapshot": {"builtin.snapshot"},
            "media_probe": {"builtin.ffprobe"},
            "video_proxy": {"builtin.ffmpeg-proxy"},
            "media_waveform": {"builtin.ffmpeg-waveform"},
            "video_render": {
                "builtin.ffmpeg-ugc-v1",
                "hyperframes.cli",
                "builtin.ffmpeg-contextual-v1",
                "hyperframes.contextual-v2",
                "motion-canvas.contextual-v1",
                "remotion.contextual-v1",
                "remotion.contextual-v2",
            },
            "scene_generation": {
                "local.wan21-diffusers",
                "local.wan21-t2v-local-experimental-v1",
                "local.animatediff-lightning-sd15-a-v1",
                "local.animatediff-lightning-sd15-b-v1",
            },
        }
        if self.job_type in {
            "acoustic_analysis",
            "stock_voice",
            "transcription",
            "voice_clone",
            "avatar_video",
        }:
            return self
        if self.provider not in expected[self.job_type]:
            raise ValueError("Provider does not support requested job type")
        return self


class CancelGenerationJobRequest(StudioContract):
    reason: str = Field(default="Cancelled by user", min_length=1, max_length=500)


class CreateStudioReviewRequest(StudioContract):
    comment: str | None = Field(default=None, max_length=4000)
    render_job_id: str | None = Field(default=None, max_length=120)


class StudioListeningReviewSubmissionV1(StudioContract):
    """A human attestation, never a classifier result or a rights clearance."""

    render_asset_id: str = Field(min_length=1, max_length=120)
    render_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    listened_entire_mix: Literal[True]
    speech_absent: Literal["pass", "fail", "inconclusive"]
    music_absent: Literal["pass", "fail", "inconclusive"]
    natural_sounds_coherent: Literal["pass", "fail", "inconclusive"]
    mix_balanced: Literal["pass", "fail", "inconclusive"]

    def all_passed(self) -> bool:
        return all(
            value == "pass"
            for value in (
                self.speech_absent,
                self.music_absent,
                self.natural_sounds_coherent,
                self.mix_balanced,
            )
        )


class StudioListeningReviewRecordV1(StudioContract):
    schema_version: Literal["studio.listening-review.v1"] = "studio.listening-review.v1"
    assessment_id: str
    review_id: str
    document_id: str
    document_version: int = Field(ge=1)
    snapshot_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    reviewer_id: str
    reviewed_at: datetime
    result: Literal["pass", "needs_changes"]
    submission: StudioListeningReviewSubmissionV1
    publication_admitted: Literal[False] = False


class StudioAcousticAnalysisJobRequestV1(StudioContract):
    """Immutable input sent to a promoted speech/music absence detector."""

    schema_version: Literal["studio.acoustic-analysis-request.v1"] = "studio.acoustic-analysis-request.v1"
    review_id: str
    document_id: str
    document_version: int = Field(ge=1)
    snapshot_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    render_asset_id: str
    render_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    policy: Literal["no-speech-no-music-v1"] = "no-speech-no-music-v1"


class StudioAcousticDetectionCheckV1(StudioContract):
    kind: Literal["speech", "music"]
    status: Literal["pass", "fail", "inconclusive"]
    detected_duration_ms: int = Field(ge=0)
    maximum_score: float | None = Field(default=None, ge=0, le=1)
    decision_threshold: float | None = Field(default=None, ge=0, le=1)
    detail: str = Field(min_length=1, max_length=1000)


class StudioAcousticDetectorResultV1(StudioContract):
    """Provider output. Admission metadata is added only by the control plane."""

    schema_version: Literal["studio.acoustic-detector-result.v1"] = "studio.acoustic-detector-result.v1"
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=120)
    source_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    analyzed_duration_ms: int = Field(gt=0)
    checks: list[StudioAcousticDetectionCheckV1] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def requires_one_speech_and_music_check(self) -> StudioAcousticDetectorResultV1:
        kinds = [check.kind for check in self.checks]
        if sorted(kinds) != ["music", "speech"]:
            raise ValueError("Acoustic result requires one speech and one music check")
        return self

    def all_passed(self) -> bool:
        return all(check.status == "pass" for check in self.checks)


class StudioAcousticAnalysisRecordV1(StudioContract):
    schema_version: Literal["studio.acoustic-analysis.v1"] = "studio.acoustic-analysis.v1"
    analysis_id: str
    job_id: str
    review_id: str
    workspace_id: str
    document_id: str
    document_version: int = Field(ge=1)
    snapshot_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    render_asset_id: str
    render_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    provider_registration_id: str
    model_registration_id: str
    model_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    benchmark_digest_sha256: str = Field(pattern=SHA256_PATTERN)
    result: StudioAcousticDetectorResultV1
    status: Literal["pass", "fail", "inconclusive"]
    production_qualified: Literal[True] = True
    analyzed_at: datetime


class StudioAcousticAnalysisCapabilityV1(StudioContract):
    schema_version: Literal["studio.acoustic-analysis-capability.v1"] = "studio.acoustic-analysis-capability.v1"
    status: Literal["ready", "unavailable"]
    reason_code: str = Field(min_length=1, max_length=160)
    detail: str = Field(min_length=1, max_length=1000)
    provider: str | None = None
    provider_version: str | None = None
    model_name: str | None = None
    model_version: str | None = None


class StudioNaturalSoundAdmissionRecordV1(StudioContract):
    schema_version: Literal["studio.natural-sound-admission.v1"] = "studio.natural-sound-admission.v1"
    admission_id: str
    review_id: str
    document_id: str
    document_version: int = Field(ge=1)
    snapshot_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    render_asset_id: str
    render_checksum_sha256: str = Field(pattern=SHA256_PATTERN)
    acoustic_analysis_id: str
    listening_assessment_id: str
    rights_review_ids: list[str] = Field(min_length=1, max_length=100)
    admitted_at: datetime
    publication_admitted: Literal[True] = True


class StudioReviewDecisionRequest(StudioContract):
    action: Literal["approve", "request_changes", "reject"]
    comment: str | None = Field(default=None, max_length=4000)
    listening_review: StudioListeningReviewSubmissionV1 | None = None

    @model_validator(mode="after")
    def changes_require_comment(self) -> StudioReviewDecisionRequest:
        if self.action == "request_changes" and not (self.comment or "").strip():
            raise ValueError("Requesting changes requires a comment")
        return self


class StudioReviewRequestV1(StudioContract):
    schema_version: Literal["studio.review-request.v1"] = "studio.review-request.v1"
    id: str
    workspace_id: str
    document_id: str
    document_version: int = Field(ge=1)
    post_id: str | None = None
    status: Literal["requested", "approved", "changes_requested", "rejected"]
    snapshot: CreativeDocumentV1
    render_job_id: str | None = None
    render_asset_id: str | None = None
    render_checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    requested_by: str | None = None
    decided_by: str | None = None
    decision_comment: str | None = None
    requested_at: datetime
    decided_at: datetime | None = None
    listening_review: StudioListeningReviewRecordV1 | None = None
    acoustic_analysis: StudioAcousticAnalysisRecordV1 | None = None
    natural_sound_admission: StudioNaturalSoundAdmissionRecordV1 | None = None


class StudioPreflightCheckV1(StudioContract):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=240)
    status: Literal["passed", "warning", "failed"]
    detail: str = Field(min_length=1, max_length=1000)


class StudioPublicationPreflightV1(StudioContract):
    schema_version: Literal["studio.publication-preflight.v1"] = "studio.publication-preflight.v1"
    review_id: str
    document_id: str
    document_version: int = Field(ge=1)
    post_id: str
    title: str
    platform: str
    format: str
    caption: str
    hashtags: list[str] = Field(default_factory=list, max_length=100)
    content_type: Literal["visual", "carousel", "video", "presenter"]
    page_ids: list[str] = Field(default_factory=list, max_length=100)
    status: Literal["ready", "scheduled"]
    scheduled_at: datetime | None = None
    checks: list[StudioPreflightCheckV1] = Field(min_length=1, max_length=20)


class StudioInternalScheduleRequest(StudioContract):
    scheduled_at: datetime


class StudioInternalScheduleReceiptV1(StudioContract):
    schema_version: Literal["studio.internal-schedule-receipt.v1"] = "studio.internal-schedule-receipt.v1"
    receipt_id: str
    review_id: str
    document_id: str
    document_version: int = Field(ge=1)
    post_id: str
    scheduled_at: datetime
    external_publication_confirmed: Literal[False] = False


class StudioExportRequest(StudioContract):
    format: Literal["png", "png_set"] = "png"


ConsentScope = Literal[
    "identity.enroll",
    "avatar.generate",
    "voice.enroll",
    "voice.clone",
    "publish.synthetic",
]


class ConsentGrantV1(StudioContract):
    schema_version: Literal["studio.consent-grant.v1"] = "studio.consent-grant.v1"
    id: str = Field(min_length=1, max_length=120)
    workspace_id: str = Field(min_length=1, max_length=120)
    subject_key: str = Field(min_length=1, max_length=160)
    subject_display_name: str = Field(min_length=1, max_length=240)
    purpose: str = Field(min_length=1, max_length=2000)
    scopes: list[ConsentScope] = Field(min_length=1, max_length=20)
    brand_ids: list[str] = Field(default_factory=list, max_length=100)
    channels: list[str] = Field(default_factory=list, max_length=100)
    policy_version: str = Field(min_length=1, max_length=120)
    evidence_asset_id: str | None = Field(default=None, max_length=120)
    status: Literal["active", "revoked", "expired"] = "active"
    granted_by: str = Field(min_length=1, max_length=120)
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    revoked_by: str | None = Field(default=None, max_length=120)
    revocation_reason: str | None = Field(default=None, max_length=2000)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_consent_period(self) -> ConsentGrantV1:
        if self.expires_at <= self.granted_at:
            raise ValueError("Consent expiry must be after grant time")
        if self.status == "revoked" and not self.revoked_at:
            raise ValueError("Revoked consent requires revokedAt")
        if len(self.scopes) != len(set(self.scopes)):
            raise ValueError("Consent scopes must be unique")
        return self


class CreateConsentGrantRequest(StudioContract):
    workspace_id: str = Field(min_length=1, max_length=120)
    subject_key: str = Field(min_length=1, max_length=160)
    subject_display_name: str = Field(min_length=1, max_length=240)
    purpose: str = Field(min_length=1, max_length=2000)
    scopes: list[ConsentScope] = Field(min_length=1, max_length=20)
    brand_ids: list[str] = Field(default_factory=list, max_length=100)
    channels: list[str] = Field(default_factory=list, max_length=100)
    policy_version: str = Field(min_length=1, max_length=120)
    evidence_asset_id: str | None = Field(default=None, max_length=120)
    expires_at: datetime

    @model_validator(mode="after")
    def validate_unique_scopes(self) -> CreateConsentGrantRequest:
        if len(self.scopes) != len(set(self.scopes)):
            raise ValueError("Consent scopes must be unique")
        return self


class RevokeConsentGrantRequest(StudioContract):
    reason: str = Field(min_length=1, max_length=2000)


class IdentityProfileV1(StudioContract):
    schema_version: Literal["studio.identity-profile.v1"] = "studio.identity-profile.v1"
    id: str
    workspace_id: str
    subject_key: str
    display_name: str
    identity_type: Literal["natural_person", "synthetic_character"]
    status: Literal["draft", "active", "revoked", "deleting", "deleted"]
    owner_user_id: str | None = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class IdentityVersionV1(StudioContract):
    schema_version: Literal["studio.identity-version.v1"] = "studio.identity-version.v1"
    id: str
    workspace_id: str
    profile_id: str
    version: int = Field(ge=1)
    consent_grant_id: str | None = None
    status: Literal["draft", "active", "rejected", "superseded", "revoked", "deleting", "deleted"]
    capabilities: list[str] = Field(default_factory=list, max_length=100)
    sample_asset_ids: list[str] = Field(default_factory=list, max_length=1000)
    derived_artifacts: list[AssetReferenceV1] = Field(default_factory=list, max_length=1000)
    content_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    created_by: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateIdentityProfileRequest(StudioContract):
    workspace_id: str
    subject_key: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=240)
    identity_type: Literal["natural_person", "synthetic_character"] = "natural_person"
    owner_user_id: str | None = None


class CreateIdentityVersionRequest(StudioContract):
    consent_grant_id: str | None = None
    capabilities: list[str] = Field(default_factory=list, max_length=100)
    sample_asset_ids: list[str] = Field(default_factory=list, max_length=1000)
    derived_artifacts: list[AssetReferenceV1] = Field(default_factory=list, max_length=1000)


class VoiceProfileV1(StudioContract):
    schema_version: Literal["studio.voice-profile.v1"] = "studio.voice-profile.v1"
    id: str
    workspace_id: str
    identity_profile_id: str | None = None
    display_name: str
    locale: str
    voice_type: Literal["stock", "cloned"]
    status: Literal["draft", "active", "revoked", "deleting", "deleted"]
    created_by: str
    created_at: datetime
    updated_at: datetime


class VoiceVersionV1(StudioContract):
    schema_version: Literal["studio.voice-version.v1"] = "studio.voice-version.v1"
    id: str
    workspace_id: str
    profile_id: str
    version: int = Field(ge=1)
    consent_grant_id: str | None = None
    status: Literal["draft", "active", "rejected", "superseded", "revoked", "deleting", "deleted"]
    sample_asset_ids: list[str] = Field(default_factory=list, max_length=1000)
    derived_artifacts: list[AssetReferenceV1] = Field(default_factory=list, max_length=1000)
    pronunciation_profile: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    created_by: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateVoiceProfileRequest(StudioContract):
    workspace_id: str
    identity_profile_id: str | None = None
    display_name: str = Field(min_length=1, max_length=240)
    locale: str = Field(default="pt-BR", min_length=2, max_length=32)
    voice_type: Literal["stock", "cloned"] = "cloned"


class CreateVoiceVersionRequest(StudioContract):
    consent_grant_id: str | None = None
    sample_asset_ids: list[str] = Field(default_factory=list, max_length=1000)
    derived_artifacts: list[AssetReferenceV1] = Field(default_factory=list, max_length=1000)
    pronunciation_profile: dict[str, Any] = Field(default_factory=dict)


class QualityCheckV1(StudioContract):
    code: str = Field(min_length=1, max_length=120)
    passed: bool
    score: float | None = Field(default=None, ge=0, le=1)
    detail: str | None = Field(default=None, max_length=2000)


class IdentityEvaluationV1(StudioContract):
    schema_version: Literal["studio.identity-evaluation.v1"] = "studio.identity-evaluation.v1"
    id: str
    workspace_id: str
    target_type: Literal["identity_version", "voice_version"]
    identity_version_id: str | None = None
    voice_version_id: str | None = None
    status: Literal["passed", "failed"]
    evaluator_kind: Literal["automated", "human", "combined"]
    quality_metrics: dict[str, float] = Field(default_factory=dict)
    checks: list[QualityCheckV1] = Field(default_factory=list, max_length=100)
    preview_asset_ids: list[str] = Field(default_factory=list, max_length=100)
    provider_registration_id: str | None = None
    model_registration_id: str | None = None
    evaluated_by: str
    evaluated_at: datetime
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateIdentityEvaluationRequest(StudioContract):
    status: Literal["passed", "failed"]
    evaluator_kind: Literal["automated", "human", "combined"]
    quality_metrics: dict[str, float] = Field(default_factory=dict, max_length=100)
    checks: list[QualityCheckV1] = Field(default_factory=list, max_length=100)
    preview_asset_ids: list[str] = Field(default_factory=list, max_length=100)
    provider_registration_id: str | None = None
    model_registration_id: str | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_evaluation(self) -> CreateIdentityEvaluationRequest:
        if any(value < 0 or value > 1 for value in self.quality_metrics.values()):
            raise ValueError("Quality metrics must be between zero and one")
        if self.status == "passed" and not self.preview_asset_ids:
            raise ValueError("Passed evaluation requires a private preview")
        if self.status == "passed" and any(not check.passed for check in self.checks):
            raise ValueError("Passed evaluation cannot contain a failed check")
        return self


class ReviewIdentityVersionRequest(StudioContract):
    action: Literal["approve", "reject"]
    comment: str = Field(min_length=3, max_length=4000)


class IdentityDeletionRequestV1(StudioContract):
    schema_version: Literal["studio.identity-deletion-request.v1"] = "studio.identity-deletion-request.v1"
    id: str
    workspace_id: str
    target_type: Literal["identity_profile", "voice_profile"]
    identity_profile_id: str | None = None
    voice_profile_id: str | None = None
    status: Literal["planned", "queued", "running", "completed", "failed"]
    reason: str
    delete_source_samples: bool
    deletion_plan: dict[str, Any]
    idempotency_key: str
    requested_by: str
    requested_at: datetime
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempt_count: int = Field(default=0, ge=0)
    execution_receipt: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateIdentityDeletionRequest(StudioContract):
    reason: str = Field(min_length=3, max_length=4000)
    delete_source_samples: bool = False


class ProviderRegistrationV1(StudioContract):
    schema_version: Literal["studio.provider-registration.v1"] = "studio.provider-registration.v1"
    id: str
    capability: str
    provider: str
    provider_version: str
    source_url: str
    source_revision: str
    code_license: str
    status: Literal["evaluation", "approved", "disabled", "rejected"]
    risk_class: Literal["low", "medium", "high", "biometric"]
    manifest: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ModelRegistrationV1(StudioContract):
    schema_version: Literal["studio.model-registration.v1"] = "studio.model-registration.v1"
    id: str
    provider_registration_id: str
    name: str
    version: str
    digest_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    model_license: str
    commercial_use: Literal["approved", "restricted", "unknown"]
    languages: list[str] = Field(default_factory=list, max_length=100)
    capabilities: list[str] = Field(default_factory=list, max_length=100)
    status: Literal["evaluation", "approved", "disabled", "rejected"]
    manifest: dict[str, Any] = Field(default_factory=dict)
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CreateProviderRegistrationRequest(StudioContract):
    """Governed candidate registration; it never advertises a worker provider."""

    workspace_id: str = Field(min_length=1, max_length=120)
    capability: str = Field(min_length=1, max_length=120)
    provider: str = Field(min_length=1, max_length=120)
    provider_version: str = Field(min_length=1, max_length=120)
    source_url: str = Field(min_length=1, max_length=4000)
    source_revision: str = Field(min_length=7, max_length=160)
    code_license: str = Field(min_length=1, max_length=120)
    risk_class: Literal["low", "medium", "high", "biometric"]
    manifest: dict[str, Any] = Field(default_factory=dict)


class CreateModelRegistrationRequest(StudioContract):
    workspace_id: str = Field(min_length=1, max_length=120)
    provider_registration_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    version: str = Field(min_length=1, max_length=120)
    digest_sha256: str = Field(pattern=SHA256_PATTERN)
    model_license: str = Field(min_length=1, max_length=160)
    commercial_use: Literal["approved", "restricted", "unknown"] = "unknown"
    languages: list[str] = Field(default_factory=list, max_length=100)
    capabilities: list[str] = Field(default_factory=list, max_length=100)
    manifest: dict[str, Any] = Field(default_factory=dict)


StudioCapabilityName = Literal["presenter", "avatar", "voice_clone", "stock_voice", "transcription"]


class StudioCapabilityReadinessV1(StudioContract):
    """Tenant-scoped, provider-neutral projection of the Studio activation gates.

    This is intentionally a read model. It never activates a provider, creates an
    identity, or authorizes publication; it only explains why a capability is (or
    is not) eligible at the moment it is queried.
    """

    schema_version: Literal["studio.capability-readiness.v1"] = "studio.capability-readiness.v1"
    workspace_id: str
    capability: StudioCapabilityName
    status: Literal["unavailable", "blocked", "review", "ready"]
    provider_ready: bool = False
    capture_ready: bool = False
    provider_candidates: int = Field(default=0, ge=0)
    approved_providers: int = Field(default=0, ge=0)
    model_candidates: int = Field(default=0, ge=0)
    approved_models: int = Field(default=0, ge=0)
    active_identity_versions: int = Field(default=0, ge=0)
    active_voice_versions: int = Field(default=0, ge=0)
    active_consent_grants: int = Field(default=0, ge=0)
    benchmark_ready: bool = False
    license_ready: bool = False
    consent_ready: bool = False
    publication_allowed: bool = False
    reasons: list[str] = Field(default_factory=list, max_length=40)
    evaluated_at: datetime


class StudioCapabilitiesV1(StudioContract):
    """All Studio capability projections for one workspace."""

    schema_version: Literal["studio.capabilities.v1"] = "studio.capabilities.v1"
    workspace_id: str
    capabilities: list[StudioCapabilityReadinessV1] = Field(min_length=1, max_length=5)
    evaluated_at: datetime
