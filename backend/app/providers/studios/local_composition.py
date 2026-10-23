"""Pillow raster primitives shared by PNG export and the canonical FFmpeg compiler."""

import math
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from ...domain.studios.local_composition import LocalLayerStyle


def value_at(keys, property, default, frame):
    points = sorted((key for key in keys if key.property == property), key=lambda key: key.frame)
    if not points:
        return default
    if frame <= points[0].frame:
        return points[0].value
    for a, b in zip(points, points[1:], strict=False):
        if frame <= b.frame:
            progress = (frame - a.frame) / (b.frame - a.frame)
            if b.easing == "ease-in-out":
                progress = progress * progress * (3 - 2 * progress)
            elif b.easing == "ease-out":
                progress = 1 - (1 - progress) ** 3
            return a.value + (b.value - a.value) * progress
    return points[-1].value


def font(style):
    windows = "segoeuib.ttf" if style.font_weight == 700 else "segoeui.ttf"
    dejavu = "DejaVuSans-Bold.ttf" if style.font_weight == 700 else "DejaVuSans.ttf"
    liberation = "LiberationSans-Bold.ttf" if style.font_weight == 700 else "LiberationSans-Regular.ttf"
    candidates = (
        [f"C:/Windows/Fonts/{windows}", f"/usr/share/fonts/truetype/dejavu/{dejavu}"]
        if style.font_family == "system"
        else [
            f"/usr/share/fonts/truetype/liberation2/{liberation}",
            f"/usr/share/fonts/truetype/liberation/{liberation}",
        ]
    )
    path = next((path for path in candidates if Path(path).is_file()), None)
    if path is None:
        raise ValueError("timeline_title_font_unavailable")
    return ImageFont.truetype(path, style.font_size)


def text_layout(layer, style):
    """Stable full-text word positions shared by still and video reveal masks."""
    face = font(style)
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines = []
    for paragraph in style.text.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = (line + " " + word).strip()
            if draw.textlength(candidate, font=face) > layer.width:
                if not line or draw.textlength(word, font=face) > layer.width:
                    raise ValueError("local_text_does_not_fit")
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    if len(lines) * style.font_size * 1.3 > layer.height:
        raise ValueError("local_text_does_not_fit")
    runs = []
    for row, line in enumerate(lines):
        width = draw.textlength(line, font=face)
        x = 0 if style.align == "left" else (layer.width - width) / (2 if style.align == "center" else 1)
        prefix = ""
        for word in line.split():
            left = x + draw.textlength(prefix, font=face)
            runs.append((word, left, row * style.font_size * 1.3, draw.textlength(word, font=face)))
            prefix += word + " "
    return face, runs


def raster(layer, paths, frame=None):
    style = LocalLayerStyle.model_validate(layer.properties)
    size = (max(1, round(layer.width)), max(1, round(layer.height)))
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)
    if layer.kind == "image":
        with Image.open(paths[style.asset_id]) as source:
            if source.width * source.height > 40_000_000:
                raise ValueError("local_image_pixel_limit")
            source = ImageOps.exif_transpose(source).convert("RGBA")
            if style.crop:
                box = style.crop
                source = source.crop(
                    (
                        round(box.x * source.width),
                        round(box.y * source.height),
                        round((box.x + box.width) * source.width),
                        round((box.y + box.height) * source.height),
                    )
                )
            image = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)
            for enhancer, factor in (
                (ImageEnhance.Brightness, style.brightness),
                (ImageEnhance.Contrast, style.contrast),
                (ImageEnhance.Color, style.saturation),
            ):
                image = enhancer(image).enhance(factor)
    elif layer.kind == "shape":
        mask = Image.new("L", size)
        mask_draw = ImageDraw.Draw(mask)
        box = (0, 0, size[0] - 1, size[1] - 1)
        if style.shape == "ellipse":
            mask_draw.ellipse(box, fill=255)
        else:
            mask_draw.rounded_rectangle(box, radius=style.radius, fill=255)
        image = Image.new("RGBA", size, style.fill)
        if style.gradient_end:
            start, end = ImageColor.getrgb(style.fill), ImageColor.getrgb(style.gradient_end)
            gradient = ImageDraw.Draw(image)
            for y in range(size[1]):
                ratio = y / max(1, size[1] - 1)
                gradient.line(
                    (0, y, size[0], y), fill=tuple(round(a + (b - a) * ratio) for a, b in zip(start, end, strict=True))
                )
        image.putalpha(mask)
    elif layer.kind == "text":
        face, runs = text_layout(layer, style)
        # All words share a font baseline. Using 'lt' independently aligns each
        # word's ink top and makes short words float above their neighbours.
        top = face.getbbox(" ".join(style.text.split()))[1]
        for index, (word, x, y, _width) in enumerate(runs):
            if frame is None or style.text_reveal == "all" or frame >= index * style.word_stagger_frames:
                draw.text((x, y - top), word, font=face, fill=style.color, anchor="la")
    else:
        raise ValueError("local_layer_unsupported")
    if style.shadow:
        shadow = Image.new("RGBA", size)
        shadow.putalpha(image.getchannel("A").filter(ImageFilter.GaussianBlur(4)).point(lambda a: round(a * 0.22)))
        shadow.alpha_composite(image)
        image = shadow
    return image


def render_page(page, paths, frame=0, duration_frames=1):
    image = Image.new("RGBA", (page.width, page.height), page.background)
    for layer in sorted(page.layers, key=lambda item: item.z_index):
        style = LocalLayerStyle.model_validate(layer.properties)
        relative = frame - style.start_frame
        if not layer.visible or relative < 0 or relative >= (style.duration_frames or duration_frames):
            continue
        bitmap = raster(layer, paths, relative)
        scale = value_at(style.keyframes, "scale", 1, relative)
        bitmap = bitmap.resize(
            (max(1, round(bitmap.width * scale)), max(1, round(bitmap.height * scale))), Image.Resampling.LANCZOS
        )
        angle = value_at(style.keyframes, "rotation", layer.rotation, relative)
        if angle:
            bitmap = bitmap.rotate(-angle, resample=Image.Resampling.BICUBIC, expand=True)
        opacity = value_at(style.keyframes, "opacity", layer.opacity, relative)
        if opacity != 1:
            bitmap.putalpha(bitmap.getchannel("A").point(lambda a, opacity=opacity: round(a * opacity)))
        x = layer.x + layer.width / 2 + value_at(style.keyframes, "x", 0, relative) - bitmap.width / 2
        y = layer.y + layer.height / 2 + value_at(style.keyframes, "y", 0, relative) - bitmap.height / 2
        if not math.isfinite(x + y):
            raise ValueError("local_position_invalid")
        image.alpha_composite(bitmap, (round(x), round(y)))
    return image
