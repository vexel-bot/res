"""Isolated Motion Canvas graphics renderer for contextual draft compositions."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ...domain.studios.contracts import VideoRenderEncodeResultV1
from ...domain.studios.motion import MotionGraphProjectionV1
from .media_probe import MEDIA_PROBE_PROVIDERS
from .motion_canvas_projection import compile_motion_canvas_composition


class MotionCanvasGraphicsProvider:
    name = "motion-canvas.graphics-v1"
    version = "3.17.2-res.1"

    def __init__(self, node_path: str, ffmpeg_path: str, timeout_seconds: int, worker_dir: Path | None = None):
        self.node_path = node_path
        self.ffmpeg_path = ffmpeg_path
        self.timeout_seconds = timeout_seconds
        self.worker_dir = worker_dir or Path(__file__).resolve().parents[4] / "workers" / "motion-canvas-local"

    def render(self, document, request, assets, destination, progress, is_cancelled, *, motion_projection=None, automatic_draft=False):
        if not automatic_draft or not isinstance(motion_projection, MotionGraphProjectionV1):
            raise ValueError("motion_canvas_bound_automatic_draft_required")
        if request.output.width != document.composition.pages[0].width or request.output.height != document.composition.pages[0].height:
            raise ValueError("motion_canvas_output_size_mismatch")
        if request.output.format != "mp4" or request.output.video_codec != "h264" or request.output.audio_codec != "none":
            raise ValueError("motion_canvas_graphics_output_unsupported")
        if not (self.worker_dir / "node_modules" / "@motion-canvas" / "core").is_dir():
            raise ValueError("motion_canvas_worker_not_installed")
        from ...services.object_storage import sha256_file

        refs = {ref.id: ref for ref in document.assets}
        bindings = {}
        for asset_id, source in assets.items():
            if asset_id not in refs or not refs[asset_id].checksum:
                raise ValueError("motion_canvas_asset_checksum_required:" + asset_id)
            digest = sha256_file(source)
            if digest.lower() != refs[asset_id].checksum.lower():
                raise ValueError("motion_canvas_asset_checksum_conflict:" + asset_id)
            mime = refs[asset_id].media_type
            bindings[asset_id] = {"path": str(source.resolve()), "sha256": digest, "mime": mime}
        manifest = compile_motion_canvas_composition(document, motion_projection, bindings)
        if abs(request.output.fps - manifest["fps"]) > 1e-6:
            raise ValueError("motion_canvas_output_frame_rate_mismatch")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="res-motion-canvas-") as temporary:
            output_dir = Path(temporary)
            manifest_path = output_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            command = [self.node_path, str(self.worker_dir / "render.mjs"), str(manifest_path), str(output_dir / "frames"), self.ffmpeg_path]
            with tempfile.TemporaryFile() as log:
                process = subprocess.Popen(
                    command, cwd=self.worker_dir, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                while process.poll() is None:
                    if is_cancelled():
                        process.terminate()
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        raise InterruptedError("motion_canvas_render_cancelled")
                    if time.monotonic() - started > self.timeout_seconds:
                        process.kill()
                        raise TimeoutError("motion_canvas_render_timeout")
                    time.sleep(0.25)
                if process.returncode:
                    log.seek(0)
                    detail = log.read(4_000).decode("utf-8", errors="replace")
                    raise ValueError("motion_canvas_render_failed:" + detail[-2_000:])
            progress(65)
            receipt = json.loads((output_dir / "frames" / "receipt.json").read_text(encoding="utf-8"))
            visual = output_dir / "frames" / "visual.mp4"
            with visual.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if (
                receipt.get("result") != 0
                or len(receipt.get("frames", [])) != manifest["durationFrames"]
                or receipt.get("videoSha256") != digest
                or receipt.get("manifestSha256") != sha256_file(manifest_path)
            ):
                raise ValueError("motion_canvas_receipt_invalid")
            probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(visual, asset_id="render-pending", checksum_sha256=digest)
            if not probe.video_streams or probe.video_streams[0].width != manifest["width"] or probe.video_streams[0].height != manifest["height"]:
                raise ValueError("motion_canvas_output_probe_mismatch")
            shutil.copyfile(visual, destination)
        return VideoRenderEncodeResultV1(
            provider=self.name, provider_version=self.version,
            width=manifest["width"], height=manifest["height"],
            duration_ms=round(manifest["durationFrames"] / manifest["fps"] * 1000),
            fps=manifest["fps"], video_codec="h264", audio_codec="none",
            render_duration_ms=round((time.monotonic() - started) * 1000),
            frames_rendered=manifest["durationFrames"],
            rendered_layer_ids=[layer["id"] for layer in manifest["layers"] if layer["visible"]],
            renderer_checks={"motionCanvasReceipt": receipt},
            warnings=["Motion Canvas graphics are an experimental draft; human visual review pending."],
        )


from .contextual_motion_render import ContextualMotionRenderProvider


class MotionCanvasContextualRenderProvider(ContextualMotionRenderProvider):
    name = "motion-canvas.contextual-v1"
    version = "3.17.2-res.1"
    projection_target = "motion_canvas"
