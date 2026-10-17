import pytest
from test_scene_compiler_v2 import direction, document

from app.domain.studios.composition_geometry import evaluate_scene_geometry
from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.services.studios.scene_compiler import compile_scenes


def test_group_rotation_scale_and_origin_are_composed_for_audit_bounds():
    request = direction()
    scene = request.scenes[0]
    scene.elements = [
        {
            "id": "group",
            "kind": "group",
            "purpose": "Mover o conjunto",
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 200,
            "durationFrames": 120,
            "originX": 0.5,
            "originY": 0.5,
            "animations": [
                {
                    "property": "scale_x",
                    "keyframes": [{"frame": 0, "value": 2}, {"frame": 119, "value": 2}],
                },
                {
                    "property": "scale_y",
                    "keyframes": [{"frame": 0, "value": 2}, {"frame": 119, "value": 2}],
                },
                {
                    "property": "rotation_degrees",
                    "keyframes": [{"frame": 0, "value": 90}, {"frame": 119, "value": 90}],
                },
            ],
        },
        {
            "id": "child",
            "kind": "shape",
            "purpose": "Forma articulada",
            "parentId": "group",
            "x": 50,
            "y": 0,
            "width": 100,
            "height": 50,
            "durationFrames": 120,
            "visualRole": "hero",
        },
    ]
    request = ContextualPlanRequestV2.model_validate(request.model_dump(mode="json", by_alias=True))
    _, graph, _, _ = compile_scenes(document(), request, "user", "plan")

    geometry = evaluate_scene_geometry(
        scene=request.scenes[0],
        graph=graph,
        scene_start=0,
        local_frame=60,
        canvas_width=640,
        canvas_height=640,
    )
    child = geometry["child"][0]

    assert child.width == pytest.approx(100)
    assert child.height == pytest.approx(200)
    assert (child.x, child.y) != pytest.approx((150, 100))
    assert child.visible is True


def test_nested_parent_opacity_affects_effective_visibility():
    request = direction()
    scene = request.scenes[0]
    scene.elements = [
        {
            "id": "group",
            "kind": "group",
            "purpose": "Grupo oculto",
            "width": 200,
            "height": 200,
            "durationFrames": 120,
            "depthTreatment": {"opacity": 0},
        },
        {
            "id": "child",
            "kind": "shape",
            "purpose": "Filho",
            "parentId": "group",
            "width": 100,
            "height": 100,
            "durationFrames": 120,
            "visualRole": "hero",
        },
    ]
    request = ContextualPlanRequestV2.model_validate(request.model_dump(mode="json", by_alias=True))
    _, graph, _, _ = compile_scenes(document(), request, "user", "plan")

    child = evaluate_scene_geometry(request.scenes[0], graph, 0, 20, 640, 640)["child"][0]

    assert child.opacity == 0
    assert child.visible is False
