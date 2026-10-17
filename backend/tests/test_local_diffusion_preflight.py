import importlib.util
from pathlib import Path


def _preflight_module():
    path = Path(__file__).resolve().parents[2] / "workers" / "media-generation-local" / "preflight.py"
    spec = importlib.util.spec_from_file_location("res_local_diffusion_preflight", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_diffusion_preflight_blocks_before_download_on_current_profile(tmp_path, monkeypatch):
    module = _preflight_module()
    monkeypatch.setattr(
        module,
        "_system_memory_details",
        lambda: {
            "totalPhysicalMiB": 8_000,
            "availablePhysicalMiB": 1_000,
            "totalCommitMiB": 16_000,
            "availableCommitMiB": 1_000,
        },
    )
    monkeypatch.setattr(module, "_gpu_memory_mib", lambda: [{"name": "test", "totalMiB": 4096, "freeMiB": 4000}])
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _: module.shutil._ntuple_diskusage(20_000, 1_000, 19_000),
    )

    result = module.inspect(cache_path=tmp_path)

    assert result["status"] == "blocked_resources"
    assert "insufficient_system_ram" in result["reasons"]
    assert "insufficient_vram" in result["reasons"]
    assert result["modelDownloadStarted"] is False


def test_light_profile_distinguishes_installation_from_busy_execution(tmp_path, monkeypatch):
    module = _preflight_module()
    monkeypatch.setattr(
        module,
        "_system_memory_details",
        lambda: {
            "totalPhysicalMiB": 8_000,
            "availablePhysicalMiB": 400,
            "totalCommitMiB": 24_000,
            "availableCommitMiB": 10_000,
        },
    )
    monkeypatch.setattr(module, "_gpu_memory_mib", lambda: [{"name": "test", "totalMiB": 4096, "freeMiB": 3900}])
    monkeypatch.setattr(
        module.shutil,
        "disk_usage",
        lambda _: module.shutil._ntuple_diskusage(30_000_000_000, 10, 20_000_000_000),
    )

    install = module.inspect(profile_id="animatediff-lightning-sd15-a-v1", cache_path=tmp_path, phase="install")
    execute = module.inspect(profile_id="animatediff-lightning-sd15-a-v1", cache_path=tmp_path, phase="execution")

    assert install["status"] == "admitted"
    assert execute["status"] == "blocked_resources"
    assert execute["reasons"] == ["blocked_current_load"]


def test_profile_inheritance_keeps_pinned_repositories():
    module = _preflight_module()
    profile = module.get_profile("animatediff-lightning-sd15-b-v1")
    assert profile["frames"] == 16
    assert profile["repositories"][0]["revision"] == "027c893eec01df7330f5d4b733bc9485ee02e8b2"


def test_environment_reports_installed_version_different_from_lock(tmp_path, monkeypatch):
    module = _preflight_module()
    lock = tmp_path / "requirements.lock"
    lock.write_text("# lockStatus: qualified\ntorch==0.0.1\n", encoding="utf-8")
    monkeypatch.setattr(module, "LOCK", lock)
    monkeypatch.setattr(
        module.importlib.metadata,
        "version",
        lambda package: "9.9.9",
    )
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 0, "stdout": "1"})(),
    )

    environment = module._environment_status()

    assert environment["lockStatus"] == "unqualified"
    assert environment["versionMismatches"]["torch"] == {
        "locked": "0.0.1",
        "installed": "9.9.9",
    }
    assert len(environment["lockDigestSha256"]) == 64
