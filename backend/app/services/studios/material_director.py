"""Resolve editorial needs against actual files; never treat a search result as media."""

from ...domain.studios.contextual_editing import EditingAlternativeV1, EditingBlockerV1
from ...domain.studios.editing_resources import ResolveResourceV1
from .editing_resources import resolve_resource


def resolve_material_needs(db, workspace_id, document_id, request, beats, user_id):
    requests, blockers = [], []
    indexed = {b.clip_id: b for b in beats}
    for need in request.material_needs:
        if need.clip_id not in indexed:
            raise ValueError("editing_material_scene_not_found")
        result = resolve_resource(
            db,
            workspace_id,
            ResolveResourceV1(
                query=need.query,
                kind=need.kind,
                document_id=document_id,
                exact=need.exact,
            ),
        )
        candidates = result["candidates"]

        def eligible(candidate, need=need):
            resource = candidate["resource"]
            return (
                candidate.get("reviewStatus") in (None, "passed")
                and (need.kind != "font" or resource.get("variant") == need.font_variant)
                and (
                    not need.official_required
                    or (resource.get("official") and resource.get("sourceUrl") and not candidate.get("generationJobId"))
                )
            )

        candidates = [candidate for candidate in candidates if eligible(candidate)]
        sources = [
            s
            for s in result.get("sources", [])
            if s.get("autoAcquire")
            and (not need.exact or s["title"].casefold() == need.query.casefold())
            and (not need.official_required or s.get("official"))
        ]
        acquisition_error = None
        if need.kind == "font":
            candidates = [c for c in candidates if c["resource"].get("variant") == need.font_variant]
            if not candidates and not need.asset_id and not sources:
                from .editing_fonts import acquire_font

                try:
                    acquire_font(db, workspace_id, need.query, need.font_variant, user_id)
                    candidates = resolve_resource(db, workspace_id, ResolveResourceV1(query=need.query, kind="font"))[
                        "candidates"
                    ]
                    candidates = [c for c in candidates if c["resource"].get("variant") == need.font_variant]
                except (ValueError, OSError):
                    acquisition_error = "Envie a variante da fonte ou configure sua origem no acervo."
        if not candidates and not need.asset_id and len(sources) == 1:
            from .editing_resources import acquire_registered_source

            try:
                acquire_registered_source(db, workspace_id, sources[0]["id"], user_id, automatic=True)
                candidates = resolve_resource(
                    db, workspace_id, ResolveResourceV1(query=need.query, kind=need.kind, exact=need.exact)
                )["candidates"]
            except (ValueError, OSError):
                acquisition_error = (
                    "Não foi possível obter o arquivo da fonte cadastrada. Envie o material ou escolha outra fonte."
                )
        candidates = [candidate for candidate in candidates if eligible(candidate)]
        if need.asset_id:
            # Explicit selection still goes through workspace, format, review and origin checks.
            from .editing_resources import catalog

            candidates = [c for c in catalog(db, workspace_id, kind=need.kind, asset_id=need.asset_id) if eligible(c)]
        chosen = candidates[0] if len(candidates) == 1 else None
        record = {
            **need.model_dump(mode="json", by_alias=True),
            "candidates": candidates,
            "status": "resolved" if chosen else "awaiting_choice",
            "resolvedAssetId": chosen["id"] if chosen else None,
            "searchOrder": ["project", "catalog", "registered_sources", "generation_or_request"],
            "sources": result.get("sources", []),
            "acquisitionError": acquisition_error,
            "generationAllowed": not need.official_required and need.kind in {"image", "video", "wardrobe"},
        }
        beat = indexed[need.clip_id]
        field = (
            "mask_asset_id"
            if need.role == "mask"
            else "audio_asset_id"
            if need.role in {"music", "ambience", "effect", "narration", "dialogue"}
            else "support_asset_id"
        )
        if chosen and need.role == "font":
            if need.kind != "font" or (request.font_asset_id and request.font_asset_id != chosen["id"]):
                chosen = None
            else:
                request.font_asset_id = chosen["id"]
        elif chosen and need.role != "reference":
            valid_media = (
                chosen["mediaType"].startswith("audio/")
                if field == "audio_asset_id"
                else chosen["mediaType"].startswith(("image/", "video/"))
            )
            if not valid_media or (getattr(beat, field) and getattr(beat, field) != chosen["id"]):
                chosen = None
            else:
                setattr(beat, field, chosen["id"])
                if field == "audio_asset_id":
                    beat.audio_role = need.role
        if not chosen:
            record.update(status="awaiting_choice", resolvedAssetId=None)
            alternatives = [
                EditingAlternativeV1(
                    id="supply",
                    label="Adicionar ou escolher o material",
                    impact=f"{need.purpose} Use o acervo, envie um arquivo ou importe de uma fonte cadastrada.",
                    action="wait",
                )
            ]
            if not need.required:
                alternatives.append(
                    EditingAlternativeV1(
                        id="keep-original",
                        label="Continuar sem este complemento",
                        impact="Preservar o material original da cena.",
                        action="keep_original",
                    )
                )
            blockers.append(
                EditingBlockerV1(
                    id=f"material-{need.id}",
                    code="editing_material_required",
                    target_id=need.clip_id,
                    message=f"Material necessário: {need.query}. {need.purpose}",
                    alternatives=alternatives,
                )
            )
        requests.append(record)
    return requests, blockers
