from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExecutionCapability = Literal[
    "control",
    "media_cpu",
    "speech_cpu",
    "speech_gpu",
    "vision_gpu",
    "llm_gpu",
]


@dataclass(frozen=True)
class ExecutionProfile:
    capability: ExecutionCapability
    queue: str
    resource_class: str
    hard_time_limit_seconds: int

    @property
    def soft_time_limit_seconds(self) -> int:
        return max(60, self.hard_time_limit_seconds - 60)


EXECUTION_PROFILES: dict[str, ExecutionProfile] = {
    "editing_gemini": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 1800),
    "editing_ai": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 1800),
    "document_snapshot": ExecutionProfile("control", "studio.cpu", "cpu.standard", 300),
    "media_probe": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 900),
    "video_proxy": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 3_600),
    "media_waveform": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 3_600),
    "video_ingest": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 1_800),
    "stock_voice": ExecutionProfile("speech_cpu", "studio.speech.cpu", "cpu.speech", 1_800),
    "transcription": ExecutionProfile("speech_gpu", "studio.gpu.speech", "gpu.speech", 3_600),
    "voice_clone": ExecutionProfile("speech_gpu", "studio.gpu.speech", "gpu.speech", 3_600),
    "lip_sync": ExecutionProfile("vision_gpu", "studio.gpu.vision", "gpu.vision", 7_200),
    "avatar_video": ExecutionProfile("vision_gpu", "studio.gpu.vision", "gpu.vision", 7_200),
    "scene_generation": ExecutionProfile("vision_gpu", "studio.gpu.vision", "gpu.vision.local", 1_800),
    "reality_analysis": ExecutionProfile("vision_gpu", "studio.gpu.vision", "gpu.vision", 7_200),
    "video_physical_qc": ExecutionProfile("vision_gpu", "studio.gpu.vision", "gpu.vision", 7_200),
    "planning_copy": ExecutionProfile("llm_gpu", "studio.gpu.llm", "gpu.llm", 3_600),
    "video_render": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 7_200),
    "acoustic_analysis": ExecutionProfile("media_cpu", "studio.media.cpu", "cpu.media", 3_600),
}


def execution_profile(job_type: str) -> ExecutionProfile:
    try:
        return EXECUTION_PROFILES[job_type]
    except KeyError as error:
        raise ValueError(f"unsupported_studio_job_type:{job_type}") from error
