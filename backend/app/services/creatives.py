from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..schemas import CreativeCanvas, CreativeTextLayer

FONT_PATHS = {
    "normal": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}
MAX_SOURCE_PIXELS = 16_000_000


def _font(size: int, weight: str = "normal") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        FONT_PATHS.get(weight, FONT_PATHS["normal"]),
        "DejaVuSans-Bold.ttf" if weight == "bold" else "DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrapped_lines(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: float) -> list[str]:
    paragraphs = text.splitlines() or [""]
    lines: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.getlength(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def fit_text(layer: CreativeTextLayer) -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, list[str], int]:
    """Fit wrapped text inside its layer box and return font, lines and pixel line height."""
    for size in range(layer.font_size, layer.min_font_size - 1, -1):
        font = _font(size, layer.font_weight)
        lines = _wrapped_lines(layer.text, font, layer.width)
        line_height = max(1, round(size * layer.line_height))
        widest = max((font.getlength(line) for line in lines), default=0)
        if widest <= layer.width and line_height * len(lines) <= layer.height:
            return font, lines, line_height
    font = _font(layer.min_font_size, layer.font_weight)
    return font, _wrapped_lines(layer.text, font, layer.width), max(1, round(layer.min_font_size * layer.line_height))


def _place(base: Image.Image, layer_image: Image.Image, layer: Any) -> None:
    if layer.opacity < 1:
        alpha = layer_image.getchannel("A").point(lambda value: round(value * layer.opacity))
        layer_image.putalpha(alpha)
    if layer.rotation:
        layer_image = layer_image.rotate(-layer.rotation, expand=True, resample=Image.Resampling.BICUBIC)
        x = round(layer.x + (layer.width - layer_image.width) / 2)
        y = round(layer.y + (layer.height - layer_image.height) / 2)
    else:
        x, y = round(layer.x), round(layer.y)
    base.alpha_composite(layer_image, (x, y))


def render_creative(document: CreativeCanvas, asset_paths: dict[str, Path]) -> Image.Image:
    base = Image.new("RGBA", (document.width, document.height), document.background)
    for layer in sorted(document.layers, key=lambda item: item.z_index):
        if not layer.visible or layer.opacity <= 0:
            continue
        width, height = max(1, round(layer.width)), max(1, round(layer.height))
        layer_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer_image)
        if layer.type == "shape":
            if layer.shape == "ellipse":
                draw.ellipse((0, 0, width - 1, height - 1), fill=layer.fill)
            else:
                draw.rounded_rectangle(
                    (0, 0, width - 1, height - 1), radius=min(layer.radius, width // 2, height // 2), fill=layer.fill
                )
        elif layer.type == "text":
            font, lines, line_height = fit_text(layer)
            for index, line in enumerate(lines):
                line_width = font.getlength(line)
                x = 0 if layer.align == "left" else (width - line_width) / (2 if layer.align == "center" else 1)
                draw.text((round(x), index * line_height), line, fill=layer.color, font=font)
        elif layer.type == "image":
            source_path = asset_paths.get(layer.asset_id)
            if not source_path or not source_path.is_file():
                raise ValueError(f"Image asset {layer.asset_id} is unavailable")
            with Image.open(source_path) as source:
                if source.width * source.height > MAX_SOURCE_PIXELS:
                    raise ValueError(f"Image asset {layer.asset_id} exceeds the 16 megapixel render limit")
                source = ImageOps.exif_transpose(source).convert("RGBA")
                rendered = (
                    ImageOps.fit(source, (width, height), Image.Resampling.LANCZOS)
                    if layer.fit == "cover"
                    else ImageOps.contain(source, (width, height), Image.Resampling.LANCZOS)
                )
                if layer.fit == "contain":
                    layer_image.alpha_composite(
                        rendered, ((width - rendered.width) // 2, (height - rendered.height) // 2)
                    )
                else:
                    layer_image = rendered
        _place(base, layer_image, layer)
    return base
