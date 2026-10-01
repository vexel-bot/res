"""Workspace catalog over LibraryAsset and the existing object store."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fontTools.ttLib import TTFont, TTLibError
from PIL import Image, ImageFont
from sqlalchemy import select

from ...config import get_settings
from ...domain.studios.contracts import AssetReferenceV1
from ...domain.studios.editing_resources import ResourceMetadataV1
from ...models import LibraryAsset
from ...providers.studios.media_probe import MEDIA_PROBE_PROVIDERS
from ...providers.studios.resource_download import download_resource
from ..object_storage import get_object_storage, object_key, sha256_file
from .compatibility import persist_contract, record_to_contract
from .review_binding import invalidate_linked_post_review


def catalog(db, workspace_id, query="", kind=None, *, asset_id=None):
    import re
    import unicodedata

    def tokens(value):
        value = unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode()
        return set(re.findall(r"[a-z0-9]{3,}", value)) - {"para", "com", "uma", "que", "the", "and"}

    terms = tokens(query)
    statement = (
        select(LibraryAsset)
        .where(LibraryAsset.workspace_id == workspace_id, LibraryAsset.lifecycle_status == "active")
        .order_by(LibraryAsset.created_at.desc())
    )
    if asset_id:
        statement = statement.where(LibraryAsset.id == asset_id)
    items = db.scalars(statement).yield_per(100)
    result = []
    for asset in items:
        metadata = (asset.object_metadata or {}).get("editingResource", {})
        if not asset.storage_key or (kind and metadata.get("kind") != kind):
            continue
        searchable = tokens(
            " ".join(
                [
                    asset.title,
                    *(asset.tags or []),
                    *(
                        str(metadata.get(field, ""))
                        for field in (
                            "description",
                            "framing",
                            "focal_point",
                            "focalPoint",
                            "negative_space",
                            "negativeSpace",
                            "motion_description",
                            "motionDescription",
                            "editorial_function",
                            "editorialFunction",
                            "energy",
                        )
                    ),
                ]
            )
        )
        score = 4 * len(terms & tokens(asset.title)) + len(terms & searchable)
        if not terms or score:
            result.append(
                {
                    "relevanceScore": score,
                    "id": asset.id,
                    "title": asset.title,
                    "mediaType": asset.media_type,
                    "checksum": asset.checksum_sha256,
                    "resource": metadata,
                    "reviewStatus": (asset.object_metadata or {}).get("visualReview"),
                    "generationJobId": (asset.object_metadata or {}).get("generationJobId"),
                    "url": f"/api/v1/assets/{asset.id}/content",
                }
            )
    # Score the complete tenant catalog before limiting candidates. A missing query
    # term is uncertainty for the resolver, not proof that a resource is irrelevant.
    return sorted(result, key=lambda item: -item["relevanceScore"])[:100]


def validate_resource(path: Path, metadata: ResourceMetadataV1):
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("resource_too_large")
    if metadata.kind == "font":
        try:
            with TTFont(path) as font:
                if font.flavor is not None:
                    raise ValueError("resource_use_ttf_or_otf")
                cmap = font.getBestCmap() or {}
                if not all(ord(c) in cmap for c in "Aa09áéíóúãõçÁÉÍÓÚÃÕÇ"):
                    raise ValueError("resource_font_missing_portuguese_glyphs")
                family = font["name"].getDebugName(1)
        except (TTLibError, KeyError) as error:
            raise ValueError("resource_font_invalid") from error
        ImageFont.truetype(str(path), 24)
        return "font/otf" if path.read_bytes()[:4] == b"OTTO" else "font/ttf", {"family": family}
    if metadata.kind in {"logo", "image", "wardrobe"}:
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > 50_000_000:
                raise ValueError("resource_image_unsupported")
            info = {"width": image.width, "height": image.height}
            mime = Image.MIME[image.format]
            image.verify()
        return mime, info
    with path.open("rb") as source:
        header = source.read(12)
    if metadata.kind == "video":
        if header[4:8] != b"ftyp":
            raise ValueError("resource_mp4_required")
        mime = "video/mp4"
    elif header[:4] == b"RIFF" and header[8:12] == b"WAVE":
        mime = "audio/wav"
    elif header[:4] == b"fLaC":
        mime = "audio/flac"
    elif header[:3] == b"ID3" or (len(header) >= 2 and header[0] == 255 and header[1] & 224 == 224):
        mime = "audio/mpeg"
    else:
        raise ValueError("resource_audio_format_unsupported")
    probe = MEDIA_PROBE_PROVIDERS["builtin.ffprobe"].probe(path, asset_id="resource", checksum_sha256=None)
    if metadata.kind == "video" and not probe.video_streams:
        raise ValueError("resource_video_required")
    if metadata.kind in {"music", "sound_effect"} and not probe.audio_streams:
        raise ValueError("resource_audio_required")
    return mime, {
        "durationMicroseconds": probe.duration_microseconds,
        "probe": probe.model_dump(mode="json", by_alias=True),
    }


def store_resource(db, workspace_id, title, path, metadata, user_id, *, provenance=None):
    vector_origin = None
    if metadata.kind in {"logo", "image", "wardrobe"}:
        with path.open("rb") as source:
            signature = source.read(1024).lstrip(b"\xef\xbb\xbf \n\r\t")
        if signature.startswith((b"<svg", b"<?xml")):
            import subprocess
            import sys

            from ...providers.studios.svg_raster import validate_svg

            if path.stat().st_size > 1024 * 1024:
                raise ValueError("resource_svg_too_large")
            validate_svg(path.read_bytes())
            vector_origin = {
                "sourceChecksum": sha256_file(path),
                "renderer": "resvg-py-0.5.0",
            }
            converted = path.with_suffix(".converted.png")
            try:
                subprocess.run(
                    [sys.executable, "-m", "app.providers.studios.svg_raster", str(path), str(converted)],
                    check=True,
                    capture_output=True,
                    timeout=20,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (subprocess.SubprocessError, OSError) as error:
                raise ValueError("resource_svg_conversion_failed") from error
            path = converted
    mime, technical = validate_resource(path, metadata)
    if vector_origin:
        technical["vectorSource"] = vector_origin
    checksum = sha256_file(path)
    existing_items = db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.checksum_sha256 == checksum,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    requested_metadata = metadata.model_dump(mode="json", by_alias=True)
    for existing in existing_items:
        prior = (existing.object_metadata or {}).get("editingResource", {})
        if (
            not provenance
            and not (existing.object_metadata or {}).get("derivation")
            and existing.title == title
            and all(prior.get(key) == value for key, value in requested_metadata.items())
            and prior.get("technical", {}).get("vectorSource", {}).get("sourceChecksum")
            == (vector_origin or {}).get("sourceChecksum")
        ):
            return existing
    extension = {
        "font/ttf": ".ttf",
        "font/otf": ".otf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/flac": ".flac",
    }[mime]
    storage = get_object_storage()
    stored = storage.put_file(path, key=object_key(workspace_id, "raw", extension), media_type=mime)
    item = LibraryAsset(
        workspace_id=workspace_id,
        title=title,
        asset_type={
            "font": "document",
            "logo": "image",
            "wardrobe": "image",
            "music": "audio",
            "sound_effect": "audio",
        }.get(metadata.kind, metadata.kind),
        tags=metadata.tags,
        storage_key=stored.key,
        storage_backend=stored.backend,
        media_type=mime,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        object_metadata={
            "editingResource": {
                **metadata.model_dump(mode="json", by_alias=True),
                "technical": technical,
                "importedBy": user_id,
                "importedAt": datetime.now(UTC).isoformat(),
            },
            **(provenance or {}),
        },
    )
    db.add(item)
    db.flush()
    return item


def import_resource(db, workspace_id, request, user_id):
    with tempfile.TemporaryDirectory(prefix="res-resource-") as directory:
        path = Path(directory) / "download"
        url = download_resource(request.url, path, get_settings().studio_resource_hosts)
        metadata = ResourceMetadataV1.model_validate(request.model_dump(exclude={"title", "url"}))
        metadata.source_url = url
        return store_resource(db, workspace_id, request.title, path, metadata, user_id)


def attach_resource(db, record, asset_id, expected_revision):
    db.refresh(record, with_for_update=True)
    if record.revision != expected_revision:
        raise ValueError("studio_document_conflict")
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == asset_id,
            LibraryAsset.workspace_id == record.workspace_id,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if not asset or not asset.storage_key:
        raise ValueError("resource_not_found")
    if (asset.object_metadata or {}).get("derivation") and (asset.object_metadata or {}).get(
        "visualReview"
    ) != "passed":
        raise ValueError("resource_visual_review_required")
    contract = record_to_contract(record)
    if asset.id not in {a.id for a in contract.assets}:
        metadata = (asset.object_metadata or {}).get("editingResource", {})
        if not metadata.get("usageEvidence"):
            raise ValueError("resource_usage_evidence_required")
        contract.assets.append(
            AssetReferenceV1(
                id=asset.id,
                media_type=asset.media_type,
                checksum=asset.checksum_sha256,
                version=asset.checksum_sha256,
                rights_status="verified",
                origin="generated" if (asset.object_metadata or {}).get("derivation") else "workspace",
                provenance=asset.object_metadata or {},
            )
        )
        contract.revision += 1
        contract.updated_at = datetime.now(UTC)
        persist_contract(record, contract)
        invalidate_linked_post_review(db, record)
        db.flush()
    return contract


def resolve_resource(db, workspace_id, request):
    candidates = catalog(db, workspace_id, request.query, request.kind)
    candidates = [c for c in candidates if not c.get("reviewStatus") or c["reviewStatus"] == "passed"]
    if request.exact:
        candidates = [c for c in candidates if c["title"].casefold() == request.query.casefold()]
    if request.document_id:
        from ...models import CreativeDocument

        record = db.get(CreativeDocument, request.document_id)
        if not record or record.workspace_id != workspace_id:
            raise ValueError("resource_document_not_found")
        ids = {a.id for a in record_to_contract(record).assets}
        candidates.sort(key=lambda c: c["id"] not in ids)
    return {
        "status": "resolved" if candidates else "awaiting_choice",
        "candidates": candidates,
        "sources": registered_sources(db, workspace_id, request.query, request.kind),
        "alternatives": []
        if candidates
        else [
            {"action": "import", "label": "Importar arquivo ou URL de fonte cadastrada"},
            {"action": "generate", "label": "Gerar material com Gemini"}
            if request.kind in {"image", "wardrobe", "video"}
            else {"action": "wait", "label": "Adicionar um arquivo ao acervo"},
        ],
    }


def register_source(db, workspace_id, request, user_id):
    from urllib.parse import urlsplit

    from ...domain.studios.contextual_editing import digest
    from ...models import KnowledgeDocument

    url = urlsplit(request.url)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.port not in (None, 443):
        raise ValueError("resource_source_https_required")
    payload = request.model_dump(mode="json", by_alias=True)
    fingerprint = digest({"registeredEditingSource": payload})
    record = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.content_hash == fingerprint
        )
    )
    if not record:
        record = KnowledgeDocument(
            workspace_id=workspace_id,
            title=request.title,
            source_type="editing-resource-source",
            source_url=request.url,
            content_hash=fingerprint,
            status="ready",
            embedding_status="unconfigured",
            document_metadata={"source": payload, "registeredBy": user_id},
        )
        db.add(record)
        db.flush()
    return {"id": record.id, **record.document_metadata["source"]}


def registered_sources(db, workspace_id, query="", kind=None):
    from ...models import KnowledgeDocument

    records = db.scalars(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.workspace_id == workspace_id,
            KnowledgeDocument.source_type == "editing-resource-source",
            KnowledgeDocument.status == "ready",
        )
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(1000)
    ).all()
    result = []
    terms = query.casefold().split()
    for record in records:
        source = (record.document_metadata or {}).get("source", {})
        searchable = " ".join(
            [source.get("title", ""), source.get("description", ""), *source.get("tags", [])]
        ).casefold()
        if (not kind or source.get("kind") == kind) and all(t in searchable for t in terms):
            result.append({"id": record.id, **source})
    return result[:100]


def acquire_registered_source(db, workspace_id, source_id, user_id, *, automatic=False):
    from urllib.parse import urlsplit

    from ...domain.studios.editing_resources import RegisteredEditingSourceV1
    from ...models import KnowledgeDocument

    record = db.get(KnowledgeDocument, source_id)
    if (
        not record
        or record.workspace_id != workspace_id
        or record.source_type != "editing-resource-source"
        or record.status != "ready"
    ):
        raise ValueError("resource_source_not_found")
    source = RegisteredEditingSourceV1.model_validate(record.document_metadata["source"])
    if automatic and not source.auto_acquire:
        raise ValueError("resource_source_manual_acquisition_required")
    with tempfile.TemporaryDirectory(prefix="res-source-") as directory:
        path = Path(directory) / "resource"
        # The exact URL was registered by this workspace. Public DNS is still pinned and validated.
        url = download_resource(
            source.url, path, [urlsplit(source.url).hostname, *get_settings().studio_resource_hosts]
        )
        metadata = ResourceMetadataV1.model_validate(source.model_dump(include=set(ResourceMetadataV1.model_fields)))
        metadata.source_url = source.source_url or url
        item = store_resource(db, workspace_id, source.title, path, metadata, user_id)
    record.document_metadata = {
        **record.document_metadata,
        "lastSuccessfulAcquisitionAt": datetime.now(UTC).isoformat(),
        "lastAssetId": item.id,
        "lastChecksum": item.checksum_sha256,
    }
    db.flush()
    return item


def apply_generated_resource(db, record, request):
    """Replace one verified source interval; retain neighboring footage and timeline timing."""
    from ...domain.studios.contracts import CreativeDocumentV1, SourceTimeRangeV1, TimelineFrameRangeV1
    from ...domain.studios.editing_resources import EditingAIRequestV1
    from ...models import StudioGenerationJob
    from .contextual_editing import generated_asset_admitted
    from .gemini_editing import validate_binding

    db.refresh(record, with_for_update=True)
    if record.revision != request.expected_document_revision:
        raise ValueError("studio_document_conflict")
    asset = db.get(LibraryAsset, request.asset_id)
    if not asset or asset.workspace_id != record.workspace_id or asset.lifecycle_status != "active":
        raise ValueError("resource_not_found")
    if not generated_asset_admitted(db, asset):
        raise ValueError("resource_visual_review_or_source_validation_required")
    job = db.get(StudioGenerationJob, asset.object_metadata["generationJobId"])
    if job.job_type not in {"editing_gemini", "editing_ai"} or job.document_id != record.id:
        raise ValueError("resource_generation_document_conflict")
    _, contract = validate_binding(db, job)
    generation = EditingAIRequestV1.model_validate(job.request_payload["input"])
    if generation.operation not in {"edit_image", "edit_video"}:
        raise ValueError("resource_use_generated_material_as_support")
    timeline = contract.composition.media_timeline
    targets = [
        (track, index, clip)
        for track in (timeline.tracks if timeline else [])
        if track.kind in {"video", "overlay"}
        for index, clip in enumerate(track.clips)
        if clip.id == request.target_clip_id
    ]
    if len(targets) != 1:
        raise ValueError("resource_target_clip_not_found")
    track, index, clip = targets[0]
    if track.locked or clip.locked or not clip.enabled:
        raise ValueError("resource_target_clip_locked")
    if clip.asset_id != generation.source_asset_id:
        raise ValueError("resource_target_source_conflict")
    replacement = clip.model_copy(deep=True)
    replacement.asset_id = asset.id
    if generation.operation == "edit_image":
        if not asset.media_type.startswith("image/"):
            raise ValueError("resource_image_required")
        pieces = [replacement]
    else:
        if not asset.media_type.startswith("video/") or clip.playback_rate != 1:
            raise ValueError("resource_transform_requires_normal_speed")
        if any(effect.get("kind") == "freeze" for effect in clip.effects):
            raise ValueError("resource_transform_requires_moving_source")
        fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
        source_start = clip.source.start_microseconds if clip.source else 0
        offset = (generation.source_start_seconds * 1e6 - source_start) * fps / 1e6
        count = generation.duration_seconds * fps
        if abs(offset - round(offset)) > 0.01 or abs(count - round(count)) > 0.01:
            raise ValueError("resource_transform_interval_not_frame_aligned")
        first, length = round(offset), round(count)
        if first < 0 or first + length > clip.timeline.duration_frames:
            raise ValueError("resource_transform_interval_outside_clip")
        partial = first != 0 or length != clip.timeline.duration_frames
        if partial and (clip.keyframes or clip.effects):
            raise ValueError("resource_split_animated_clip_requires_replanning")
        pieces = []
        if first:
            before = clip.model_copy(deep=True)
            before.id = f"before-{job.id}"
            before.timeline.duration_frames = first
            before.source = SourceTimeRangeV1(
                start_microseconds=source_start, duration_microseconds=round(first * 1e6 / fps)
            )
            pieces.append(before)
        replacement.timeline = TimelineFrameRangeV1(
            start_frame=clip.timeline.start_frame + first, duration_frames=length
        )
        replacement.source = SourceTimeRangeV1(
            start_microseconds=0, duration_microseconds=generation.duration_seconds * 1_000_000
        )
        pieces.append(replacement)
        remaining = clip.timeline.duration_frames - first - length
        if remaining:
            after = clip.model_copy(deep=True)
            after.id = f"after-{job.id}"
            after.timeline = TimelineFrameRangeV1(
                start_frame=clip.timeline.start_frame + first + length, duration_frames=remaining
            )
            after.source = SourceTimeRangeV1(
                start_microseconds=source_start + round((first + length) * 1e6 / fps),
                duration_microseconds=round(remaining * 1e6 / fps),
            )
            pieces.append(after)
    track.clips[index : index + 1] = pieces
    contract.assets.append(
        AssetReferenceV1(
            id=asset.id,
            media_type=asset.media_type,
            checksum=asset.checksum_sha256,
            version=asset.checksum_sha256,
            rights_status="verified",
            origin="generated",
            provenance={**asset.object_metadata, "appliedToClip": clip.id, "sourceDocumentRevision": record.revision},
        )
    )
    contract.revision += 1
    contract.updated_at = datetime.now(UTC)
    contract = CreativeDocumentV1.model_validate(contract.model_dump())
    persist_contract(record, contract)
    invalidate_linked_post_review(db, record)
    db.flush()
    return contract
