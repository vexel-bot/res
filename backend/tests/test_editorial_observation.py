from types import SimpleNamespace

from test_contextual_editing import ffmpeg

from app.providers.studios.editorial_observation import observe_render


def test_encoded_pixels_reveal_static_interval_without_claiming_quality(tmp_path):
    path = tmp_path / "still.mp4"
    ffmpeg("-f", "lavfi", "-i", "color=blue:s=160x160:r=25:d=3", "-c:v", "libx264", path)
    result = observe_render(path, scenes=[SimpleNamespace(id="explanation", duration_frames=75)], frame_rate=25)
    assert result["nearStaticSampleRatio"] == 1
    assert result["findings"][0]["sceneId"] == "explanation"
    assert result["audioStreamPresent"] is False
    assert result["humanReview"] == "pending"
    assert result["editorialQuality"] == "unreviewed"
    assert result["speechIntelligibility"] == "unknown"


def test_observation_reports_bounded_coverage(tmp_path):
    path = tmp_path / "motion.mp4"
    ffmpeg("-f", "lavfi", "-i", "testsrc2=s=160x160:r=25:d=3", "-c:v", "libx264", path)
    result = observe_render(path, max_seconds=1)
    assert result["coverageSeconds"] == 1
    assert result["durationSeconds"] > result["coverageSeconds"]
    assert result["nearStaticSampleRatio"] < 1
    assert result["status"] == "partial"
