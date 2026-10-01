"""Inspect immutable downloaded pixels using the existing durable AI job executor."""

import re

from ...models import LibraryAsset
from ...providers.studios.contextual_render import ContextualFFmpegProvider
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ..object_storage import get_object_storage, sha256_file


def bound_asset(db, workspace_id, request):
    asset = db.get(LibraryAsset, request.asset_id)
    if (
        not asset
        or asset.workspace_id != workspace_id
        or asset.lifecycle_status != "active"
        or asset.checksum_sha256 != request.checksum
        or not asset.storage_key
    ):
        raise ValueError("material_inspection_asset_conflict")
    if not (asset.object_metadata or {}).get("editingResource", {}).get("usageEvidence"):
        raise ValueError("material_inspection_usage_required")
    return asset


def prepare_samples(db, workspace_id, request, stack, directory, settings, cancelled):
    asset = bound_asset(db, workspace_id, request)
    path = stack.enter_context(get_object_storage(asset.storage_backend).materialize(asset.storage_key))
    if sha256_file(path) != request.checksum:
        raise ValueError("material_inspection_checksum_conflict")
    if asset.media_type.startswith("image/"):
        return [(path, asset.media_type)], [{"index": 0, "checksum": request.checksum}], request.required_seconds
    if not asset.media_type.startswith("video/"):
        raise ValueError("material_inspection_visual_required")
    probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(path, asset_id=asset.id, checksum_sha256=request.checksum)
    duration = probe.duration_microseconds / 1e6
    media, evidence = [], []
    start = request.source_start_seconds
    end = min(duration, start + max(request.required_seconds, 1))
    if start >= duration:
        raise ValueError("material_inspection_source_interval_unavailable")
    renderer = ContextualFFmpegProvider(settings.ffmpeg_path, settings.ffmpeg_timeout_seconds)
    sample_times = [start + max(0, end - start - 0.08) * index / 5 for index in range(6)]
    if request.max_samples > 6:
        renderer._run(
            [
                "-ss",
                str(start),
                "-i",
                str(path),
                "-t",
                str(end - start),
                "-an",
                "-vf",
                "scale=160:-2,select=gt(scene\\,0.3),metadata=mode=print:file=scene-changes.txt",
                "-f",
                "null",
                "-",
            ],
            directory,
            cancelled,
        )
        changes_file = directory / "scene-changes.txt"
        cuts = (
            [float(value) + start for value in re.findall(r"pts_time:([0-9.]+)", changes_file.read_text())]
            if changes_file.exists()
            else []
        )
        for cut in cuts:
            for seconds in (max(start, cut - 0.08), min(end - 0.001, cut + 0.08)):
                if len(sample_times) < request.max_samples and all(
                    abs(seconds - previous) > 0.02 for previous in sample_times
                ):
                    sample_times.append(seconds)
        for index in range(request.max_samples):
            seconds = start + max(0, end - start - 0.08) * index / (request.max_samples - 1)
            if len(sample_times) < request.max_samples and all(
                abs(seconds - previous) > 0.02 for previous in sample_times
            ):
                sample_times.append(seconds)
    for index, seconds in enumerate(sorted(sample_times)):
        sample = directory / f"material-{index}.jpg"
        renderer._run(
            ["-y", "-ss", str(seconds), "-i", str(path), "-frames:v", "1", "-vf", "scale=512:-2", str(sample)],
            directory,
            cancelled,
        )
        media.append((sample, "image/jpeg"))
        evidence.append({"index": index, "seconds": seconds, "checksum": sha256_file(sample)})
    return media, evidence, duration
