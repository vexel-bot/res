"""Curated visual evidence, stored per workspace and never attached to an edit."""

import base64
import hashlib
import json
from pathlib import Path
from uuid import UUID

from PIL import Image
from sqlalchemy import select

from ...config import get_settings
from ...domain.studios.editing_resources import ResourceMetadataV1
from ...models import LibraryAsset, Membership, User
from ..object_storage import get_object_storage, sha256_file
from .editing_resources import store_resource

CATALOG_PATH = Path(__file__).with_name("craft_reference_evidence.v1.json")
EVIDENCE_ROOT = Path(__file__).resolve().parents[4] / "docs/studios/knowledge/reference-evidence"
ROLE = "analysis/reference_only"
WORKSPACE_PREFIX = "workspace."


def _read_catalog(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schemaVersion") != "clicko.reference-evidence.v1":
        raise ValueError("craft_reference_catalog_invalid")
    entries = value.get("references", [])
    if not entries or len({item["id"] for item in entries}) != len(entries):
        raise ValueError("craft_reference_catalog_invalid")
    return value


def _catalog():
    return _read_catalog(CATALOG_PATH)


def _workspace_root(workspace_id):
    return Path(get_settings().storage_path).resolve() / "_craft_reference_packs" / str(UUID(str(workspace_id)))


def _workspace_entries(workspace_id):
    if workspace_id is None:
        return []
    manifest = _workspace_root(workspace_id) / "catalog.json"
    if not manifest.is_file():
        return []
    entries = _read_catalog(manifest)["references"]
    if any(not item["id"].startswith(WORKSPACE_PREFIX) for item in entries):
        raise ValueError("craft_reference_workspace_catalog_invalid")
    return entries


def evidence_version(workspace_id=None):
    catalog = _catalog()
    local = _workspace_entries(workspace_id)
    if local:
        catalog = {**catalog, "references": [*catalog["references"], *local]}
    return hashlib.sha256(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def reference_index(workspace_id=None):
    """A compact, non-mutating list; only inspect_reference loads image pixels."""
    return [{
        "id": item["id"], "title": item["reference"]["title"],
        "creator": item["reference"]["creator"], "sourceUrl": item["reference"].get("url"),
        "role": ROLE, "coverage": item["coverage"], "state": item["state"],
        "inspectionTool": "inspect_reference",
        "temporalAvailable": bool(item.get("temporal")),
    } for item in [*_catalog()["references"], *_workspace_entries(workspace_id)]]


def _entry(reference_id, workspace_id=None):
    if not isinstance(reference_id, str) or not 1 <= len(reference_id) <= 160:
        raise ValueError("craft_reference_id_invalid")
    entries = (_workspace_entries(workspace_id) if reference_id.startswith(WORKSPACE_PREFIX)
               else _catalog()["references"])
    item = next((entry for entry in entries if entry["id"] == reference_id), None)
    if item is None:
        raise ValueError("craft_reference_not_found")
    return item


def _evidence_root(item, workspace_id):
    return _workspace_root(workspace_id) if item["id"].startswith(WORKSPACE_PREFIX) else EVIDENCE_ROOT


def _evidence_file(item, workspace_id=None):
    name = item["file"]
    if not isinstance(name, str) or not name or "/" in name or "\\" in name or Path(name).name != name:
        raise ValueError("craft_reference_catalog_path_invalid")
    root = _evidence_root(item, workspace_id)
    path = (root / name).resolve()
    if path.parent != root.resolve() or not path.is_file():
        raise ValueError("craft_reference_evidence_unavailable")
    if path.stat().st_size > 5 * 1024 * 1024 or sha256_file(path) != item["sha256"]:
        raise ValueError("craft_reference_evidence_checksum_mismatch")
    with Image.open(path) as image:
        if image.format != "JPEG" or image.width > 8000 or image.height > 8000:
            raise ValueError("craft_reference_evidence_image_invalid")
        image.verify()
    return path


def _authorized(db, workspace_id, user_id):
    member = db.scalar(select(Membership.id).join(User, User.id == Membership.user_id).where(
        Membership.workspace_id == workspace_id, Membership.user_id == user_id, User.is_active.is_(True),
    ))
    if member is None:
        raise ValueError("craft_reference_workspace_forbidden")


def _metadata(item, workspace_id=None):
    return {
        "referenceId": item["id"], "role": ROLE, "reference": item["reference"],
        "coverage": item["coverage"], "state": item["state"], "sha256": item["sha256"],
        "catalogVersion": evidence_version(workspace_id if item["id"].startswith(WORKSPACE_PREFIX) else None),
        "productionUse": "not_authorized",
        **({"baseline": item["baseline"]} if "baseline" in item else {}),
    }


def register_reference(db, workspace_id, user_id, reference_id):
    """Return a verified analysis asset. Caller owns its transaction; no project is changed."""
    _authorized(db, workspace_id, user_id)
    item = _entry(reference_id, workspace_id)
    source = _evidence_file(item, workspace_id)
    metadata = _metadata(item, workspace_id)
    candidates = db.scalars(select(LibraryAsset).where(
        LibraryAsset.workspace_id == workspace_id,
        LibraryAsset.checksum_sha256 == item["sha256"],
        LibraryAsset.lifecycle_status == "active",
    ).order_by(LibraryAsset.created_at, LibraryAsset.id))
    for candidate in candidates:
        if (candidate.object_metadata or {}).get("craftReferenceEvidence") == metadata:
            return candidate
    resource = ResourceMetadataV1(
        kind="image", description="Curated sampled visual evidence for editing analysis, not production media.",
        sourceUrl=item["reference"].get("url"),
        usageEvidence=(
            "Analysis only. Source attribution and incomplete coverage are recorded; production use is not authorized."
        ),
        tags=["reference_only", "analysis", reference_id],
    )
    return store_resource(
        db, workspace_id, "Reference evidence · " + item["reference"]["title"], source, resource, user_id,
        provenance={"craftReferenceEvidence": metadata, "rightsStatus": "restricted", "usageRole": ROLE},
    )


def inspect_reference(db, workspace_id, user_id, reference_id):
    """Resolve a curated ID to text + actual image blocks, outside production manifests."""
    asset = register_reference(db, workspace_id, user_id, reference_id)
    metadata = {
        **(asset.object_metadata or {})["craftReferenceEvidence"], "assetId": asset.id,
        "workspaceId": workspace_id, "mediaType": asset.media_type,
        "interpretation": (
            "These are sampled visual states, not an observation of all motion or sound. "
            "Requested sample times are approximate landmarks, not measured cut boundaries. "
            "Do not import this analysis-only asset into the advertisement."
        ),
    }
    with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
        if sha256_file(source) != metadata["sha256"]:
            raise ValueError("craft_reference_asset_checksum_mismatch")
        data = source.read_bytes()
    blocks = [
        {"type": "text", "text": json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.b64encode(data).decode("ascii")}},
    ]
    return {"reference": metadata, "blocks": blocks}


def temporal_source(reference_id, workspace_id=None):
    """Resolve a registered temporal reference and verify its source bytes."""
    item = _entry(reference_id, workspace_id)
    temporal = item.get("temporal")
    if not temporal:
        return item, None
    name = temporal["file"]
    root = _evidence_root(item, workspace_id)
    path = (root / name).resolve()
    if (Path(name).name != name or path.parent != root.resolve() or not path.is_file()
            or sha256_file(path) != temporal["sha256"] or temporal["mediaType"] not in {"video/mp4", "audio/wav"}):
        raise ValueError("craft_reference_temporal_evidence_invalid")
    return item, path


def review_reference(draft, reference_id, args, *, workspace_id=None):
    """Read an optional hash-bound temporal source without adding production media."""
    from .craft_review import review_draft

    item, path = temporal_source(reference_id, workspace_id)
    if path is None:
        return {"status": "unavailable", "reason": "Only sampled still evidence is registered for this reference.",
                "referenceId": reference_id, "coverage": item["coverage"]}
    temporal = item["temporal"]
    identifier = "reference:" + reference_id
    original = draft.params["media"]
    try:
        draft.params["media"] = [*original, {"assetId": identifier, "path": str(path),
            "checksumSha256": temporal["sha256"], "mediaType": temporal["mediaType"]}]
        result = review_draft(draft, {**args, "assetId": identifier})
    finally:
        draft.params["media"] = original
    result["report"]["source"].update(kind="reference_only", referenceId=reference_id)
    report = result["report"]
    report["reference"] = _metadata(item, workspace_id)
    if temporal.get("transcript"):
        interval = report["interval"]
        report["transcript"] = {
            "status": "machine_transcript",
            "timeBasis": "reference_source",
            "segments": [segment for segment in temporal["transcript"]
                         if segment["startSeconds"] < interval["endSeconds"]
                         and segment["endSeconds"] > interval["startSeconds"]],
            "limitations": "Automatic transcript. Check uncertain words and delivery against playback.",
        }
    # Rebuild the text block after source classification. No production asset is registered.
    result["blocks"][0] = {"type": "text", "text": json.dumps(result["report"], ensure_ascii=False)}
    return result
