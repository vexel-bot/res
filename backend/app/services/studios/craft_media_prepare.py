"""Prepare production excerpts without implicit crop, upscale or time stretching."""
import hashlib
import json
import math
import subprocess
from fractions import Fraction
from pathlib import Path


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                            check=True, capture_output=True, timeout=30)
    return json.loads(result.stdout)


def prepare_video_excerpt(source, output, start, duration, *, maximum_side=None):
    """Use the master for production; a bounded working copy is explicitly identified."""
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if source == output or output.exists():
        raise ValueError("craft_preparation_output_must_be_new")
    if not all(type(value) in {int, float} and math.isfinite(value) for value in (start, duration)) or start < 0 or duration <= 0:
        raise ValueError("craft_preparation_interval_invalid")
    metadata = probe(source)
    video = next((stream for stream in metadata["streams"] if stream["codec_type"] == "video"), None)
    if not video:
        raise ValueError("craft_preparation_video_required")
    rate = Fraction(video["avg_frame_rate"])
    if rate <= 0 or start + duration > float(metadata["format"]["duration"]) + 1 / float(rate):
        raise ValueError("craft_preparation_interval_out_of_range")
    width, height = video["width"], video["height"]
    filters = ["setpts=PTS-STARTPTS"]
    if maximum_side is not None:
        if type(maximum_side) is not int or maximum_side < 64:
            raise ValueError("craft_preparation_size_invalid")
        factor = min(1, maximum_side / max(width, height))
        filters.append(f"scale={max(2, int(width * factor)//2*2)}:{max(2, int(height * factor)//2*2)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-n", "-ss", str(start), "-i", str(source),
                        "-t", str(duration), "-map", "0:v:0", "-an", "-vf", ",".join(filters),
                        "-fps_mode", "passthrough", "-threads", "2", "-c:v", "libx264", "-crf", "16",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)],
                       check=True, capture_output=True, timeout=180)
        prepared = probe(output)
    except (OSError, subprocess.SubprocessError):
        output.unlink(missing_ok=True)
        raise
    stream = next(stream for stream in prepared["streams"] if stream["codec_type"] == "video")
    if Fraction(stream["avg_frame_rate"]) != rate:
        output.unlink(missing_ok=True)
        raise ValueError("craft_preparation_cadence_changed")
    with source.open("rb") as handle:
        source_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    with output.open("rb") as handle:
        output_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    receipt = {"sourceSha256": source_hash, "outputSha256": output_hash, "sourceStartSeconds": start,
               "sourceDurationSeconds": duration, "outputDurationSeconds": float(prepared["format"]["duration"]),
               "sourceDimensions": [width, height], "outputDimensions": [stream["width"], stream["height"]],
               "frameRate": str(rate), "speed": 1, "crop": None, "upscaled": False,
               "role": "preview" if maximum_side else "production", "masterPath": str(source),
               "audio": "excluded; mix uses separately registered audio"}
    output.with_suffix(output.suffix + ".preparation.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt
