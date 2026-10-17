import hashlib
import importlib.util
import sys
import types
from pathlib import Path


def _module():
    root = Path(__file__).resolve().parents[2] / "workers" / "media-generation-local"
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("res_local_diffusion_model_store", root / "model_store.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_provision_verifies_artifacts_then_creates_receipt(tmp_path, monkeypatch):
    module = _module()
    content = b"pinned-test-weight"
    checksum = hashlib.sha256(content).hexdigest()
    profile = {
        "profileId": "test-profile-v1",
        "repositories": [
            {
                "id": "test/repository",
                "revision": "pinned-revision",
                "allowPatterns": ["model.safetensors"],
                "artifacts": [
                    {
                        "path": "model.safetensors",
                        "sizeBytes": len(content),
                        "sha256": checksum,
                    }
                ],
            }
        ],
    }
    profile_root = tmp_path / "profiles" / profile["profileId"]
    monkeypatch.setattr(module, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(module, "get_profile", lambda _: profile)
    monkeypatch.setattr(module, "inspect", lambda **_: {"status": "admitted"})
    monkeypatch.setattr(module, "profile_directory", lambda _: profile_root)
    monkeypatch.setattr(module, "repository_directory", lambda *_: profile_root / "test--repository")

    hub = types.ModuleType("huggingface_hub")

    def snapshot_download(**kwargs):
        target = Path(kwargs["local_dir"])
        (target / "model.safetensors").write_bytes(content)

    hub.snapshot_download = snapshot_download
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)

    receipt = module.provision(profile["profileId"])

    assert receipt["status"] == "ready"
    assert (profile_root / "provision-receipt.json").is_file()
    assert module.status(profile["profileId"])["status"] == "ready"
