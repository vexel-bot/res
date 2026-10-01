from app.domain.studios.motion import MotionGraphProjectionV1
from app.providers.studios.motion_canvas_projection import compile_motion_canvas_manifest


def test_motion_canvas_adapter_emits_data_without_executable_code():
    projection = MotionGraphProjectionV1.model_validate(
        {
            "target": "motion_canvas",
            "sourceGraphId": "graph-1",
            "sourceGraphDigestSha256": "a" * 64,
            "frameRate": {"numerator": 30, "denominator": 1},
            "durationFrames": 30,
            "nodes": [],
            "tracks": [
                {
                    "sourceTrackId": "track-1",
                    "targetLayerId": "layer-1",
                    "propertyPath": "position.x",
                    "unit": "pixels",
                    "keyframes": [
                        {"frame": 0, "value": 0, "easing": "ease_out"},
                        {"frame": 29, "value": 100, "easing": "hold"},
                    ],
                }
            ],
            "previewOnly": True,
        }
    )
    result = compile_motion_canvas_manifest(projection)
    assert result["runtimeStatus"] == "adapter_only"
    assert result["executableCodeIncluded"] is False
    assert result["projection"]["tracks"][0]["propertyPath"] == "position.x"
