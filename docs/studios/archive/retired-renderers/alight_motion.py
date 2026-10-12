"""Experimental graphics provider; unavailable until real-device calibration."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from ...domain.studios.contextual_editing import digest
from ...domain.studios.contracts import VideoRenderEncodeResultV1
from ...domain.studios.motion_recipes import RECIPE_CAPABILITIES
from .alight_worker import NAME, PhysicalAlightWorker, file_hash
from .contextual_motion_render import ContextualMotionRenderProvider
from .media_probe import MEDIA_PROBE_PROVIDERS


def required_capabilities(document):
    capabilities = {
        RECIPE_CAPABILITIES[recipe["technique"]]
        for recipe in document.composition.narrative.get("editorialV2", {}).get("motionRecipes", [])
    }
    for page in document.composition.pages:
        for layer in page.layers:
            if not layer.visible:
                continue
            capabilities.add("composition." + layer.kind)
            component = layer.properties.get("nativeComponent")
            if component:
                capabilities.add(f"native.{component['component']}.v{component['version']}")
            for effect in layer.properties.get("effects", []):
                capabilities.add("effect." + effect["kind"])
    return capabilities


def prepare_bundle(document, request, assets, root, job_id):
    """A checksummed transport manifest, deliberately NOT an Alight XML file."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    refs = {ref.id: ref for ref in document.assets}
    bindings = {}
    for asset_id, source in sorted(assets.items()):
        ref = refs.get(asset_id)
        if not ref or not ref.checksum or file_hash(source) != ref.checksum.lower():
            raise ValueError("alight_source_checksum_conflict")
        if ref.rights_status != "verified":
            raise ValueError("alight_source_rights_unverified")
        name = "assets/" + digest(asset_id) + Path(source).suffix.lower()
        target = root / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        if file_hash(target) != ref.checksum.lower():
            raise ValueError("alight_source_changed_during_copy")
        bindings[asset_id] = {"path": name, "sha256": file_hash(target), "mime": ref.media_type}
    narrative = document.composition.narrative.get("editorialV2", {})
    bundle = {
        "schemaVersion": "studio.alight-transport.v1",
        "jobId": job_id,
        "bundleCompilerVersion": "res.alight-bundle.v1",
        "document": document.model_dump(mode="json", by_alias=True),
        "planId": narrative.get("planId"),
        "plan": request.execution_plan_snapshot,
        "recipes": narrative.get("motionRecipes", []),
        "recipeDigest": digest(narrative.get("motionRecipes", [])),
        "assets": bindings,
        "output": request.output.model_dump(mode="json", by_alias=True),
        "audioPolicy": "silent_visual_ffmpeg_mix",
        "manualInterventions": [],
    }
    bundle["packageDigest"] = digest(bundle)
    (root / "manifest.json").write_text(json.dumps(bundle, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return bundle


class AlightGraphicsProvider:
    name = "alight-motion.graphics-v1"
    version = "experimental.1"

    def __init__(self, worker):
        self.worker = worker

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
        status = self.worker.status()
        if not automatic_draft or not status["available"]:
            raise ValueError("alight_worker_not_ready")
        if (
            request.output.audio_codec != "none"
            or request.output.format != "mp4"
            or request.output.video_codec != "h264"
        ):
            raise ValueError("alight_silent_h264_output_required")
        required = required_capabilities(document)
        if not required.issubset(status["capabilities"]):
            raise ValueError("alight_recipe_capability_missing")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="res-alight-") as temporary:
            root = Path(temporary)
            bundle = prepare_bundle(document, request, assets, root, request.execution_job_id or str(uuid4()))
            visual = root / "visual.mp4"
            receipt_path = root / "receipt.json"
            cmd = [
                sys.executable,
                "-m",
                "app.providers.studios.alight_worker",
                "render",
                "--adb",
                self.worker.adb,
                "--profile",
                str(self.worker.profile_path),
                "--state",
                str(self.worker.state_dir.resolve()),
                "--bundle",
                str(root),
                "--output",
                str(visual),
                "--receipt",
                str(receipt_path),
                "--timeout",
                str(self.worker.timeout),
                "--execution-mode",
                self.worker.execution_mode,
            ]
            self.worker.state_dir.mkdir(parents=True, exist_ok=True)
            log_path = self.worker.state_dir / (digest(bundle["jobId"]) + ".worker.log")
            with log_path.open("w+b") as log:
                process = subprocess.Popen(
                    cmd,
                    cwd=Path(__file__).resolve().parents[3],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    shell=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                while process.poll() is None:
                    running = self.worker.state_dir / (digest(bundle["jobId"]) + ".running.json")
                    deadline_expired = False
                    try:
                        deadline_expired = time.time() > json.loads(running.read_text(encoding="utf-8"))["deadlineUnix"]
                    except (OSError, ValueError, KeyError):
                        pass
                    if is_cancelled() or deadline_expired or time.monotonic() - started > self.worker.timeout * 2 + 30:
                        if sys.platform == "win32":
                            subprocess.run(
                                ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False
                            )
                        else:
                            process.kill()
                        process.wait(timeout=10)
                        # A killed process cannot attest device interruption.
                        from .alight_worker import load_profile

                        profile = load_profile(self.worker.profile_path)
                        self.worker.state_dir.mkdir(parents=True, exist_ok=True)
                        (self.worker.state_dir / (digest(profile["serial"]) + ".quarantine")).write_text(
                            "Worker interrupted; inspect device and journal before recovery.", encoding="utf-8"
                        )
                        raise (
                            InterruptedError("alight_render_cancelled")
                            if is_cancelled()
                            else TimeoutError("alight_render_timeout")
                        )
                    progress(min(65, round((time.monotonic() - started) / self.worker.timeout * 65)))
                    time.sleep(0.25)
                if process.returncode:
                    log.seek(0)
                    diagnostic = log.read().decode("utf-8", errors="replace")[-2000:]
                    raise ValueError("alight_worker_failed:" + diagnostic)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("packageDigest") != bundle["packageDigest"] or receipt.get("videoSha256") != file_hash(
                visual
            ):
                raise ValueError("alight_output_checksum_conflict")
            probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                visual, asset_id="alight-pending", checksum_sha256=file_hash(visual)
            )
            stream = probe.video_streams[0] if len(probe.video_streams) == 1 else None
            timeline = document.composition.media_timeline
            expected_seconds = (
                timeline.duration_frames * timeline.frame_rate.denominator / timeline.frame_rate.numerator
            )
            if (
                not stream
                or probe.audio_streams
                or stream.codec != "h264"
                or (stream.width, stream.height) != (request.output.width, request.output.height)
                or abs(stream.frame_rate.numerator / stream.frame_rate.denominator - request.output.fps) > 0.001
                or abs(probe.duration_microseconds / 1e6 - expected_seconds) > 2 / request.output.fps
            ):
                raise ValueError("alight_output_probe_mismatch")
            shutil.copyfile(visual, destination)
        return VideoRenderEncodeResultV1(
            provider=self.name,
            provider_version=status["providerVersion"],
            width=stream.width,
            height=stream.height,
            duration_ms=round(probe.duration_microseconds / 1000),
            fps=request.output.fps,
            video_codec="h264",
            audio_codec="none",
            render_duration_ms=round((time.monotonic() - started) * 1000),
            frames_rendered=timeline.duration_frames,
            rendered_layer_ids=[],
            rendered_caption_track_ids=[],
            warnings=["Alight experimental; pixel geometry unavailable, human visual review required."],
            renderer_checks={
                "alightReceipt": receipt,
                "motionRecipesDigest": bundle["recipeDigest"],
                "geometrySamples": [],
                "geometryObservation": "unavailable",
            },
        )


class AlightContextualRenderProvider(ContextualMotionRenderProvider):
    name = NAME
    version = "experimental.1"
    projection_target = "remotion"

    def render(self, *args, **kwargs):
        result = super().render(*args, **kwargs)
        return result.model_copy(
            update={
                "rendered_layer_ids": [],
                "renderer_checks": {
                    **result.renderer_checks,
                    "plannedLayerIds": result.rendered_layer_ids,
                    "geometryObservation": "unavailable",
                    "sourceTimesBasis": "declared_plan",
                },
                "warnings": [
                    *result.warnings,
                    "Alight: layer geometry is not measured; declared IDs are planned only.",
                ],
            }
        )


def worker_from_settings(settings):
    return PhysicalAlightWorker(
        settings.studio_alight_adb_path,
        settings.studio_alight_profile_path,
        timeout=settings.studio_alight_worker_timeout_seconds,
        execution_mode=settings.studio_alight_execution_mode,
    )


def refresh_registration(settings, registry):
    registry.pop(NAME, None)
    return {"provider": NAME, "available": False, "blockers": ["editor_replaced_by_effectcraft"], "capabilities": []}
