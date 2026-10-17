"""Bounded static vector import. Unsupported active/external content is rejected."""

import math
import re
import sys
from pathlib import Path

from defusedxml import ElementTree

ALLOWED = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
    "mask",
    "title",
    "desc",
}


def validate_svg(data):
    if len(data) > 1_000_000:
        raise ValueError("resource_svg_too_large")
    try:
        root = ElementTree.fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except Exception as error:
        raise ValueError("resource_svg_invalid") from error
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("resource_svg_namespace_required")
    elements = list(root.iter())
    if len(elements) > 2000:
        raise ValueError("resource_svg_too_complex")
    for element in elements:
        tag = element.tag.removeprefix("{http://www.w3.org/2000/svg}")
        if tag not in ALLOWED:
            raise ValueError("resource_svg_element_unsupported")
        for name, value in element.attrib.items():
            if name.startswith("{") or name.lower().startswith("on") or name.lower() in {"href", "src"}:
                raise ValueError("resource_svg_external_or_active_content")
            stripped = re.sub(r"url\(\s*#[a-zA-Z0-9_-]+\s*\)", "", value)
            if re.search(r"url\s*\(|https?:|file:|data:|@|\\", stripped, re.I):
                raise ValueError("resource_svg_external_or_active_content")

    def dimension(name, fallback):
        raw = root.get(name, str(fallback)).removesuffix("px")
        try:
            return float(raw)
        except ValueError as error:
            raise ValueError("resource_svg_dimensions_required") from error

    try:
        view = [float(n) for n in re.split(r"[\s,]+", root.get("viewBox", "0 0 1024 1024").strip())]
        if len(view) != 4 or not all(math.isfinite(n) for n in view) or min(view[2:]) <= 0:
            raise ValueError("invalid viewbox")
        width, height = dimension("width", view[2]), dimension("height", view[3])
        if not all(math.isfinite(n) and 0 < n <= 4096 for n in (width, height)) or width * height > 16_000_000:
            raise ValueError("resource_svg_dimensions_exceeded")
    except ValueError as error:
        raise ValueError("resource_svg_dimensions_invalid") from error
    return data.decode("utf-8-sig"), max(1, round(width)), max(1, round(height))


def rasterize(source, destination):
    import resvg_py

    svg, width, height = validate_svg(Path(source).read_bytes())
    Path(destination).write_bytes(
        resvg_py.svg_to_bytes(
            svg_string=svg, width=width, height=height, skip_system_fonts=True, font_files=[], font_dirs=[]
        )
    )


if __name__ == "__main__":
    rasterize(sys.argv[1], sys.argv[2])
