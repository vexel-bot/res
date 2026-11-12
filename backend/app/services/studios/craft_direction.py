"""Native editing research and project-scoped material preparation."""
import json
import hashlib
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

from ...domain.studios.contracts import NativeMediaReferenceV1
from ...domain.studios.editing_resources import ResourceMetadataV1
from ..object_storage import get_object_storage, sha256_file
from .editing_resources import acquire_registered_source, registered_sources, store_resource

NATIVE_KINDS = {"image", "logo", "wardrobe", "video", "music", "sound_effect"}
NATIVE_MEDIA = {"image/png", "image/jpeg", "image/webp", "video/mp4", "audio/wav", "audio/mpeg", "audio/flac"}


def repertoire():
    def load(name):
        return json.loads(Path(__file__).with_name(name).read_text(encoding="utf-8"))
    native = load("craft_motion_repertoire.v1.json")
    old = load("motion_editorial_cards.v1.json")
    styles = load("craft_editing_styles.v1.json")
    research = load("craft_research_observations.v1.json")
    cards = {}
    for source, entries in (("motion_editorial_cards.v1.json", old["cards"]),
                            ("craft_motion_repertoire.v1.json", native["cards"]),
                            ("craft_editing_styles.v1.json", styles["cards"]),
                            ("craft_research_observations.v1.json", research["cards"])):
        for original in entries:
            card = dict(original)
            card["provenance"] = {"file": source, "evidenceState": card.get("state", "hypothesis")}
            if "operations" in card:
                card["operationBinding"] = {
                    "language": "legacy_canonical", "requiresNativeAdaptation": True,
                    "instruction": "These are editorial operation names. Discover equivalent native commands before execution.",
                }
            elif card.get("native"):
                card["operationBinding"] = {
                    "language": "native_editorial_recipe", "requiresCapabilityCheck": True,
                }
            else:
                card["operationBinding"] = {"language": "editorial_procedure", "requiresNativeAdaptation": True}
            cards[card["id"]] = card
    return cards


def reference_index():
    return [
        {"id": key, "intent": card["intent"], "state": card.get("state"),
         "formats": card.get("formats", []), "kind": card.get("kind", "technique")}
        for key, card in repertoire().items()
    ]


def repertoire_version():
    from .editing_repertoire import seed_techniques
    payload = {"cards": repertoire(), "legacy": [card.model_dump(mode="json", by_alias=True)
                                                for card in seed_techniques()], "method": editing_method()}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def references(ids):
    if not isinstance(ids, list) or not 1 <= len(ids) <= 5 or not all(isinstance(item, str) for item in ids):
        raise ValueError("craft_reference_ids_invalid")
    cards = repertoire()
    return {key: cards.get(key, {}) for key in ids}


def editing_method():
    return json.loads(Path(__file__).with_name("craft_editing_styles.v1.json").read_text(encoding="utf-8"))["method"]


def search_repertoire(db, workspace_id, query, engine="effectcraft", limit=12):
    """Retrieve editorial evidence from native, legacy and tenant-owned knowledge without inference calls."""
    from . import editing_repertoire

    if not isinstance(query, str) or len(query) > 2000 or type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("craft_repertoire_query_invalid")
    if engine not in {"effectcraft", "filmcraft", "photocraft"}:
        raise ValueError("craft_repertoire_engine_invalid")

    def terms(text):
        plain = unicodedata.normalize("NFKD", text.casefold()).encode("ascii", "ignore").decode()
        return set(re.findall(r"[a-z0-9]{3,}", plain))

    wanted = terms(query)
    local = []
    for card in repertoire().values():
        score = len(wanted & terms(json.dumps(card, ensure_ascii=False)))
        local.append((score, card["id"], card))
    hits = editing_repertoire.search_repertoire(db, workspace_id, query) if query.strip() else []
    hit_documents = {hit["documentId"] for hit in hits}
    from sqlalchemy import select
    from ...models import KnowledgeDocument
    retrieved = set()
    if hit_documents:
        rows = db.scalars(select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == workspace_id, KnowledgeDocument.id.in_(hit_documents),
        ))
        retrieved = {(row.document_metadata or {}).get("technique", {}).get("id") for row in rows}
    for technique in editing_repertoire.available_repertoire(db, workspace_id):
        payload = technique.model_dump(mode="json", by_alias=True)
        score = len(wanted & terms(json.dumps(payload, ensure_ascii=False))) + (10 if technique.id in retrieved else 0)
        if not score and wanted:
            continue
        local.append((score, "legacy:" + technique.id, {
            "id": "legacy:" + technique.id, "intent": technique.purpose, "state": technique.qualification,
            "technique": payload, "provenance": {"library": "editing_repertoire", "workspaceId": workspace_id},
            "operationBinding": {"language": "legacy_canonical", "requiresNativeAdaptation": True,
                                 "nativeEngine": engine},
        }))
    ranked = sorted(local, key=lambda item: (-item[0], item[1]))
    matches = [card for score, _, card in ranked if score or not wanted]
    return {"query": query, "engine": engine, "repertoireVersion": repertoire_version(),
            "matches": matches[:limit], "total": len(matches), "retrievedKnowledge": hits,
            "instruction": "Preserve evidence qualifications. Adapt editorial procedures to verified native commands."}


def editorial_context(db, workspace_id, document_id, query="", engine="effectcraft", brand_id=None):
    from .craft_learning import project_feedback, style_guide

    # Retrieval has a short search contract. The full creative instruction is
    # separately retained in the directing context; never reject a valid long brief here.
    retrieval_query = query[:2000]
    guides = [style_guide(db, workspace_id)]
    if document_id:
        guides.append(style_guide(db, workspace_id, "document", document_id))
    if brand_id:
        guides.append(style_guide(db, workspace_id, "brand", brand_id))
    return {
        "method": editing_method(), "repertoireVersion": repertoire_version(), "referenceIndex": reference_index(),
        "relevantReferences": search_repertoire(db, workspace_id, retrieval_query, engine, limit=6),
        "retrievalQueryCoverage": {"sourceCharacters": len(query), "searchedCharacters": len(retrieval_query),
                                   "fullInstructionRetainedByDirector": True},
        "styleGuides": guides, "projectFeedback": project_feedback(db, workspace_id, document_id) if document_id else [],
        "instruction": "Use approved lessons as scoped preferences. Candidate lessons are proposals awaiting user review. "
                       "Choose and combine editing languages for the brief and available materials.",
    }


def source_candidates(db, workspace_id, query):
    if not isinstance(query, str) or len(query) > 250:
        raise ValueError("craft_material_query_invalid")
    return [
        {key: candidate.get(key) for key in ("id", "title", "kind", "description", "sourceUrl", "autoAcquire")}
        for candidate in registered_sources(db, workspace_id, query) if candidate.get("kind") in NATIVE_KINDS
    ][:12]


def working_copy(db, job, user, asset, maximum_side):
    if not asset.media_type.startswith("image/"):
        raise ValueError("craft_material_resize_requires_image")
    meta = (asset.object_metadata or {}).get("editingResource", {})
    fields = {field.serialization_alias or name for name, field in ResourceMetadataV1.model_fields.items()}
    metadata = ResourceMetadataV1.model_validate({key: value for key, value in meta.items() if key in fields})
    with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
        if sha256_file(source).lower() != asset.checksum_sha256.lower():
            raise ValueError("craft_asset_checksum_mismatch")
        with Image.open(source) as opened:
            if max(opened.size) <= maximum_side:
                return asset
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((maximum_side, maximum_side), Image.Resampling.LANCZOS)
            alpha = "A" in image.getbands() or "transparency" in image.info
            with tempfile.TemporaryDirectory(prefix="clicko-source-working-copy-") as directory:
                path = Path(directory) / ("image.png" if alpha else "image.jpg")
                if alpha:
                    image.convert("RGBA").save(path, format="PNG")
                else:
                    image.convert("RGB").save(path, format="JPEG", quality=92)
                return store_resource(
                    db, job.workspace_id, f"{asset.title[:207]} · {maximum_side}px", path,
                    metadata, user.id,
                    provenance={"craftWorkingCopy": {
                        "sourceAssetId": asset.id, "sourceChecksum": asset.checksum_sha256,
                        "maximumSide": maximum_side,
                    }},
                )


def acquire_material(db, job, user, draft, manifests, source_id, maximum_side=None):
    if not isinstance(source_id, str) or not 1 <= len(source_id) <= 120:
        raise ValueError("craft_material_source_invalid")
    if maximum_side is not None and (type(maximum_side) is not int or not 480 <= maximum_side <= 8192):
        raise ValueError("craft_material_size_invalid")
    state = job.result_payload or {}
    acquired = state.get("acquiredSources", {})
    acquisition_key = f"{source_id}:{maximum_side}" if maximum_side else source_id
    if acquisition_key in acquired:
        return acquired[acquisition_key]
    asset = acquire_registered_source(db, job.workspace_id, source_id, user.id, automatic=True)
    if asset.media_type not in NATIVE_MEDIA:
        raise ValueError("craft_material_format_unavailable")
    if (asset.object_metadata or {}).get("rightsStatus") == "restricted":
        raise ValueError("craft_material_restricted")
    original_id = asset.id
    if maximum_side is not None:
        asset = working_copy(db, job, user, asset, maximum_side)
    info = {
        "sourceId": source_id, "originalAssetId": original_id, "assetId": asset.id, "title": asset.title, "mediaType": asset.media_type,
        "provenance": (asset.object_metadata or {}).get("editingResource", {}),
    }
    entry = None
    if not any(entry.asset_id == asset.id for entry in manifests):
        relative_path = f"assets/{asset.id}{Path(asset.storage_key).suffix}"
        target = draft.directory / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
            if sha256_file(source).lower() != asset.checksum_sha256.lower():
                raise ValueError("craft_asset_checksum_mismatch")
            shutil.copyfile(source, target)
        entry = NativeMediaReferenceV1(
            asset_id=asset.id, path=relative_path, checksum_sha256=asset.checksum_sha256, media_type=asset.media_type,
        )
        media = {
            "assetId": asset.id, "path": str(target), "relativePath": relative_path,
            "checksumSha256": asset.checksum_sha256, "mediaType": asset.media_type,
        }
    job.result_payload = {**state, "acquiredSources": {**acquired, acquisition_key: info}}
    db.commit()
    if entry is not None:
        manifests.append(entry)
        draft.params["media"].append(media)
    return info


def media_ids(job):
    return list(dict.fromkeys([
        *job.request_payload["assetIds"],
        *(entry["assetId"] for entry in (job.result_payload or {}).get("acquiredSources", {}).values()),
    ]))
