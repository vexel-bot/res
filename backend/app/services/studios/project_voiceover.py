"""A selected voice narrates a brand video or still through FilmCraft's native timeline."""

from fractions import Fraction
from math import ceil
from pathlib import PurePosixPath
from subprocess import TimeoutExpired

from PIL import Image

from ...domain.studios.contracts import MediaTimelineV1
from ...models import StudioGenerationJob
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ..object_storage import get_object_storage, sha256_file
from .cast_speech import selected_speech_asset
from .casting import resolve_cast
from .project_montage import FPS, plan_video_montage


def final_speech(db, row):
    refs = resolve_cast(db, row.workspace_id, None, row.payload.get("voiceVersionId"))
    voice = refs.get("voice")
    if not voice or voice != (row.payload.get("casting") or {}).get("voice"):
        raise ValueError("production_voice_selection_conflict")
    narration = row.payload.get("narration") or {}
    job = db.get(StudioGenerationJob, narration.get("jobId")) if narration.get("jobId") else None
    if not job or job.workspace_id != row.workspace_id or job.correlation_id != f"department-narration:{row.id}":
        raise ValueError("voiceover_final_narration_required")
    if row.payload.get("narrationDraft") and row.payload["narrationDraft"] != narration.get("text"):
        raise ValueError("voiceover_narration_draft_not_generated")
    audio = selected_speech_asset(db, job, voice, narration["text"])
    if not audio:
        raise ValueError("voiceover_final_narration_required")
    return audio, job


def plan_voiceover(db, row, source):
    audio, job = final_speech(db, row)
    if (
        not source
        or source.workspace_id != row.workspace_id
        or source.lifecycle_status != "active"
        or not source.storage_key
        or not source.checksum_sha256
    ):
        raise ValueError("studio_montage_material_invalid")
    still = (source.media_type or "").startswith("image/")
    if not still and not (source.media_type or "").startswith("video/"):
        raise ValueError("studio_montage_material_invalid")
    if any(PurePosixPath(asset.storage_key).parts[0] != row.workspace_id for asset in (source, audio)):
        raise ValueError("studio_montage_material_invalid")
    source_plan = None if still else plan_video_montage(row.workspace_id, [source])
    with get_object_storage(source.storage_backend).materialize(source.storage_key) as path:
        if sha256_file(path) != source.checksum_sha256:
            raise ValueError("studio_montage_material_checksum_mismatch")
        try:
            if still:
                with Image.open(path) as image:
                    image.verify()
            else:
                video = (
                    MEDIA_PROBE_PROVIDERS["builtin.ffprobe"]
                    .probe(path, asset_id=source.id, checksum_sha256=source.checksum_sha256)
                    .video_streams[0]
                )
        except (OSError, ValueError, TimeoutExpired) as error:
            raise ValueError("studio_montage_material_unreadable") from error
    with get_object_storage(audio.storage_backend).materialize(audio.storage_key) as path:
        if sha256_file(path) != audio.checksum_sha256:
            raise ValueError("studio_montage_material_checksum_mismatch")
        try:
            probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                path, asset_id=audio.id, checksum_sha256=audio.checksum_sha256
            )
        except (OSError, ValueError, TimeoutExpired) as error:
            raise ValueError("studio_montage_material_unreadable") from error
    if not probe.audio_streams or probe.duration_microseconds <= 0:
        raise ValueError("voiceover_narration_audio_required")
    declared = (job.result_payload.get("speech") or {}).get("durationMs")
    if not isinstance(declared, int) or abs(declared - probe.duration_microseconds / 1000) > 150:
        raise ValueError("voiceover_narration_duration_mismatch")
    frames = (probe.duration_microseconds * FPS + 999_999) // 1_000_000
    hold = None
    source_us = None
    if not still:
        source_us = source_plan["clips"][0]["measuredDurationMicroseconds"]
        video_us = video.duration_microseconds
        if not video_us:
            raise ValueError("voiceover_video_duration_unverified")
        if video_us * FPS < frames * 1_000_000:
            source_frame_us = Fraction(1_000_000 * video.frame_rate.denominator, video.frame_rate.numerator)
            last_frame = max(0, video_us - source_frame_us)
            hold = min(max(0, (video_us * FPS + 999_999) // 1_000_000 - 1), max(0, ceil(last_frame * FPS / 1_000_000)))
    timeline = MediaTimelineV1.model_validate(
        {
            "durationFrames": frames,
            "frameRate": {"numerator": FPS, "denominator": 1},
            "tracks": [
                {
                    "id": "brand-picture",
                    "kind": "video",
                    "name": "Imagem da marca",
                    "clips": [
                        {
                            "id": "brand-picture",
                            "assetId": source.id,
                            "label": "Material da marca",
                            "timeline": {"startFrame": 0, "durationFrames": frames},
                        }
                    ],
                },
                {
                    "id": "selected-voice",
                    "kind": "audio",
                    "name": "Voz escolhida",
                    "clips": [
                        {
                            "id": "selected-voice",
                            "assetId": audio.id,
                            "label": "Narração final",
                            "timeline": {"startFrame": 0, "durationFrames": frames},
                            "source": {"startMicroseconds": 0, "durationMicroseconds": probe.duration_microseconds},
                        }
                    ],
                },
            ],
        }
    )
    return {
        "schemaVersion": "clicko.project-voiceover.v1",
        "mode": "voiceover",
        "fps": FPS,
        "durationMs": (frames * 1000 + FPS - 1) // FPS,
        "narrationJobId": job.id,
        "sourceAssetId": source.id,
        "sourceChecksumSha256": source.checksum_sha256,
        "audioAssetId": audio.id,
        "audioChecksumSha256": audio.checksum_sha256,
        "sourceDurationMicroseconds": source_us,
        "audioDurationMicroseconds": probe.duration_microseconds,
        "stillImage": still,
        "holdFromFrame": hold,
        "originalAudioEnabled": False,
        "timeline": timeline.model_dump(by_alias=True, mode="json"),
    }, audio


def native_voiceover_commands(plan):
    commands = [{"id": "edit.selectAll", "params": {}}, {"id": "clip.fitToFrame", "params": {}}]
    if plan["stillImage"] or plan["holdFromFrame"] is not None:
        commands.append(
            {"id": "clip.frameHold", "params": {"frame": 0 if plan["stillImage"] else plan["holdFromFrame"]}}
        )
    return commands
