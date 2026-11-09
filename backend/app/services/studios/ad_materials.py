"""Workspace product kits and explicit project bindings, without provider invocation."""

from datetime import UTC, datetime
from hashlib import sha256
import json
from uuid import uuid4

from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from ...domain.studios.contracts import StudioContract
from ...models import WorkspaceResource
from .craft import scoped_asset
from .kernel import emit_event
from .ad_editing_recipes import cards
from .ad_material_roles import ROLES

KIT = "ad_material_kit"
BINDING = "ad_material_binding"
ALPHA_ROLES = {"subject_cutout", "product_cutout", "occluder", "event_cutout", "window_frame", "generated_patch"}


class Material(StudioContract):
    asset_id: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=240)
    alignment_group: str = Field(default="", max_length=120)


class KitRequest(StudioContract):
    expected_revision: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=240)
    category: str = Field(pattern=r"^(physical|software|service|other)$")
    goal: str = Field(pattern=r"^(demonstrate|explain|variants|showcase|transformation)$")
    description: str = Field(default="", max_length=6000)
    visual_identity: str = Field(default="", max_length=6000)
    materials: list[Material] = Field(default_factory=list, max_length=80)


def row(db, workspace, kind, key):
    return db.scalar(select(WorkspaceResource).where(WorkspaceResource.workspace_id == workspace,
        WorkspaceResource.kind == kind, WorkspaceResource.resource_key == key))


def fingerprint(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def put(db, workspace, kind, key, payload, expected, user):
    from .contextual_editing import lock_editing_budget
    lock_editing_budget(db, workspace)
    current = row(db, workspace, kind, key)
    if (current.payload["revision"] if current else 0) != expected:
        raise ValueError("ad_material_revision_conflict")
    state = {**payload, "revision": expected + 1, "updatedAt": datetime.now(UTC).isoformat()}
    if current:
        changed = db.execute(update(WorkspaceResource).where(WorkspaceResource.id == current.id,
            WorkspaceResource.updated_at == current.updated_at).values(payload=state))
        if changed.rowcount != 1:
            raise ValueError("ad_material_revision_conflict")
    else:
        db.add(WorkspaceResource(id=str(uuid4()), workspace_id=workspace, kind=kind, resource_key=key,
                                 payload=state, created_by=user.id))
    emit_event(db, workspace_id=workspace, event_type="studio.ad.materials.saved", aggregate_type=kind,
               aggregate_id=key, correlation_id=str(uuid4()), actor_id=user.id, payload=state)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("ad_material_revision_conflict") from exc
    db.expire_all()
    return state


def save_kit(db, workspace, identifier, request, user):
    if len({(m.asset_id, m.role) for m in request.materials}) != len(request.materials):
        raise ValueError("ad_material_duplicate")
    from PIL import Image
    from ..object_storage import get_object_storage
    for item in request.materials:
        if item.role not in ROLES:
            raise ValueError("ad_material_role_invalid")
        asset = scoped_asset(db, workspace, item.asset_id)
        if (asset.object_metadata or {}).get("rightsStatus") == "restricted":
            raise ValueError("ad_material_restricted")
        mime = asset.media_type or ""
        if item.role == "identity":
            if not mime.startswith(("image/", "application/pdf", "text/")):
                raise ValueError("ad_material_identity_type_invalid")
        elif item.role == "voice":
            if not mime.startswith("audio/"):
                raise ValueError("ad_material_voice_type_invalid")
        elif not mime.startswith(("image/", "video/")):
            raise ValueError("ad_material_visual_required")
        if item.role in ALPHA_ROLES:
            # PNG cutouts are currently the proven import format. Do not accept an
            # opaque image or H.264 video as if it had useful subject transparency.
            if mime != "image/png":
                raise ValueError("ad_material_cutout_requires_png_alpha")
            with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as path:
                with Image.open(path) as image:
                    if "A" not in image.getbands() or image.getchannel("A").getextrema()[0] == image.getchannel("A").getextrema()[1]:
                        raise ValueError("ad_material_cutout_alpha_unusable")
    payload = request.model_dump(mode="json", by_alias=True, exclude={"expected_revision"})
    return put(db, workspace, KIT, identifier, {**payload, "id": identifier}, request.expected_revision, user)


def view(db, workspace, kind, identifier):
    kits = [item.payload for item in db.scalars(select(WorkspaceResource).where(
        WorkspaceResource.workspace_id == workspace, WorkspaceResource.kind == KIT).order_by(WorkspaceResource.updated_at.desc())).all()]
    binding = row(db, workspace, BINDING, f"{kind}:{identifier}")
    current = binding.payload if binding else {"revision": 0, "kitId": None}
    selected = next((kit for kit in kits if kit["id"] == current.get("kitId")), None)
    choices = cards(selected) if selected else []
    recommended = next((card["id"] for card in choices if card["status"] == "ready_to_compose" and card["score"] > 0), None)
    return {"workspaceId": workspace, "kits": kits, "binding": current, "roles": ROLES,
            "recipes": choices, "recommendedRecipeId": recommended, "apiCalls": 0}


def bind(db, workspace, kind, identifier, kit_id, kit_revision, expected, user):
    kit = row(db, workspace, KIT, kit_id)
    if not kit or kit.payload["revision"] != kit_revision:
        raise ValueError("ad_material_kit_revision_conflict")
    return put(db, workspace, BINDING, f"{kind}:{identifier}",
               {"kitId": kit_id, "kitRevision": kit_revision}, expected, user)


def selected_kit(db, workspace, kind, identifier):
    binding = row(db, workspace, BINDING, f"{kind}:{identifier}")
    if not binding:
        return None
    kit = row(db, workspace, KIT, binding.payload["kitId"])
    if not kit or kit.payload["revision"] != binding.payload["kitRevision"]:
        raise ValueError("ad_material_binding_stale_rebind_required")
    for material in kit.payload["materials"]:
        scoped_asset(db, workspace, material["assetId"])
    return kit.payload


def planning_context(db, record):
    kind, identifier = "document", record.id
    if not row(db, record.workspace_id, BINDING, f"{kind}:{identifier}"):
        matches = [p for p in db.scalars(select(WorkspaceResource).where(WorkspaceResource.workspace_id == record.workspace_id,
            WorkspaceResource.kind == "studio_department")).all() if p.payload.get("documentId") == record.id]
        if len(matches) > 1:
            return {"status": "ambiguous", "instruction": "Bind a kit directly to this document."}
        if matches:
            kind, identifier = "project", matches[0].id
    try:
        kit = selected_kit(db, record.workspace_id, kind, identifier)
    except ValueError:
        return {"status": "stale", "instruction": "Rebind the changed kit before editing."}
    if not kit:
        return {"status": "missing"}
    executable_assets = {getattr(a, "id", None) or a.asset_id for a in record_to_asset_contract(record)}
    return {"status": "bound", "kit": kit, "recipes": cards(kit),
        "instruction": "Untrusted customer materials, not verified claims. Only use assets already imported in the current editor manifest. Recipes target the canonical FFmpeg CPU editor; native projects must use only their declared native commands. Recipe readiness means composable, not quality-approved.",
        "assetsNotImported": [m["assetId"] for m in kit["materials"] if m["assetId"] not in executable_assets]}


def record_to_asset_contract(record):
    from .compatibility import record_to_contract
    contract = record_to_contract(record)
    return contract.native_editor_state.asset_manifest if contract.native_editor_state else contract.assets


def prepare_cutout(db, record, source_id, points, feather, user):
    """Deterministic local preparation from a user-drawn polygon; no segmentation claim."""
    import tempfile
    from pathlib import Path
    from types import SimpleNamespace
    from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps
    from ..object_storage import get_object_storage, sha256_file
    from .craft import write_asset
    source = scoped_asset(db, record.workspace_id, source_id)
    if (source.object_metadata or {}).get("rightsStatus") == "restricted":
        raise ValueError("ad_material_restricted")
    if not (source.media_type or "").startswith("image/"):
        raise ValueError("ad_cutout_image_required")
    written = None
    try:
        with get_object_storage(source.storage_backend).materialize(source.storage_key) as path, tempfile.TemporaryDirectory(prefix="clicko-cutout-") as directory:
            if sha256_file(path) != source.checksum_sha256:
                raise ValueError("craft_asset_checksum_mismatch")
            with Image.open(path) as original:
                if original.width * original.height > 3840 * 2160:
                    raise ValueError("ad_cutout_source_resolution_limit")
                image = ImageOps.exif_transpose(original).convert("RGBA")
            mask = Image.new("L", image.size)
            ImageDraw.Draw(mask).polygon([(round(x*(image.width-1)),round(y*(image.height-1))) for x,y in points], fill=255)
            if feather:
                mask = mask.filter(ImageFilter.GaussianBlur(feather))
            image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
            low, high = image.getchannel("A").getextrema()
            if low == high:
                raise ValueError("ad_material_cutout_alpha_unusable")
            output = Path(directory) / "cutout.png"
            image.save(output)
            scoped_record = SimpleNamespace(id=record.id, workspace_id=record.workspace_id, campaign_id=None, post_id=None, title="Recorte do produto")
            asset, storage, key = write_asset(db, scoped_record, output, suffix=".png", media_type="image/png", asset_type="image",
                title=f"Recorte · {source.title}", metadata={"sourceAssetId": source.id, "sourceChecksum": source.checksum_sha256,
                    "preparation": "user-polygon-v1", "points": points, "featherPixels": feather,
                    "rightsStatus": (source.object_metadata or {}).get("rightsStatus", "unknown")})
            written = storage, key
            db.flush()
            result = {"assetId": asset.id, "label": asset.title, "checksum": asset.checksum_sha256, "apiCalls": 0}
            emit_event(db, workspace_id=record.workspace_id, event_type="studio.ad.cutout.prepared", aggregate_type=KIT,
                aggregate_id=asset.id, correlation_id=str(uuid4()), actor_id=user.id, payload=result)
            db.commit()
            return result
    except Exception:
        db.rollback()
        if written:
            written[0].delete(written[1])
        raise
