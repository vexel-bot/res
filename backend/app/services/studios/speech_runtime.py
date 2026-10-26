"""Resolve trusted deployment configuration without promoting any candidate."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError, field_validator, model_validator
from sqlalchemy import select

from ...config import get_settings
from ...domain.studios.contracts import StudioContract
from ...domain.studios.execution import OPENVOICE_CPU_PROVIDER, execution_profile
from ...domain.studios.providers import SPEECH_PROVIDERS, VOICE_CLONE_PROVIDERS
from ...models import StudioProviderRegistration
from ...providers.studios.kokoro_docker import KokoroDockerSpeechProvider
from ...providers.studios.kokoro_stock import KokoroStockConfig
from ...providers.studios.openvoice_cpu import create_openvoice_cpu_provider
from ...providers.studios.voice_clone_sidecar import (
    create_chatterbox_sidecar_provider,
    create_openvoice_sidecar_provider,
)
from .jobs import require_speech_provider_admission
from .worker_runtime import load_worker_manifest, manifest_digest


class RuntimeBase(StudioContract):
    worker_manifest_path: Path
    worker_image_digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    timeout_seconds: float = Field(default=1800, ge=1, le=7200, allow_inf_nan=False)

    @field_validator("worker_manifest_path")
    @classmethod
    def absolute_path(cls, value):
        if not value.is_absolute():
            raise ValueError("absolute_runtime_path_required")
        return value


class KokoroRuntime(RuntimeBase):
    kind: Literal["kokoro-docker"]
    docker_executable: Path
    source_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    model_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    model_digest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    cpu_hourly_cost_usd: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("docker_executable")
    @classmethod
    def absolute_executable(cls, value):
        return cls.absolute_path(value)

    @property
    def provider(self):
        return "kokoro-82m-stock"

    @property
    def job_type(self):
        return "stock_voice"


class CloneRuntime(RuntimeBase):
    kind: Literal["chatterbox-multilingual-v3", "chatterbox-pt-br", "kokoro-openvoice-v2"]
    manifest_path: Path
    asset_root: Path
    command: tuple[str, ...] = Field(min_length=1, max_length=16)
    gpu_hourly_cost_usd: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("manifest_path", "asset_root")
    @classmethod
    def absolute_assets(cls, value):
        return cls.absolute_path(value)

    @field_validator("command")
    @classmethod
    def absolute_command(cls, value):
        if not Path(value[0]).is_absolute() or any("\0" in arg for arg in value):
            raise ValueError("absolute_runtime_command_required")
        return value

    @property
    def provider(self):
        return "candidate." + self.kind

    @property
    def job_type(self):
        return "voice_clone"


class OpenVoiceCPURuntime(RuntimeBase):
    kind: Literal["kokoro-openvoice-cpu-docker"]
    docker_executable: Path
    manifest_path: Path
    asset_root: Path
    kokoro_manifest_path: Path
    kokoro_repository: Path
    cpu_hourly_cost_usd: float = Field(gt=0, allow_inf_nan=False)

    @field_validator("docker_executable", "manifest_path", "asset_root", "kokoro_manifest_path", "kokoro_repository")
    @classmethod
    def absolute_cpu_paths(cls, value):
        return cls.absolute_path(value)

    @property
    def provider(self):
        return OPENVOICE_CPU_PROVIDER

    @property
    def job_type(self):
        return "voice_clone"


class SpeechRuntimeConfigurationV1(StudioContract):
    schema_version: Literal["studio.speech-runtime-config.v1"]
    runtimes: list[Annotated[KokoroRuntime | CloneRuntime | OpenVoiceCPURuntime, Field(discriminator="kind")]] = Field(
        max_length=5
    )

    @model_validator(mode="after")
    def unique_provider(self):
        providers = [item.provider for item in self.runtimes]
        if len(providers) != len(set(providers)):
            raise ValueError("duplicate_speech_runtime")
        return self


def load_speech_runtime_configuration():
    filename = get_settings().studio_speech_runtime_config_file
    if not filename:
        return None
    path = Path(filename)
    try:
        if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            raise ValueError("invalid_runtime_configuration_file")
        return SpeechRuntimeConfigurationV1.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, ValidationError) as exc:
        raise ValueError("speech_runtime_configuration_invalid") from exc


def _construct(spec, worker_digest):
    if isinstance(spec, OpenVoiceCPURuntime):
        return create_openvoice_cpu_provider(
            manifest_path=spec.manifest_path,
            asset_root=spec.asset_root,
            kokoro_manifest_path=spec.kokoro_manifest_path,
            kokoro_repository=spec.kokoro_repository,
            worker_manifest_digest_sha256=worker_digest,
            worker_image_digest=spec.worker_image_digest,
            docker_executable=spec.docker_executable,
            cpu_hourly_cost_usd=spec.cpu_hourly_cost_usd,
            timeout_seconds=spec.timeout_seconds,
        )
    if isinstance(spec, KokoroRuntime):
        return KokoroDockerSpeechProvider(
            KokoroStockConfig(
                source_revision=spec.source_revision,
                model_revision=spec.model_revision,
                model_digest_sha256=spec.model_digest_sha256,
                worker_manifest_digest_sha256=worker_digest,
                worker_image_digest=spec.worker_image_digest,
                cpu_hourly_cost_usd=spec.cpu_hourly_cost_usd,
            ),
            docker_executable=spec.docker_executable,
            timeout_seconds=spec.timeout_seconds,
        )
    arguments = {
        "manifest_path": spec.manifest_path,
        "asset_root": spec.asset_root,
        "worker_manifest_digest_sha256": worker_digest,
        "worker_image_digest": spec.worker_image_digest,
        "command": spec.command,
        "gpu_hourly_cost_usd": spec.gpu_hourly_cost_usd,
        "timeout_seconds": spec.timeout_seconds,
    }
    if spec.kind == "kokoro-openvoice-v2":
        return create_openvoice_sidecar_provider(**arguments)
    return create_chatterbox_sidecar_provider(candidate_id=spec.kind, **arguments)


def resolve_speech_provider(db, *, job_type, provider_name):
    """Recheck admission every time; keep process-local plugin registries intact."""
    if job_type not in {"stock_voice", "voice_clone"}:
        raise ValueError("speech_job_type_required")
    registry = SPEECH_PROVIDERS if job_type == "stock_voice" else VOICE_CLONE_PROVIDERS
    existing = registry.get(provider_name)
    if existing is not None:
        require_speech_provider_admission(
            db,
            job_type=job_type,
            provider_name=provider_name,
            provider_version=existing.version,
            model_digest_sha256=getattr(getattr(existing, "config", None), "model_digest_sha256", None),
        )
        return existing
    configuration = load_speech_runtime_configuration()
    spec = (
        next(
            (item for item in configuration.runtimes if item.provider == provider_name and item.job_type == job_type),
            None,
        )
        if configuration
        else None
    )
    if spec is None:
        return None
    require_speech_provider_admission(db, job_type=job_type, provider_name=provider_name)
    worker = load_worker_manifest(spec.worker_manifest_path)
    if (
        job_type not in worker.job_types
        or provider_name not in worker.providers
        or worker.capability != execution_profile(job_type, provider_name).capability
    ):
        raise ValueError("speech_runtime_worker_not_advertised")
    digest = manifest_digest(worker)
    adapter = _construct(spec, digest)
    config = adapter.config
    require_speech_provider_admission(
        db,
        job_type=job_type,
        provider_name=provider_name,
        provider_version=adapter.version,
        model_digest_sha256=config.model_digest_sha256,
    )
    registration = db.scalar(
        select(StudioProviderRegistration).where(
            StudioProviderRegistration.provider == provider_name,
            StudioProviderRegistration.capability == job_type,
            StudioProviderRegistration.provider_version == adapter.version,
            StudioProviderRegistration.status == "approved",
        )
    )
    expected = {
        "schemaVersion": "studio.speech-runtime-binding.v1",
        "kind": spec.kind,
        "sourceRevision": config.source_revision,
        "modelDigestSha256": config.model_digest_sha256,
        "workerManifestDigestSha256": digest,
        "workerImageDigest": spec.worker_image_digest,
    }
    if (
        registration.source_revision != config.source_revision
        or (registration.manifest or {}).get("runtimeBinding") != expected
    ):
        raise ValueError("speech_runtime_registration_binding_mismatch")
    return adapter
