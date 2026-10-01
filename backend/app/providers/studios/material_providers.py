"""Provider-neutral discovery policy for editorial materials.

Discovery never makes a candidate render-ready. Acquisition, rights checks and
pixel inspection remain separate steps.
"""

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MaterialProviderSpec:
    id: str
    kinds: tuple[str, ...]
    capabilities: tuple[str, ...]
    acquisition: str
    cost_policy: str


PROVIDERS = {
    "pexels": MaterialProviderSpec(
        "pexels",
        ("image", "video"),
        ("discover", "acquire", "license_receipt"),
        "download_then_inspect",
        "api_free_tier_request",
    ),
    "brandfetch": MaterialProviderSpec(
        "brandfetch",
        ("logo",),
        ("discover", "preview", "brand_metadata"),
        "preview_only_without_verified_brand_asset",
        "provider_contract",
    ),
    "procedural-icon": MaterialProviderSpec(
        "procedural-icon",
        ("image",),
        ("discover", "acquire", "deterministic"),
        "local_registered_component",
        "local",
    ),
    "procedural-sound": MaterialProviderSpec(
        "procedural-sound",
        ("sound_effect",),
        ("discover", "acquire", "deterministic", "original"),
        "local_registered_component",
        "local",
    ),
    "gemini-image": MaterialProviderSpec(
        "gemini-image",
        ("image", "wardrobe"),
        ("generate", "acquire", "original_only"),
        "generate_then_inspect",
        "reserved_before_submission",
    ),
    "local-diffusion": MaterialProviderSpec(
        "local-diffusion",
        ("video",),
        ("generate", "acquire", "original_only", "quarantine", "experimental"),
        "generate_then_inspect_and_review",
        "local_compute_measured",
    ),
    "gemini-video": MaterialProviderSpec(
        "gemini-video",
        ("video",),
        ("generate", "acquire", "original_only", "experimental"),
        "generate_then_inspect",
        "reserved_before_submission",
    ),
    "sora-video": MaterialProviderSpec(
        "sora-video",
        ("video",),
        ("generate", "acquire", "original_only"),
        "single_four_second_clip_then_inspect",
        "usd_0.10_per_second_until_retirement",
    ),
}


def provider_manifest(settings):
    image_provider = settings.studio_editing_ai_image_provider or settings.studio_editing_ai_provider
    video_provider = settings.studio_editing_ai_video_provider or settings.studio_editing_ai_provider
    gemini_key = (
        settings.studio_gemini_production_key
        if settings.environment == "production"
        else settings.studio_gemini_test_key
    )
    readiness = {
        "pexels": bool(settings.pexels_api_key),
        "brandfetch": bool(getattr(settings, "brandfetch_client_id", None)),
        "procedural-icon": True,
        "procedural-sound": True,
        "gemini-image": bool(settings.studio_gemini_enabled and gemini_key and image_provider == "gemini"),
        "local-diffusion": bool(getattr(settings, "studio_local_diffusion_enabled", False)),
        "gemini-video": bool(
            settings.studio_gemini_enabled
            and getattr(settings, "gemini_video_generation_enabled", False)
            and gemini_key
            and video_provider == "gemini"
            and settings.studio_gemini_video_model == "veo-3.1-lite-generate-preview"
        ),
        "sora-video": bool(
            settings.openai_outbound_enabled
            and settings.openai_video_generation_enabled
            and settings.openai_api_key
            and settings.studio_editing_ai_video_provider == "sora"
        ),
    }
    return [
        {**asdict(spec), "configured": readiness[provider_id]}
        for provider_id, spec in PROVIDERS.items()
    ]


def _value(need, name, default=None):
    return getattr(need, name, default)


def _semantic_query(need):
    return " ".join(
        part.strip()
        for part in (
            need.query,
            _value(need, "entity", ""),
            _value(need, "action", ""),
            _value(need, "appearance", ""),
        )
        if part and part.strip()
    )


def _brand_domain(query):
    match = re.search(r"(?i)(?:https?://)?([a-z0-9](?:[a-z0-9-]{0,62})(?:\.[a-z0-9-]{1,63})+)", query)
    return match.group(1).lower() if match else None


def _generation_candidate(need, settings):
    image_provider = settings.studio_editing_ai_image_provider or settings.studio_editing_ai_provider
    key = (
        settings.studio_gemini_production_key
        if settings.environment == "production"
        else settings.studio_gemini_test_key
    )
    if not settings.studio_gemini_enabled or image_provider != "gemini" or not key:
        return None
    return {
        "id": "generate-original:" + _value(need, "id", "material"),
        "provider": "gemini-image",
        "providerId": settings.studio_gemini_image_model,
        "kind": "image",
        "description": _value(need, "visual_description", "") or _semantic_query(need),
        "query": need.query,
        "purpose": need.purpose,
        "estimatedCostUsd": 0.08,
        "rightsStatus": "generated_original_candidate",
        "official": False,
        "renderReady": False,
        "requiresGeneration": True,
        "requiresInspection": True,
    }


def _video_generation_candidate(need, settings):
    if not (
        settings.openai_outbound_enabled
        and settings.openai_video_generation_enabled
        and settings.openai_api_key
        and settings.studio_editing_ai_video_provider == "sora"
    ):
        return None
    duration = _value(need, "duration_seconds")
    if duration is not None and not 3.5 <= duration <= 4.5:
        return None
    return {
        "id": "generate-video-original:" + _value(need, "id", "material"),
        "provider": "sora-video",
        "providerId": "sora-2",
        "profileId": "sora-2",
        "kind": "video",
        "description": _value(need, "visual_description", "") or _semantic_query(need),
        "query": need.query,
        "purpose": need.purpose,
        "durationSeconds": 4,
        "estimatedCostUsd": 0.40,
        "rightsStatus": "generated_original_candidate",
        "official": False,
        "renderReady": False,
        "requiresGeneration": True,
        "requiresInspection": True,
    }


def _gemini_video_generation_candidate(need, settings):
    key = (
        settings.studio_gemini_production_key
        if settings.environment == "production"
        else settings.studio_gemini_test_key
    )
    model = getattr(settings, "studio_gemini_video_model", "")
    video_provider = getattr(settings, "studio_editing_ai_video_provider", None) or settings.studio_editing_ai_provider
    if not (
        settings.studio_gemini_enabled
        and getattr(settings, "gemini_video_generation_enabled", False)
        and key
        and video_provider == "gemini"
        and model == "veo-3.1-lite-generate-preview"
    ):
        return None
    duration = float(_value(need, "duration_seconds", 0) or 0)
    if not 3 <= duration <= 10:
        return None
    return {
        "id": "generate-video-gemini:" + _value(need, "id", "material"),
        "provider": "gemini-video",
        "providerId": model,
        "profileId": "veo-3.1-lite-720p-experimental-v1",
        "kind": "video",
        "description": _value(need, "visual_description", "") or _semantic_query(need),
        "query": need.query,
        "purpose": need.purpose,
        "durationSeconds": duration,
        "estimatedCostUsd": round(duration * 0.05, 6),
        "priceVersion": "google-2026-09-14",
        "rightsStatus": "generated_original_candidate",
        "official": False,
        "renderReady": False,
        "requiresGeneration": True,
        "requiresInspection": True,
        "qualificationState": "experimental",
    }


def _local_video_generation_candidate(need, settings):
    if not getattr(settings, "studio_local_diffusion_enabled", False):
        return None
    requested = float(_value(need, "duration_seconds", 1) or 1)
    return {
        "id": "generate-video-local:" + _value(need, "id", "material"),
        "provider": "local-diffusion",
        "providerId": "animatediff-lightning-sd15-a-v1",
        "profileId": "animatediff-lightning-sd15-a-v1",
        "kind": "video",
        "description": _value(need, "visual_description", "") or _semantic_query(need),
        "query": need.query,
        "purpose": need.purpose,
        "durationSeconds": min(requested, 1.0),
        "estimatedCostUsd": 0,
        "costPolicy": "local_compute_measured",
        "rightsStatus": "generated_original_candidate",
        "official": False,
        "renderReady": False,
        "requiresGeneration": True,
        "requiresInspection": True,
        "requiresHumanAdmission": True,
        "qualificationState": "experimental",
    }


def discover_with_registry(need, settings, *, pexels_discover, procedural_discover):
    """Choose providers by declared need; never degrade required footage to an icon."""
    kind = need.kind
    source_class = _value(need, "source_class", "auto")
    fallback = _value(need, "fallback_behavior", "block")
    official = bool(_value(need, "official_required", False))

    # A composable icon is a request for the registered graphic component,
    # not a stock photograph with similar search terms. If its subject is not
    # registered, expose that limitation rather than changing the medium.
    if (
        kind == "image"
        and not official
        and _value(need, "requirement_class") == "composable"
        and _value(need, "component_id") == "procedural-icon"
    ):
        result = procedural_discover(need.query, need.purpose, kind)
        return {
            **result,
            "reason": None if result.get("candidates") else "registered_component_semantic_match_required",
            "providerReceipts": [
                {"provider": "procedural-icon", "configured": True, "status": result.get("status")}
            ],
        }

    if kind == "sound_effect" and source_class in {"auto", "catalog", "generated_original"}:
        from .procedural_audio import discover as discover_procedural_sound

        result = discover_procedural_sound(need.query, need.purpose, kind)
        if result.get("candidates"):
            return {
                **result,
                "providerReceipts": [
                    {"provider": "procedural-sound", "configured": True, "status": result.get("status")}
                ],
            }

    procedural_eligible = (
        kind == "image"
        and source_class in {"auto", "catalog", "generated_original", "licensed_stock"}
        and fallback == "block"
        and bool(_value(need, "alpha_required", False))
        and set(_value(need, "post_processing", [])) <= {"remove_background", "convert_to_png"}
    )

    if official or source_class == "brand_asset" or kind == "logo":
        domain = _brand_domain(need.query)
        client_id = getattr(settings, "brandfetch_client_id", None)
        if not domain or not client_id:
            return {
                "status": "registered_sources_required",
                "candidates": [],
                "reason": "authorized_brand_asset_required",
                "providerReceipts": [{"provider": "brandfetch", "configured": bool(client_id)}],
            }
        preview = f"https://cdn.brandfetch.io/{domain}?c={client_id.get_secret_value()}"
        return {
            "status": "discovery_only",
            "candidates": [
                {
                    "id": "brandfetch-preview:" + domain,
                    "provider": "brandfetch",
                    "providerId": domain,
                    "kind": "logo",
                    "previewUrl": preview,
                    "renderReady": False,
                    "acquisitionAllowed": False,
                    "cachePolicy": "remote_hotlink_preview_only",
                    "rightsStatus": "verified_asset_required",
                    "reason": "brandfetch_logo_api_hotlink_is_not_a_reproducible_render_asset",
                }
            ],
            "providerReceipts": [{"provider": "brandfetch", "configured": True}],
        }

    receipts = []
    if kind in {"image", "video"} and source_class not in {"project", "catalog", "generated_original"}:
        key = settings.pexels_api_key
        result = pexels_discover(
            key.get_secret_value() if key else None,
            _semantic_query(need),
            kind,
            orientation=_value(need, "orientation", "any"),
            duration_seconds=_value(need, "duration_seconds"),
        )
        receipts.append({"provider": "pexels", "configured": bool(key), "status": result.get("status")})
        if result.get("candidates"):
            # An alpha-backed icon request can be satisfied by a registered
            # component even when stock discovery returns only photographs.
            # Keep both routes explicit so inspection/ranking can choose the
            # semantically appropriate candidate; never silently replace a
            # required photo or video with an icon.
            if procedural_eligible:
                procedural = procedural_discover(need.query, need.purpose, kind)
                receipts.append(
                    {"provider": "procedural-icon", "configured": True, "status": procedural.get("status")}
                )
                if procedural.get("candidates"):
                    return {
                        **result,
                        "candidates": [*procedural["candidates"], *result["candidates"]],
                        "providerReceipts": receipts,
                    }
            return {**result, "providerReceipts": receipts}

    if kind == "video" and source_class == "generated_original":
        local_generation = _local_video_generation_candidate(need, settings)
        receipts.append({"provider": "local-diffusion", "configured": bool(local_generation)})
        generation = _video_generation_candidate(need, settings)
        receipts.append({"provider": "sora-video", "configured": bool(generation)})
        gemini_generation = _gemini_video_generation_candidate(need, settings)
        receipts.append({"provider": "gemini-video", "configured": bool(gemini_generation)})
        generated_candidates = [item for item in (local_generation, gemini_generation, generation) if item]
        if generated_candidates:
            return {
                "status": "generation_candidate",
                "candidates": generated_candidates,
                "providerReceipts": receipts,
            }

    # Registered components precede generation when their semantic rule matches
    # exactly. They support alpha directly, so remove-background/PNG requests are
    # redundant rather than incompatible. An unrecognized object never receives
    # a generic icon fallback.
    if procedural_eligible:
        result = procedural_discover(need.query, need.purpose, kind)
        receipts.append({"provider": "procedural-icon", "configured": True, "status": result.get("status")})
        if result.get("candidates"):
            return {**result, "providerReceipts": receipts}

    generation = None
    if kind in {"image", "wardrobe"} and (
        source_class == "generated_original" or fallback == "generated_original"
    ):
        generation = _generation_candidate(need, settings)
        receipts.append({"provider": "gemini-image", "configured": bool(generation)})
        if generation:
            return {"status": "generation_candidate", "candidates": [generation], "providerReceipts": receipts}

    return {
        "status": "unconfigured"
        if any(receipt["provider"] == "pexels" and not receipt["configured"] for receipt in receipts)
        else "unavailable",
        "candidates": [],
        "reason": "required_material_provider_unavailable",
        "providerReceipts": receipts,
        "alternatives": ["project", "catalog", "licensed_stock", "generated_original"],
    }
