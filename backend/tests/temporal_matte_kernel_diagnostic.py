"""Explicit qualification experiment; combined admission gate remains pending.

Not collected by the default suite. The retained API experiments preceded
restoration of the admission diagnostic after unresolved raster edge probes.
"""
# ruff: noqa: F811
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_remotion_native import native_direction

from app.database import SessionLocal
from app.domain.studios.motion_recipes import TemporalExposureV1
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.providers.studios.heavy_media_lease import _active, _read, lease_path
from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
from app.services.object_storage import get_object_storage
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.jobs import execute_job_once

# x/y/w/h, animated dx/dy/rotation/scale-x delta/scale-y delta.
GEOMETRY = {"outer": (18, 16, 240, 260, 70, 8, 12, -.05, .1),
            "rig": (15, 18, 210, 200, 20, -4, -10, .08, -.04),
            "hero": (10, 10, 170, 150, 24, 8, 10, .05, 0),
            "mask-rig": (100, 74, 80, 96, 20, 12, -8, .1, .1),
            "matte": (0, 0, 80, 96, 10, 0, 0, 0, 0)}
VARIANTS = [("control", "external", "alpha", False), ("child", "external", "alpha", False),
            ("child", "external", "alpha", True), ("rig", "external", "alpha", False),
            ("rig", "external", "luminance", True), ("child", "common", "alpha", False),
            ("rig", "common", "luminance", False)]
FRAMES = (0, 4, 7, 8, 10, 15)


def original_mask():
    mask = Image.new("RGBA", (80, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mask)
    draw.polygon([(0, 0), (39, 0), (0, 47)], fill=(255, 255, 255, 255))
    draw.ellipse((13, 13, 29, 29), fill=(255, 255, 255, 0))
    draw.rectangle((40, 0, 79, 47), fill=(0, 0, 0, 255))
    draw.rectangle((0, 48, 39, 95), fill=(128, 128, 128, 128))
    return mask


def direction_for(asset, scope, source_branch, mode, invert):
    raw = native_direction().model_dump(mode="json", by_alias=True)
    scene = raw["scenes"][0]
    scene.update(id="temporal-matte", durationFrames=16, background="#000000", nativeComponents=[],
                 elements=[], motionRecipes=[])
    for target, values in GEOMETRY.items():
        x, y, width, height, dx, dy, angle, sx, sy = values
        if target == "mask-rig" and source_branch == "common":
            x, y = 80, 60
        element = {"id": target, "kind": "shape" if target == "hero" else "image" if target == "matte" else "group",
                   "purpose": "Original affine matte exposure witness", "x": x, "y": y,
                   "width": width, "height": height, "durationFrames": 16, "originX": .5, "originY": .5,
                   "depthTreatment": {"opacity": {"outer": .9, "rig": .9, "hero": .85,
                                                  "mask-rig": .2, "matte": .6}[target]}}
        if target in {"rig", "hero", "matte"}:
            element["parentId"] = {"rig": "outer", "hero": "rig", "matte": "mask-rig"}[target]
        if target == "mask-rig" and source_branch == "common":
            element["parentId"] = "outer"
        if target == "rig":
            element.update(borderWidth=2, borderColor="#000000")
        if target == "hero":
            element.update(fill="#ffffff", radius=0, visualRole="hero")
        if target == "matte":
            element.update(assetId=asset, objectFit="contain")
        scene["elements"].append(element)
        tracks = [{"targetId": target, "property": prop, "keyframes": [
            {"frame": 0, "value": first, "curve": [0, 0, 1, 1]}, {"frame": 8, "value": last},
            {"frame": 15, "value": last}]} for prop, first, last in
            [("x", 0, dx), ("y", 0, dy), ("rotation", 0, angle), ("scale_x", 1, 1 + sx), ("scale_y", 1, 1 + sy)]]
        if target == "matte":
            tracks.append({"targetId": target, "property": "opacity", "keyframes": [
                {"frame": 0, "value": .6, "curve": [0, 0, 1, 1]}, {"frame": 8, "value": .9},
                {"frame": 15, "value": .9}]})
        scene["motionRecipes"].append({"id": target + "-move", "technique": "motion_choreography",
            "targetIds": [target], "startFrame": 0, "endFrameExclusive": 16,
            "intent": "Affine motion and hold", "continuityAnchor": "Same target and original pixels",
            "parameters": {"pivot": [.5, .5], "tracks": tracks}, "verification": ["Pixels retain matte identity"]})
    scene["motionRecipes"].append({"id": "world-matte", "technique": "asset_matte", "targetIds": ["hero"],
        "startFrame": 0, "endFrameExclusive": 16, "intent": "World-space original matte",
        "continuityAnchor": "Same bitmap", "parameters": {"assetMatte": {
            "sourceTargetId": "matte", "mode": mode, "invert": invert}}, "verification": ["Mask does not drift"]})
    if scope != "control":
        scene["motionRecipes"].append({"id": "local-exposure", "technique": "velocity_blur",
            "targetIds": ["hero" if scope == "child" else "rig"], "startFrame": 0, "endFrameExclusive": 16,
            "intent": "Expose local subtree while external world stays at center", "continuityAnchor": "Same matte",
            "parameters": {"temporalSamples": 8, "shutterDegrees": 180,
                           "temporalExposure": TemporalExposureV1().model_dump(mode="json", by_alias=True)},
            "verification": ["World matte and sampled target agree"]})
    return raw


def mul(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, m = right
    return a*g+c*h, b*g+d*h, a*i+c*j, b*i+d*j, a*k+c*m+e, b*k+d*m+f


def inverse(matrix):
    a, b, c, d, e, f = matrix
    det = a*d-b*c
    return d/det, -b/det, -c/det, a/det, (c*f-d*e)/det, (b*e-a*f)/det


def point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return a*x+c*y+e, b*x+d*y+f


def local(target, frame, branch):
    x, y, w, h, dx, dy, degrees, dsx, dsy = GEOMETRY[target]
    if target == "mask-rig" and branch == "common":
        x, y = 80, 60
    p = max(0, min(frame / 8, 1))
    angle = math.radians(degrees * p)
    a, b = math.cos(angle)*(1+dsx*p), math.sin(angle)*(1+dsx*p)
    c, d = -math.sin(angle)*(1+dsy*p), math.cos(angle)*(1+dsy*p)
    return a, b, c, d, x+dx*p+w/2-a*w/2-c*h/2, y+dy*p+h/2-b*w/2-d*h/2


def worlds(frame, sample, scope, branch):
    outer = local("outer", frame, branch)
    rig = mul(outer, local("rig", sample if scope == "rig" else frame, branch))
    target = mul(mul(rig, (1, 0, 0, 1, 2, 2)), local("hero", sample, branch))
    source = mul(local("mask-rig", frame, branch), local("matte", frame, branch))
    if branch == "common":
        source = mul(outer, source)
    return target, source


def times_for(frame, scope):
    if scope == "control" or frame >= 10:
        return [frame]
    low, high = max(0, frame-.25), min(16, frame+.25)
    return [low+(i+.5)*(high-low)/8 for i in range(8)]


def raster_value(mask, u, v, mode):
    # The SVG image viewport clips coverage. Within it, texture interpolation
    # clamps edge texels; it does not fade into fictitious transparent texels.
    if not (0 <= u < mask.width and 0 <= v < mask.height):
        return 0
    u, v = u-.5, v-.5
    left, top = math.floor(u), math.floor(v)
    total = 0
    for x in (left, left+1):
        for y in (top, top+1):
            red, green, blue, alpha = mask.getpixel((max(0, min(mask.width-1, x)), max(0, min(mask.height-1, y))))
            value = alpha/255
            if mode == "luminance":
                value *= (.2126*red+.7152*green+.0722*blue)/255
            total += value*(1-abs(u-x))*(1-abs(v-y))
    return total


def expected_pixel(mask, frame, scope, branch, mode, invert, x, y, grid=8):
    alpha = .9*.9*.85
    source_opacity = .6+.3*min(frame/8, 1)
    matrices = [(inverse(target), inverse(source)) for sample in times_for(frame, scope)
                for target, source in [worlds(frame, sample, scope, branch)]]
    value = 0
    # Rasterize content and the clipped mask as separate alpha images, then
    # multiply per pixel. Multiplying continuous geometry before rasterization
    # incorrectly removes the second antialiased silhouette at mask bounds.
    # Neither DOM matrices nor observed pixels define this original oracle.
    for target, source in matrices:
        for px in range(2):
            for py in range(2):
                content_coverage = mask_coverage = 0
                for dx in range(grid):
                    for dy in range(grid):
                        wx, wy = x+px+(dx+.5)/grid, y+py+(dy+.5)/grid
                        tx, ty = point(target, wx, wy)
                        if not (0 <= tx < 170 and 0 <= ty < 150):
                            continue
                        content_coverage += 1
                        u, v = point(source, wx, wy)
                        coverage = raster_value(mask, u, v, mode)*source_opacity
                        mask_coverage += 1-coverage if invert else coverage
                value += content_coverage/grid**2 * mask_coverage/grid**2 * alpha*255
    return value/(len(matrices)*4)


def probe_points(frame, scope, branch):
    target, source = worlds(frame, frame, scope, branch)
    source_uv = [(4, 4), (20, 12), (20, 30), (39, 8), (40, 8), (42, 8), (60, 8),
                 (8, 60), (20, 60), (39, 60), (45, 60), (60, 60), (-2, 20), (0, 20),
                 (1, 20), (79, 20), (80, 20), (82, 20), (20, -2), (20, 0), (20, 94), (20, 96), (20, 98)]
    authored = [point(source, u, v) for u, v in source_uv]
    authored += [point(target, u, v) for u, v in [(-1, 50), (0, 50), (1, 50), (169, 50), (170, 50),
                                                (50, -1), (50, 0), (50, 149), (50, 150)]]
    return sorted({(int(x)//2*2, int(y)//2*2) for x, y in authored if 2 <= x < 317 and 2 <= y < 317})
