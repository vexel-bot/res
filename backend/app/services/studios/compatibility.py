from __future__ import annotations

from datetime import UTC, datetime

from ...domain.studios.contracts import (
    BrandMemoryReferenceV1,
    CreativeBriefV1,
    CreativeCompositionV1,
    CreativeDocumentV1,
    CreativeLayerV1,
    CreativePageV1,
)
from ...models import CreativeDocument
from ...schemas import CreativeCanvas


def canvas_to_composition(canvas: CreativeCanvas, *, page_id: str = "page-1") -> CreativeCompositionV1:
    layers = []
    for layer in canvas.layers:
        raw = layer.model_dump(by_alias=True)
        layers.append(
            CreativeLayerV1(
                id=layer.id,
                kind=layer.type,
                name=layer.name,
                x=layer.x,
                y=layer.y,
                width=layer.width,
                height=layer.height,
                rotation=layer.rotation,
                opacity=layer.opacity,
                visible=layer.visible,
                locked=layer.locked,
                z_index=layer.z_index,
                properties=raw,
            )
        )
    return CreativeCompositionV1(
        pages=[
            CreativePageV1(
                id=page_id,
                width=canvas.width,
                height=canvas.height,
                safe_area=canvas.safe_area,
                background=canvas.background,
                layers=layers,
            )
        ]
    )


def composition_page_to_canvas(document: CreativeDocumentV1, page_index: int = 0) -> CreativeCanvas:
    page = document.composition.pages[page_index]
    if document.composition.narrative.get("editorialV2"):
        # The legacy canvas cannot represent temporal groups or video. Store an explicit
        # read-only navigation poster; the full composition stays in canonical_document.
        return CreativeCanvas.model_validate(
            {
                "width": min(page.width, 4096),
                "height": min(page.height, 4096),
                "background": "#10181c",
                "brandTokens": {"editorialV2": True, "readOnly": True},
                "layers": [
                    {
                        "id": "editorial-studio-poster",
                        "type": "text",
                        "name": "Abrir no estúdio",
                        "text": "Vídeo com edição e motion.\nAbra no estúdio de vídeo para visualizar e revisar.",
                        "x": 24,
                        "y": 24,
                        "width": min(page.width, 4096) - 48,
                        "height": min(page.height, 4096) - 48,
                        "fontSize": 24,
                    }
                ],
            }
        )
    layers = []
    for layer in page.layers:
        raw = dict(layer.properties)
        raw.update(
            {
                "id": layer.id,
                "name": layer.name,
                "type": layer.kind,
                "x": layer.x,
                "y": layer.y,
                "width": layer.width,
                "height": layer.height,
                "rotation": layer.rotation,
                "opacity": layer.opacity,
                "visible": layer.visible,
                "locked": layer.locked,
                "zIndex": layer.z_index,
            }
        )
        layers.append(raw)
    return CreativeCanvas.model_validate(
        {
            "schemaVersion": "creative-v1",
            "width": page.width,
            "height": page.height,
            "safeArea": page.safe_area,
            "background": page.background,
            "brandTokens": {"brandRevision": document.brand_memory_ref.revision},
            "layers": layers,
        }
    )


def composition_to_canvas(document: CreativeDocumentV1) -> CreativeCanvas:
    return composition_page_to_canvas(document)


def record_to_contract(record: CreativeDocument) -> CreativeDocumentV1:
    if record.canonical_document:
        contract = CreativeDocumentV1.model_validate(record.canonical_document)
        return contract.model_copy(
            update={
                "revision": record.revision,
                "version": record.version,
                "updated_at": record.updated_at,
            }
        )

    canvas = CreativeCanvas.model_validate(record.document)
    created_at = record.created_at or datetime.now(UTC)
    updated_at = record.updated_at or created_at
    return CreativeDocumentV1(
        document_id=record.id,
        workspace_id=record.workspace_id,
        title=record.title,
        content_type="visual",
        revision=getattr(record, "revision", 1) or 1,
        version=record.version,
        actor_id=getattr(record, "created_by", None),
        correlation_id=getattr(record, "correlation_id", None) or f"legacy:{record.id}",
        campaign_ref={"id": record.campaign_id} if record.campaign_id else None,
        post_ref={"id": record.post_id} if record.post_id else None,
        brand_memory_ref=BrandMemoryReferenceV1(id=record.workspace_id, revision=1),
        brief=CreativeBriefV1(objective="Imported legacy creative", audience="Workspace audience"),
        composition=canvas_to_composition(canvas),
        created_at=created_at,
        updated_at=updated_at,
    )


def persist_contract(record: CreativeDocument, contract: CreativeDocumentV1) -> None:
    record.schema_version = contract.schema_version
    record.canonical_document = contract.model_dump(by_alias=True, mode="json")
    record.document = composition_to_canvas(contract).model_dump(by_alias=True)
    record.revision = contract.revision
    record.correlation_id = contract.correlation_id
