"""Experimental native timeline plan for a presenter window over a brand video.

The presenter retains its original rectangular background.
"""

from ...domain.studios.contracts import MediaTimelineV1
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ..object_storage import get_object_storage, sha256_file
from .project_montage import FPS, plan_video_montage


def plan_presenter_overlay(workspace_id, brand, presenter, *, frame_width=1080, frame_height=1350):
    if brand.id == presenter.id or frame_width <= 0 or frame_height <= 0:
        raise ValueError("presenter_overlay_material_invalid")
    measured = plan_video_montage(workspace_id, [brand, presenter], avatar_asset_id=presenter.id)
    brand_clip, presenter_clip = measured["clips"]
    if brand_clip["measuredDurationMicroseconds"] < presenter_clip["measuredDurationMicroseconds"]:
        raise ValueError("presenter_overlay_brand_video_too_short")
    sizes = []
    for asset in (brand, presenter):
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
            if sha256_file(path) != asset.checksum_sha256:
                raise ValueError("studio_montage_material_checksum_mismatch")
            probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                path, asset_id=asset.id, checksum_sha256=asset.checksum_sha256
            )
            video = probe.video_streams[0]
            if video.rotation_degrees % 360:
                raise ValueError("presenter_overlay_rotation_unverified")
            sizes.append((video.width, video.height))
    brand_width, brand_height = sizes[0]
    presenter_width, presenter_height = sizes[1]
    brand_scale = 100 * min(frame_width / brand_width, frame_height / brand_height)
    presenter_scale = 100 * min(frame_width * 0.36 / presenter_width, frame_height * 0.36 / presenter_height)
    presenter_frame_width = presenter_width * presenter_scale / 100
    presenter_frame_height = presenter_height * presenter_scale / 100
    margin = frame_width * 0.04
    position = [frame_width - margin - presenter_frame_width / 2, frame_height - margin - presenter_frame_height / 2]
    brand_frames = brand_clip["durationFrames"]
    presenter_frames = presenter_clip["durationFrames"]
    timeline = MediaTimelineV1.model_validate(
        {
            "durationFrames": brand_frames,
            "frameRate": {"numerator": FPS, "denominator": 1},
            "tracks": [
                {
                    "id": "brand-picture",
                    "kind": "video",
                    "name": "Vídeo da marca",
                    "clips": [
                        {
                            "id": "brand-picture",
                            "assetId": brand.id,
                            "timeline": {"startFrame": 0, "durationFrames": brand_frames},
                            "transform": {"scale": brand_scale, "position": [frame_width / 2, frame_height / 2]},
                        }
                    ],
                },
                {
                    "id": "presenter-window",
                    "kind": "overlay",
                    "name": "Janela da apresentação",
                    "clips": [
                        {
                            "id": "presenter-window",
                            "assetId": presenter.id,
                            "timeline": {"startFrame": 0, "durationFrames": presenter_frames},
                            "transform": {"scale": presenter_scale, "position": position},
                        }
                    ],
                },
                {
                    "id": "presenter-speech",
                    "kind": "audio",
                    "name": "Fala escolhida",
                    "clips": [
                        {
                            "id": "presenter-speech",
                            "assetId": presenter.id,
                            "timeline": {"startFrame": 0, "durationFrames": presenter_frames},
                        }
                    ],
                },
            ],
        }
    )
    return {
        "schemaVersion": "clicko.presenter-overlay-plan.v1",
        "mode": "picture_in_picture",
        "durationMs": (brand_frames * 1000 + FPS - 1) // FPS,
        "backgroundRemoval": False,
        "originalAudioEnabled": False,
        "assets": [{"id": item.id, "checksumSha256": item.checksum_sha256} for item in (brand, presenter)],
        "timeline": timeline.model_dump(by_alias=True, mode="json"),
    }
