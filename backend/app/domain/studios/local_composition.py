"""Executable local subset of existing CreativeLayerV1; never code or renderer expressions."""

from typing import Literal

from pydantic import Field, model_validator

from .contracts import CreativeCompositionV1, StudioContract
from .image_edit import NormalizedRegionV1
from .timeline_editor import MotionKey


class LocalLayerStyle(StudioContract):
    schema_version: Literal["studio.local-layer.v1"] = "studio.local-layer.v1"
    text: str = Field(default="", max_length=1000)
    font_family: Literal["system", "Liberation Sans"] = "system"
    font_size: int = Field(default=48, ge=8, le=240)
    font_weight: Literal[400, 700] = 700
    text_reveal: Literal["all", "words"] = "all"
    word_stagger_frames: int = Field(default=6, ge=1, le=120)
    align: Literal["left", "center", "right"] = "left"
    color: str = Field(default="#FFFFFF", pattern=r"^#[0-9a-fA-F]{6}$")
    fill: str = Field(default="#FF7F50", pattern=r"^#[0-9a-fA-F]{6}$")
    gradient_end: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    shape: Literal["rectangle", "ellipse"] = "rectangle"
    radius: int = Field(default=0, ge=0, le=240)
    shadow: bool = False
    asset_id: str | None = Field(default=None, min_length=1, max_length=120)
    crop: NormalizedRegionV1 | None = None
    brightness: float = Field(default=1, ge=0.25, le=2, allow_inf_nan=False)
    contrast: float = Field(default=1, ge=0.25, le=2, allow_inf_nan=False)
    saturation: float = Field(default=1, ge=0, le=2, allow_inf_nan=False)
    start_frame: int = Field(default=0, ge=0, le=36000)
    duration_frames: int | None = Field(default=None, ge=1, le=36000)
    keyframes: list[MotionKey] = Field(default_factory=list, max_length=32)

    @model_validator(mode="after")
    def unique_keys(self):
        if len({(key.property, key.frame) for key in self.keyframes}) != len(self.keyframes):
            raise ValueError("local_duplicate_keyframe")
        return self


class LocalScene(StudioContract):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(max_length=120)
    start_frame: int = Field(ge=0, le=36000, strict=True)
    duration_frames: int = Field(ge=1, le=36000, strict=True)
    layer_ids: list[str] = Field(max_length=24)


def validate_scenes(composition):
    production = composition.narrative.get("localProduction")
    if production is None:
        return
    if not isinstance(production, dict):
        raise ValueError("local_scene_metadata_invalid")
    scenes = production.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) > 24:
        raise ValueError("local_scene_metadata_invalid")
    seen = set()
    for value in scenes:
        if not isinstance(value, dict):
            raise ValueError("local_scene_metadata_invalid")
        # Validate known navigation fields without destroying extension metadata.
        scene = LocalScene.model_validate(
            {key: value[key] for key in ("id", "title", "startFrame", "durationFrames", "layerIds") if key in value}
        )
        if scene.id in seen or len(set(scene.layer_ids)) != len(scene.layer_ids):
            raise ValueError("local_scene_duplicate_id")
        seen.add(scene.id)
        timeline = composition.media_timeline
        if not timeline or scene.start_frame + scene.duration_frames > timeline.duration_frames:
            raise ValueError("local_scene_exceeds_duration")


def validate_composition(composition: CreativeCompositionV1, content_type: str):
    if len(composition.pages) != 1 or content_type not in {"visual", "video"}:
        raise ValueError("local_single_page_project_required")
    page = composition.pages[0]
    if max(page.width, page.height) > 1920 or page.width % 2 or page.height % 2:
        raise ValueError("local_dimensions_unsupported")
    if len(page.layers) > 24 or len({layer.id for layer in page.layers}) != len(page.layers):
        raise ValueError("local_layer_limit_or_duplicate")
    timeline = composition.media_timeline
    if content_type == "video" and not timeline:
        raise ValueError("local_timeline_required")
    if content_type == "visual" and timeline:
        raise ValueError("local_image_timeline_unsupported")
    validate_scenes(composition)
    assets = set()
    for layer in page.layers:
        if layer.kind not in {"text", "shape", "image"} or max(layer.width, layer.height) > 1920:
            raise ValueError("local_layer_unsupported")
        style = LocalLayerStyle.model_validate(layer.properties)
        if layer.kind == "text" and not style.text.strip():
            raise ValueError("local_text_required")
        if style.text_reveal == "words":
            words = len(style.text.split())
            if layer.kind != "text" or not timeline or not 1 <= words <= 32:
                raise ValueError("local_word_reveal_requires_video_text_max_32_words")
            if (words - 1) * style.word_stagger_frames >= (style.duration_frames or timeline.duration_frames):
                raise ValueError("local_word_reveal_exceeds_duration")
        if layer.kind == "image":
            if not style.asset_id:
                raise ValueError("local_image_asset_required")
            assets.add(style.asset_id)
        elif style.asset_id or style.crop:
            raise ValueError("local_non_image_asset_invalid")
        end = style.start_frame + (style.duration_frames or (timeline.duration_frames if timeline else 1))
        if timeline and (
            end > timeline.duration_frames or any(key.frame > end - style.start_frame for key in style.keyframes)
        ):
            raise ValueError("local_layer_exceeds_duration")
        if not timeline and (style.keyframes or style.start_frame or style.duration_frames):
            raise ValueError("local_image_animation_unsupported")
    return assets
