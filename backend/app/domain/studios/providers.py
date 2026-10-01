from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Protocol

from .contracts import (
    AudioWaveformManifestV1,
    AudioWaveformSpecV1,
    AvatarVideoEncodeResultV1,
    AvatarVideoRequest,
    CreativeDocumentV1,
    MediaProbeResultV1,
    MediaProxyEncodeResultV1,
    MediaProxySpecV1,
    SpeechSynthesisRequestV1,
    SpeechSynthesisResultV1,
    StudioAcousticAnalysisJobRequestV1,
    StudioAcousticDetectorResultV1,
    TranscriptionRequestV1,
    TranscriptionResultV1,
    VideoRenderEncodeResultV1,
    VideoRenderRequestV1,
    VideoRenderSpecV1,
    VideoTechnicalQualityEvaluationV1,
    VideoTechnicalQualityPolicyV1,
    VoiceCloneReferenceV1,
)
from .duplex import (
    DuplexEventV1,
    DuplexInputAudioFrameV1,
    DuplexInterruptRequestV1,
    DuplexSessionCloseReceiptV1,
    DuplexSessionRequestV1,
)
from .generative_video import (
    GenerativeVideoDownloadV1,
    GenerativeVideoOperationV1,
    GenerativeVideoRequestV1,
)
from .intelligence import (
    EditProposalV1,
    LStoryboardV1,
    MediaIndexV1,
    PlanningCopyRequestV1,
    PlanningCopyResultV1,
)
from .motion import MotionGraphProjectionV1
from .reality import (
    PhysicalPlausibilityEvaluationV1,
    PhysicalPlausibilityPolicyV1,
    PhysicalPlausibilityRequestV1,
    RealityAnalysisRequestV1,
    RealityContributionV1,
    RealityModelV1,
    ShotRealityConstraintSetV1,
)

ProgressCallback = Callable[[int], None]
CancellationCheck = Callable[[], bool]


class GenerationProvider(Protocol):
    name: str

    def execute(
        self,
        document: CreativeDocumentV1 | None,
        request: dict[str, Any],
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> dict[str, Any]: ...


class AvatarVideoProvider(Protocol):
    """Biometric presenter port kept separate from generic generation."""

    name: str
    version: str

    def render(
        self,
        document: CreativeDocumentV1,
        request: AvatarVideoRequest,
        identity_samples: list[Path],
        driving_audio: Path,
        destination: Path,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> AvatarVideoEncodeResultV1: ...


class GenerativeVideoProvider(Protocol):
    """Paid asynchronous shot generation; distinct from avatar rendering."""

    name: str
    version: str

    def preflight(self, request: GenerativeVideoRequestV1) -> None: ...

    def start(self, request: GenerativeVideoRequestV1) -> GenerativeVideoOperationV1: ...

    def wait(
        self,
        operation: GenerativeVideoOperationV1,
        *,
        is_cancelled: CancellationCheck,
    ) -> GenerativeVideoOperationV1: ...

    def download(
        self,
        request: GenerativeVideoRequestV1,
        operation: GenerativeVideoOperationV1,
        destination: Path,
    ) -> GenerativeVideoDownloadV1: ...


class SpeechSynthesisProvider(Protocol):
    """Typed speech port; adapters must return an auditable audio result."""

    name: str
    version: str

    def synthesize(
        self,
        request: SpeechSynthesisRequestV1,
        destination: Path,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> SpeechSynthesisResultV1: ...


class VoiceCloneProvider(Protocol):
    """Clones only from a consent-bound reference materialized for one job."""

    name: str
    version: str

    def clone(
        self,
        request: SpeechSynthesisRequestV1,
        reference: VoiceCloneReferenceV1,
        reference_path: Path,
        destination: Path,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> SpeechSynthesisResultV1: ...


class VoiceReferenceNormalizer(Protocol):
    """Normalizes private enrollment audio without persisting a new identity asset."""

    name: str
    version: str

    def normalize(
        self,
        source: Path,
        destination: Path,
        *,
        voice_version_id: str,
        consent_grant_id: str,
        source_asset_id: str,
        source_checksum_sha256: str,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> VoiceCloneReferenceV1: ...


class DuplexConversationSession(Protocol):
    """One isolated full-duplex session; transport and persistence stay outside."""

    session_id: str

    async def push_audio(
        self,
        frame: DuplexInputAudioFrameV1,
        payload: bytes,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> None: ...

    def events(self) -> AsyncIterator[DuplexEventV1]: ...

    async def interrupt(
        self,
        request: DuplexInterruptRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> DuplexEventV1: ...

    async def close(
        self,
        reason: str,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> DuplexSessionCloseReceiptV1: ...


class DuplexConversationProvider(Protocol):
    """Starts a conversational voice session, never a rendered TTS/clone job."""

    name: str
    version: str

    async def start(
        self,
        request: DuplexSessionRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> DuplexConversationSession: ...


class TranscriptionProvider(Protocol):
    """Typed speech-to-text port; adapters never own transcript persistence."""

    name: str
    version: str

    def transcribe(
        self,
        request: TranscriptionRequestV1,
        source: Path,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> TranscriptionResultV1: ...


class VideoRenderProvider(Protocol):
    """Capability port implemented by adapters, never by the Studio domain itself."""

    name: str
    version: str

    def render(
        self,
        document: CreativeDocumentV1,
        request: VideoRenderRequestV1,
        assets: dict[str, Path],
        destination: Path,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
        *,
        motion_projection: MotionGraphProjectionV1 | None = None,
    ) -> VideoRenderEncodeResultV1: ...


class VideoTechnicalQualityProvider(Protocol):
    """Evaluates a rendered artifact without owning render or review semantics."""

    name: str
    version: str

    def evaluate(
        self,
        artifact: Path,
        *,
        expected: VideoRenderSpecV1,
        expected_duration_ms: int,
        policy: VideoTechnicalQualityPolicyV1,
        is_cancelled: CancellationCheck,
    ) -> VideoTechnicalQualityEvaluationV1: ...


class AcousticAnalysisProvider(Protocol):
    """Detects prohibited speech/music; it never grants publication itself."""

    name: str
    version: str

    def analyze(
        self,
        source: Path,
        request: StudioAcousticAnalysisJobRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> StudioAcousticDetectorResultV1: ...


class MediaProbeProvider(Protocol):
    """Normalizes technical media metadata without leaking ffprobe/provider JSON into the domain."""

    name: str
    version: str

    def probe(self, path: Path, *, asset_id: str, checksum_sha256: str | None) -> MediaProbeResultV1: ...


class MediaProxyProvider(Protocol):
    """Produces an editable derivative while the original remains the canonical source."""

    name: str
    version: str

    def transcode(
        self,
        source: Path,
        destination: Path,
        spec: MediaProxySpecV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> MediaProxyEncodeResultV1: ...


class MediaWaveformProvider(Protocol):
    """Decodes audio incrementally and emits a portable, source-clock waveform manifest."""

    name: str
    version: str

    def generate(
        self,
        source: Path,
        destination: Path,
        *,
        media_ingest_id: str,
        source_asset_id: str,
        source_checksum_sha256: str,
        audio_stream_index: int,
        start_microseconds: int,
        source_duration_microseconds: int,
        spec: AudioWaveformSpecV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> AudioWaveformManifestV1: ...


class VideoUnderstandingProvider(Protocol):
    """Builds a source-clock media index; it never edits a document or approves output."""

    name: str
    version: str

    def analyze(
        self,
        source: Path,
        *,
        workspace_id: str,
        media_ingest_id: str,
        source_asset_id: str,
        source_checksum_sha256: str,
        duration_microseconds: int,
        transcript_contract: dict[str, Any] | None,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> MediaIndexV1: ...


class PlanningCopyProvider(Protocol):
    """Produces an evidence-aware draft; review and persistence remain Clicko-owned."""

    name: str
    version: str

    def plan(
        self,
        request: PlanningCopyRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> PlanningCopyResultV1: ...


class EditPlanningProvider(Protocol):
    """Emits evidence-bound suggestions; persistence and application remain Clicko-owned."""

    name: str
    version: str

    def plan(
        self,
        document: CreativeDocumentV1,
        media_index: MediaIndexV1,
        storyboard: LStoryboardV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> EditProposalV1: ...


class VisualGeometryProvider(Protocol):
    """Emits camera/depth evidence without deciding whether a scene is physically valid."""

    name: str
    version: str

    def observe(
        self,
        source: Path,
        request: RealityAnalysisRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityContributionV1: ...


class ObjectTrackingProvider(Protocol):
    """Emits entities and trajectories without owning Clicko's reality graph."""

    name: str
    version: str

    def observe(
        self,
        source: Path,
        request: RealityAnalysisRequestV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityContributionV1: ...


class PhysicalSceneUnderstandingProvider(Protocol):
    """Synthesizes provider contributions into the canonical RealityModelV1."""

    name: str
    version: str

    def synthesize(
        self,
        request: RealityAnalysisRequestV1,
        contributions: list[RealityContributionV1],
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityModelV1: ...


class VideoWorldModelProvider(Protocol):
    """Adds predictive evidence; it never approves, blocks or explains a video alone."""

    name: str
    version: str

    def predict(
        self,
        source: Path,
        request: RealityAnalysisRequestV1,
        reality_model: RealityModelV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> RealityContributionV1: ...


class PhysicalPlausibilityProvider(Protocol):
    """Produces localized, advisory checks bound to exact inputs and policy."""

    name: str
    version: str

    def evaluate(
        self,
        request: PhysicalPlausibilityRequestV1,
        reality_model: RealityModelV1,
        constraints: ShotRealityConstraintSetV1,
        policy: PhysicalPlausibilityPolicyV1,
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> PhysicalPlausibilityEvaluationV1: ...


class RealityCalibrationProvider(Protocol):
    """Calibrates confidence while preserving every exact evaluation binding."""

    name: str
    version: str

    def calibrate(
        self,
        evaluation: PhysicalPlausibilityEvaluationV1,
        *,
        calibration_policy_digest_sha256: str,
    ) -> PhysicalPlausibilityEvaluationV1: ...


class DocumentSnapshotProvider:
    """Built-in deterministic provider used to validate orchestration without an external model."""

    name = "builtin.snapshot"

    def execute(
        self,
        document: CreativeDocumentV1 | None,
        request: dict[str, Any],
        progress: ProgressCallback,
        is_cancelled: CancellationCheck,
    ) -> dict[str, Any]:
        progress(20)
        if is_cancelled():
            return {"cancelled": True}
        if document is None:
            raise ValueError("document_snapshot requires a document")
        progress(70)
        if is_cancelled():
            return {"cancelled": True}
        return {
            "documentId": document.document_id,
            "revision": document.revision,
            "version": document.version,
            "pageCount": len(document.composition.pages),
            "request": request,
        }


PROVIDERS: dict[str, GenerationProvider] = {DocumentSnapshotProvider.name: DocumentSnapshotProvider()}

# Biometric adapters are promoted explicitly after rights, supply-chain and
# benchmark gates. Production starts empty and therefore fails closed.
AVATAR_VIDEO_PROVIDERS: dict[str, AvatarVideoProvider] = {}

# External paid providers are injected only by explicit one-shot runners. Keeping
# this empty prevents ordinary Studio jobs from spending through a generic route.
GENERATIVE_VIDEO_PROVIDERS: dict[str, GenerativeVideoProvider] = {}

# Intentionally empty until a candidate passes benchmark, legal, provenance and
# promotion gates. A generic GenerationProvider must not silently become speech.
SPEECH_PROVIDERS: dict[str, SpeechSynthesisProvider] = {}

# Clone adapters are deliberately separated from stock TTS. They receive a
# one-job reference path only after consent and tenant-scoped storage checks.
VOICE_CLONE_PROVIDERS: dict[str, VoiceCloneProvider] = {}

# Technical normalizers are not clone engines and do not advertise an AI
# capability. The built-in FFmpeg implementation is registered in its adapter
# module and injected by the speech worker.
VOICE_REFERENCE_NORMALIZERS: dict[str, VoiceReferenceNormalizer] = {}

# Kept separate from synthesis so a generic speech adapter cannot silently
# become WhisperX/ASR. Registration and benchmark gates remain mandatory.
TRANSCRIPTION_PROVIDERS: dict[str, TranscriptionProvider] = {}

# Promotion requires commercial-use review, a representative benchmark and an
# advertised media worker. Research-only YAMNet/VAD adapters never enter here.
ACOUSTIC_ANALYSIS_PROVIDERS: dict[str, AcousticAnalysisProvider] = {}
