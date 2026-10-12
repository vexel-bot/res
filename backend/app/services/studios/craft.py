"""Immutable native projects, optimistic commits and genuine Craft engine execution."""

import hashlib
import json
import shutil
import tempfile
import zipfile
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select, update

from ...config import get_settings
from ...domain.studios.contracts import (
    AssetReferenceV1,
    CreateGenerationJobRequest,
    CreativeDocumentV1,
    ExportReferenceV1,
    NativeEditorStateV1,
    NativeMediaReferenceV1,
    NativePageProjectV1,
    ReviewReferenceV1,
)
from ...models import CreativeDocument, LibraryAsset, StudioDomainEvent, StudioGenerationJob, StudioMotionGraph
from ...providers.studios.craft import ENGINES, EXTENSIONS, CraftRuntimeError, call_engine, require_capability
from ..object_storage import get_object_storage, object_key, sha256_file
from .compatibility import composition_to_canvas, record_to_contract
from .kernel import emit_event
from .review_binding import invalidate_linked_post_review


def operation_digest(operation: str, payload: dict) -> str:
    encoded = json.dumps(
        {"operation": operation, "payload": payload}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def receipt(db, record, key: str, digest: str) -> dict | None:
    events = db.scalars(
        select(StudioDomainEvent)
        .where(
            StudioDomainEvent.workspace_id == record.workspace_id,
            StudioDomainEvent.aggregate_id == record.id,
            StudioDomainEvent.event_type == "studio.craft.operation_committed",
        )
        .order_by(StudioDomainEvent.occurred_at.desc())
    ).all()
    for event in events:
        if event.payload.get("idempotencyKey") == key:
            if event.payload.get("payloadHash") != digest:
                raise ValueError("idempotency_payload_conflict")
            return event.payload["receipt"]
    return None


def scoped_asset(db, workspace: str, asset_id: str, checksum: str | None = None):
    asset = db.scalar(
        select(LibraryAsset).where(
            LibraryAsset.id == asset_id,
            LibraryAsset.workspace_id == workspace,
            LibraryAsset.lifecycle_status == "active",
        )
    )
    if not asset or not asset.storage_key or not asset.checksum_sha256:
        raise ValueError("craft_asset_unavailable")
    if not asset.storage_key.startswith(workspace + "/"):
        raise ValueError("craft_asset_storage_scope_mismatch")
    if checksum and asset.checksum_sha256.lower() != checksum.lower():
        raise ValueError("craft_asset_checksum_mismatch")
    return asset


def write_asset(
    db,
    record,
    source: Path,
    *,
    suffix: str,
    media_type: str,
    metadata: dict,
    title: str | None = None,
    asset_type: str = "document",
):
    storage = get_object_storage()
    key = object_key(record.workspace_id, "derived", suffix)
    stored = storage.put_file(
        source, key=key, media_type=media_type, metadata={"document-id": record.id, "source": "clicko-craft"}
    )
    asset = LibraryAsset(
        id=str(uuid4()),
        workspace_id=record.workspace_id,
        title=(title or record.title)[:240],
        asset_type=asset_type,
        campaign_id=record.campaign_id,
        content_id=record.post_id,
        tags=["craft", f"document:{record.id}"],
        storage_key=key,
        storage_backend=stored.backend,
        media_type=media_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        object_metadata={**metadata, "craftImmutable": True},
    )
    db.add(asset)
    return asset, storage, key


@contextmanager
def workspace_files(db, record, state: NativeEditorStateV1 | None, *, extra_asset_ids=()):
    """Only verified workspace objects are materialized inside the job directory."""
    with ExitStack() as stack:
        directory = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="clicko-craft-"))).resolve()
        manifests = [*(state.asset_manifest if state else []), *(state.font_manifest if state else [])]
        known = {entry.asset_id for entry in manifests}
        for asset_id in extra_asset_ids:
            if asset_id in known:
                continue
            asset = scoped_asset(db, record.workspace_id, asset_id)
            manifests.append(
                NativeMediaReferenceV1(
                    asset_id=asset.id,
                    path=f"assets/{asset.id}{Path(asset.storage_key).suffix}",
                    checksum_sha256=asset.checksum_sha256,
                    media_type=asset.media_type or "application/octet-stream",
                )
            )
            known.add(asset_id)
        media, paths = [], set()
        for entry in manifests:
            if entry.path in paths:
                raise ValueError("craft_media_manifest_path_conflict")
            paths.add(entry.path)
            asset = scoped_asset(db, record.workspace_id, entry.asset_id, entry.checksum_sha256)
            source = stack.enter_context(get_object_storage(asset.storage_backend).materialize(asset.storage_key))
            if sha256_file(source).lower() != entry.checksum_sha256.lower():
                raise ValueError("craft_asset_checksum_mismatch")
            destination = directory / entry.path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            media.append(
                {
                    "assetId": asset.id,
                    "path": str(destination),
                    "relativePath": entry.path,
                    "checksumSha256": entry.checksum_sha256,
                    "mediaType": entry.media_type,
                }
            )
        params = {"mediaRoot": str(directory), "media": media}
        if state:
            asset = scoped_asset(db, record.workspace_id, state.project_asset_id, state.checksum_sha256)
            source = stack.enter_context(get_object_storage(asset.storage_backend).materialize(asset.storage_key))
            if sha256_file(source).lower() != state.checksum_sha256.lower():
                raise ValueError("craft_native_checksum_mismatch")
            native = directory / ("input" + EXTENSIONS[state.engine])
            shutil.copyfile(source, native)
            params["nativePath"] = str(native)
        yield directory, params, manifests


def assert_build(state: NativeEditorStateV1, capability: dict) -> None:
    if state.build_id != capability["buildId"] or state.upstream_revision != capability["upstreamRevision"]:
        raise ValueError("craft_engine_build_mismatch")


def select_page_state(state, page_id=None):
    if not state.page_projects:
        if page_id and state.engine != "photocraft":
            raise ValueError("craft_page_selection_requires_photocraft")
        return state
    page = (
        next((item for item in state.page_projects if item.page_id == page_id), None)
        if page_id
        else state.page_projects[0]
    )
    if not page:
        raise ValueError("craft_page_not_found")
    return state.model_copy(
        update={
            "project_asset_id": page.project_asset_id,
            "checksum_sha256": page.checksum_sha256,
            "size_bytes": page.size_bytes,
            "page_projects": [],
        }
    )


def page_list(state):
    return [
        {"id": page.page_id, "title": page.title, "width": page.width, "height": page.height}
        for page in state.page_projects
    ]


def native_state_digest(state):
    return operation_digest("native-state", state.model_dump(by_alias=True, mode="json"))


def inspection(db, record, *, frame: int = 0, page_id=None) -> dict:
    state = record_to_contract(record).native_editor_state
    if not state:
        raise ValueError("craft_native_project_required")
    capability = require_capability(state.engine)
    assert_build(state, capability)
    with workspace_files(db, record, select_page_state(state, page_id)) as (_directory, params, _manifest):
        project = call_engine(state.engine, "project.inspect", {**params, "frame": frame})
    return {
        "schemaVersion": "studio.craft-inspection.v1",
        "documentId": record.id,
        "revision": record.revision,
        "engine": state.engine,
        "nativeEditorState": state.model_dump(by_alias=True, mode="json"),
        "project": project.get("inspection", project),
        "capabilities": capability,
        "migrationWarnings": state.migration_warnings,
        "pages": page_list(state),
        "activePageId": page_id or (state.page_projects[0].page_id if state.page_projects else None),
    }


def _commit_project(
    db,
    record,
    user,
    source: Path,
    *,
    engine: str,
    capability: dict,
    expected_revision: int,
    key: str,
    digest: str,
    project: dict,
    manifests=(),
    warnings=(),
    legacy_archive=None,
    dependencies=None,
    label="Edição no Studio",
    operation_metadata=None,
    history_cursor=None,
    selected_page_id=None,
    page_outputs=None,
    page_projects_override=None,
    composition_override=None,
) -> dict:
    if not source.is_file() or not source.stat().st_size:
        raise ValueError("craft_native_output_missing")
    if source.stat().st_size > get_settings().studio_craft_max_upload_bytes:
        raise ValueError("craft_native_project_too_large")
    written = []
    try:
        current = record_to_contract(record)
        if current.revision != expected_revision:
            raise ValueError("studio_document_conflict")
        previous = current.native_editor_state
        archive_id = previous.legacy_archive_asset_id if previous else None
        if legacy_archive:
            archive, storage, storage_key = write_asset(
                db,
                record,
                legacy_archive,
                suffix=".json",
                media_type="application/json",
                metadata={"craftLegacyArchive": True, "documentRevision": record.revision},
                title=f"Original antes da migração · {record.title}",
                asset_type="archive",
            )
            written.append((storage, storage_key))
            archive_id = archive.id
        native, storage, storage_key = write_asset(
            db,
            record,
            source,
            suffix=EXTENSIONS[engine],
            media_type=f"application/vnd.clicko.{engine}-project",
            metadata={
                "craftProject": True,
                "engine": engine,
                "buildId": capability["buildId"],
                "upstreamRevision": capability["upstreamRevision"],
                "formatVersion": capability["formatVersion"],
                "documentRevision": expected_revision + 1,
            },
            title=f"{record.title} · {engine} r{expected_revision + 1}",
        )
        written.append((storage, storage_key))
        pages = list(
            page_projects_override if page_projects_override is not None else previous.page_projects if previous else []
        )
        if engine == "photocraft":
            canonical_pages = (composition_override or current.composition).pages
            selected_id = selected_page_id or (pages[0].page_id if pages else canonical_pages[0].id)
            selected_canonical = next((item for item in canonical_pages if item.id == selected_id), canonical_pages[0])
            new_page = NativePageProjectV1(
                page_id=selected_id,
                title=next(
                    (item.title for item in pages if item.page_id == selected_id),
                    selected_canonical.role or selected_id,
                ),
                width=selected_canonical.width,
                height=selected_canonical.height,
                project_asset_id=native.id,
                checksum_sha256=native.checksum_sha256,
                size_bytes=native.size_bytes,
            )
            pages = [new_page if item.page_id == selected_id else item for item in pages] if pages else [new_page]
            if selected_id not in {item.page_id for item in pages}:
                pages.append(new_page)
            for page, path in page_outputs or []:
                extra, storage, storage_key = write_asset(
                    db,
                    record,
                    path,
                    suffix=".pcraft",
                    media_type="application/vnd.clicko.photocraft-project",
                    metadata={
                        "craftProject": True,
                        "engine": engine,
                        "buildId": capability["buildId"],
                        "pageId": page.id,
                    },
                )
                written.append((storage, storage_key))
                pages.append(
                    NativePageProjectV1(
                        page_id=page.id,
                        title=page.role or page.id,
                        width=page.width,
                        height=page.height,
                        project_asset_id=extra.id,
                        checksum_sha256=extra.checksum_sha256,
                        size_bytes=extra.size_bytes,
                    )
                )
            primary = pages[0]
            primary_asset_id, primary_checksum, primary_size = (
                primary.project_asset_id,
                primary.checksum_sha256,
                primary.size_bytes,
            )
        else:
            primary_asset_id, primary_checksum, primary_size = native.id, native.checksum_sha256, native.size_bytes
        state = NativeEditorStateV1(
            engine=engine,
            format_version=capability["formatVersion"],
            build_id=capability["buildId"],
            upstream_revision=capability["upstreamRevision"],
            project_asset_id=primary_asset_id,
            checksum_sha256=primary_checksum,
            size_bytes=primary_size,
            page_projects=pages,
            asset_manifest=[item for item in manifests if not item.media_type.startswith("font/")],
            font_manifest=[item for item in manifests if item.media_type.startswith("font/")],
            dependencies=dependencies if dependencies is not None else previous.dependencies if previous else [],
            migration_warnings=list(warnings)[:1000],
            legacy_archive_asset_id=archive_id,
        )
        now = datetime.now(UTC)
        updated = current.model_copy(
            update={
                "native_editor_state": state,
                "revision": expected_revision + 1,
                "version": record.version + 1,
                "actor_id": user.id,
                "updated_at": now,
                "review": ReviewReferenceV1(),
                "status": "draft",
            }
        )
        references = {item.id: item for item in current.assets}
        for media in manifests:
            if media.asset_id not in references:
                references[media.asset_id] = AssetReferenceV1(
                    id=media.asset_id,
                    media_type=media.media_type,
                    checksum=media.checksum_sha256,
                    origin="workspace",
                    rights_status="unknown",
                )
        updated = updated.model_copy(update={"assets": list(references.values())})
        if composition_override is not None:
            updated = updated.model_copy(update={"composition": composition_override})
            if engine == "photocraft":
                updated = updated.model_copy(update={"content_type": "carousel" if len(pages) > 1 else "visual"})
        snapshots = list(record.versions or [])
        if history_cursor is None and snapshots and snapshots[-1].get("craftHistoryCursor") is not None:
            cursor = snapshots[-1]["craftHistoryCursor"]
            eligible = [
                item
                for item in snapshots
                if item.get("canonicalDocument", {}).get("nativeEditorState")
                and item.get("craftHistoryCursor") is None
                and not item.get("craftRedo")
            ]
            for item in eligible[cursor + 1 :]:
                item["craftRedo"] = True
        if not snapshots:
            snapshots.append(
                {
                    "number": record.version,
                    "label": "Original",
                    "createdAt": now.isoformat(),
                    "actorId": user.id,
                    "document": record.document,
                    "canonicalDocument": current.model_dump(by_alias=True, mode="json"),
                }
            )
        snapshots.append(
            {
                "number": updated.version,
                "label": label,
                "createdAt": now.isoformat(),
                "actorId": user.id,
                "document": composition_to_canvas(updated).model_dump(by_alias=True),
                "canonicalDocument": updated.model_dump(by_alias=True, mode="json"),
                "craftHistoryCursor": history_cursor,
            }
        )
        db.flush()
        result = db.execute(
            update(CreativeDocument)
            .where(
                CreativeDocument.id == record.id,
                CreativeDocument.workspace_id == record.workspace_id,
                CreativeDocument.revision == expected_revision,
            )
            .values(
                canonical_document=updated.model_dump(by_alias=True, mode="json"),
                document=composition_to_canvas(updated).model_dump(by_alias=True),
                revision=updated.revision,
                version=updated.version,
                versions=snapshots[-100:],
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise ValueError("studio_document_conflict")
        invalidate_linked_post_review(db, record)
        view = {
            "schemaVersion": "studio.craft-inspection.v1",
            "documentId": record.id,
            "revision": updated.revision,
            "engine": engine,
            "nativeEditorState": state.model_dump(by_alias=True, mode="json"),
            "project": project,
            "capabilities": capability,
            "migrationWarnings": state.migration_warnings,
            "pages": page_list(state),
            "activePageId": selected_page_id or (pages[0].page_id if pages else None),
        }
        answer = {
            "document": updated.model_dump(by_alias=True, mode="json"),
            "inspection": view,
            "receiptId": str(uuid4()),
            **(operation_metadata or {}),
        }
        emit_event(
            db,
            workspace_id=record.workspace_id,
            event_type="studio.craft.operation_committed",
            aggregate_type="creative_document",
            aggregate_id=record.id,
            correlation_id=updated.correlation_id,
            actor_id=user.id,
            payload={
                "idempotencyKey": key,
                "payloadHash": digest,
                "receipt": answer,
                "sourceRevision": expected_revision,
                "revision": updated.revision,
            },
        )
        db.commit()
        db.refresh(record)
        return answer
    except Exception as exc:
        db.rollback()
        for storage, storage_key in written:
            storage.delete(storage_key)
        if isinstance(exc, ValueError) and str(exc) == "studio_document_conflict":
            replay = receipt(db, record, key, digest)
            if replay:
                return replay
        raise


def legacy_conversion_warnings(contract, engine: str) -> list[str]:
    """Flag authored treatments outside the explicit native migration mapping."""
    warnings = []
    for page in contract.composition.pages:
        for layer in page.layers:
            props = layer.properties
            for field in (
                "effects",
                "nativeComponent",
                "textSpans",
                "editorialShadow",
                "editorialDepth",
                "editorialBlur",
                "editorialTiming",
                "maskAssetId",
                "crop",
                "stroke",
                "strokeWidth",
            ):
                if props.get(field):
                    if field == "editorialTiming" and engine == "effectcraft":
                        timing = props[field]
                        if isinstance(timing, dict):
                            fps, duration = timing.get("fps"), timing.get("durationFrames")
                            if (
                                isinstance(fps, (int, float))
                                and isinstance(duration, (int, float))
                                and fps > 0
                                and duration > 0
                                and timing.get("reveal", "none") == "none"
                            ):
                                continue
                    warnings.append(f"Layer {layer.id}: {field} needs native {engine} review; original preserved.")
            if engine == "effectcraft" and layer.kind == "text":
                for field in ("fontFamily", "fontWeight", "fontAssetId", "lineHeight", "letterSpacing", "align"):
                    if props.get(field) is not None:
                        warnings.append(
                            f"Layer {layer.id}: typography {field} needs native review; original preserved."
                        )
    recipes = contract.composition.narrative.get("editorialV2", {}).get("motionRecipes", [])
    if recipes:
        warnings.append("Legacy motion recipes require native EffectCraft authoring; original recipes preserved.")
    return warnings


def migrate(db, record, request, user, key: str) -> dict:
    digest = operation_digest("migrate", request.model_dump(mode="json"))
    existing = receipt(db, record, key, digest)
    if existing:
        return existing["inspection"]
    contract = record_to_contract(record)
    if contract.revision != request.expected_revision:
        raise ValueError("studio_document_conflict")
    if contract.native_editor_state:
        if contract.native_editor_state.engine != request.engine:
            raise ValueError("craft_engine_change_requires_separate_document")
        return inspection(db, record)
    capability = require_capability(request.engine)
    motion_graphs = db.scalars(
        select(StudioMotionGraph)
        .where(
            StudioMotionGraph.document_id == record.id,
            StudioMotionGraph.workspace_id == record.workspace_id,
        )
        .order_by(StudioMotionGraph.updated_at.desc())
    ).all()
    motion_archive = [
        {
            "id": graph.id,
            "documentRevision": graph.document_revision,
            "storageRevision": graph.storage_revision,
            "graphDigestSha256": graph.graph_digest_sha256,
            "status": graph.status,
            "graph": graph.graph,
            "evaluation": graph.evaluation,
        }
        for graph in motion_graphs
    ]
    legacy_motion = (
        motion_graphs[0].graph
        if motion_graphs
        else (contract.composition.narrative.get("editorialV2") or {}).get("motionGraph")
        or contract.composition.narrative.get("motionGraph")
    )
    available_assets, missing = [], []
    for ref in contract.assets:
        try:
            scoped_asset(db, record.workspace_id, ref.id)
            available_assets.append(ref.id)
        except ValueError:
            missing.append(f"asset_unavailable:{ref.id}; original retained in legacy archive")
    with workspace_files(db, record, None, extra_asset_ids=available_assets) as (directory, params, manifests):
        output = directory / ("output" + EXTENSIONS[request.engine])
        archive = directory / "legacy-original.json"
        archive.write_text(
            json.dumps(
                {
                    "canonicalDocument": contract.model_dump(by_alias=True, mode="json"),
                    "legacyCanvas": record.document,
                    "versions": record.versions or [],
                    "motionGraphs": motion_archive,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        first = contract.composition.pages[0]
        page_outputs, projects, warnings = [], [], [*missing, *legacy_conversion_warnings(contract, request.engine)]
        if legacy_motion and request.engine != "effectcraft":
            warnings.append(
                "legacy motion graphs require conversion in EffectCraft; "
                "complete graphs retained in the original archive"
            )
        source_pages = contract.composition.pages if request.engine == "photocraft" else [first]
        for index, page in enumerate(source_pages):
            destination = output if index == 0 else directory / f"page-{index}.pcraft"
            legacy = contract.model_dump(by_alias=True, mode="json")
            if request.engine == "photocraft":
                legacy["composition"]["pages"] = [page.model_dump(by_alias=True, mode="json")]
                legacy["contentType"] = "visual"
            result = call_engine(
                request.engine,
                "project.new",
                {
                    **params,
                    "outputPath": str(destination),
                    "title": contract.title,
                    "width": page.width,
                    "height": page.height,
                    "fps": 30,
                    "legacyDocument": legacy,
                    "legacyMotionGraph": legacy_motion if request.engine == "effectcraft" else None,
                    "durationMs": page.duration_ms or 5000,
                },
            )
            validation = call_engine(request.engine, "project.open", {**params, "nativePath": str(destination)})
            projects.append(result.get("inspection", validation.get("inspection", validation)))
            warnings.extend(f"{page.id}: {warning}" for warning in result.get("warnings", []))
            if index:
                page_outputs.append((page, destination))
        return _commit_project(
            db,
            record,
            user,
            output,
            engine=request.engine,
            capability=capability,
            expected_revision=request.expected_revision,
            key=key,
            digest=digest,
            project=projects[0],
            manifests=manifests,
            page_outputs=page_outputs,
            warnings=warnings,
            legacy_archive=archive,
            label="Migração para o Studio",
        )["inspection"]


def validate_commands(commands, capability: dict) -> None:
    from jsonschema import Draft202012Validator, SchemaError, ValidationError

    by_id = {value["id"]: value for value in capability["commands"]}
    for command in commands:
        spec = by_id.get(command.id)
        if not spec:
            raise ValueError("craft_command_not_supported:" + command.id)
        if any(word in command.id.lower() for word in ("script", "plugin", "shell", "file.open", "file.save")):
            raise ValueError("craft_command_requires_isolated_manual_session")
        try:
            Draft202012Validator.check_schema(spec["inputSchema"])
            Draft202012Validator(spec["inputSchema"]).validate(command.params)
        except (ValidationError, SchemaError) as exc:
            raise ValueError("craft_command_params_invalid:" + command.id) from exc

        def safe(value):
            if isinstance(value, dict):
                for field, child in value.items():
                    if field.lower() in {
                        "nativepath",
                        "outputpath",
                        "mediaroot",
                        "sourcepath",
                        "filepath",
                        "filename",
                        "file",
                        "uri",
                        "url",
                    }:
                        raise ValueError("craft_command_server_owned_path")
                    if (
                        field.lower() == "path"
                        and isinstance(child, str)
                        and (
                            child.startswith(("/", "\\", "file:", "http:", "https:"))
                            or ":" in child
                            or ".." in Path(child).parts
                        )
                    ):
                        raise ValueError("craft_command_server_owned_path")
                    safe(child)
            elif isinstance(value, list):
                for child in value:
                    safe(child)

        safe(command.params)


def commands(db, record, request, user, key: str, *, metadata=None, digest_override=None, dependencies=None) -> dict:
    digest = digest_override or operation_digest("commands", request.model_dump(mode="json"))
    existing = receipt(db, record, key, digest)
    if existing:
        return existing
    contract = record_to_contract(record)
    state = contract.native_editor_state
    if contract.revision != request.expected_revision:
        raise ValueError("studio_document_conflict")
    if not state:
        raise ValueError("craft_native_project_required")
    capability = require_capability(state.engine)
    assert_build(state, capability)
    validate_commands(request.commands, capability)
    if any(command.id.startswith("host.history.") for command in request.commands):
        if len(request.commands) != 1:
            raise ValueError("craft_history_command_must_be_exclusive")
        return history_command(db, record, request, user, key, digest, capability)
    if any(command.id.startswith("host.pages.") for command in request.commands):
        if len(request.commands) != 1 or state.engine != "photocraft":
            raise ValueError("craft_page_command_must_be_exclusive")
        return page_command(db, record, request, user, key, digest, capability)
    extra = set()

    def collect(value):
        if isinstance(value, dict):
            for field, child in value.items():
                if field == "assetId" and isinstance(child, str):
                    extra.add(child)
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    for command in request.commands:
        collect(command.params)
    with workspace_files(db, record, select_page_state(state, request.page_id), extra_asset_ids=extra) as (
        directory,
        params,
        manifests,
    ):
        output = directory / ("output" + EXTENSIONS[state.engine])
        result = call_engine(
            state.engine,
            "engine.execute",
            {
                **params,
                "outputPath": str(output),
                "commands": [command.model_dump(mode="json") for command in request.commands],
            },
        )
        validation = call_engine(state.engine, "project.open", {**params, "nativePath": str(output)})
        return _commit_project(
            db,
            record,
            user,
            output,
            engine=state.engine,
            capability=capability,
            expected_revision=request.expected_revision,
            key=key,
            digest=digest,
            project=result.get("inspection", validation.get("inspection", validation)),
            manifests=manifests,
            warnings=[*state.migration_warnings, *result.get("warnings", [])],
            label=request.label,
            operation_metadata=metadata,
            dependencies=dependencies,
            selected_page_id=request.page_id,
        )


def history_command(db, record, request, user, key, digest, capability):
    snapshots = list(record.versions or [])
    eligible = [
        snapshot
        for snapshot in snapshots
        if snapshot.get("canonicalDocument", {}).get("nativeEditorState")
        and snapshot.get("craftHistoryCursor") is None
        and not snapshot.get("craftRedo")
    ]
    if not eligible:
        raise ValueError("craft_history_empty")
    cursor = snapshots[-1].get("craftHistoryCursor")
    cursor = len(eligible) - 1 if cursor is None else cursor
    target_cursor = cursor + (-1 if request.commands[0].id == "host.history.undo" else 1)
    if not 0 <= target_cursor < len(eligible):
        raise ValueError("craft_history_boundary")
    target_document = CreativeDocumentV1.model_validate(eligible[target_cursor]["canonicalDocument"])
    target = target_document.native_editor_state
    assert_build(target, capability)
    with workspace_files(db, record, target) as (_directory, params, manifests):
        result = call_engine(target.engine, "project.inspect", params)
        return _commit_project(
            db,
            record,
            user,
            Path(params["nativePath"]),
            engine=target.engine,
            capability=capability,
            expected_revision=request.expected_revision,
            key=key,
            digest=digest,
            project=result.get("inspection", result),
            manifests=manifests,
            warnings=target.migration_warnings,
            dependencies=target.dependencies,
            label="Desfazer" if target_cursor < cursor else "Refazer",
            history_cursor=target_cursor,
            page_projects_override=target.page_projects,
            composition_override=target_document.composition,
        )


def page_command(db, record, request, user, key, digest, capability):
    from ...domain.studios.contracts import CreativePageV1

    contract = record_to_contract(record)
    state = contract.native_editor_state
    command = request.commands[0]
    params = command.params
    pages = list(state.page_projects)
    canonical_pages = list(contract.composition.pages)
    selected_id = params["pageId"]
    selected = next((page for page in pages if page.page_id == selected_id), None)
    if command.id == "host.pages.add":
        if selected or len(pages) >= 100:
            raise ValueError("craft_page_id_duplicate_or_limit")
        new_page = CreativePageV1(
            id=selected_id,
            role="support",
            width=params["width"],
            height=params["height"],
            safe_area=0,
            background="#ffffff",
            layers=[],
        )
        canonical_pages.append(new_page)
        with workspace_files(db, record, None) as (directory, runtime_params, manifests):
            output = directory / "new-page.pcraft"
            result = call_engine(
                "photocraft",
                "project.new",
                {
                    **runtime_params,
                    "outputPath": str(output),
                    "title": params["title"],
                    "width": params["width"],
                    "height": params["height"],
                },
            )
            composition = contract.composition.model_copy(update={"pages": canonical_pages})
            answer = _commit_project(
                db,
                record,
                user,
                output,
                engine="photocraft",
                capability=capability,
                expected_revision=request.expected_revision,
                key=key,
                digest=digest,
                project=result.get("inspection", result),
                manifests=[*state.asset_manifest, *state.font_manifest],
                warnings=state.migration_warnings,
                label="Adicionar página",
                selected_page_id=selected_id,
                composition_override=composition,
            )
            return answer
    if not selected:
        raise ValueError("craft_page_not_found")
    if command.id == "host.pages.delete":
        if len(pages) < 2:
            raise ValueError("craft_last_page_cannot_be_deleted")
        pages = [page for page in pages if page.page_id != selected_id]
        canonical_pages = [page for page in canonical_pages if page.id != selected_id]
    else:
        index = params["index"]
        if index >= len(pages):
            raise ValueError("craft_page_index_invalid")
        pages.remove(selected)
        pages.insert(index, selected)
        by_id = {page.id: page for page in canonical_pages}
        canonical_pages = [by_id[page.page_id] for page in pages]
    target_state = state.model_copy(
        update={
            "project_asset_id": pages[0].project_asset_id,
            "checksum_sha256": pages[0].checksum_sha256,
            "size_bytes": pages[0].size_bytes,
            "page_projects": pages,
        }
    )
    with workspace_files(db, record, target_state) as (_directory, runtime_params, manifests):
        result = call_engine("photocraft", "project.inspect", runtime_params)
        return _commit_project(
            db,
            record,
            user,
            Path(runtime_params["nativePath"]),
            engine="photocraft",
            capability=capability,
            expected_revision=request.expected_revision,
            key=key,
            digest=digest,
            project=result.get("inspection", result),
            manifests=manifests,
            warnings=state.migration_warnings,
            label="Remover página" if command.id == "host.pages.delete" else "Mover página",
            selected_page_id=pages[0].page_id,
            page_projects_override=pages,
            composition_override=contract.composition.model_copy(update={"pages": canonical_pages}),
        )


def save_native(
    db,
    record,
    user,
    source: Path,
    *,
    engine,
    expected_revision,
    key,
    asset_manifest=None,
    font_manifest=None,
    page_id=None,
) -> dict:
    digest = operation_digest(
        "native-upload",
        {
            "engine": engine,
            "expectedRevision": expected_revision,
            "checksum": sha256_file(source),
            "pageId": page_id,
            "assetManifest": [item.model_dump() for item in asset_manifest or []],
            "fontManifest": [item.model_dump() for item in font_manifest or []],
        },
    )
    existing = receipt(db, record, key, digest)
    if existing:
        return existing
    contract = record_to_contract(record)
    state = contract.native_editor_state
    if contract.revision != expected_revision:
        raise ValueError("studio_document_conflict")
    if state and state.engine != engine:
        raise ValueError("craft_native_engine_mismatch")
    capability = require_capability(engine)
    if state:
        assert_build(state, capability)
    with workspace_files(db, record, select_page_state(state, page_id) if state else None) as (
        directory,
        params,
        manifests,
    ):
        if asset_manifest is not None or font_manifest is not None:
            manifests = [*(asset_manifest or []), *(font_manifest or [])]
            for entry in manifests:
                scoped_asset(db, record.workspace_id, entry.asset_id, entry.checksum_sha256)
        native = directory / ("uploaded" + EXTENSIONS[engine])
        shutil.copyfile(source, native)
        result = call_engine(engine, "project.open", {**params, "nativePath": str(native)})
        legacy_archive = None
        if not state:
            legacy_archive = directory / "legacy-original.json"
            legacy_archive.write_text(
                json.dumps(
                    {
                        "canonicalDocument": contract.model_dump(by_alias=True, mode="json"),
                        "legacyCanvas": record.document,
                        "versions": record.versions or [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        return _commit_project(
            db,
            record,
            user,
            native,
            engine=engine,
            capability=capability,
            expected_revision=expected_revision,
            key=key,
            digest=digest,
            project=result.get("inspection", result),
            manifests=manifests,
            warnings=state.migration_warnings if state else [],
            label="Salvar projeto nativo",
            selected_page_id=page_id,
            legacy_archive=legacy_archive,
        )


def render_frame(db, record, state=None, *, frame=0, page_id=None) -> bytes:
    state = state or record_to_contract(record).native_editor_state
    if not state:
        raise ValueError("craft_native_project_required")
    assert_build(state, require_capability(state.engine))
    with workspace_files(db, record, select_page_state(state, page_id)) as (directory, params, _manifests):
        output = directory / "preview.png"
        call_engine(
            state.engine,
            "render.frame",
            {**params, "outputPath": str(output), "frame": frame, "pageId": page_id, "format": "png"},
        )
        if not output.is_file():
            raise ValueError("craft_render_artifact_invalid")
        if output.stat().st_size > 64 * 1024**2:
            raise ValueError("craft_preview_too_large")
        result = output.read_bytes()
        if result[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("craft_render_artifact_invalid")
        validate_render_output(output, "png")
        return result


def validate_render_output(path, output_format):
    """Validate delivered container bytes; decoding is verification, never a rendering fallback."""
    if output_format in {"png", "jpeg", "jpg", "webp", "gif", "tiff", "tif"}:
        from PIL import Image

        with Image.open(path) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                raise ValueError("craft_render_dimensions_invalid")
            image.verify()
        return {"width": width, "height": height, "validation": "image-decoder"}
    if output_format in {"mp4", "mov", "webm"}:
        with path.open("rb") as source:
            header = source.read(32)
        if output_format == "webm" and header[:4] != b"\x1aE\xdf\xa3":
            raise ValueError("craft_render_container_invalid")
        if output_format in {"mp4", "mov"} and (len(header) < 12 or header[4:8] not in {b"ftyp", b"wide", b"mdat"}):
            raise ValueError("craft_render_container_invalid")
        return {"validation": "native-export-and-container-signature"}
    return {"validation": "native-export-file-integrity"}


def create_render_job(db, record, request, user, key):
    from .jobs import create_job

    existing = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.workspace_id == record.workspace_id,
            StudioGenerationJob.document_id == record.id,
            StudioGenerationJob.job_type == "craft_render",
            StudioGenerationJob.idempotency_key == key,
        )
    )
    if existing:
        if existing.request_payload.get("output") != request.model_dump(by_alias=True):
            raise ValueError("idempotency_payload_conflict")
        return existing, False
    contract = record_to_contract(record)
    state = contract.native_editor_state
    if not state:
        raise ValueError("craft_native_project_required")
    if request.expected_revision != contract.revision:
        raise ValueError("studio_document_conflict")
    capability = require_capability(state.engine)
    assert_build(state, capability)
    if request.format not in capability.get("formats", []):
        raise ValueError("craft_export_format_unavailable")
    input_request = CreateGenerationJobRequest(
        workspace_id=record.workspace_id,
        document_id=record.id,
        job_type="craft_render",
        provider="craft." + state.engine,
        correlation_id=contract.correlation_id,
        request={
            "schemaVersion": "studio.craft-render-input.v1",
            "nativeEditorState": state.model_dump(by_alias=True),
            "documentRevision": contract.revision,
            "documentVersion": contract.version,
            "output": request.model_dump(by_alias=True),
            "documentSnapshot": contract.model_dump(by_alias=True, mode="json"),
        },
    )
    return create_job(db, input_request, key, user)


def execute_render_job(db, job, progress, is_cancelled):
    if job.provider not in {"craft." + engine for engine in ENGINES}:
        raise ValueError("craft_render_provider_invalid")
    state = NativeEditorStateV1.model_validate(job.request_payload["nativeEditorState"])
    if job.provider != "craft." + state.engine:
        raise ValueError("craft_render_provider_mismatch")
    for cached_asset in db.scalars(
        select(LibraryAsset).where(
            LibraryAsset.workspace_id == job.workspace_id, LibraryAsset.lifecycle_status == "active"
        )
    ).all():
        cached = (cached_asset.object_metadata or {}).get("craftRenderResult")
        if isinstance(cached, dict) and cached.get("jobId") == job.id:
            if cached.get("nativeStateDigestSha256") != native_state_digest(state):
                raise ValueError("craft_render_cached_snapshot_mismatch")
            scoped_asset(db, job.workspace_id, cached_asset.id, cached["artifact"]["checksumSha256"])
            with get_object_storage(cached_asset.storage_backend).materialize(cached_asset.storage_key) as path:
                if sha256_file(path) != cached_asset.checksum_sha256:
                    raise ValueError("craft_render_cached_artifact_changed")
            return cached
    contract = CreativeDocumentV1.model_validate(job.request_payload["documentSnapshot"])
    record = db.get(CreativeDocument, job.document_id)
    if not record or record.workspace_id != job.workspace_id or contract.document_id != record.id:
        raise ValueError("craft_render_document_mismatch")
    assert_build(state, require_capability(state.engine))
    if is_cancelled():
        return {"cancelled": True}
    progress(5)
    spec = job.request_payload["output"]
    suffix = "." + {
        "png_set": "zip",
        "jpeg": "jpg",
        "dnxhr": "mov",
        "apv": "mov",
        "mjpeg": "mov",
        "mxf_op1a": "mxf",
        "mxf_opatom": "mxf",
        "aac": "m4a",
        "aiff": "aif",
    }.get(spec["format"], spec["format"])
    mime = {
        "png_set": "application/zip",
        "png": "image/png",
        "jpeg": "image/jpeg",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "webp": "image/webp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "exr": "image/x-exr",
        "psd": "image/vnd.adobe.photoshop",
        "gif": "image/gif",
        "mov": "video/quicktime",
        "avi": "video/x-msvideo",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "aiff": "audio/aiff",
        "aac": "audio/mp4",
        "dnxhr": "video/quicktime",
        "apv": "video/quicktime",
        "mjpeg": "video/quicktime",
        "mxf_op1a": "application/mxf",
        "mxf_opatom": "application/mxf",
        "bmp": "image/bmp",
        "tga": "image/x-tga",
        "dpx": "image/x-dpx",
    }.get(spec["format"], "application/octet-stream")
    written = None
    try:
        with workspace_files(db, record, select_page_state(state, spec.get("pageId"))) as (
            directory,
            params,
            _manifests,
        ):
            output = directory / ("export" + suffix)
            if spec["format"] == "png_set":
                if state.engine != "photocraft":
                    raise ValueError("craft_png_set_requires_photocraft")
                page_ids = [page.page_id for page in state.page_projects] or [contract.composition.pages[0].id]
                manifest = {
                    "schemaVersion": "studio.craft-page-export.v1",
                    "orderedPages": page_ids,
                    "pages": {page_id: f"{index + 1:03d}.png" for index, page_id in enumerate(page_ids)},
                }
                with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    for index, page_id in enumerate(page_ids):
                        if is_cancelled():
                            return {"cancelled": True}
                        payload = render_frame(db, record, state, page_id=page_id)
                        archive.writestr(manifest["pages"][page_id], payload)
                        progress(min(80, 5 + int(75 * (index + 1) / len(page_ids))))
                    archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
                result = {"warnings": [], "frames": len(page_ids)}
            else:
                result = call_engine(
                    state.engine,
                    "render.export",
                    {
                        **params,
                        "outputPath": str(output),
                        "format": "jpg" if spec["format"] == "jpeg" else spec["format"],
                        "frame": spec.get("frame", 0),
                        "quality": spec["quality"],
                        "alpha": state.engine == "effectcraft" and spec["format"] == "webm",
                    },
                    cancelled=is_cancelled,
                )
            if not output.is_file() or not output.stat().st_size:
                raise ValueError("craft_render_artifact_missing")
            verified_metadata = validate_render_output(output, spec["format"])
            if is_cancelled():
                return {"cancelled": True}
            progress(85)
            asset, storage, storage_key = write_asset(
                db,
                record,
                output,
                suffix=suffix,
                media_type=mime,
                asset_type="video"
                if mime.startswith("video/")
                else "audio"
                if mime.startswith("audio/")
                else "archive"
                if spec["format"] == "png_set"
                else "image"
                if mime.startswith("image/")
                else "document",
                metadata={
                    "craftRender": True,
                    "jobId": job.id,
                    "engine": state.engine,
                    "buildId": state.build_id,
                    "projectChecksumSha256": state.checksum_sha256,
                    "nativeStateDigestSha256": native_state_digest(state),
                    "documentRevision": contract.revision,
                    "documentVersion": contract.version,
                },
                title=f"{contract.title} · exportação {spec['format']}",
            )
            written = storage, storage_key
            db.flush()
            artifact = {
                "assetId": asset.id,
                "checksumSha256": asset.checksum_sha256,
                "mediaType": mime,
                "sizeBytes": asset.size_bytes,
                "downloadUrl": f"/api/v1/assets/{asset.id}/content",
                **{
                    name: result.get(name, result.get("artifact", {}).get(name))
                    for name in ("width", "height", "durationMs", "fps")
                },
                **verified_metadata,
            }
            payload = {
                "schemaVersion": "studio.craft-render-result.v1",
                "jobId": job.id,
                "workspaceId": job.workspace_id,
                "documentId": contract.document_id,
                "documentRevision": contract.revision,
                "documentVersion": contract.version,
                "engine": state.engine,
                "buildId": state.build_id,
                "projectChecksumSha256": state.checksum_sha256,
                "nativeStateDigestSha256": native_state_digest(state),
                "pageId": spec.get("pageId"),
                "format": spec["format"],
                "artifact": artifact,
                "warnings": result.get("warnings", []),
                "completedAt": datetime.now(UTC).isoformat(),
            }
            asset.object_metadata = {**asset.object_metadata, "craftRenderResult": payload}
            db.refresh(record)
            current = record_to_contract(record)
            if current.native_editor_state and native_state_digest(current.native_editor_state) == native_state_digest(
                state
            ):
                exports = [
                    *current.exports,
                    ExportReferenceV1(
                        asset_id=asset.id,
                        document_version=contract.version,
                        target="library",
                        format=spec["format"],
                        created_at=datetime.now(UTC),
                    ),
                ]
                updated = current.model_copy(update={"exports": exports})
                db.execute(
                    update(CreativeDocument)
                    .where(CreativeDocument.id == record.id, CreativeDocument.revision == current.revision)
                    .values(canonical_document=updated.model_dump(by_alias=True, mode="json"))
                )
            db.commit()
            progress(99)
            return payload
    except CraftRuntimeError as exc:
        if exc.code == "craft_execution_cancelled":
            return {"cancelled": True}
        if written:
            db.rollback()
            written[0].delete(written[1])
        raise
    except Exception:
        if written:
            db.rollback()
            written[0].delete(written[1])
        raise


def asset_is_retained(db, asset: LibraryAsset) -> bool:
    if (asset.object_metadata or {}).get("craftImmutable"):
        return True
    records = db.scalars(select(CreativeDocument).where(CreativeDocument.workspace_id == asset.workspace_id)).all()
    for record in records:
        snapshots = [
            record.canonical_document or {},
            *[entry.get("canonicalDocument", {}) for entry in record.versions or []],
        ]
        for snapshot in snapshots:
            state = snapshot.get("nativeEditorState") or {}
            refs = [*state.get("assetManifest", []), *state.get("fontManifest", [])]
            if any(entry.get("assetId") == asset.id for entry in refs):
                return True
    return False


@contextmanager
def native_bundle(db, record, state):
    """Build on disk, including native media, so multi-GB bundles never fill RAM."""
    with tempfile.TemporaryDirectory(prefix="craft-native-bundle-") as directory:
        output = Path(directory) / "projects.zip"
        pages = state.page_projects
        entries = [(page.page_id, select_page_state(state, page.page_id)) for page in pages] or [("project", state)]
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("manifest.json", state.model_dump_json(by_alias=True))
            for index, (_page_id, page_state) in enumerate(entries):
                with workspace_files(db, record, page_state) as (_directory, params, _manifest):
                    archive.write(params["nativePath"], f"{index + 1:03d}{EXTENSIONS[state.engine]}")
            copied = set()
            for reference in [*state.asset_manifest, *state.font_manifest]:
                if reference.path in copied:
                    continue
                if Path(reference.path).is_absolute() or ".." in Path(reference.path).parts:
                    raise ValueError("craft_bundle_media_path_invalid")
                asset = scoped_asset(db, record.workspace_id, reference.asset_id, reference.checksum_sha256)
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                    if sha256_file(path) != reference.checksum_sha256:
                        raise ValueError("craft_bundle_media_checksum_mismatch")
                    archive.write(path, reference.path)
                copied.add(reference.path)
            for index, reference in enumerate(state.dependencies):
                asset = scoped_asset(db, record.workspace_id, reference.project_asset_id, reference.checksum_sha256)
                with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                    if sha256_file(path) != reference.checksum_sha256:
                        raise ValueError("craft_bundle_dependency_checksum_mismatch")
                    archive.write(path, f"dependencies/{index + 1:03d}{EXTENSIONS[reference.engine]}")
        yield output


def verified_render(db, record, job_id):
    from ...models import StudioGenerationJob

    contract = record_to_contract(record)
    job = db.scalar(
        select(StudioGenerationJob).where(
            StudioGenerationJob.id == job_id,
            StudioGenerationJob.workspace_id == record.workspace_id,
            StudioGenerationJob.document_id == record.id,
        )
    )
    if not job or job.job_type != "craft_render":
        raise ValueError("studio_review_craft_render_required")
    if job.status != "succeeded" or not job.result_payload:
        raise ValueError("studio_review_render_not_ready")
    result = job.result_payload
    state = contract.native_editor_state
    if (
        not state
        or result.get("documentRevision") != record.revision
        or result.get("documentVersion") != record.version
        or result.get("nativeStateDigestSha256") != native_state_digest(state)
    ):
        raise ValueError("studio_review_render_snapshot_mismatch")
    if state.engine == "photocraft" and len(state.page_projects) > 1 and result.get("format") != "png_set":
        raise ValueError("studio_review_all_pages_render_required")
    if state.engine != "photocraft" and result.get("format") not in {"mp4", "webm"}:
        raise ValueError("studio_review_full_video_render_required")
    artifact = scoped_asset(
        db, record.workspace_id, result["artifact"]["assetId"], result["artifact"]["checksumSha256"]
    )
    with get_object_storage(artifact.storage_backend).materialize(artifact.storage_key) as path:
        if sha256_file(path) != artifact.checksum_sha256:
            raise ValueError("studio_review_render_artifact_mismatch")
    return result


def link_composition(db, record, source, request, user, key):
    from ...domain.studios.contracts import NativeCompositionReferenceV1
    from ...domain.studios.craft import CraftCommandRequestV1, CraftCommandV1, CraftRenderRequestV1
    from .jobs import execute_job_once

    digest = operation_digest("link-composition", request.model_dump(mode="json"))
    existing = receipt(db, record, key, digest)
    if existing:
        return existing
    if source.workspace_id != record.workspace_id or source.id == record.id:
        raise ValueError("craft_composition_workspace_mismatch")
    target_state = record_to_contract(record).native_editor_state
    source_state = record_to_contract(source).native_editor_state
    if (
        not target_state
        or target_state.engine != "filmcraft"
        or not source_state
        or source_state.engine != "effectcraft"
    ):
        raise ValueError("craft_link_requires_filmcraft_and_effectcraft")
    if request.expected_revision != record.revision:
        raise ValueError("studio_document_conflict")
    capability = require_capability("effectcraft")
    # VP9 webm keeps alpha for linked compositions. Never flatten implicitly.
    if "webm" not in capability.get("formats", []):
        raise ValueError("craft_link_transparent_render_unavailable")
    target_capability = require_capability("filmcraft")
    if not any(command["id"] == "composition.link" for command in target_capability["commands"]):
        raise ValueError("craft_link_native_import_unavailable")
    render, created = create_render_job(
        db, source, CraftRenderRequestV1(expected_revision=source.revision, format="webm"), user, "link:" + key
    )
    if created or render.status in {"queued", "retrying"}:
        execute_job_once(db, render)
        db.refresh(render)
    if render.status != "succeeded":
        raise ValueError("craft_link_composition_render_failed")
    artifact_id = render.result_payload["artifact"]["assetId"]
    dependency = NativeCompositionReferenceV1(
        engine="effectcraft",
        project_asset_id=source_state.project_asset_id,
        checksum_sha256=source_state.checksum_sha256,
        build_id=source_state.build_id,
        source_document_id=source.id,
        rendered_asset_id=artifact_id,
    )
    dependencies = [item for item in target_state.dependencies if item.source_document_id != source.id]
    previous = next((item for item in target_state.dependencies if item.source_document_id == source.id), None)
    params = {"assetId": artifact_id, "sourceDocumentId": source.id}
    if previous and previous.rendered_asset_id:
        params["replaceAssetId"] = previous.rendered_asset_id
    return commands(
        db,
        record,
        CraftCommandRequestV1(
            expected_revision=request.expected_revision,
            commands=[CraftCommandV1(id="composition.link", params=params)],
            label="Vincular composição e efeitos",
        ),
        user,
        key,
        digest_override=digest,
        dependencies=[*dependencies, dependency],
    )


def refresh_linked_compositions(db, source, user):
    from ...domain.studios.craft import CraftLinkRequestV1

    state = record_to_contract(source).native_editor_state
    if not state or state.engine != "effectcraft":
        return []
    candidates = db.scalars(
        select(CreativeDocument).where(
            CreativeDocument.workspace_id == source.workspace_id, CreativeDocument.id != source.id
        )
    ).all()
    outcomes = []
    for target in candidates:
        target_state = record_to_contract(target).native_editor_state
        if not target_state or target_state.engine != "filmcraft":
            continue
        linked = next((item for item in target_state.dependencies if item.source_document_id == source.id), None)
        if not linked or linked.checksum_sha256 == state.checksum_sha256:
            continue
        key = "link-refresh:" + operation_digest("link", {"target": target.id, "source": native_state_digest(state)})
        try:
            result = link_composition(
                db,
                target,
                source,
                CraftLinkRequestV1(expected_revision=target.revision, composition_document_id=source.id),
                user,
                key,
            )
            outcomes.append({"documentId": target.id, "status": "updated", "receiptId": result["receiptId"]})
        except ValueError as exc:
            db.rollback()
            emit_event(
                db,
                workspace_id=source.workspace_id,
                event_type="studio.craft.link_refresh_failed",
                aggregate_type="creative_document",
                aggregate_id=target.id,
                correlation_id=source.correlation_id,
                actor_id=user.id,
                payload={"sourceDocumentId": source.id, "code": str(exc)},
            )
            db.commit()
            outcomes.append({"documentId": target.id, "status": "failed", "code": str(exc)})
    return outcomes
