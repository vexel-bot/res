from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./nexus.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False
    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 60 * 24
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    ai_base_url: str | None = None
    ai_api_key: str | None = None
    ai_model: str | None = None
    ai_embedding_model: str | None = None
    gemini_api_key_1: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY_1", "API_1"),
    )
    gemini_api_key_2: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY_2", "API_2"),
    )
    gemini_outbound_enabled: bool = False
    gemini_video_generation_enabled: bool = False
    gemini_max_external_spend_usd: float = Field(default=0, ge=0, le=100_000)
    studio_gemini_enabled: bool = False
    studio_editing_ai_provider: Literal["none", "compatible", "gemini"] = "gemini"
    studio_editing_ai_planning_provider: Literal["none", "compatible", "gemini"] | None = None
    studio_editing_ai_image_provider: Literal["none", "gemini"] | None = None
    studio_editing_ai_video_provider: Literal["none", "gemini", "runway", "sora"] | None = None
    studio_runway_enabled: bool = False
    studio_runway_test_key: SecretStr | None = None
    studio_runway_production_key: SecretStr | None = None
    studio_runway_test_budget_usd: float = Field(default=0, ge=0)
    studio_runway_output_hosts: list[str] = Field(default_factory=lambda: ["dnznrvs05pmza.cloudfront.net"])
    studio_editing_ai_base_url: str | None = None
    studio_editing_ai_model: str | None = None
    studio_editing_ai_test_key: SecretStr | None = None
    studio_editing_ai_production_key: SecretStr | None = None
    studio_editing_ai_test_budget_usd: float = Field(default=0, ge=0)
    studio_production_test_budget_usd: float = Field(default=0, ge=0, le=10)
    studio_visual_quality_indicator_enabled: bool = False
    studio_editing_ai_price_version: str = "unpriced"
    studio_editing_ai_input_usd_per_million: float = Field(default=0, ge=0)
    studio_editing_ai_output_usd_per_million: float = Field(default=0, ge=0)
    # A reservation is still reconciled against measured usage. Keep the
    # default used by existing installations, while allowing a local pilot to
    # bind a cheaper model to a smaller explicit floor. The conservative
    # prompt/output worst-case remains the effective lower bound.
    studio_editing_ai_minimum_reservation_usd: float = Field(default=0.10, gt=0, le=1)
    # Contextual V2 compositions can legitimately exceed the former 8K response
    # ceiling. 10K still fits the conservative planning reservation used by the
    # local US$1 pilot while leaving the global bound explicit.
    # Complex multi-scene structured plans can legitimately exceed 10K output
    # tokens. The per-request tariff and production envelope still reserve the
    # worst case before submission.
    studio_editing_ai_max_output_tokens: int = Field(default=4096, ge=256, le=16384)
    studio_editing_ai_max_prompt_chars: int = Field(default=100_000, ge=1_000, le=500_000)
    studio_gemini_production_key: SecretStr | None = None
    studio_gemini_test_key: SecretStr | None = None
    studio_gemini_planning_model: Literal[
        "gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"
    ] = "gemini-3.8-flash"
    studio_gemini_image_model: Literal[
        "gemini-3.1-flash-lite-image", "gemini-3.1-flash-image"
    ] = "gemini-3.1-flash-lite-image"
    studio_gemini_video_model: Literal[
        "gemini-omni-1.1-flash",
        "veo-3.1-lite-generate-preview",
        "veo-3.1-fast-generate-preview",
    ] = "gemini-omni-1.1-flash"
    studio_gemini_test_budget_usd: float = Field(default=0, ge=0)
    studio_gemini_input_usd_per_million: float = Field(default=0, ge=0)
    studio_gemini_output_usd_per_million: float = Field(default=0, ge=0)
    studio_gemini_image_reservation_usd: float = Field(default=0.10, ge=0, le=1)
    studio_resource_hosts: list[str] = Field(default_factory=lambda: ["fonts.gstatic.com"])
    google_fonts_api_key: SecretStr | None = None
    pexels_api_key: SecretStr | None = None
    brandfetch_client_id: SecretStr | None = None
    studio_background_removal_enabled: bool = False
    studio_background_removal_python_path: str | None = None
    studio_background_removal_model_path: str | None = None
    studio_background_removal_model_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    studio_local_vlm_inspection_enabled: bool = False
    studio_local_vlm_python_path: str | None = None
    studio_local_diffusion_enabled: bool = False
    studio_local_diffusion_url: str = "http://127.0.0.1:8094"
    studio_local_diffusion_token: SecretStr | None = Field(default=None, min_length=32)
    studio_longcat_avatar_enabled: bool = False
    studio_longcat_avatar_url: str = "http://127.0.0.1:8095"
    studio_longcat_avatar_token: SecretStr | None = Field(default=None, min_length=32)
    openai_api_key: SecretStr | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_outbound_enabled: bool = False
    openai_video_generation_enabled: bool = False
    openai_max_external_spend_usd: float = Field(default=0, ge=0, le=100_000)
    storage_path: str = "./data/uploads"
    object_storage_backend: Literal["local", "s3"] = "local"
    object_storage_bucket: str | None = None
    object_storage_endpoint_url: str | None = None
    object_storage_region: str = "us-east-1"
    object_storage_access_key: str | None = None
    object_storage_secret_key: str | None = None
    object_storage_signed_url_seconds: int = Field(default=900, ge=60, le=86_400)
    studio_isolated_queues_enabled: bool = False
    studio_worker_manifest_path: str | None = None
    studio_worker_capability: Literal["media_cpu", "speech_cpu", "speech_gpu", "vision_gpu"] | None = None
    studio_worker_instance_id: str | None = Field(default=None, max_length=160)
    studio_worker_image_digest: str | None = Field(default=None, pattern=r"^sha256:[a-f0-9]{64}$")
    studio_acoustic_promotion_hmac_secret: str | None = Field(default=None, min_length=32)
    studio_acoustic_promotion_key_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
    identity_deletion_execution_enabled: bool = False
    ffprobe_path: str = "ffprobe"
    ffprobe_timeout_seconds: int = Field(default=120, ge=5, le=900)
    ffmpeg_path: str = "ffmpeg"
    ffmpeg_timeout_seconds: int = Field(default=1_800, ge=30, le=7_200)
    studio_ugc_font_path: str | None = None
    studio_editing_monthly_budget_cents: int = Field(default=50_000, ge=0)
    studio_editing_infrastructure_reserve_cents: int = Field(default=15_000, ge=0)
    studio_editing_estimated_cents_per_minute: int = Field(default=50, ge=1)
    hyperframes_enabled: bool = False
    hyperframes_local_qualification_enabled: bool = False
    hyperframes_node_path: str = "node"
    hyperframes_cli_path: str | None = None
    hyperframes_timeout_seconds: int = Field(default=7_200, ge=60, le=21_600)
    motion_canvas_enabled: bool = False
    motion_canvas_node_path: str = "node"
    motion_canvas_timeout_seconds: int = Field(default=7_200, ge=60, le=21_600)
    remotion_enabled: bool = False
    remotion_native_enabled: bool = False
    remotion_node_path: str = "node"
    remotion_timeout_seconds: int = Field(default=7_200, ge=60, le=21_600)
    studio_editorial_motion_provider: Literal["hyperframes.contextual-v2", "motion-canvas.contextual-v1", "remotion.contextual-v1", "remotion.contextual-v2"] = "hyperframes.contextual-v2"
    max_external_text_chars: int = 20_000
    rate_limit_requests: int = Field(default=240, ge=1, le=100_000)
    rate_limit_auth_requests: int = Field(default=10, ge=1, le=10_000)
    rate_limit_intensive_requests: int = Field(default=30, ge=1, le=10_000)
    rate_limit_upload_requests: int = Field(default=20, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=86_400)
    radar_contextual_v2_enabled: bool = False
    radar_contextual_v2_shadow_mode: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator(
        "studio_worker_manifest_path",
        "studio_worker_capability",
        "studio_worker_instance_id",
        "studio_worker_image_digest",
        "studio_acoustic_promotion_hmac_secret",
        "studio_acoustic_promotion_key_id",
        "studio_local_diffusion_token",
        "studio_longcat_avatar_token",
        mode="before",
    )
    @classmethod
    def empty_worker_values_are_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    def validate_for_startup(self) -> None:
        if self.environment == "production":
            if self.openai_outbound_enabled or self.openai_video_generation_enabled:
                raise RuntimeError("OpenAI is restricted to local tests")
            if self.secret_key == "development-only-change-me" or len(self.secret_key) < 32:
                raise RuntimeError("SECRET_KEY must be a random value of at least 32 characters")
            if not self.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
                raise RuntimeError("Production requires PostgreSQL")
            if self.celery_task_always_eager:
                raise RuntimeError("CELERY_TASK_ALWAYS_EAGER cannot be enabled in production")
        if self.object_storage_backend == "s3" and not self.object_storage_bucket:
            raise RuntimeError("OBJECT_STORAGE_BUCKET is required when OBJECT_STORAGE_BACKEND=s3")
        if bool(self.object_storage_access_key) != bool(self.object_storage_secret_key):
            raise RuntimeError("Object storage access and secret keys must be configured together")
        if bool(self.studio_worker_manifest_path) != bool(self.studio_worker_capability):
            raise RuntimeError("STUDIO_WORKER_MANIFEST_PATH and STUDIO_WORKER_CAPABILITY must be configured together")
        if bool(self.studio_acoustic_promotion_hmac_secret) != bool(self.studio_acoustic_promotion_key_id):
            raise RuntimeError(
                "STUDIO_ACOUSTIC_PROMOTION_HMAC_SECRET and STUDIO_ACOUSTIC_PROMOTION_KEY_ID must be configured together"
            )
        if self.gemini_outbound_enabled and not (
            self.gemini_api_key_1 or self.gemini_api_key_2
        ):
            raise RuntimeError("Gemini outbound calls require at least one configured API key")
        if self.gemini_video_generation_enabled:
            if not self.gemini_outbound_enabled:
                raise RuntimeError("Gemini video generation requires GEMINI_OUTBOUND_ENABLED=true")
            if self.gemini_max_external_spend_usd <= 0:
                raise RuntimeError(
                    "Gemini video generation requires an explicit positive external spend limit"
                )
        if self.openai_outbound_enabled and not self.openai_api_key:
            raise RuntimeError("OpenAI outbound calls require OPENAI_API_KEY")
        if self.openai_video_generation_enabled:
            if not self.openai_outbound_enabled:
                raise RuntimeError("OpenAI video generation requires OPENAI_OUTBOUND_ENABLED=true")
            if self.openai_max_external_spend_usd <= 0:
                raise RuntimeError(
                    "OpenAI video generation requires an explicit positive external spend limit"
                )
        if self.studio_worker_capability:
            if not self.studio_isolated_queues_enabled:
                raise RuntimeError("Studio workers require STUDIO_ISOLATED_QUEUES_ENABLED=true")
            if self.celery_task_always_eager:
                raise RuntimeError("Studio workers cannot use CELERY_TASK_ALWAYS_EAGER")
            if self.environment == "production" and not self.studio_worker_image_digest:
                raise RuntimeError("Production Studio workers require STUDIO_WORKER_IMAGE_DIGEST")
        if self.hyperframes_enabled:
            local_qualification = (
                self.environment != "production"
                and self.hyperframes_local_qualification_enabled
                and self.celery_task_always_eager
            )
            if not self.studio_isolated_queues_enabled and not local_qualification:
                raise RuntimeError("HyperFrames requires STUDIO_ISOLATED_QUEUES_ENABLED=true")
            if not self.hyperframes_cli_path:
                raise RuntimeError("HYPERFRAMES_CLI_PATH is required when HyperFrames is enabled")
        if self.studio_background_removal_enabled and not (
            self.studio_background_removal_model_path and self.studio_background_removal_model_sha256
        ):
            raise RuntimeError(
                "Background removal requires STUDIO_BACKGROUND_REMOVAL_MODEL_PATH and "
                "STUDIO_BACKGROUND_REMOVAL_MODEL_SHA256"
            )
        if self.studio_local_diffusion_enabled:
            if not self.studio_local_diffusion_token:
                raise RuntimeError("Local diffusion requires STUDIO_LOCAL_DIFFUSION_TOKEN")
            if not self.studio_local_diffusion_url.startswith(("http://127.0.0.1:", "http://localhost:")):
                raise RuntimeError("Local diffusion worker must use a loopback URL")
        if self.studio_longcat_avatar_enabled:
            if not self.studio_longcat_avatar_token:
                raise RuntimeError("LongCat avatar worker requires STUDIO_LONGCAT_AVATAR_TOKEN")
            if not self.studio_longcat_avatar_url.startswith(("http://127.0.0.1:", "http://localhost:")):
                raise RuntimeError("LongCat avatar worker must use a loopback URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
