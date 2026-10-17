from __future__ import annotations

import hashlib
import re
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from uuid import uuid4

from ..config import Settings, get_settings

SAFE_SCOPE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SAFE_ZONES = {"raw", "derived", "exports", "identity", "voice", "temporary"}


@dataclass(frozen=True)
class StoredObject:
    key: str
    backend: str
    size_bytes: int
    checksum_sha256: str
    media_type: str
    metadata: dict[str, str]


class ObjectStorage(Protocol):
    backend: str

    def put_file(
        self,
        source: Path,
        *,
        key: str,
        media_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

    def local_path(self, key: str) -> Path | None: ...

    def signed_download_url(self, key: str, *, filename: str | None = None) -> str | None: ...

    @contextmanager
    def materialize(self, key: str) -> Iterator[Path]: ...


def object_key(workspace_id: str, zone: str, suffix: str) -> str:
    if not SAFE_SCOPE.fullmatch(workspace_id):
        raise ValueError("invalid_object_storage_scope")
    if zone not in SAFE_ZONES:
        raise ValueError("invalid_object_storage_zone")
    normalized_suffix = suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", normalized_suffix):
        raise ValueError("invalid_object_storage_suffix")
    return f"{workspace_id}/{zone}/{uuid4().hex}{normalized_suffix}"


def normalize_key(key: str) -> PurePosixPath:
    if not key or "\\" in key:
        raise ValueError("invalid_object_storage_key")
    normalized = PurePosixPath(key)
    if normalized.is_absolute() or any(part in {"", ".", ".."} for part in normalized.parts):
        raise ValueError("invalid_object_storage_key")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class LocalObjectStorage:
    backend = "local"

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        relative = normalize_key(key)
        candidate = self.root.joinpath(*relative.parts).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("object_storage_key_escaped_root")
        return candidate

    def put_file(
        self,
        source: Path,
        *,
        key: str,
        media_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        destination = self._path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # A duplicate key belongs to an existing object; never delete it while
        # cleaning up a failed exclusive create.
        output = destination.open("xb")
        try:
            with output, source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output, length=1024 * 1024)
        except Exception:
            self.delete(key)
            raise
        return StoredObject(
            key=key,
            backend=self.backend,
            size_bytes=destination.stat().st_size,
            checksum_sha256=sha256_file(destination),
            media_type=media_type,
            metadata=dict(metadata or {}),
        )

    def delete(self, key: str) -> None:
        path = self._path(key)
        path.unlink(missing_ok=True)
        parent = path.parent
        while parent != self.root and self.root in parent.parents:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def local_path(self, key: str) -> Path | None:
        path = self._path(key)
        return path if path.is_file() else None

    def signed_download_url(self, key: str, *, filename: str | None = None) -> str | None:
        return None

    @contextmanager
    def materialize(self, key: str) -> Iterator[Path]:
        path = self.local_path(key)
        if path is None:
            raise FileNotFoundError(key)
        yield path


class S3ObjectStorage:
    backend = "s3"

    def __init__(self, settings: Settings) -> None:
        if not settings.object_storage_bucket:
            raise RuntimeError("object_storage_bucket_not_configured")
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as error:  # pragma: no cover - guarded by production dependencies
            raise RuntimeError("boto3_not_installed") from error
        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": settings.object_storage_region,
        }
        if settings.object_storage_endpoint_url:
            kwargs["endpoint_url"] = settings.object_storage_endpoint_url
        if settings.object_storage_access_key:
            kwargs["aws_access_key_id"] = settings.object_storage_access_key
            kwargs["aws_secret_access_key"] = settings.object_storage_secret_key
        self.client = boto3.client(**kwargs)
        self.client_error = ClientError
        self.bucket = settings.object_storage_bucket
        self.expires_seconds = settings.object_storage_signed_url_seconds

    def put_file(
        self,
        source: Path,
        *,
        key: str,
        media_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        normalize_key(key)
        digest = sha256_file(source)
        object_metadata = {**(metadata or {}), "sha256": digest}
        self.client.upload_file(
            str(source),
            self.bucket,
            key,
            ExtraArgs={"ContentType": media_type, "Metadata": object_metadata},
        )
        return StoredObject(
            key=key,
            backend=self.backend,
            size_bytes=source.stat().st_size,
            checksum_sha256=digest,
            media_type=media_type,
            metadata=object_metadata,
        )

    def delete(self, key: str) -> None:
        normalize_key(key)
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        normalize_key(key)
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except self.client_error as error:
            status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status == 404:
                return False
            raise
        return True

    def local_path(self, key: str) -> Path | None:
        normalize_key(key)
        return None

    def signed_download_url(self, key: str, *, filename: str | None = None) -> str | None:
        normalize_key(key)
        params = {"Bucket": self.bucket, "Key": key}
        if filename:
            escaped = filename.replace('"', "")
            params["ResponseContentDisposition"] = f'attachment; filename="{escaped}"'
        return self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=self.expires_seconds,
        )

    @contextmanager
    def materialize(self, key: str) -> Iterator[Path]:
        normalize_key(key)
        suffix = PurePosixPath(key).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            path = Path(temporary.name)
        try:
            self.client.download_file(self.bucket, key, str(path))
            yield path
        finally:
            path.unlink(missing_ok=True)


def get_object_storage(backend: str | None = None, settings: Settings | None = None) -> ObjectStorage:
    active_settings = settings or get_settings()
    selected = backend or active_settings.object_storage_backend
    if selected == "local":
        return LocalObjectStorage(active_settings.storage_path)
    if selected == "s3":
        return S3ObjectStorage(active_settings)
    raise ValueError("unsupported_object_storage_backend")
