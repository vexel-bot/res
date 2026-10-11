"""Research reference, independently calibrated by exact texels and quad controls."""
import importlib.util
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/tests"))
from tests.temporal_matte_kernel_diagnostic import inverse, point, raster_value, times_for, worlds  # noqa: E402


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


raster = module("independent_quad_raster", ROOT / "scripts/validation/editor-temporal-matte-quad-raster-reference.py")
geometry = module("independent_polygon_geometry", ROOT / "scripts/validation/editor-temporal-matte-uniform-analysis.py")


def aligned(polygon):
    return all(abs(polygon[(i + 1) % 4][0] - x) < 1e-8 or abs(polygon[(i + 1) % 4][1] - y) < 1e-8
               for i, (x, y) in enumerate(polygon))


@lru_cache(maxsize=256)
def sample_geometry(frame, sample, scope, branch):
    target, source = worlds(frame, sample, scope, branch)
    target_poly = [point(target, u, v) for u, v in [(0, 0), (170, 0), (170, 150), (0, 150)]]
    source_poly = [point(source, u, v) for u, v in [(0, 0), (80, 0), (80, 96), (0, 96)]]
    source_inverse = inverse(source)
    return {"targetPolygon": target_poly, "sourcePolygon": source_poly, "sourceInverse": source_inverse,
            "targetTriangles": raster.quad_triangles(target_poly), "sourceTriangles": raster.quad_triangles(source_poly),
            "textureTriangles": raster.texture_triangles(source_poly, source_inverse), "targetAligned": aligned(target_poly)}


def source_channel(mask, frame, sample, scope, branch, mode, x, y):
    prepared = sample_geometry(frame, sample, scope, branch)
    opacity = raster.byte((.6 + .3 * min(frame / 8, 1)) * 255)
    source_coverage = raster.coverage(prepared["sourceTriangles"], x + .5, y + .5)
    local = raster.interpolate_texture_coordinates(prepared["textureTriangles"], x + .5, y + .5)
    u, v = local if local is not None else point(prepared["sourceInverse"], x + .5, y + .5)
    texture = raster_value(mask, max(1e-8, min(80 - 1e-8, u)), max(1e-8, min(96 - 1e-8, v)), mode)
    return raster.byte(source_coverage * texture * opacity)


def single_channel(mask, frame, sample, scope, branch, mode, invert, x, y):
    prepared = sample_geometry(frame, sample, scope, branch)
    quad = raster.coverage(prepared["targetTriangles"], x + .5, y + .5)
    clip = quad if prepared["targetAligned"] else geometry.pixel_coverage(prepared["targetPolygon"], x, y)
    matte = source_channel(mask, frame, sample, scope, branch, mode, x, y)
    mask_alpha = raster.byte(raster.byte(clip * 255) * (255 - matte if invert else matte) / 255)
    result = raster.byte(raster.byte(quad * raster.byte(.85 * 255)) * mask_alpha / 255)
    for authored_opacity in [.9, .9]:
        result = raster.byte(result * raster.byte(authored_opacity * 255) / 255)
    return result


def expected_pixel(mask, frame, scope, branch, mode, invert, x, y):
    total = 0
    samples = times_for(frame, scope)
    for sample in samples:
        for dx in range(2):
            for dy in range(2):
                total += single_channel(mask, frame, sample, scope, branch, mode, invert, x + dx, y + dy)
    return total / (4 * len(samples))
