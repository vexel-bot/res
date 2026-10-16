from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from ...domain.studios.image_edit import (
    ImageEditExecutionV1,
    ImageEditResultV1,
)


def _bounds(region, width: int, height: int) -> tuple[int, int, int, int]:
    left = round(region.x * width)
    top = round(region.y * height)
    right = round((region.x + region.width) * width)
    bottom = round((region.y + region.height) * height)
    return left, top, right, bottom


class PillowImageEditProvider:
    """Deterministic local adapter; the domain contract does not depend on Pillow."""

    name = "pillow"
    version = "1"

    def derive(
        self,
        source_path: str,
        output_path: str,
        request: ImageEditExecutionV1,
    ) -> ImageEditResultV1:
        with Image.open(source_path) as opened:
            source = ImageOps.exif_transpose(opened).convert("RGBA")
        adjusted = ImageEnhance.Brightness(source).enhance(request.brightness)
        adjusted = ImageEnhance.Contrast(adjusted).enhance(request.contrast)
        mask = Image.new("L", source.size, 0 if request.edit_mask else 255)
        draw = ImageDraw.Draw(mask)
        if request.edit_mask:
            bounds = _bounds(request.edit_mask, *source.size)
            if request.edit_mask.shape == "ellipse":
                draw.ellipse(bounds, fill=255)
            else:
                draw.rectangle(bounds, fill=255)
        for region in request.protected_regions:
            draw.rectangle(_bounds(region, *source.size), fill=0)
        result = Image.composite(adjusted, source, mask)
        result.save(Path(output_path), format="PNG", optimize=True)
        return ImageEditResultV1(
            width=result.width,
            height=result.height,
            provider=self.name,
            provider_version=self.version,
        )
