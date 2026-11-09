"""Small, scoped frame samples for visual planning; never a claim of full playback."""

import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

from ...providers.studios.timeline_ffmpeg import probe, tool
from ...services.object_storage import get_object_storage
from .craft import scoped_asset


@contextmanager
def visual_samples(db, record, contract, enabled=False):
    media, observations = [], []
    with tempfile.TemporaryDirectory(prefix="clicko-edit-evidence-") as temporary:
        if enabled:
            identifiers = list(
                dict.fromkeys(
                    clip.asset_id
                    for track in contract.composition.media_timeline.tracks
                    if track.kind in {"video", "overlay"}
                    for clip in track.clips
                )
            )[:3]
            for identifier in identifiers:
                asset = scoped_asset(db, record.workspace_id, identifier)
                if not (asset.media_type or "").startswith("video/"):
                    continue
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
                    duration = float(probe(source)["format"]["duration"])
                    for fraction in (0.15, 0.8):
                        second = duration * fraction
                        output = Path(temporary) / f"frame-{len(media)}.jpg"
                        process = subprocess.run(
                            [
                                tool("ffmpeg"),
                                "-nostdin",
                                "-hide_banner",
                                "-loglevel",
                                "error",
                                "-ss",
                                str(second),
                                "-i",
                                str(source),
                                "-frames:v",
                                "1",
                                "-vf",
                                "scale=448:-2",
                                "-threads",
                                "1",
                                "-y",
                                str(output),
                            ],
                            capture_output=True,
                            timeout=30,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        if process.returncode or not output.is_file():
                            raise ValueError("timeline_visual_sample_failed")
                        observations.append({"imageIndex": len(media), "assetId": identifier, "sourceSeconds": second})
                        media.append((output, "image/jpeg"))
        yield media, observations
