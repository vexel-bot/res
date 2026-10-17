from types import SimpleNamespace

import pytest

from app.services.studios.material_discovery import discover_for_need


def need(**changes):
    return SimpleNamespace(
        **{
            "kind": "video",
            "query": "people discussing an idea",
            "official_required": False,
            "purpose": "Demonstrate communication",
            "acceptance_criteria": ["Visible discussion"],
            "source_class": "licensed_stock",
            "fallback_behavior": "block",
            "orientation": "landscape",
            "duration_seconds": 2,
            "alpha_required": False,
            "post_processing": [],
            "visual_description": "People exchanging a message",
            "entity": "two creators",
            "action": "sharing a draft",
            "appearance": "natural office light",
            **changes,
        }
    )


def settings(**changes):
    return SimpleNamespace(
        **{
            "environment": "test",
            "pexels_api_key": None,
            "brandfetch_client_id": None,
            "studio_editing_ai_provider": "none",
            "studio_editing_ai_image_provider": "none",
            "studio_gemini_enabled": False,
            "studio_gemini_test_key": None,
            "studio_gemini_production_key": None,
            "studio_gemini_image_model": "gemini-3.1-flash-lite-image",
            "studio_local_diffusion_enabled": False,
            "studio_editing_ai_video_provider": "none",
            "openai_outbound_enabled": False,
            "openai_video_generation_enabled": False,
            "openai_api_key": None,
            **changes,
        }
    )


def test_system_searches_from_need_without_importing_or_certifying(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.studios.material_discovery.get_settings", settings
    )

    def search(*args, **kwargs):
        calls.append((args, kwargs))
        return {"status": "candidates", "candidates": [{"providerId": "one", "renderReady": False}]}

    monkeypatch.setattr("app.services.studios.material_discovery.discover", search)
    cache = {}
    result = discover_for_need(need(), cache=cache)
    assert result["nextStep"] == "import_and_inspect"
    assert result["renderReady"] is False
    discover_for_need(need(), cache=cache)
    assert len(calls) == 1
    assert calls[0][0][1] == (
        "people discussing an idea two creators sharing a draft natural office light"
    )


def test_official_material_does_not_fall_back_to_stock(monkeypatch):
    def unexpected(*args):
        raise AssertionError("Stock search must not replace official material")

    monkeypatch.setattr("app.services.studios.material_discovery.discover", unexpected)
    assert discover_for_need(need(official_required=True), cache={})["status"] == "registered_sources_required"


def test_missing_connector_is_explicit(monkeypatch):
    monkeypatch.setattr("app.services.studios.material_discovery.get_settings", settings)
    result = discover_for_need(need(), cache={})
    assert result["status"] == "unconfigured"
    assert not result["candidates"]


def test_required_footage_never_falls_back_to_procedural_icon(monkeypatch):
    monkeypatch.setattr("app.services.studios.material_discovery.get_settings", settings)
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover_procedural",
        lambda *args: (_ for _ in ()).throw(AssertionError("procedural fallback is incompatible")),
    )
    result = discover_for_need(need(kind="video"), cache={})
    assert result["status"] == "unconfigured"
    assert result["reason"] == "required_material_provider_unavailable"


def test_registered_component_precedes_image_generation_on_exact_match(monkeypatch):
    monkeypatch.setattr("app.services.studios.material_discovery.get_settings", settings)
    result = discover_for_need(
        need(
            kind="image",
            query="ícone de lâmpada para uma ideia",
            source_class="generated_original",
            alpha_required=True,
            post_processing=["remove_background"],
            visual_description="símbolo de ideia com transparência",
            duration_seconds=None,
        ),
        cache={},
    )
    assert result["candidates"][0]["provider"] == "procedural-icon"
    assert result["candidates"][0]["providerId"] == "Lightbulb"
    assert result["candidates"][0]["semanticMatch"]["confidence"] == "rule_exact"


def test_explicit_composable_icon_does_not_query_stock(monkeypatch):
    monkeypatch.setattr("app.services.studios.material_discovery.get_settings", settings)
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("stock must not replace a graphic component")),
    )
    result = discover_for_need(
        need(
            kind="image",
            query="Minimalist editorial icon for tablet",
            source_class="auto",
            requirement_class="composable",
            component_id="procedural-icon",
            alpha_required=False,
            duration_seconds=None,
        ),
        cache={},
    )
    assert result["candidates"][0]["providerId"] == "Tablet"
    missing = discover_for_need(
        need(
            kind="image",
            query="icon for an unknown subject",
            source_class="auto",
            requirement_class="composable",
            component_id="procedural-icon",
            duration_seconds=None,
        ),
        cache={},
    )
    assert missing["candidates"] == []
    assert missing["reason"] == "registered_component_semantic_match_required"


def test_synthesized_icon_siblings_keep_the_declared_component_route():
    from app.domain.studios.contextual_editing_v2 import EditorialMaterialV2
    from app.services.studios.contextual_editing_v2 import (
        ensure_visual_material_needs,
        promote_synthesized_composable_icons,
    )
    from test_semantic_demonstration import canonical_direction

    direction = canonical_direction()
    scene = direction.scenes[0]
    scene.material_needs = [
        EditorialMaterialV2(
            id="icon-main", target_id="hero", kind="image", query="ícone de tela",
            purpose="Tela principal", requirement_class="composable", component_id="procedural-icon",
            blueprint_requirement_id="screen-family",
        ),
        EditorialMaterialV2(
            id="inspect-derived", target_id="other", kind="image", query="Smartphone inativo",
            purpose="Smartphone inativo",
        ),
    ]
    repairs = promote_synthesized_composable_icons(direction)
    assert len(repairs) == 1
    assert repairs[0]["component"] == "Smartphone"
    assert scene.material_needs[1].component_id == "procedural-icon"
    assert scene.material_needs[1].blueprint_requirement_id == "screen-family"
    ensure_visual_material_needs(direction)
    assert all(need.alpha_required for need in scene.material_needs[:2])


def test_registered_interface_sound_is_discovered_and_decodes_as_audio(monkeypatch, tmp_path):
    import subprocess

    from app.providers.studios.procedural_audio import render

    monkeypatch.setattr("app.services.studios.material_discovery.get_settings", settings)
    result = discover_for_need(
        need(
            kind="sound_effect",
            query="som curto de publicação",
            purpose="Confirmar que a peça entrou no feed",
            source_class="catalog",
            duration_seconds=None,
            visual_description="",
        ),
        cache={},
    )
    candidate = result["candidates"][0]
    assert candidate["provider"] == "procedural-sound"
    assert candidate["providerId"] == "publish_confirm"

    output = tmp_path / "publish.wav"
    receipt = render(candidate["providerId"], output)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert receipt["durationSeconds"] > 0
    assert probe.stdout.strip() == "audio"


def test_alpha_icon_request_keeps_procedural_route_with_configured_stock(monkeypatch):
    class Secret:
        @staticmethod
        def get_secret_value():
            return "pexels-test-key"

    monkeypatch.setattr(
        "app.services.studios.material_discovery.get_settings",
        lambda: settings(pexels_api_key=Secret()),
    )
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover",
        lambda *args, **kwargs: {
            "status": "candidates",
            "candidates": [{"provider": "pexels", "providerId": "photo-1", "kind": "image"}],
        },
    )
    result = discover_for_need(
        need(
            kind="image",
            query="ícone de lâmpada para uma ideia",
            alpha_required=True,
            post_processing=["remove_background", "convert_to_png"],
            visual_description="símbolo de ideia com transparência",
            duration_seconds=None,
        ),
        cache={},
    )
    assert result["candidates"][0]["provider"] == "procedural-icon"
    assert any(item.get("provider") == "pexels" for item in result["candidates"])


def test_mockup_cannot_be_accepted_as_unrelated_icon():
    from app.providers.studios.procedural_resources import discover as discover_procedural

    result = discover_procedural(
        "mockup de post vertical típico de rede social",
        "Visualizar um formato derivado da ideia",
        "image",
    )
    assert result["candidates"] == []


def test_unrecognized_image_does_not_receive_generic_procedural_fallback(monkeypatch):
    monkeypatch.setattr("app.services.studios.material_discovery.get_settings", settings)
    result = discover_for_need(
        need(
            kind="image",
            query="ornitorrinco em uma biblioteca barroca",
            source_class="catalog",
            alpha_required=False,
            post_processing=[],
            visual_description="",
            duration_seconds=None,
        ),
        cache={},
    )
    assert result["candidates"] == []


def test_brandfetch_candidate_is_preview_only(monkeypatch):
    class Secret:
        def get_secret_value(self):
            return "public-client"

    monkeypatch.setattr(
        "app.services.studios.material_discovery.get_settings",
        lambda: settings(brandfetch_client_id=Secret()),
    )
    result = discover_for_need(
        need(kind="logo", query="example.com", official_required=True, source_class="brand_asset"),
        cache={},
    )
    assert result["status"] == "discovery_only"
    assert result["candidates"][0]["acquisitionAllowed"] is False
    assert result["nextStep"] == "provide_authorized_asset"


def test_background_removal_fails_closed_without_pinned_model(tmp_path, monkeypatch):
    from app.providers.studios.background_removal import remove_background

    source = tmp_path / "source.png"
    source.write_bytes(b"not-used-before-preflight")
    config = settings(
        studio_background_removal_enabled=True,
        studio_background_removal_model_path=str(tmp_path / "u2netp.onnx"),
        studio_background_removal_model_sha256="a" * 64,
    )
    monkeypatch.setattr(
        "app.providers.studios.background_removal.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("worker must not start")),
    )
    with pytest.raises(ValueError, match="pinned_model_required"):
        remove_background(source, tmp_path / "result.png", config)


def test_sora_is_only_a_four_second_generated_original_candidate(monkeypatch):
    class Secret:
        @staticmethod
        def get_secret_value():
            return "test"

    monkeypatch.setattr(
        "app.services.studios.material_discovery.get_settings",
        lambda: settings(
            studio_editing_ai_video_provider="sora",
            openai_outbound_enabled=True,
            openai_video_generation_enabled=True,
            openai_api_key=Secret(),
        ),
    )
    accepted = discover_for_need(
        need(source_class="generated_original", duration_seconds=4, fallback_behavior="block"), cache={}
    )
    assert accepted["status"] == "generation_candidate"
    assert accepted["candidates"][0]["estimatedCostUsd"] == 0.40
    rejected = discover_for_need(
        need(source_class="generated_original", duration_seconds=8, fallback_behavior="block"), cache={}
    )
    assert not rejected["candidates"]


def test_local_diffusion_is_an_explicit_quarantined_candidate(monkeypatch):
    monkeypatch.setattr(
        "app.services.studios.material_discovery.get_settings",
        lambda: settings(studio_local_diffusion_enabled=True),
    )
    result = discover_for_need(
        need(source_class="generated_original", duration_seconds=1, fallback_behavior="block"),
        cache={},
    )
    candidate = result["candidates"][0]
    assert candidate["provider"] == "local-diffusion"
    assert candidate["providerId"] == "animatediff-lightning-sd15-a-v1"
    assert candidate["estimatedCostUsd"] == 0
    assert candidate["requiresHumanAdmission"] is True
    assert candidate["renderReady"] is False


def test_acquisition_rejects_unregistered_download_host_before_network(monkeypatch):
    from app.services.studios.material_acquisition import acquire_candidate

    def unexpected(*args):
        raise AssertionError("Invalid host must not reach download")

    monkeypatch.setattr("app.services.studios.material_acquisition.download_resource", unexpected)
    with pytest.raises(ValueError, match="material_acquisition_download_missing"):
        acquire_candidate(
            None,
            "tenant",
            {
                "provider": "pexels",
                "kind": "video",
                "providerId": "x",
                "files": [{"link": "https://127.0.0.1/private.mp4"}],
            },
            need(),
            "actor",
        )


def test_acquisition_stores_pending_inspection_not_render_approval(monkeypatch):
    from app.services.studios.material_acquisition import acquire_candidate

    monkeypatch.setattr("app.services.studios.material_acquisition.download_resource", lambda *args: None)
    asset = SimpleNamespace(object_metadata={}, checksum_sha256="a" * 64)
    monkeypatch.setattr("app.services.studios.material_acquisition.store_resource", lambda *args: asset)
    result = acquire_candidate(
        SimpleNamespace(flush=lambda: None),
        "tenant",
        {
            "provider": "pexels",
            "kind": "video",
            "providerId": "x",
            "files": [{"link": "https://videos.pexels.com/example.mp4"}],
        },
        need(),
        "actor",
    )
    assert result.object_metadata["visualReview"] == "pending"
    assert result.object_metadata["materialAcquisition"]["status"] == "awaiting_inspection"
