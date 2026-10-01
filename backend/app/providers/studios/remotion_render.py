"""Isolated Remotion renderer for the contextual graphics subset."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from ...domain.studios.contracts import VideoRenderEncodeResultV1
from ...domain.studios.motion import MotionGraphProjectionV1
from .contextual_motion_render import ContextualMotionRenderProvider
from .media_probe import MEDIA_PROBE_PROVIDERS
from .motion_canvas_projection import compile_motion_canvas_composition


class RemotionGraphicsProvider:
    name = "remotion.graphics-v1"
    version = "4.0.527-res.1"
    runner = "render-plan.mjs"
    compile_composition = staticmethod(compile_motion_canvas_composition)

    def __init__(self, node_path: str, ffmpeg_path: str, timeout_seconds: int, worker_dir: Path | None = None):
        self.node_path = node_path
        self.ffmpeg_path = ffmpeg_path
        self.timeout_seconds = timeout_seconds
        self.worker_dir = worker_dir or Path(__file__).resolve().parents[4] / "workers" / "remotion-benchmark"

    def render(
        self,
        document,
        request,
        assets,
        destination,
        progress,
        is_cancelled,
        *,
        motion_projection=None,
        automatic_draft=False,
    ):
        if not automatic_draft or not isinstance(motion_projection, MotionGraphProjectionV1):
            raise ValueError("remotion_bound_automatic_draft_required")
        if (
            request.output.format != "mp4"
            or request.output.video_codec != "h264"
            or request.output.audio_codec != "none"
        ):
            raise ValueError("remotion_graphics_output_unsupported")
        if not (self.worker_dir / "node_modules" / "@remotion" / "renderer").is_dir():
            raise ValueError("remotion_worker_not_installed")
        from ...services.object_storage import sha256_file

        refs = {ref.id: ref for ref in document.assets}
        bindings = {}
        for asset_id, source in assets.items():
            if asset_id not in refs or not refs[asset_id].checksum:
                raise ValueError("remotion_asset_checksum_required:" + asset_id)
            digest = sha256_file(source)
            if digest.lower() != refs[asset_id].checksum.lower():
                raise ValueError("remotion_asset_checksum_conflict:" + asset_id)
            bindings[asset_id] = {"path": str(source.resolve()), "sha256": digest, "mime": refs[asset_id].media_type}
        manifest = self.compile_composition(document, motion_projection, bindings)
        if (
            request.output.width != manifest["width"]
            or request.output.height != manifest["height"]
            or abs(request.output.fps - manifest["fps"]) > 1e-6
        ):
            raise ValueError("remotion_output_spec_conflict")
        if is_cancelled():
            raise InterruptedError("remotion_render_cancelled")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="res-remotion-") as temporary:
            root = Path(temporary)
            manifest_path = root / "manifest.json"
            visual = root / "visual.mp4"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            command = [self.node_path, str(self.worker_dir / self.runner), str(manifest_path), str(visual)]
            with tempfile.TemporaryFile(mode="w+b") as log:
                process = subprocess.Popen(
                    command,
                    cwd=self.worker_dir,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                while process.poll() is None:
                    cancelled = is_cancelled()
                    if cancelled or time.monotonic() - started > self.timeout_seconds:
                        if __import__("os").name == "nt":
                            subprocess.run(
                                ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False
                            )
                        else:
                            process.kill()
                        process.wait(timeout=10)
                        if cancelled:
                            raise InterruptedError("remotion_render_cancelled")
                        raise TimeoutError("remotion_render_timeout")
                    time.sleep(0.25)
                log.seek(0)
                output = log.read().decode("utf-8", errors="replace")
            if process.returncode:
                diagnostic = output[:700] if len(output) <= 700 else output[:700] + "\n...\n" + output[-1300:]
                raise ValueError("remotion_render_failed:" + diagnostic)
            try:
                receipt = json.loads(output.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError) as exc:
                raise ValueError("remotion_receipt_invalid") from exc
            if not visual.is_file() or receipt.get("videoSha256") != sha256_file(visual):
                raise ValueError("remotion_output_checksum_conflict")
            if receipt.get("manifestSha256") != sha256_file(manifest_path):
                raise ValueError("remotion_manifest_checksum_conflict")
            geometry = []
            geometry_path = root / "geometry.json"
            if geometry_path.is_file():
                if receipt.get("geometrySha256") != sha256_file(geometry_path):
                    raise ValueError("remotion_geometry_checksum_conflict")
                geometry = json.loads(geometry_path.read_text(encoding="utf-8"))
            probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                visual, asset_id="render-pending", checksum_sha256=receipt["videoSha256"]
            )
            if (
                not probe.video_streams
                or probe.video_streams[0].width != manifest["width"]
                or probe.video_streams[0].height != manifest["height"]
            ):
                raise ValueError("remotion_output_probe_mismatch")
            shutil.copyfile(visual, destination)
        progress(100)
        return VideoRenderEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=manifest["width"],
            height=manifest["height"],
            duration_ms=round(manifest["durationFrames"] / manifest["fps"] * 1000),
            fps=manifest["fps"],
            video_codec="h264",
            audio_codec="none",
            render_duration_ms=round((time.monotonic() - started) * 1000),
            frames_rendered=manifest["durationFrames"],
            rendered_layer_ids=[layer["id"] for layer in manifest["layers"] if layer["visible"]],
            renderer_checks={
                "remotionReceipt": receipt,
                "nativeCompositionDigest": manifest.get("nativeCompositionDigest"),
                "editorialOperations": manifest.get("editorialOperations", []),
                "geometrySchemaVersion": "studio.rendered-geometry.v1",
                "geometrySamples": geometry,
            },
            warnings=["Remotion is experimental; license and human visual review pending."],
        )


class RemotionContextualRenderProvider(ContextualMotionRenderProvider):
    name = "remotion.contextual-v1"
    version = "4.0.527-res.1"
    projection_target = "motion_canvas"


class RemotionNativeGraphicsProvider(RemotionGraphicsProvider):
    from .remotion_projection import compile_remotion_composition

    name = "remotion.native-graphics-v2"
    version = "4.0.527-native.3"
    runner = "render-hybrid.mjs"
    compile_composition = staticmethod(compile_remotion_composition)


class RemotionNativeContextualRenderProvider(ContextualMotionRenderProvider):
    name = "remotion.contextual-v2"
    version = "4.0.527-native.3"
    projection_target = "remotion"
