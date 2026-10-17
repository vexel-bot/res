from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "studios-speech-kokoro-candidate.yml"


def test_candidate_workflow_resolves_all_external_inputs_before_build():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "uv lock --python 3.11" in workflow
    assert "generate_kokoro_model_manifest.py" in workflow
    assert "generate_espeak_runtime_manifest.py" in workflow
    assert "Dockerfile.candidate" in workflow
    assert "KOKORO_MODEL_REVISION: f3ff3571791e39611d31c381e3a41a3af07b4987" in workflow
    assert "ESPEAK_SOURCE_REVISION: 7d426728fe146f4168fa716e29d8e276c7da33f2" in workflow
    assert "ESPEAK_LOADER_WHEEL_DIGEST: 08721baf27d13d461f6be6eed9a65277e70d68234ff484fd8b9897b222cdcb6d" in workflow
    assert "--output=.candidate-build/espeak-ng.tar.gz" in workflow


def test_candidate_workflow_only_exports_oci_and_keeps_provider_unadvertised():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "push: false" in workflow
    assert "provenance: mode=max" in workflow
    assert "sbom: true" in workflow
    assert "--provider-label none" in workflow
    assert "docker/login-action" not in workflow
    assert "kubectl" not in workflow
    assert "providers: [" not in workflow
