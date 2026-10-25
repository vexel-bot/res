"""Measured, sequential placement of project video materials in the native timeline."""

from pathlib import PurePosixPath
from subprocess import TimeoutExpired

from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ..object_storage import get_object_storage, sha256_file

FPS = 30


def plan_video_montage(workspace_id, assets, *, avatar_asset_id=None):
    clips, next_frame = [], 0
    for asset in assets:
        if (
            not asset
            or asset.workspace_id != workspace_id
            or asset.lifecycle_status != "active"
            or not asset.storage_key
            or not asset.checksum_sha256
            or not (asset.media_type or "").startswith("video/")
            or PurePosixPath(asset.storage_key).parts[0] != workspace_id
        ):
            raise ValueError("studio_montage_material_invalid")
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            if sha256_file(path) != asset.checksum_sha256:
                raise ValueError("studio_montage_material_checksum_mismatch")
            try:
                probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                    path, asset_id=asset.id, checksum_sha256=asset.checksum_sha256
                )
            except (OSError, TimeoutExpired, ValueError) as error:
                raise ValueError("studio_montage_material_unreadable") from error
        if not probe.video_streams or not probe.duration_microseconds or probe.duration_microseconds <= 0:
            raise ValueError("studio_montage_video_duration_required")
        if asset.id == avatar_asset_id:
            declared = (asset.object_metadata or {}).get("avatarVideoJobResult", {}).get("avatar", {}).get("durationMs")
            if not probe.audio_streams:
                raise ValueError("studio_montage_avatar_audio_missing")
            if not isinstance(declared, int) or abs(probe.duration_microseconds / 1000 - declared) > 150:
                raise ValueError("studio_montage_avatar_duration_mismatch")
        # Start each following clip at a complete output-frame boundary. Never
        # place another video/audio on top of the selected final speech.
        frames = (probe.duration_microseconds * FPS + 999_999) // 1_000_000
        clips.append(
            {
                "assetId": asset.id,
                "checksumSha256": asset.checksum_sha256,
                "startFrame": next_frame,
                "durationFrames": frames,
                "measuredDurationMicroseconds": probe.duration_microseconds,
                "hasAudio": bool(probe.audio_streams),
                "framing": "contain",
            }
        )
        next_frame += frames
    if not clips:
        raise ValueError("studio_montage_material_required")
    return {
        "schemaVersion": "clicko.project-montage.v1",
        "fps": FPS,
        "clips": clips,
        "durationMs": (next_frame * 1000 + FPS - 1) // FPS,
    }


def native_imports(plan):
    return [
        command
        for clip in plan["clips"]
        for command in [
            {
                "id": "asset.import",
                "params": {
                    "assetId": clip["assetId"],
                    "addToTimeline": True,
                    "seconds": clip["startFrame"] / plan["fps"],
                },
            },
            {"id": "clip.fitToFrame", "params": {}},
        ]
    ]
