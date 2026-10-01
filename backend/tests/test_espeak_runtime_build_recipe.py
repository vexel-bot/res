from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "workers" / "speech-cpu" / "Dockerfile.espeak-runtime"
WORKFLOW = ROOT / ".github" / "workflows" / "studios-speech-espeak-runtime.yml"


def test_espeak_runtime_recipe_is_exact_non_deployable_artifact_export():
    recipe = DOCKERFILE.read_text(encoding="utf-8")

    assert "7d426728fe146f4168fa716e29d8e276c7da33f2" in recipe
    assert "sha256:272efc3f94bec901e2bc7a5c9984b3d113c317839edca2714c6a388b9476f8fc" in recipe
    assert "-DBUILD_SHARED_LIBS=ON" in recipe
    assert "-DUSE_LIBSONIC=OFF" in recipe
    assert "-DUSE_MBROLA=OFF" in recipe
    assert "-DUSE_SPEECHPLAYER=OFF" in recipe
    assert "espeak-ng-COPYING" in recipe
    assert "espeak-ng.tar.gz" in recipe
    assert "FROM scratch" in recipe
    assert "CMD" not in recipe
    assert "ENTRYPOINT" not in recipe


def test_espeak_runtime_workflow_stays_manual_and_does_not_push_or_deploy():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "push: false" in workflow
    assert "outputs: type=local" in workflow
    assert "generate_espeak_runtime_manifest.py" in workflow
    assert "--output=.candidate-build/espeak-ng.tar.gz" in workflow
    assert "7d426728fe146f4168fa716e29d8e276c7da33f2" in workflow
    assert "08721baf27d13d461f6be6eed9a65277e70d68234ff484fd8b9897b222cdcb6d" in workflow
    assert "kubectl" not in workflow
    assert "docker/login-action" not in workflow
