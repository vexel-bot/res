"""Deterministic 2D composition geometry shared by planning and audit.

The math follows the renderer's DOM hierarchy and transform order. Pixel
inspection remains authoritative for mattes, glyph outlines and media ROIs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .contextual_editing import digest

Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1, 0, 0, 1, 0, 0)


def _multiply(left: Matrix, right: Matrix) -> Matrix:
    a, b, c, d, e, f = left
    g, h, i, j, k, last = right
    return (
        a * g + c * h,
        b * g + d * h,
        a * i + c * j,
        b * i + d * j,
        a * k + c * last + e,
        b * k + d * last + f,
    )


def _translation(x: float, y: float) -> Matrix:
    return (1, 0, 0, 1, x, y)


def _scale(x: float, y: float) -> Matrix:
    return (x, 0, 0, y, 0, 0)


def _rotation(degrees: float) -> Matrix:
    radians = math.radians(degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    return (cosine, sine, -sine, cosine, 0, 0)


def _point(matrix: Matrix, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def _bezier(keyframe, progress: float) -> float:
    controls = keyframe.cubic_bezier
    if not controls:
        return progress
    x1, y1, x2, y2 = controls

    def component(t: float, first: float, second: float) -> float:
        inverse = 1 - t
        return 3 * inverse * inverse * t * first + 3 * inverse * t * t * second + t * t * t

    low, high, value = 0.0, 1.0, progress
    for _ in range(16):
        if component(value, x1, x2) < progress:
            low = value
        else:
            high = value
        value = (low + high) / 2
    return component(value, y1, y2)


def track_value(track, frame: float) -> float:
    keys = track.keyframes
    if frame <= keys[0].frame:
        return keys[0].value
    if frame >= keys[-1].frame:
        return keys[-1].value
    for first, second in zip(keys, keys[1:], strict=False):
        if first.frame <= frame <= second.frame:
            progress = (frame - first.frame) / (second.frame - first.frame)
            if first.easing == "hold":
                progress = 0
            elif first.easing == "ease_in":
                progress *= progress
            elif first.easing == "ease_out":
                progress = 1 - (1 - progress) ** 2
            elif first.easing == "ease_in_out":
                progress = 2 * progress * progress if progress < 0.5 else 1 - (-2 * progress + 2) ** 2 / 2
            elif first.easing == "cubic_bezier":
                progress = _bezier(first, progress)
            return first.value + (second.value - first.value) * progress
    return keys[-1].value


def _target_id(scene_id: str, element_id: str, instance: int = 0) -> str:
    return "ed2-" + digest([scene_id, element_id, instance])[:24]


@dataclass(frozen=True)
class EffectiveGeometry:
    layer_id: str
    semantic_id: str
    instance: int
    x: float
    y: float
    width: float
    height: float
    opacity: float
    visible: bool

    @property
    def area(self) -> float:
        return self.width * self.height


def evaluate_scene_geometry(
    scene,
    graph,
    scene_start: int,
    local_frame: int,
    canvas_width: float,
    canvas_height: float,
):
    """Return transformed axis-aligned bounds for all declared instances."""
    absolute_frame = scene_start + local_frame
    indexed = {element.id: element for element in scene.elements}
    positions: dict[str, tuple[float, float]] = {}

    def position_of(element):
        if element.id not in positions:
            x, y = element.x, element.y
            if element.alignment:
                reference = indexed[element.alignment.target_id]
                rx, ry = position_of(reference)
                if element.alignment.horizontal:
                    ratio = {"left": 0, "center": 0.5, "right": 1}[element.alignment.horizontal]
                    x = rx + (reference.width - element.width) * ratio + element.x
                if element.alignment.vertical:
                    ratio = {"top": 0, "middle": 0.5, "bottom": 1}[element.alignment.vertical]
                    y = ry + (reference.height - element.height) * ratio + element.y
            positions[element.id] = x, y
        return positions[element.id]

    layer_specs: dict[str, dict] = {}
    for identifier in (
        "scene-root",
        "background-group",
        "content-group",
        "text-group",
        "background",
    ):
        layer_specs[_target_id(scene.id, identifier)] = {
            "semantic_id": identifier,
            "instance": 0,
            "x": 0,
            "y": 0,
            "width": canvas_width,
            "height": canvas_height,
            "rotation": 0,
            "opacity": 1,
            "start": scene_start,
            "end": scene_start + scene.duration_frames,
            "parent_layer_id": (
                None
                if identifier == "scene-root"
                else _target_id(scene.id, "scene-root")
                if identifier in {"background-group", "content-group", "text-group"}
                else _target_id(scene.id, "background-group")
            ),
        }
    starts: dict[str, int] = {}

    def start_of(element):
        if element.id not in starts:
            previous = indexed.get(element.after_element_id)
            dependency_end = start_of(previous) + previous.duration_frames if previous else 0
            starts[element.id] = element.start_frame + dependency_end
        return starts[element.id]

    for element in scene.elements:
        x, y = position_of(element)
        for instance in range(element.repeat_count):
            layer_specs[_target_id(scene.id, element.id, instance)] = {
                "semantic_id": element.id,
                "instance": instance,
                "x": x + instance * element.repeat_dx,
                "y": y + instance * element.repeat_dy,
                "width": element.width,
                "height": element.height,
                "rotation": element.rotation,
                "opacity": element.depth_treatment.opacity,
                "start": scene_start + start_of(element) + instance * element.stagger_frames,
                "end": scene_start + start_of(element) + instance * element.stagger_frames + element.duration_frames,
                "parent_layer_id": (
                    _target_id(scene.id, element.parent_id)
                    if element.parent_id
                    else _target_id(
                        scene.id,
                        "background-group"
                        if element.visual_role == "background"
                        else "text-group"
                        if element.visual_role == "text" or element.kind == "text"
                        else "content-group",
                    )
                ),
            }

    node_by_id = {node.node_id: node for node in graph.nodes} if graph else {}
    node_by_layer = {node.target_layer_id: node for node in graph.nodes} if graph else {}
    tracks_by_layer: dict[str, dict] = {}
    if graph:
        for track in graph.tracks:
            tracks_by_layer.setdefault(track.target_layer_id, {})[track.property] = track
    matrices: dict[str, Matrix] = {}
    opacities: dict[str, float] = {}

    def matrix_for(layer_id: str) -> Matrix:
        if layer_id in matrices:
            return matrices[layer_id]
        spec = layer_specs.get(
            layer_id,
            {
                "x": 0,
                "y": 0,
                "width": canvas_width,
                "height": canvas_height,
                "rotation": 0,
                "opacity": 1,
            },
        )
        node = node_by_layer.get(layer_id)
        origin_x = (node.transform_origin_x if node else 0.5) * spec["width"]
        origin_y = (node.transform_origin_y if node else 0.5) * spec["height"]
        tracks = tracks_by_layer.get(layer_id, {})
        tx = track_value(tracks["position_x"], absolute_frame) if "position_x" in tracks else 0
        ty = track_value(tracks["position_y"], absolute_frame) if "position_y" in tracks else 0
        sx = track_value(tracks["scale_x"], absolute_frame) if "scale_x" in tracks else 1
        sy = track_value(tracks["scale_y"], absolute_frame) if "scale_y" in tracks else 1
        rotation = (
            track_value(tracks["rotation_degrees"], absolute_frame)
            if "rotation_degrees" in tracks
            else spec["rotation"]
        )
        local = _multiply(
            _translation(spec["x"], spec["y"]),
            _multiply(
                _translation(origin_x, origin_y),
                _multiply(
                    _translation(tx, ty),
                    _multiply(_scale(sx, sy), _multiply(_rotation(rotation), _translation(-origin_x, -origin_y))),
                ),
            ),
        )
        parent = node_by_id.get(node.parent_node_id) if node and node.parent_node_id else None
        parent_layer_id = parent.target_layer_id if parent else spec.get("parent_layer_id")
        matrices[layer_id] = _multiply(matrix_for(parent_layer_id), local) if parent_layer_id else local
        own_opacity = track_value(tracks["opacity"], absolute_frame) if "opacity" in tracks else spec["opacity"]
        opacities[layer_id] = own_opacity * (opacities.get(parent_layer_id, 1) if parent_layer_id else 1)
        return matrices[layer_id]

    output: dict[str, list[EffectiveGeometry]] = {}
    for layer_id, spec in layer_specs.items():
        if spec["semantic_id"] in {"scene-root", "background-group", "content-group", "text-group", "background"}:
            continue
        matrix = matrix_for(layer_id)
        corners = [
            _point(matrix, 0, 0),
            _point(matrix, spec["width"], 0),
            _point(matrix, spec["width"], spec["height"]),
            _point(matrix, 0, spec["height"]),
        ]
        left, right = min(point[0] for point in corners), max(point[0] for point in corners)
        top, bottom = min(point[1] for point in corners), max(point[1] for point in corners)
        visible = spec["start"] <= absolute_frame < spec["end"] and opacities.get(layer_id, 1) > 0
        item = EffectiveGeometry(
            layer_id=layer_id,
            semantic_id=spec["semantic_id"],
            instance=spec["instance"],
            x=left,
            y=top,
            width=right - left,
            height=bottom - top,
            opacity=opacities.get(layer_id, 1),
            visible=visible,
        )
        output.setdefault(item.semantic_id, []).append(item)
    return output
