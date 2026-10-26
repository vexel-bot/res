"""CPU adapter/asset contracts with fake runtime objects; not clone quality evidence."""

import hashlib
import importlib.util
import io
import json
import sys
import tomllib
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from test_openvoice_model_assets import _tiny_manifest

from scripts import download_openvoice_model_assets as downloader

ROOT = Path(__file__).resolve().parents[2]


def sidecar():
    filename = ROOT / "workers/speech-gpu/sidecars/kokoro_openvoice_clone.py"
    spec = importlib.util.spec_from_file_location("clicko_openvoice_cpu_device_fixture", filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_modules(monkeypatch):
    calls = []

    class Model:
        def to(self, device):
            calls.append(("model_device", device))
            return self

        def eval(self):
            return self

    class Converter:
        def __init__(self, filename, *, device, enable_watermark):
            calls.append(("converter", device, enable_watermark))

        def load_ckpt(self, filename):
            calls.append(("checkpoint", str(filename)))

    for name in ("librosa", "numpy", "soundfile"):
        monkeypatch.setitem(sys.modules, name, ModuleType(name))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
    monkeypatch.setitem(sys.modules, "wavmark", SimpleNamespace(load_model=lambda path: Model()))
    monkeypatch.setitem(
        sys.modules,
        "kokoro",
        SimpleNamespace(
            KModel=lambda **kwargs: Model(), KPipeline=lambda **kwargs: calls.append(("pipeline", kwargs["device"]))
        ),
    )
    monkeypatch.setitem(sys.modules, "openvoice", ModuleType("openvoice"))
    monkeypatch.setitem(sys.modules, "openvoice.api", SimpleNamespace(ToneColorConverter=Converter))
    return calls


def test_cpu_is_explicit_and_does_not_require_cuda(monkeypatch, tmp_path):
    module = sidecar()
    calls = fake_modules(monkeypatch)
    runtime = module.LocalKokoroOpenVoiceRuntime(tmp_path / "kokoro", tmp_path / "openvoice", device="cpu")
    assert runtime.device == "cpu"
    assert ("pipeline", "cpu") in calls
    assert ("converter", "cpu", False) in calls
    assert all(call[1] == "cpu" for call in calls if call[0] == "model_device")


def test_default_gpu_runtime_does_not_silently_fall_back_to_cpu(monkeypatch, tmp_path):
    module = sidecar()
    calls = fake_modules(monkeypatch)
    with pytest.raises(RuntimeError, match="cuda_required"):
        module.LocalKokoroOpenVoiceRuntime(tmp_path / "kokoro", tmp_path / "openvoice")
    assert not calls
    with pytest.raises(ValueError, match="execution_device_invalid"):
        module.LocalKokoroOpenVoiceRuntime(tmp_path / "kokoro", tmp_path / "openvoice", device="auto")


def test_cpu_lock_is_frozen_without_cuda_packages():
    lock_path = ROOT / "workers/speech-cpu/openvoice-candidate/uv.lock"
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = {item["name"]: item for item in lock["package"]}
    assert packages["torch"]["version"] == "2.6.0+cpu"
    assert packages["torchaudio"]["version"] == "2.6.0+cpu"
    assert packages["numpy"]["version"] == "1.26.4"
    assert not any(name.startswith("nvidia-") for name in packages)
    assert (
        hashlib.sha256(lock_path.read_bytes()).hexdigest()
        == "3255154038b7bd3896dc51ecec5b0fbb483d0767e592b79eff7f176b6590b6c1"
    )
    patch = ROOT / "workers/speech-gpu/candidate-v2/patches/openvoice-explicit-watermark-toggle.patch"
    assert (
        hashlib.sha256(patch.read_bytes()).hexdigest()
        == "fbc61b661289010fe0815437c464351f71d1107066b2b3781255fc54916d2d92"
    )
    manifest = json.loads((ROOT / "workers/speech-gpu/worker.manifest.json").read_text(encoding="utf-8"))
    assert manifest["providers"] == []


def test_asset_downloader_streams_only_pinned_bytes_and_reuses_verified_files(tmp_path, monkeypatch):
    seed, target = tmp_path / "seed", tmp_path / "download"
    manifest = _tiny_manifest(seed)
    calls = []

    def response(url, timeout):
        calls.append(url)
        entry = next(item for item in manifest.files if url.endswith(item.source_path))
        assert entry.source_revision in url
        return io.BytesIO((seed / entry.runtime_path).read_bytes())

    monkeypatch.setattr(downloader, "urlopen", response)
    assert len(downloader.download(manifest, target)) == 64
    assert len(calls) == 3
    downloader.download(manifest, target)
    assert len(calls) == 3


def test_asset_downloader_never_persists_a_corrupt_checkpoint(tmp_path, monkeypatch):
    seed, target = tmp_path / "seed", tmp_path / "download"
    manifest = _tiny_manifest(seed)
    first = manifest.files[0]
    monkeypatch.setattr(downloader, "urlopen", lambda *args, **kwargs: io.BytesIO(b"x" * first.size_bytes))
    with pytest.raises(ValueError, match="integrity_mismatch"):
        downloader.download(manifest, target)
    assert not any(path.is_file() for path in target.rglob("*"))


def test_kokoro_materialization_preserves_verified_bytes_and_original_cache(tmp_path):
    from test_kokoro_model_assets import _fixture

    snapshot, manifest = _fixture(tmp_path / "source")
    source_repository = snapshot.parent.parent
    target_repository = tmp_path / "flat-models"
    before = {entry.relative_path: (snapshot / entry.relative_path).read_bytes() for entry in manifest.files}
    digest = downloader.materialize_kokoro(manifest, source_repository, target_repository)
    assert len(digest) == 64
    target = target_repository / "snapshots" / manifest.source_revision
    assert {entry.relative_path: (target / entry.relative_path).read_bytes() for entry in manifest.files} == before
    assert all(not path.is_symlink() for path in target.rglob("*"))
    assert {entry.relative_path: (snapshot / entry.relative_path).read_bytes() for entry in manifest.files} == before
    assert downloader.materialize_kokoro(manifest, source_repository, target_repository) == digest


def test_kokoro_materialization_refuses_to_overwrite_a_changed_asset(tmp_path):
    from test_kokoro_model_assets import _fixture

    snapshot, manifest = _fixture(tmp_path / "source")
    target = tmp_path / "flat-models"
    downloader.materialize_kokoro(manifest, snapshot.parent.parent, target)
    voice = target / "snapshots" / manifest.source_revision / "voices/pf_dora.pt"
    voice.write_bytes(b"changed-existing-file")
    with pytest.raises(ValueError, match="asset_(size|checksum)_mismatch"):
        downloader.materialize_kokoro(manifest, snapshot.parent.parent, target)
    assert voice.read_bytes() == b"changed-existing-file"
