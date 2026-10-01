"""Discover from an editorial need; external candidates remain outside the render."""

from datetime import UTC, datetime
from types import SimpleNamespace

from ...config import get_settings
from ...providers.studios.material_providers import discover_with_registry
from ...providers.studios.pexels_resources import discover
from ...providers.studios.procedural_resources import discover as discover_procedural


def discover_for_need(need, *, cache):
    # Cache is scoped to one planning operation, never shared across clients.
    key = (
        need.kind,
        need.query,
        need.official_required,
        need.purpose,
        tuple(need.acceptance_criteria),
        getattr(need, "source_class", "auto"),
        getattr(need, "requirement_class", None),
        getattr(need, "component_id", None),
        getattr(need, "visual_description", ""),
        getattr(need, "entity", ""),
        getattr(need, "action", ""),
        getattr(need, "appearance", ""),
        getattr(need, "orientation", "any"),
        getattr(need, "duration_seconds", None),
        getattr(need, "alpha_required", False),
        tuple(getattr(need, "post_processing", [])),
        getattr(need, "fallback_behavior", "block"),
    )
    if key in cache:
        return cache[key]
    if len(cache) >= 8:
        result = {"status": "deferred", "candidates": [], "reason": "discovery_batch_limit"}
    else:
        try:
            result = discover_with_registry(
                need,
                get_settings(),
                pexels_discover=discover,
                procedural_discover=discover_procedural,
            )
        except ValueError as error:
            result = {"status": "unavailable", "candidates": [], "reason": str(error)}
    result = {
        **result,
        "queriedAt": datetime.now(UTC).isoformat(),
        "query": need.query,
        "purpose": need.purpose,
        "entity": getattr(need, "entity", ""),
        "action": getattr(need, "action", ""),
        "appearance": getattr(need, "appearance", ""),
        "acceptanceCriteria": need.acceptance_criteria,
        "nextStep": (
            "generate_and_inspect"
            if result.get("status") == "generation_candidate"
            else "provide_authorized_asset"
            if result.get("status") == "discovery_only"
            else "import_and_inspect"
            if result.get("candidates")
            else "resolve_source_access"
        ),
        "renderReady": False,
    }
    cache[key] = result
    return result


def preliminary_inventory(direction):
    """Discover cheap candidates before executable composition is finalized.

    The inventory contains provider metadata only. It never admits a file or
    claims that a candidate satisfies a visual requirement.
    """

    cache = {}
    inventory = []
    for beat in direction.beats:
        demonstration = beat.visual_blueprint.demonstration if beat.visual_blueprint else None
        for material in demonstration.indispensable_materials if demonstration else []:
            if material.requirement_class == "composable" or material.procedural_allowed:
                inventory.append(
                    {
                        "beatId": beat.id,
                        "requirementId": material.id,
                        "requirementClass": material.requirement_class,
                        "status": "component_available",
                        "componentId": material.component_id,
                        "candidates": [],
                        "visualSuitability": "not_observed",
                    }
                )
                continue
            need = SimpleNamespace(
                id=material.id,
                kind=material.kind,
                query=material.query,
                purpose=material.purpose,
                official_required=material.source_class == "brand_asset",
                source_class=material.source_class,
                visual_description=material.query,
                entity="",
                action="",
                appearance="",
                orientation="any",
                duration_seconds=None,
                alpha_required=False,
                post_processing=[],
                fallback_behavior="block",
                acceptance_criteria=material.acceptance_criteria,
                preferred_criteria=material.preferred_criteria,
            )
            discovery = discover_for_need(need, cache=cache)
            candidates = [
                {
                    key: candidate.get(key)
                    for key in (
                        "provider",
                        "providerId",
                        "kind",
                        "width",
                        "height",
                        "durationSeconds",
                        "description",
                        "observation",
                    )
                    if candidate.get(key) is not None
                }
                for candidate in discovery.get("candidates", [])[:6]
            ]
            inventory.append(
                {
                    "beatId": beat.id,
                    "requirementId": material.id,
                    "requirementClass": material.requirement_class,
                    "status": discovery.get("status"),
                    "query": material.query,
                    "candidates": candidates,
                    "visualSuitability": "not_observed",
                    "reason": discovery.get("reason"),
                }
            )
    return inventory
