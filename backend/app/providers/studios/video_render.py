from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import tempfile
import textwrap
import time
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from ...config import get_settings
from ...domain.studios.contracts import (
    CaptionRenderStyleV1,
    CreativeDocumentV1,
    UgcShapeLayerPropertiesV1,
    UgcTextLayerPropertiesV1,
    VideoRenderEncodeResultV1,
    VideoRenderRequestV1,
)
from ...domain.studios.motion import MotionGraphProjectionV1
from ...domain.studios.providers import VideoRenderProvider
from .contextual_render import ContextualFFmpegProvider
from .hyperframes_projection import project_creative_document
from .media_probe import MEDIA_PROBE_PROVIDERS

NATURAL_SOUND_PURPOSE = "natural-sound-candidate"
LICENSED_MUSIC_PURPOSE = "licensed-music-candidate"
GOVERNED_SOUND_PURPOSES = frozenset({NATURAL_SOUND_PURPOSE, LICENSED_MUSIC_PURPOSE})


@dataclass(frozen=True)
class _UgcClipPlan:
    asset_id: str
    source_start_frame: int
    source_duration_frames: int
    duration_frames: int
    playback_rate: float
    original_audio_enabled: bool
    gain_db: float
    pan: float
    fade_in_frames: int
    fade_out_frames: int
    fit: str
    anchor: str


@dataclass(frozen=True)
class _UgcShapePlan:
    id: str
    x: int
    y: int
    width: int
    height: int
    color: str
    opacity: float
    radius: int


@dataclass(frozen=True)
class _UgcTextPlan:
    id: str
    role: str
    text: str
    x: int
    y: int
    width: int
    height: int
    font_size: int
    font_weight: str
    color: str
    opacity: float
    align: str
    line_height: float
    outline_color: str
    outline_width: int
    max_lines: int
    start_frame: int
    end_frame: int


@dataclass(frozen=True)
class _UgcSoundPlan:
    asset_id: str
    start_frame: int
    duration_frames: int
    source_start_microseconds: int
    source_duration_microseconds: int
    gain_db: float
    fade_in_frames: int
    fade_out_frames: int


@dataclass(frozen=True)
class _UgcRenderPlan:
    source_asset_ids: tuple[str, ...]
    clips: tuple[_UgcClipPlan, ...]
    sounds: tuple[_UgcSoundPlan, ...]
    frame_rate: Fraction
    duration_frames: int
    overlays: tuple[_UgcShapePlan | _UgcTextPlan, ...]
    rendered_layer_ids: tuple[str, ...]
    rendered_caption_track_ids: tuple[str, ...]
    warnings: tuple[str, ...]


@lru_cache(maxsize=8)
def _ffmpeg_version(executable: str, timeout_seconds: int) -> str:
    try:
        completed = subprocess.run(
            [executable, "-version"],
            capture_output=True,
            text=True,
            timeout=min(timeout_seconds, 30),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return (completed.stdout.splitlines() or ["unknown"])[0][:240]


def _frame_for_microseconds(value: int, frame_rate: Fraction) -> int:
    frames = Fraction(value, 1_000_000) * frame_rate
    return (2 * frames.numerator + frames.denominator) // (2 * frames.denominator)


def _microseconds_are_frame_aligned(value: int, frame_rate: Fraction) -> bool:
    frame = _frame_for_microseconds(value, frame_rate)
    exact = Fraction(value, 1_000_000) * frame_rate
    return abs(exact - frame) <= frame_rate / 1_000_000


def _seconds(value: int, frame_rate: Fraction) -> str:
    duration = Fraction(value, 1) / frame_rate
    return f"{float(duration):.12f}"


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


class HyperFramesCliVideoRenderProvider:
    name = "hyperframes.cli"

    def __init__(self, node_path: str, cli_path: str, timeout_seconds: int) -> None:
        self.node_path = node_path
        self.cli_path = Path(cli_path).resolve()
        self.timeout_seconds = timeout_seconds

    @property
    def version(self) -> str:
        package_json = self.cli_path.parent.parent / "package.json"
        try:
            return str(json.loads(package_json.read_text(encoding="utf-8"))["version"])
        except (OSError, KeyError, json.JSONDecodeError):
            return "unknown"

    def _run(self, args: list[str], cwd: Path, is_cancelled, started: float, *, entrypoint: Path | None = None) -> str:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(
                [self.node_path, str(entrypoint or self.cli_path), *args],
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                shell=False,
                creationflags=creation_flags,
            )
            while process.poll() is None:
                if is_cancelled():
                    _stop_process(process)
                    raise InterruptedError("video_render_cancelled")
                if time.monotonic() - started > self.timeout_seconds:
                    _stop_process(process)
                    raise TimeoutError("hyperframes_render_timeout")
                time.sleep(0.25)
            output.seek(0)
            text = output.read(2_000_000).decode("utf-8", errors="replace")
            if process.returncode != 0:
                # HyperFrames can emit a large preflight JSON before a final
                # CLI error. Preserve both ends so the actual cause is not
                # displaced by measurement output in persisted job errors.
                diagnostic = text if len(text) <= 4000 else text[:2000] + "\n...\n" + text[-2000:]
                raise ValueError(f"hyperframes_command_failed:{diagnostic}")
            return text

    def render(
        self,
        document: CreativeDocumentV1,
        request: VideoRenderRequestV1,
        assets: dict[str, Path],
        destination: Path,
        progress,
        is_cancelled,
        *,
        motion_projection: MotionGraphProjectionV1 | None = None,
        automatic_draft: bool = False,
    ) -> VideoRenderEncodeResultV1:
        if request.output.format == "mp4" and request.output.video_codec != "h264":
            raise ValueError("hyperframes_mp4_requires_h264")
        if request.output.format == "webm" and request.output.video_codec != "vp9":
            raise ValueError("hyperframes_webm_requires_vp9")
        if request.output.format == "mp4" and request.output.audio_codec not in {"aac", "none"}:
            raise ValueError("hyperframes_mp4_audio_codec_invalid")
        if request.output.format == "webm" and request.output.audio_codec not in {"opus", "none"}:
            raise ValueError("hyperframes_webm_audio_codec_invalid")
        started = time.monotonic()
        renderer_checks = {}
        with tempfile.TemporaryDirectory(prefix="clicko-hyperframes-") as temporary:
            project = Path(temporary)
            asset_dir = project / "assets"
            asset_dir.mkdir()
            manifest: dict[str, str] = {}
            for asset_id, source in assets.items():
                suffix = source.suffix.lower()
                if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
                    suffix = ".bin"
                filename = f"{uuid4().hex}{suffix}"
                shutil.copyfile(source, asset_dir / filename)
                manifest[asset_id] = f"./assets/{filename}"
            projected, projection_warnings = project_creative_document(
                document,
                request,
                manifest,
                motion_projection,
                automatic_draft=automatic_draft,
            )
            (project / "index.html").write_text(projected, encoding="utf-8")
            if automatic_draft:
                browser_path = self._run(["browser", "path"], project, is_cancelled, started).strip().splitlines()[-1]
                if not Path(browser_path).is_file():
                    raise ValueError("hyperframes_browser_path_invalid")
                check_output = self._run(
                    [str(self.cli_path), browser_path, str(project)],
                    project,
                    is_cancelled,
                    started,
                    entrypoint=Path(__file__).with_name("editorial_preflight.cjs"),
                )
                renderer_checks = json.loads(check_output)
            progress(12)
            lint_output = self._run(["lint", ".", "--json"], project, is_cancelled, started)
            json_start, json_end = lint_output.find("{"), lint_output.rfind("}")
            if json_start < 0 or json_end < json_start:
                raise ValueError("hyperframes_lint_invalid_json")
            lint = json.loads(lint_output[json_start : json_end + 1])
            if int(lint.get("errorCount", 0)) or int(lint.get("warningCount", 0)):
                raise ValueError(f"hyperframes_lint_failed:{json.dumps(lint, ensure_ascii=True)[:4000]}")
            progress(24)
            fps = str(request.output.fps).rstrip("0").rstrip(".")
            self._run(
                [
                    "render",
                    "-c",
                    "index.html",
                    "--fps",
                    fps,
                    "--quality",
                    request.output.quality,
                    "--format",
                    request.output.format,
                    "--workers",
                    "1",
                    "--no-browser-gpu",
                    "--quiet",
                    "-o",
                    str(destination),
                ],
                project,
                is_cancelled,
                started,
            )
            if not destination.is_file() or destination.stat().st_size <= 0:
                raise ValueError("hyperframes_render_output_missing")
            progress(84)
            probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(
                destination,
                asset_id="render-pending",
                checksum_sha256=None,
            )
        if not probe.video_streams:
            raise ValueError("hyperframes_render_video_stream_missing")
        stream = probe.video_streams[0]
        output_fps = stream.frame_rate.numerator / stream.frame_rate.denominator
        return VideoRenderEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            renderer_checks=renderer_checks,
            width=stream.width,
            height=stream.height,
            duration_ms=max(1, round(probe.duration_microseconds / 1000)),
            fps=output_fps,
            video_codec=stream.codec,
            audio_codec=probe.audio_streams[0].codec if probe.audio_streams else None,
            render_duration_ms=round((time.monotonic() - started) * 1000),
            frames_rendered=max(1, round(probe.duration_microseconds / 1_000_000 * output_fps)),
            warnings=projection_warnings,
        )


class FFmpegUgcVideoRenderProvider:
    """Render the bounded multi-source UGC timeline supported by the editor.

    It fails closed instead of silently flattening unsupported tracks, effects,
    transforms, or montage edits. The supported composition subset is typed and
    text is materialized through files so user content never becomes FFmpeg syntax.
    """

    name = "builtin.ffmpeg-ugc-v1"
    _max_clips = 128
    _max_caption_cues = 500
    _max_visible_layers = 16
    _max_text_characters = 100_000

    def __init__(
        self,
        executable: str,
        timeout_seconds: int,
        font_path: str | None = None,
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.font_path = Path(font_path).expanduser().resolve() if font_path else None

    @property
    def version(self) -> str:
        return _ffmpeg_version(self.executable, self.timeout_seconds)

    @staticmethod
    def _validate_snapshot(document: CreativeDocumentV1, request: VideoRenderRequestV1) -> None:
        if (
            document.workspace_id != request.workspace_id
            or document.document_id != request.document_id
            or document.revision != request.document_revision
            or document.version != request.document_version
        ):
            raise ValueError("ffmpeg_ugc_snapshot_mismatch")
        if document.content_type != "video" or document.composition.media_timeline is None:
            raise ValueError("ffmpeg_ugc_video_timeline_required")
        if len(document.composition.pages) != 1 or len(request.page_ids) != 1:
            raise ValueError("ffmpeg_ugc_single_page_required")
        page = document.composition.pages[0]
        if request.page_ids != [page.id]:
            raise ValueError("ffmpeg_ugc_single_page_required")
        output = request.output
        if (page.width, page.height) != (output.width, output.height):
            raise ValueError("ffmpeg_ugc_page_output_dimensions_mismatch")
        if output.width * 16 != output.height * 9:
            raise ValueError("ffmpeg_ugc_vertical_9_16_required")
        if output.format != "mp4" or output.video_codec != "h264" or output.audio_codec != "aac":
            raise ValueError("ffmpeg_ugc_mp4_h264_aac_required")
        timeline = document.composition.media_timeline
        timeline_fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
        if not math.isclose(output.fps, timeline_fps, rel_tol=1e-6, abs_tol=1e-6):
            raise ValueError("ffmpeg_ugc_output_fps_mismatch")
        if document.composition.tracks:
            raise ValueError("ffmpeg_ugc_legacy_composition_tracks_unsupported")

    @staticmethod
    def _layer_box(layer, page) -> tuple[int, int, int, int]:
        values = (layer.x, layer.y, layer.width, layer.height)
        if any(not math.isclose(value, round(value), abs_tol=1e-6) for value in values):
            raise ValueError(f"ffmpeg_ugc_fractional_layer_geometry_unsupported:{layer.id}")
        x, y, width, height = (round(value) for value in values)
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > page.width or y + height > page.height:
            raise ValueError(f"ffmpeg_ugc_layer_out_of_bounds:{layer.id}")
        if not math.isclose(layer.rotation, 0, abs_tol=1e-6):
            raise ValueError(f"ffmpeg_ugc_layer_rotation_unsupported:{layer.id}")
        return x, y, width, height

    @classmethod
    def _page_overlays(cls, page, duration_frames: int) -> tuple[list, list[str]]:
        visible_layers = sorted(
            (layer for layer in page.layers if layer.visible and layer.opacity > 0),
            key=lambda layer: layer.z_index,
        )
        if len(visible_layers) > cls._max_visible_layers:
            raise ValueError("ffmpeg_ugc_page_layer_count_unsupported")
        overlays: list[_UgcShapePlan | _UgcTextPlan] = []
        warnings: list[str] = []
        for layer in visible_layers:
            x, y, width, height = cls._layer_box(layer, page)
            if layer.kind == "shape":
                try:
                    properties = UgcShapeLayerPropertiesV1.model_validate(layer.properties)
                except ValueError as error:
                    raise ValueError(f"ffmpeg_ugc_shape_properties_unsupported:{layer.id}") from error
                overlays.append(
                    _UgcShapePlan(
                        id=layer.id,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        color=properties.fill,
                        opacity=layer.opacity,
                        radius=properties.radius,
                    )
                )
                if properties.radius:
                    warnings.append(f"ffmpeg_ugc_shape_radius_not_rendered:{layer.id}")
                continue
            if layer.kind == "text":
                try:
                    properties = UgcTextLayerPropertiesV1.model_validate(layer.properties)
                except ValueError as error:
                    raise ValueError(f"ffmpeg_ugc_text_properties_unsupported:{layer.id}") from error
                overlays.append(
                    _UgcTextPlan(
                        id=layer.id,
                        role="brand",
                        text=properties.text,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        font_size=properties.font_size,
                        font_weight=properties.font_weight,
                        color=properties.color,
                        opacity=layer.opacity,
                        align=properties.align,
                        line_height=properties.line_height,
                        outline_color="#000000",
                        outline_width=0,
                        max_lines=max(
                            1,
                            min(3, int(height / (properties.font_size * properties.line_height))),
                        ),
                        start_frame=0,
                        end_frame=duration_frames,
                    )
                )
                continue
            raise ValueError(f"ffmpeg_ugc_page_layer_unsupported:{layer.id}:{layer.kind}")
        return overlays, warnings

    @classmethod
    def _caption_overlays(cls, caption_tracks, page, duration_frames: int) -> tuple[list, list[str]]:
        if not caption_tracks:
            return [], []
        track = caption_tracks[0]
        if len(track.cues) > cls._max_caption_cues:
            raise ValueError("ffmpeg_ugc_caption_count_unsupported")
        cues = sorted(track.cues, key=lambda cue: cue.timeline.start_frame)
        overlays: list[_UgcTextPlan] = []
        warnings: list[str] = []
        previous_end = 0
        text_characters = 0
        for cue in cues:
            start_frame = cue.timeline.start_frame
            end_frame = start_frame + cue.timeline.duration_frames
            if start_frame < previous_end:
                raise ValueError("ffmpeg_ugc_overlapping_captions_unsupported")
            if end_frame > duration_frames:
                raise ValueError("ffmpeg_ugc_caption_out_of_bounds")
            style = CaptionRenderStyleV1.model_validate(cue.style)
            if style.font_asset_id:
                raise ValueError("custom_caption_font_requires_contextual_renderer")
            text_characters += len(cue.text)
            if text_characters > cls._max_text_characters:
                raise ValueError("ffmpeg_ugc_caption_text_limit_exceeded")
            x = round(page.width * 0.12)
            width = page.width - 2 * x
            y = round(page.height * 0.69)
            height = round(page.height * 0.14)
            overlays.append(
                _UgcTextPlan(
                    id=cue.id,
                    role="caption",
                    text=cue.text,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    font_size=style.font_size,
                    font_weight=style.font_weight,
                    color=style.color,
                    opacity=1,
                    align="center",
                    line_height=1.12,
                    outline_color=style.outline_color,
                    outline_width=style.outline_width,
                    max_lines=style.max_lines,
                    start_frame=start_frame,
                    end_frame=end_frame,
                )
            )
            if style.emphasis_color and "ffmpeg_ugc_caption_emphasis_not_rendered" not in warnings:
                warnings.append("ffmpeg_ugc_caption_emphasis_not_rendered")
            previous_end = end_frame
        return overlays, warnings

    @classmethod
    def _plan(
        cls,
        document: CreativeDocumentV1,
        request: VideoRenderRequestV1,
        assets: dict[str, Path],
    ) -> _UgcRenderPlan:
        cls._validate_snapshot(document, request)
        timeline = document.composition.media_timeline
        assert timeline is not None
        video_tracks = [track for track in timeline.tracks if track.kind == "video"]
        audio_tracks = [track for track in timeline.tracks if track.kind == "audio"]
        caption_tracks = [track for track in timeline.tracks if track.kind == "caption"]
        unsupported_tracks = [track for track in timeline.tracks if track.kind not in {"video", "audio", "caption"}]
        if unsupported_tracks:
            track = unsupported_tracks[0]
            raise ValueError(f"ffmpeg_ugc_track_unsupported:{track.id}:{track.kind}")
        if len(video_tracks) != 1:
            raise ValueError("ffmpeg_ugc_single_video_track_required")
        if len(audio_tracks) > 9:
            raise ValueError("ffmpeg_ugc_audio_track_count_unsupported")
        if len(caption_tracks) > 1:
            raise ValueError("ffmpeg_ugc_single_caption_track_required")

        video_track = video_tracks[0]
        video_clips = [clip for clip in video_track.clips if clip.enabled]
        video_asset_ids = {clip.asset_id for clip in video_clips}
        original_tracks = [
            track
            for track in audio_tracks
            if track.clips and all(clip.asset_id in video_asset_ids for clip in track.clips)
        ]
        if len(original_tracks) > 1:
            raise ValueError("ffmpeg_ugc_single_audio_track_required")
        audio_track = original_tracks[0] if original_tracks else None
        sound_tracks = [track for track in audio_tracks if track is not audio_track]
        if not video_clips or len(video_clips) > cls._max_clips:
            raise ValueError("ffmpeg_ugc_clip_count_unsupported")

        enabled_audio_clips = [clip for clip in audio_track.clips if clip.enabled] if audio_track else []
        audio_by_binding = {
            (
                clip.asset_id,
                clip.timeline.start_frame,
                clip.timeline.duration_frames,
                clip.source.start_microseconds if clip.source else None,
            ): clip
            for clip in enabled_audio_clips
        }
        if len(audio_by_binding) != len(enabled_audio_clips):
            raise ValueError("ffmpeg_ugc_duplicate_audio_binding")

        source_asset_ids = {clip.asset_id for clip in video_clips}
        document_asset_ids = {asset.id for asset in document.assets}
        if (
            set(request.asset_ids) != document_asset_ids
            or set(assets) != document_asset_ids
            or len(document_asset_ids) > 9
            or not source_asset_ids
            or not source_asset_ids <= document_asset_ids
            or len(source_asset_ids) > 8
        ):
            raise ValueError("ffmpeg_ugc_source_assets_invalid")
        narrative = document.composition.narrative or {}
        declared_source_ids = set(narrative.get("sourceAssetIds") or [])
        if narrative.get("sourceAssetId"):
            declared_source_ids.add(narrative["sourceAssetId"])
        source_references = [asset for asset in document.assets if asset.id in source_asset_ids]
        if (
            declared_source_ids != source_asset_ids
            or narrative.get("originalPreserved") is not True
            or any(reference.provenance.get("source") != "user-upload" for reference in source_references)
        ):
            raise ValueError("ffmpeg_ugc_original_source_required")
        if any(not assets[asset_id].is_file() for asset_id in source_asset_ids):
            raise ValueError("ffmpeg_ugc_source_asset_missing")

        frame_rate = Fraction(
            timeline.frame_rate.numerator,
            timeline.frame_rate.denominator,
        )
        sounds: list[_UgcSoundPlan] = []
        sound_asset_ids: set[str] = set()
        has_licensed_music = False
        for track in sound_tracks:
            for clip in track.clips:
                sound_asset_ids.add(clip.asset_id)
                ref = next((asset for asset in document.assets if asset.id == clip.asset_id), None)
                if (
                    not ref
                    or not ref.media_type.startswith("audio/")
                    or not ref.checksum
                    or ref.provenance.get("purpose") not in GOVERNED_SOUND_PURPOSES
                    or clip.asset_id in source_asset_ids
                    or not clip.source
                ):
                    raise ValueError("ffmpeg_ugc_sound_reference_invalid")
                if ref.provenance.get("purpose") == LICENSED_MUSIC_PURPOSE:
                    has_licensed_music = True
                    if ref.rights_status != "verified":
                        raise ValueError("ffmpeg_ugc_music_rights_required")
                if clip.effects or clip.keyframes or clip.transform or clip.pan != 0:
                    raise ValueError("ffmpeg_ugc_sound_effects_unsupported")
                if (
                    clip.timeline.start_frame + clip.timeline.duration_frames > timeline.duration_frames
                    or not _microseconds_are_frame_aligned(clip.source.duration_microseconds, frame_rate)
                    or _frame_for_microseconds(clip.source.duration_microseconds, frame_rate)
                    != clip.timeline.duration_frames
                    or clip.fade_in_frames + clip.fade_out_frames > clip.timeline.duration_frames
                    or not math.isfinite(clip.gain_db)
                ):
                    raise ValueError("ffmpeg_ugc_sound_range_invalid")
                if track.muted or not clip.enabled:
                    continue
                sounds.append(
                    _UgcSoundPlan(
                        asset_id=clip.asset_id,
                        start_frame=clip.timeline.start_frame,
                        duration_frames=clip.timeline.duration_frames,
                        source_start_microseconds=clip.source.start_microseconds,
                        source_duration_microseconds=clip.source.duration_microseconds,
                        gain_db=clip.gain_db,
                        fade_in_frames=clip.fade_in_frames,
                        fade_out_frames=clip.fade_out_frames,
                    )
                )
        if len(sounds) > 32 or not sound_asset_ids <= document_asset_ids:
            raise ValueError("ffmpeg_ugc_sound_assets_invalid")
        # Detached sound references remain in document history after a trim.
        # They must still be valid audio candidates, but never enter the mix.
        for ref in document.assets:
            if ref.id not in source_asset_ids and (
                not ref.media_type.startswith("audio/")
                or not ref.checksum
                or ref.provenance.get("purpose") not in GOVERNED_SOUND_PURPOSES
            ):
                raise ValueError("ffmpeg_ugc_sound_reference_invalid")
        if has_licensed_music and narrative.get("musicPolicy") != "licensed-with-rights":
            raise ValueError("ffmpeg_ugc_music_policy_required")
        cursor = 0
        clip_plan: list[_UgcClipPlan] = []
        matched_audio_ids: set[str] = set()
        for video_clip in video_clips:
            if video_clip.timeline.start_frame != cursor:
                raise ValueError("ffmpeg_ugc_non_contiguous_video_timeline")
            audio_clip = audio_by_binding.get(
                (
                    video_clip.asset_id,
                    video_clip.timeline.start_frame,
                    video_clip.timeline.duration_frames,
                    video_clip.source.start_microseconds if video_clip.source else None,
                )
            )
            if audio_clip:
                matched_audio_ids.add(audio_clip.id)
            if video_clip.source is None or (audio_clip is not None and audio_clip.source is None):
                raise ValueError("ffmpeg_ugc_source_range_required")
            if video_clip.effects or video_clip.keyframes:
                raise ValueError("ffmpeg_ugc_video_effects_unsupported")
            transform = video_clip.transform or {}
            if set(transform) - {"fit", "anchor", "x", "y", "scale", "rotation", "crop"}:
                raise ValueError("ffmpeg_ugc_video_transform_unsupported")
            fit = transform.get("fit", "cover")
            anchor = transform.get("anchor", "center")
            if fit not in {"cover", "contain", "fill"} or anchor not in {
                "center",
                "top",
                "bottom",
                "left",
                "right",
                "top-left",
                "top-right",
                "bottom-left",
                "bottom-right",
            }:
                raise ValueError("ffmpeg_ugc_video_transform_unsupported")
            if (
                transform.get("x", 0) != 0
                or transform.get("y", 0) != 0
                or transform.get("scale", 1) != 1
                or transform.get("rotation", 0) != 0
                or any(float(value) != 0 for value in (transform.get("crop") or {}).values())
            ):
                raise ValueError("ffmpeg_ugc_video_transform_unsupported")
            if audio_clip and (audio_clip.effects or audio_clip.keyframes or audio_clip.transform):
                raise ValueError("ffmpeg_ugc_audio_effects_unsupported")
            if audio_clip and (
                not math.isfinite(audio_clip.gain_db)
                or not math.isfinite(audio_clip.pan)
                or audio_clip.fade_in_frames + audio_clip.fade_out_frames > audio_clip.timeline.duration_frames
            ):
                raise ValueError("ffmpeg_ugc_audio_effects_unsupported")
            if audio_clip and (
                audio_clip.asset_id != video_clip.asset_id
                or audio_clip.timeline != video_clip.timeline
                or audio_clip.source != video_clip.source
                or not math.isclose(
                    audio_clip.playback_rate,
                    video_clip.playback_rate,
                    rel_tol=0,
                    abs_tol=1e-9,
                )
            ):
                raise ValueError("ffmpeg_ugc_audio_video_clip_mismatch")

            source_start_frame = _frame_for_microseconds(
                video_clip.source.start_microseconds,
                frame_rate,
            )
            source_duration_frames = _frame_for_microseconds(
                video_clip.source.duration_microseconds,
                frame_rate,
            )
            if (
                not _microseconds_are_frame_aligned(
                    video_clip.source.start_microseconds,
                    frame_rate,
                )
                or not _microseconds_are_frame_aligned(
                    video_clip.source.duration_microseconds,
                    frame_rate,
                )
                or not math.isclose(
                    source_duration_frames,
                    video_clip.timeline.duration_frames * video_clip.playback_rate,
                    rel_tol=0,
                    abs_tol=0.5,
                )
            ):
                raise ValueError("ffmpeg_ugc_source_duration_not_frame_aligned")
            clip_plan.append(
                _UgcClipPlan(
                    asset_id=video_clip.asset_id,
                    source_start_frame=source_start_frame,
                    source_duration_frames=source_duration_frames,
                    duration_frames=video_clip.timeline.duration_frames,
                    playback_rate=video_clip.playback_rate,
                    original_audio_enabled=bool(
                        audio_clip is not None and audio_track is not None and not audio_track.muted
                    ),
                    gain_db=audio_clip.gain_db if audio_clip else 0,
                    pan=audio_clip.pan if audio_clip else 0,
                    fade_in_frames=audio_clip.fade_in_frames if audio_clip else 0,
                    fade_out_frames=audio_clip.fade_out_frames if audio_clip else 0,
                    fit=fit,
                    anchor=anchor,
                )
            )
            cursor += video_clip.timeline.duration_frames
        if matched_audio_ids != {clip.id for clip in enabled_audio_clips}:
            raise ValueError("ffmpeg_ugc_audio_video_clip_mismatch")
        if cursor != timeline.duration_frames:
            raise ValueError("ffmpeg_ugc_non_contiguous_video_timeline")
        for asset_id in source_asset_ids:
            source_ranges = sorted(
                (
                    clip.source_start_frame,
                    clip.source_start_frame + clip.source_duration_frames,
                )
                for clip in clip_plan
                if clip.asset_id == asset_id
            )
            if any(
                current_start < previous_end
                for (_, previous_end), (current_start, _) in zip(
                    source_ranges,
                    source_ranges[1:],
                    strict=False,
                )
            ):
                raise ValueError("ffmpeg_ugc_overlapping_source_ranges_unsupported")

        page = document.composition.pages[0]
        page_overlays, warnings = cls._page_overlays(page, timeline.duration_frames)
        caption_overlays, caption_warnings = cls._caption_overlays(
            caption_tracks,
            page,
            timeline.duration_frames,
        )
        warnings.extend(caption_warnings)
        if sounds and not has_licensed_music:
            warnings.append("ffmpeg_ugc_natural_sound_review_pending")
        if has_licensed_music:
            warnings.append("ffmpeg_ugc_licensed_music_mixed")
        if not any(clip.original_audio_enabled for clip in clip_plan):
            warnings.append("ffmpeg_ugc_original_audio_muted")
        if not video_track.muted:
            warnings.append(f"ffmpeg_ugc_embedded_audio_suppressed:{video_track.id}")
        expected_duration_ms = round(float(Fraction(timeline.duration_frames, 1) / frame_rate) * 1000)
        if page.duration_ms is not None and abs(page.duration_ms - expected_duration_ms) > 1:
            warnings.append(f"ffmpeg_ugc_page_duration_ignored:{page.id}")
        return _UgcRenderPlan(
            source_asset_ids=tuple(sorted(source_asset_ids)),
            clips=tuple(clip_plan),
            sounds=tuple(sounds),
            frame_rate=frame_rate,
            duration_frames=timeline.duration_frames,
            overlays=tuple([*page_overlays, *caption_overlays]),
            rendered_layer_ids=tuple(layer.id for layer in page.layers if layer.visible and layer.opacity > 0),
            rendered_caption_track_ids=tuple(track.id for track in caption_tracks if track.cues),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _validate_source(plan: _UgcRenderPlan, asset_id: str, source_probe) -> None:
        if len(source_probe.video_streams) != 1:
            raise ValueError("ffmpeg_ugc_single_source_video_stream_required")
        clips = [clip for clip in plan.clips if clip.asset_id == asset_id]
        if len(source_probe.audio_streams) > 1 or (
            any(clip.original_audio_enabled for clip in clips) and not source_probe.audio_streams
        ):
            raise ValueError("ffmpeg_ugc_single_source_audio_stream_required")
        stream = source_probe.video_streams[0]
        source_fps = stream.frame_rate.numerator / stream.frame_rate.denominator
        if not math.isclose(source_fps, float(plan.frame_rate), rel_tol=1e-6, abs_tol=1e-6):
            raise ValueError("ffmpeg_ugc_source_fps_mismatch")
        source_duration = stream.duration_microseconds or source_probe.duration_microseconds
        available_frames = _frame_for_microseconds(source_duration, plan.frame_rate)
        required_frames = max(clip.source_start_frame + clip.source_duration_frames for clip in clips)
        if required_frames > available_frames:
            raise ValueError("ffmpeg_ugc_source_range_out_of_bounds")

    @staticmethod
    def _normalized_overlay_text(overlay: _UgcTextPlan) -> str:
        normalized = unicodedata.normalize("NFC", overlay.text).replace("\r\n", "\n").replace("\r", "\n")
        cleaned = "".join(
            character
            for character in normalized
            if character in {"\n", "\t"} or unicodedata.category(character) != "Cc"
        )
        cleaned = " ".join(cleaned.replace("\t", " ").split())
        if not cleaned:
            raise ValueError(f"ffmpeg_ugc_overlay_text_empty:{overlay.id}")
        approximate_character_width = max(1, round(overlay.font_size * 0.56))
        characters_per_line = max(4, overlay.width // approximate_character_width)
        wrapper = textwrap.TextWrapper(
            width=characters_per_line,
            break_long_words=True,
            break_on_hyphens=False,
            max_lines=overlay.max_lines,
            placeholder="…",
        )
        return "\n".join(wrapper.wrap(cleaned))

    @classmethod
    def _materialize_overlay_texts(
        cls,
        plan: _UgcRenderPlan,
        directory: Path,
    ) -> dict[int, str]:
        filenames: dict[int, str] = {}
        for index, overlay in enumerate(plan.overlays):
            if not isinstance(overlay, _UgcTextPlan):
                continue
            filename = f"overlay-{index:04d}.txt"
            (directory / filename).write_text(
                cls._normalized_overlay_text(overlay),
                encoding="utf-8",
            )
            filenames[index] = filename
        return filenames

    def _materialize_font(self, directory: Path) -> tuple[str, str | None]:
        if self.font_path is not None:
            candidates = [(self.font_path, None)]
        else:
            candidates = [
                (
                    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
                    None,
                ),
                (
                    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                    None,
                ),
                (
                    Path("C:/Windows/Fonts/arialbd.ttf"),
                    "ffmpeg_ugc_font_substituted:Arial-Bold",
                ),
            ]
        for source, warning in candidates:
            if not source.is_file():
                continue
            if source.stat().st_size <= 0 or source.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("ffmpeg_ugc_font_file_invalid")
            filename = "ugc-font.ttf"
            shutil.copyfile(source, directory / filename)
            return filename, warning
        raise ValueError("ffmpeg_ugc_font_unavailable")

    @staticmethod
    def _ffmpeg_color(value: str, opacity: float) -> str:
        return f"0x{value[1:].lower()}@{opacity:.4f}"

    @classmethod
    def _filter_graph(
        cls,
        plan: _UgcRenderPlan,
        width: int,
        height: int,
        text_files: dict[int, str] | None = None,
        font_filename: str = "ugc-font.ttf",
    ) -> str:
        frame_rate = f"{plan.frame_rate.numerator}/{plan.frame_rate.denominator}"
        chains: list[str] = []
        concat_inputs: list[str] = []
        source_assets = list(plan.source_asset_ids)
        for index, clip in enumerate(plan.clips):
            input_index = source_assets.index(clip.asset_id)
            source_end = clip.source_start_frame + clip.source_duration_frames
            audio_start = _seconds(clip.source_start_frame, plan.frame_rate)
            source_audio_duration = _seconds(clip.source_duration_frames, plan.frame_rate)
            output_audio_duration = _seconds(clip.duration_frames, plan.frame_rate)
            if clip.fit == "cover":
                positioning = {
                    "center": "x=(iw-ow)/2:y=(ih-oh)/2",
                    "top": "x=(iw-ow)/2:y=0",
                    "bottom": "x=(iw-ow)/2:y=ih-oh",
                    "left": "x=0:y=(ih-oh)/2",
                    "right": "x=iw-ow:y=(ih-oh)/2",
                    "top-left": "x=0:y=0",
                    "top-right": "x=iw-ow:y=0",
                    "bottom-left": "x=0:y=ih-oh",
                    "bottom-right": "x=iw-ow:y=ih-oh",
                }[clip.anchor]
                visual_fit = (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:{positioning}"
                )
            elif clip.fit == "contain":
                positioning = {
                    "center": "x=(ow-iw)/2:y=(oh-ih)/2",
                    "top": "x=(ow-iw)/2:y=0",
                    "bottom": "x=(ow-iw)/2:y=oh-ih",
                    "left": "x=0:y=(oh-ih)/2",
                    "right": "x=ow-iw:y=(oh-ih)/2",
                    "top-left": "x=0:y=0",
                    "top-right": "x=ow-iw:y=0",
                    "bottom-left": "x=0:y=oh-ih",
                    "bottom-right": "x=ow-iw:y=oh-ih",
                }[clip.anchor]
                visual_fit = (
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:{positioning}:color=black"
                )
            else:
                visual_fit = f"scale={width}:{height}"
            chains.append(
                f"[{input_index}:v:0]trim=start_frame={clip.source_start_frame}:end_frame={source_end},"
                f"setpts=(PTS-STARTPTS)/{clip.playback_rate:.8f},{visual_fit},"
                f"setsar=1,fps={frame_rate},format=yuv420p[v{index}]"
            )
            if not clip.original_audio_enabled:
                # Do not read the source audio at all. A silent AAC placeholder
                # preserves the existing output stream contract for private
                # drafts; it is not evidence of approved natural sound.
                chains.append(
                    f"anullsrc=r=48000:cl=stereo,atrim=duration={output_audio_duration},asetpts=PTS-STARTPTS[a{index}]"
                )
            else:
                audio_chain = (
                    f"[{input_index}:a:0]atrim=start={audio_start}:duration={source_audio_duration},"
                    f"asetpts=PTS-STARTPTS,aresample=48000,atempo={clip.playback_rate:.8f},"
                    f"atrim=duration={output_audio_duration},volume={clip.gain_db:.6f}dB"
                )
                if clip.pan:
                    left = 1 if clip.pan <= 0 else 1 - clip.pan
                    right = 1 if clip.pan >= 0 else 1 + clip.pan
                    audio_chain += f",pan=stereo|c0={left:.6f}*c0|c1={right:.6f}*c1"
                if clip.fade_in_frames:
                    audio_chain += f",afade=t=in:st=0:d={_seconds(clip.fade_in_frames, plan.frame_rate)}"
                if clip.fade_out_frames:
                    audio_chain += (
                        f",afade=t=out:st={_seconds(clip.duration_frames - clip.fade_out_frames, plan.frame_rate)}"
                        f":d={_seconds(clip.fade_out_frames, plan.frame_rate)}"
                    )
                chains.append(f"{audio_chain}[a{index}]")
            concat_inputs.extend([f"[v{index}]", f"[a{index}]"])
        concat_video_label = "vbase" if plan.overlays else "vout"
        concat_audio_label = "abase" if plan.sounds else "aout"
        chains.append(
            f"{''.join(concat_inputs)}concat=n={len(plan.clips)}:v=1:a=1[{concat_video_label}][{concat_audio_label}]"
        )
        sound_assets = sorted({sound.asset_id for sound in plan.sounds})
        mix_inputs = ["[abase]"]
        for index, sound in enumerate(plan.sounds):
            input_index = sound_assets.index(sound.asset_id) + len(source_assets)
            frames = sound.duration_frames
            duration = _seconds(frames, plan.frame_rate)
            delay_samples = round(Fraction(sound.start_frame * 48000, 1) / plan.frame_rate)
            chain = (
                f"[{input_index}:a:0]atrim=start={sound.source_start_microseconds / 1_000_000:.6f}:"
                f"duration={duration},asetpts=PTS-STARTPTS,aresample=48000,"
                f"aformat=channel_layouts=stereo,volume={sound.gain_db:.6f}dB"
            )
            if sound.fade_in_frames:
                chain += f",afade=t=in:st=0:d={_seconds(sound.fade_in_frames, plan.frame_rate)}"
            if sound.fade_out_frames:
                chain += (
                    f",afade=t=out:st={_seconds(frames - sound.fade_out_frames, plan.frame_rate)}"
                    f":d={_seconds(sound.fade_out_frames, plan.frame_rate)}"
                )
            chain += f",adelay={delay_samples}S:all=1[sound{index}]"
            chains.append(chain)
            mix_inputs.append(f"[sound{index}]")
        if plan.sounds:
            chains.append(
                f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:"
                "dropout_transition=0:normalize=0[aout]"
            )
        files = text_files or {
            index: f"overlay-{index:04d}.txt"
            for index, overlay in enumerate(plan.overlays)
            if isinstance(overlay, _UgcTextPlan)
        }
        input_label = concat_video_label
        for index, overlay in enumerate(plan.overlays):
            output_label = "vout" if index == len(plan.overlays) - 1 else f"vfx{index}"
            if isinstance(overlay, _UgcShapePlan):
                chains.append(
                    f"[{input_label}]drawbox=x={overlay.x}:y={overlay.y}:"
                    f"w={overlay.width}:h={overlay.height}:"
                    f"color={cls._ffmpeg_color(overlay.color, overlay.opacity)}:t=fill"
                    f"[{output_label}]"
                )
            else:
                if overlay.align == "left":
                    text_x = str(overlay.x)
                elif overlay.align == "right":
                    text_x = f"{overlay.x}+{overlay.width}-text_w"
                else:
                    text_x = f"{overlay.x}+({overlay.width}-text_w)/2"
                text_y = f"{overlay.y}+({overlay.height}-text_h)/2"
                line_spacing = max(0, round(overlay.font_size * (overlay.line_height - 1)))
                shadow = ":shadowcolor=0x000000@0.7000:shadowx=2:shadowy=2" if overlay.role == "caption" else ""
                chains.append(
                    f"[{input_label}]drawtext=fontfile='{font_filename}':textfile='{files[index]}':"
                    f"expansion=none:fontcolor={cls._ffmpeg_color(overlay.color, overlay.opacity)}:"
                    f"fontsize={overlay.font_size}:x={text_x}:y={text_y}:"
                    f"line_spacing={line_spacing}:borderw={overlay.outline_width}:"
                    f"bordercolor={cls._ffmpeg_color(overlay.outline_color, 0.9)}{shadow}:"
                    f"enable='between(n,{overlay.start_frame},{overlay.end_frame - 1})'"
                    f"[{output_label}]"
                )
            input_label = output_label
        return ";".join(chains)

    def _run(
        self,
        command: list[str],
        destination: Path,
        is_cancelled,
        started: float,
        cwd: Path | None = None,
    ) -> None:
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with tempfile.TemporaryFile() as error_log:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=error_log,
                shell=False,
                cwd=cwd,
                creationflags=creation_flags,
            )
            while process.poll() is None:
                if is_cancelled():
                    _stop_process(process)
                    destination.unlink(missing_ok=True)
                    raise InterruptedError("ffmpeg_ugc_render_cancelled")
                if time.monotonic() - started > self.timeout_seconds:
                    _stop_process(process)
                    destination.unlink(missing_ok=True)
                    raise TimeoutError("ffmpeg_ugc_render_timeout")
                time.sleep(0.2)
            if process.returncode != 0:
                error_log.seek(0)
                message = error_log.read(2_000_000).decode("utf-8", errors="replace")
                destination.unlink(missing_ok=True)
                raise ValueError(f"ffmpeg_ugc_render_failed:{message[-4000:]}")

    def render(
        self,
        document: CreativeDocumentV1,
        request: VideoRenderRequestV1,
        assets: dict[str, Path],
        destination: Path,
        progress,
        is_cancelled,
        *,
        motion_projection: MotionGraphProjectionV1 | None = None,
    ) -> VideoRenderEncodeResultV1:
        if motion_projection is not None:
            raise ValueError("ffmpeg_ugc_motion_projection_unsupported")
        if is_cancelled():
            raise InterruptedError("ffmpeg_ugc_render_cancelled")
        destination = destination.resolve()
        plan = self._plan(document, request, assets)
        probe_provider = MEDIA_PROBE_PROVIDERS.get("builtin.ffprobe")
        if probe_provider is None:
            raise ValueError("ffmpeg_ugc_probe_provider_unavailable")
        started = time.monotonic()
        progress(8)
        for asset_id in plan.source_asset_ids:
            source_probe = probe_provider.probe(
                assets[asset_id],
                asset_id=asset_id,
                checksum_sha256=None,
            )
            self._validate_source(plan, asset_id, source_probe)
        sound_assets = sorted({sound.asset_id for sound in plan.sounds})
        for asset_id in sound_assets:
            sound_probe = probe_provider.probe(assets[asset_id], asset_id=asset_id, checksum_sha256=None)
            if len(sound_probe.audio_streams) != 1 or sound_probe.video_streams:
                raise ValueError("ffmpeg_ugc_sound_stream_invalid")
            for sound in (item for item in plan.sounds if item.asset_id == asset_id):
                required_us = sound.source_start_microseconds + sound.source_duration_microseconds
                if required_us > sound_probe.duration_microseconds:
                    raise ValueError("ffmpeg_ugc_sound_source_out_of_bounds")
        if is_cancelled():
            raise InterruptedError("ffmpeg_ugc_render_cancelled")
        if time.monotonic() - started > self.timeout_seconds:
            raise TimeoutError("ffmpeg_ugc_render_timeout")
        progress(18)
        quality_crf = {"draft": "28", "standard": "23", "high": "18"}[request.output.quality]
        frame_rate = f"{plan.frame_rate.numerator}/{plan.frame_rate.denominator}"
        duration = _seconds(plan.duration_frames, plan.frame_rate)
        render_warnings = list(plan.warnings)
        with tempfile.TemporaryDirectory(prefix="clicko-ffmpeg-ugc-") as temporary:
            working_directory = Path(temporary)
            text_files = self._materialize_overlay_texts(plan, working_directory)
            font_filename = "ugc-font.ttf"
            if text_files:
                font_filename, font_warning = self._materialize_font(working_directory)
                if font_warning:
                    render_warnings.append(font_warning)
            filter_graph = self._filter_graph(
                plan,
                request.output.width,
                request.output.height,
                text_files,
                font_filename,
            )
            command = [
                self.executable,
                "-hide_banner",
                "-nostdin",
                "-loglevel",
                "error",
                "-y",
                "-filter_complex_threads",
                "1",
                *[
                    argument
                    for asset_id in plan.source_asset_ids
                    for argument in ("-threads", "2", "-i", str(assets[asset_id].resolve()))
                ],
                *[argument for asset_id in sound_assets for argument in ("-i", str(assets[asset_id].resolve()))],
                "-filter_complex",
                filter_graph,
                "-map",
                "[vout]",
                "-map",
                "[aout]",
                "-c:v",
                "libx264",
                "-threads",
                "2",
                "-preset",
                "veryfast",
                "-crf",
                quality_crf,
                "-pix_fmt",
                "yuv420p",
                "-r",
                frame_rate,
                "-fps_mode",
                "cfr",
                "-frames:v",
                str(plan.duration_frames),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-t",
                duration,
                "-movflags",
                "+faststart",
                "-sn",
                "-dn",
                str(destination.resolve()),
            ]
            self._run(
                command,
                destination,
                is_cancelled,
                started,
                cwd=working_directory,
            )
        if not destination.is_file() or destination.stat().st_size <= 0:
            raise ValueError("ffmpeg_ugc_render_output_missing")
        progress(82)
        output_probe = probe_provider.probe(
            destination,
            asset_id="render-pending",
            checksum_sha256=None,
        )
        if len(output_probe.video_streams) != 1 or len(output_probe.audio_streams) != 1:
            destination.unlink(missing_ok=True)
            raise ValueError("ffmpeg_ugc_render_streams_invalid")
        video_stream = output_probe.video_streams[0]
        audio_stream = output_probe.audio_streams[0]
        output_fps = video_stream.frame_rate.numerator / video_stream.frame_rate.denominator
        expected_duration = Fraction(plan.duration_frames, 1) / plan.frame_rate
        actual_duration = Fraction(output_probe.duration_microseconds, 1_000_000)
        duration_tolerance = Fraction(plan.frame_rate.denominator, plan.frame_rate.numerator) * 2
        if (
            (video_stream.width, video_stream.height) != (request.output.width, request.output.height)
            or video_stream.codec != "h264"
            or audio_stream.codec != "aac"
            or not math.isclose(output_fps, float(plan.frame_rate), rel_tol=1e-6, abs_tol=1e-6)
            or abs(actual_duration - expected_duration) > duration_tolerance
        ):
            destination.unlink(missing_ok=True)
            raise ValueError("ffmpeg_ugc_render_probe_mismatch")
        return VideoRenderEncodeResultV1(
            provider=self.name,
            provider_version=self.version,
            width=video_stream.width,
            height=video_stream.height,
            duration_ms=max(1, round(output_probe.duration_microseconds / 1000)),
            fps=output_fps,
            video_codec=video_stream.codec,
            audio_codec=audio_stream.codec,
            render_duration_ms=round((time.monotonic() - started) * 1000),
            frames_rendered=plan.duration_frames,
            rendered_layer_ids=list(plan.rendered_layer_ids),
            rendered_caption_track_ids=list(plan.rendered_caption_track_ids),
            warnings=render_warnings,
        )


settings = get_settings()
VIDEO_RENDER_PROVIDERS: dict[str, VideoRenderProvider] = {
    ContextualFFmpegProvider.name: ContextualFFmpegProvider(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
        settings.studio_ugc_font_path,
    ),
    FFmpegUgcVideoRenderProvider.name: FFmpegUgcVideoRenderProvider(
        settings.ffmpeg_path,
        settings.ffmpeg_timeout_seconds,
        settings.studio_ugc_font_path,
    ),
}
if settings.hyperframes_enabled and settings.hyperframes_cli_path:
    VIDEO_RENDER_PROVIDERS[HyperFramesCliVideoRenderProvider.name] = HyperFramesCliVideoRenderProvider(
        settings.hyperframes_node_path,
        settings.hyperframes_cli_path,
        settings.hyperframes_timeout_seconds,
    )
    from .contextual_motion_render import ContextualMotionRenderProvider

    VIDEO_RENDER_PROVIDERS[ContextualMotionRenderProvider.name] = ContextualMotionRenderProvider(
        VIDEO_RENDER_PROVIDERS[HyperFramesCliVideoRenderProvider.name],
        VIDEO_RENDER_PROVIDERS[ContextualFFmpegProvider.name],
    )
if settings.motion_canvas_enabled:
    from .motion_canvas_render import MotionCanvasContextualRenderProvider, MotionCanvasGraphicsProvider

    VIDEO_RENDER_PROVIDERS[MotionCanvasContextualRenderProvider.name] = MotionCanvasContextualRenderProvider(
        MotionCanvasGraphicsProvider(
            settings.motion_canvas_node_path,
            settings.ffmpeg_path,
            settings.motion_canvas_timeout_seconds,
        ),
        VIDEO_RENDER_PROVIDERS[ContextualFFmpegProvider.name],
    )
if settings.remotion_enabled:
    from .remotion_render import RemotionContextualRenderProvider, RemotionGraphicsProvider

    VIDEO_RENDER_PROVIDERS[RemotionContextualRenderProvider.name] = RemotionContextualRenderProvider(
        RemotionGraphicsProvider(
            settings.remotion_node_path,
            settings.ffmpeg_path,
            settings.remotion_timeout_seconds,
        ),
        VIDEO_RENDER_PROVIDERS[ContextualFFmpegProvider.name],
    )

if settings.remotion_native_enabled:
    from .remotion_render import RemotionNativeContextualRenderProvider, RemotionNativeGraphicsProvider

    VIDEO_RENDER_PROVIDERS[RemotionNativeContextualRenderProvider.name] = RemotionNativeContextualRenderProvider(
        RemotionNativeGraphicsProvider(settings.remotion_node_path, settings.ffmpeg_path, settings.remotion_timeout_seconds),
        VIDEO_RENDER_PROVIDERS[ContextualFFmpegProvider.name],
    )
