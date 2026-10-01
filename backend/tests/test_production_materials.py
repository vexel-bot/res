from types import SimpleNamespace as NS

from test_scene_compiler_v2 import direction

from app.domain.studios.contextual_editing import digest
from app.domain.studios.contextual_editing_v2 import EditorialAnimationV2, EditorialElementV2, EditorialMaterialV2
from app.domain.studios.motion import MotionKeyframeV1
from app.models import LibraryAsset, StudioGenerationJob
from app.services.studios.contextual_editing_v2 import omit_unresolved_optional_materials
from app.services.studios.production_materials import (
    _decompose_rejected_stock_graphic,
    _decompose_unobservable_attention_state,
    _harden_composed_stock_requirement,
    _harden_existing_stock_graphic_decomposition,
    _harden_format_transformation_footage,
    _inspection_job_state,
    _material_acquisition_with_receipt,
    _project_checksum_bound_supported_facets,
    _project_decomposed_visual_evidence,
    _project_equivalent_visual_evidence,
    _reclassify_aesthetic_acceptance_criteria,
    _replan_after_material_rejections,
    _retry_material_discovery,
    _technical_duration_reconciliation,
    advance_materials,
)


def test_unobservable_attention_is_assigned_to_path_and_text_instead_of_stock():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    scene.elements.extend(
        [
            EditorialElementV2(
                id="interrupted-path",
                kind="path",
                purpose="Caminho interrompido antes da confirmação",
                start_frame=0,
                duration_frames=target.duration_frames,
                x=80,
                y=80,
                width=400,
                height=300,
                points=[
                    {"x": 0, "y": 0},
                    {"x": 1, "y": 1},
                ],
            ),
            EditorialElementV2(
                id="attention-qualification",
                kind="text",
                purpose="Preservar a ressalva",
                start_frame=0,
                duration_frames=target.duration_frames,
                x=80,
                y=480,
                width=700,
                height=160,
                text="ALCANCE NÃO GARANTE ATENÇÃO",
            ),
        ]
    )
    need = EditorialMaterialV2(
        id="attention-stock",
        target_id=target.id,
        kind="video",
        query="person ignores a phone notification",
        purpose="Show that reach does not guarantee attention",
        source_class="licensed_stock",
        requirement_class="mandatory",
        action="Person ignores the notification",
        visual_description="Person ignores a phone notification",
        acceptance_criteria=[
            "Pessoa real visível",
            "Ausência de reação nítida",
            "Celular visível",
        ],
    )
    scene.material_needs = [need]

    revised, receipt = _decompose_unobservable_attention_state(
        NS(direction=source), {"sceneId": scene.id}, need
    )

    revised_need = revised.scenes[0].material_needs[0]
    assert revised_need.action.startswith("Pessoa usa o dispositivo")
    assert revised_need.acceptance_criteria == [
        "Pessoa reconhecível em ambiente real",
        "Dispositivo digital claro em quadro",
        "Tela do dispositivo visível",
        "Gesto natural de uso do dispositivo",
    ]
    assert receipt["reason"] == "internal_attention_state_assigned_to_deterministic_path_and_text"
    assert receipt["createdPathElementId"] is None


def test_unobservable_attention_creates_an_executable_path_when_missing():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    scene.elements.append(
        EditorialElementV2(
            id="attention-qualification",
            kind="text",
            purpose="Preservar a ressalva sobre atenção",
            start_frame=0,
            duration_frames=target.duration_frames,
            x=80,
            y=480,
            width=700,
            height=160,
            text="ALCANCE NÃO GARANTE ATENÇÃO",
        )
    )
    need = EditorialMaterialV2(
        id="attention-stock",
        target_id=target.id,
        kind="video",
        query="person ignores a phone notification",
        purpose="Show that reach does not guarantee attention",
        source_class="licensed_stock",
        requirement_class="mandatory",
        action="Person ignores the notification",
        visual_description="Person ignores a phone notification",
        acceptance_criteria=["Pessoa real visível", "Celular visível"],
    )
    scene.material_needs = [need]

    revised, receipt = _decompose_unobservable_attention_state(
        NS(direction=source), {"sceneId": scene.id}, need
    )

    path = next(element for element in revised.scenes[0].elements if element.kind == "path")
    assert path.reveal == "path"
    assert path.points
    assert "paths" in revised.scenes[0].technique_ids
    assert receipt["createdPathElementId"] == path.id


def test_material_framing_and_environment_preferences_do_not_veto_visible_subject():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    need = EditorialMaterialV2(
        id="phone",
        target_id=target.id,
        kind="video",
        query="person holding a smartphone",
        purpose="Show the message on mobile",
        source_class="licensed_stock",
        requirement_class="mandatory",
        visual_description="smartphone, hand, visible content, real environment, centered display",
        acceptance_criteria=[
            "Smartphone e mão claramente visíveis",
            "Conteúdo na tela perceptível",
            "Ambiente real claramente visível",
            "Display ocupa parcela central do quadro",
        ],
    )
    scene.material_needs = [need]

    revised, receipt = _reclassify_aesthetic_acceptance_criteria(
        NS(direction=source),
        {"sceneId": scene.id},
        need,
        {"artifacts": {}},
    )

    revised_need = revised.scenes[0].material_needs[0]
    assert revised_need.acceptance_criteria == [
        "Smartphone e mão claramente visíveis",
        "Conteúdo na tela perceptível",
    ]
    assert "Ambiente real claramente visível" in revised_need.preferred_criteria
    assert "Display ocupa parcela central do quadro" in revised_need.preferred_criteria
    assert receipt["reason"] == "aesthetic_preferences_removed_from_mandatory_pixel_gate"


def test_checksum_identity_never_certifies_a_new_semantic_claim():
    assert _project_checksum_bound_supported_facets(
        None,
        "workspace",
        {
            "materialHistory": [
                {
                    "status": "accepted",
                    "checksum": "a" * 64,
                    "request": {
                        "purpose": "Show a person using a phone",
                        "criteria": ["Person and phone are visible"],
                    },
                }
            ]
        },
        None,
        None,
        NS(
            purpose="Show the person ignoring the message",
            acceptance_criteria=["The person's attention visibly leaves the screen"],
        ),
    ) is None


def test_material_receipts_are_need_scoped_and_cumulative():
    first = {
        "status": "accepted",
        "checksum": "a" * 64,
        "request": {
            "purpose": "Show devices",
            "criteria": ["Devices visible"],
            "requiredSeconds": 4,
            "sourceStartSeconds": 0,
        },
    }
    second = {
        "status": "accepted",
        "checksum": "a" * 64,
        "request": {
            "purpose": "Show varied attention",
            "criteria": ["People visible", "Attention varies"],
            "requiredSeconds": 4,
            "sourceStartSeconds": 0,
        },
    }
    asset = NS(object_metadata={"materialAcquisition": {"inspectionReceipt": first}})

    asset.object_metadata = _material_acquisition_with_receipt(asset, second)

    acquisition = asset.object_metadata["materialAcquisition"]
    assert acquisition["inspectionReceipt"] == second
    assert acquisition["inspectionReceipts"] == [first, second]


def test_rejected_composite_stock_need_becomes_footage_plus_registered_overlay():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    need = EditorialMaterialV2(
        id="need",
        target_id=target.id,
        kind="video",
        query="human hands holding paper with an idea icon, slow circular movement",
        purpose="Show a tangible idea",
        source_class="licensed_stock",
        entity="hands and idea icon",
        action="slow circular movement",
        post_processing=["remove_background"],
        acceptance_criteria=[
            "Human hands remain visible",
            "The idea icon is clearly legible",
            "The circular motion is visible",
        ],
        blueprint_requirement_id="idea-source",
    )
    scene.material_needs = [need]
    state = {
        "materialHistory": [
            {"needId": "need", "status": "requires_alternative"}
            for _ in range(3)
        ]
    }

    revised, receipt = _decompose_rejected_stock_graphic(
        NS(direction=source),
        {"sceneId": scene.id},
        need,
        state,
        {"searchRevision": 1},
    )

    revised_scene = revised.scenes[0]
    footage_need = next(item for item in revised_scene.material_needs if item.id == "need")
    overlay_need = next(item for item in revised_scene.material_needs if item.id != "need")
    assert footage_need.query == "human hands holding paper"
    assert footage_need.visual_description == "Human hands remain visible"
    assert footage_need.acceptance_criteria == ["Human hands remain visible"]
    assert overlay_need.kind == "image"
    assert overlay_need.alpha_required
    assert overlay_need.blueprint_requirement_id == "idea-source"
    overlay = next(item for item in revised_scene.elements if item.id == overlay_need.target_id)
    assert overlay.alignment.target_id == target.id
    assert {item.property for item in overlay.animations} == {
        "position_x", "position_y", "scale_x", "scale_y"
    }
    assert receipt["providerSubmission"] is False


def test_existing_decomposition_moves_graphic_motion_out_of_stock_requirement():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    need = EditorialMaterialV2(
        id="need",
        target_id=target.id,
        kind="video",
        query="human hands holding paper slow circular movement",
        purpose="Show a tangible idea",
        source_class="licensed_stock",
        entity="hands and idea icon",
        action="slow circular movement",
        acceptance_criteria=["Human hands remain visible", "The circular motion is visible"],
    )
    scene.material_needs = [need]
    scene.elements.append(
        source.scenes[0].elements[0].model_copy(
            update={
                "id": f"{target.id}-graphic-overlay",
                "kind": "image",
                "purpose": "idea icon",
                "asset_id": None,
                "animations": [],
            }
        )
    )
    scene.material_needs.append(
        EditorialMaterialV2(
            id="need-overlay",
            target_id=f"{target.id}-graphic-overlay",
            kind="image",
            query="idea icon",
            purpose="show exact icon",
            alpha_required=True,
        )
    )

    revised, receipt = _harden_existing_stock_graphic_decomposition(
        NS(direction=source), {"sceneId": scene.id}, need
    )

    migrated = revised.scenes[0]
    footage = next(item for item in migrated.material_needs if item.id == "need")
    overlay = next(item for item in migrated.elements if item.id.endswith("graphic-overlay"))
    assert footage.query == "human hands holding paper"
    assert footage.acceptance_criteria == ["Human hands remain visible"]
    assert not footage.action
    assert overlay.alignment.target_id == target.id
    assert overlay.animations
    assert receipt["reason"] == "decomposed_overlay_execution_hardened"


def test_composed_overlay_removes_graphic_and_motion_demands_from_stock():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    scene.elements.append(
        EditorialElementV2(
            id="idea-overlay",
            kind="shape",
            purpose="Animate the idea independently from the footage",
            visual_role="accent",
            x=100,
            y=100,
            width=120,
            height=120,
            duration_frames=target.duration_frames,
            animations=[
                EditorialAnimationV2(
                    property="position_x",
                    keyframes=[
                        MotionKeyframeV1(frame=0, value=0),
                        MotionKeyframeV1(frame=10, value=20),
                    ],
                )
            ],
        )
    )
    need = EditorialMaterialV2(
        id="need",
        target_id=target.id,
        kind="video",
        query="human hands holding paper circular lento",
        purpose="Show a tangible idea",
        source_class="licensed_stock",
        acceptance_criteria=[
            "Human hands remain visible",
            "The idea icon is clearly legible",
            "The circular motion is visible",
        ],
        blueprint_requirement_id="idea-source",
    )
    scene.material_needs = [need]

    revised, receipt = _harden_composed_stock_requirement(
        NS(direction=source), {"sceneId": scene.id}, need
    )

    revised_need = revised.scenes[0].material_needs[0]
    assert revised_need.query == "human hands holding paper"
    assert revised_need.acceptance_criteria == ["Human hands remain visible"]
    assert revised_need.action == ""
    assert receipt["reason"] == "composed_stock_requirement_hardened"


def test_format_transformation_keeps_stock_context_and_moves_adaptation_to_component():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1

    clone = target.model_copy(update={"id": "second-device"})
    scene.elements.append(clone)
    scene.compositions = [
        EditorialCompositionV1(
            id="formats",
            family="format_transformation",
            target_ids=[target.id, clone.id],
            purpose="Adapt one message",
            expected_result="The viewport visibly changes",
            viewport_formats=["portrait", "landscape"],
            continuity_key="shared-device",
        )
    ]
    need = EditorialMaterialV2(
        id="need",
        target_id=target.id,
        kind="video",
        query="devices showing an adapted message",
        purpose="Show real devices",
        source_class="licensed_stock",
        visual_description="Devices showing an adapted message",
        action="continuous format adaptation",
        acceptance_criteria=[
            "Real digital devices are visible",
            "The message is adapted to each format",
            "The transition is continuous",
        ],
        blueprint_requirement_id="shared-device-source",
    )
    second = need.model_copy(update={"id": "need-2", "target_id": clone.id})
    scene.material_needs = [need, second]

    revised, receipt = _harden_format_transformation_footage(
        NS(direction=source), {"sceneId": scene.id}, need
    )

    for item in revised.scenes[0].material_needs:
        assert item.query == "people using digital devices"
        assert item.acceptance_criteria == ["Real digital devices are visible"]
        assert not item.action
    assert receipt["componentOwns"] == [
        "message_adaptation", "viewport_change", "continuous_transition"
    ]
    assert receipt["providerSubmission"] is False


def test_unresolved_preferred_media_is_omitted_from_executable_direction_with_receipt():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    from app.domain.studios.contextual_editing_v2 import EditorialCompositionV1

    first = EditorialElementV2(
        id="format-one",
        kind="card",
        purpose="First deterministic viewport",
        duration_frames=scene.duration_frames,
        width=300,
        height=500,
        text="IDEIA",
        content_identity="shared-idea",
    )
    second = first.model_copy(update={"id": "format-two"})
    scene.elements.extend([first, second])
    scene.compositions = [
        EditorialCompositionV1(
            id="formats",
            family="format_transformation",
            target_ids=[first.id, second.id],
            purpose="Adapt one message",
            expected_result="The viewport visibly changes",
            viewport_formats=["portrait", "landscape"],
            continuity_key="shared-idea",
        )
    ]
    scene.material_needs = [
        EditorialMaterialV2(
            id="optional-stock",
            target_id=target.id,
            kind="video",
            query="optional laptop footage",
            purpose="Add context",
            source_class="licensed_stock",
            requirement_class="preferred",
        )
    ]

    executable, receipts = omit_unresolved_optional_materials(
        source,
        [
            {
                "sceneId": scene.id,
                "id": "optional-stock",
                "required": False,
                "status": "awaiting_choice",
            }
        ],
    )

    executable_scene = executable.scenes[0]
    assert target.id not in {element.id for element in executable_scene.elements}
    assert not executable_scene.material_needs
    assert receipts == [
        {
            "sceneId": scene.id,
            "needId": "optional-stock",
            "targetId": target.id,
            "replacementTargetId": first.id,
            "componentId": "formats",
            "reason": "unresolved_preferred_material_omitted_from_executable_direction",
            "providerSubmission": False,
        }
    ]


def test_decomposed_footage_reuses_only_previously_supported_pixel_evidence():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    need = EditorialMaterialV2(
        id="need",
        target_id=target.id,
        kind="video",
        query="human hands holding paper",
        purpose="Show a tangible idea",
        source_class="licensed_stock",
        visual_description="Human hands remain visible",
        acceptance_criteria=["Human hands remain visible"],
        duration_seconds=1,
    )
    scene.material_needs = [need]
    old_criteria = ["old combined requirement", "Human hands remain visible", "idea icon"]
    history = [
        {"needId": "need", "reason": "composite_stock_requirement_decomposed"},
        {
            "needId": "need",
            "status": "requires_alternative",
            "assetId": "asset",
            "checksum": "a" * 64,
            "jobId": "inspection",
            "request": {
                "criteria": old_criteria,
                "requiredSeconds": 2,
                "sourceStartSeconds": 0,
            },
            "result": {
                "confidence": 0.95,
                "criteria": [
                    {"index": 0, "result": "contradicted", "evidence": "icon absent", "sampleIndices": [0]},
                    {"index": 1, "result": "supported", "evidence": "hands visible", "sampleIndices": [0, 1]},
                    {"index": 2, "result": "contradicted", "evidence": "icon absent", "sampleIndices": [0]},
                ],
            },
            "samples": [{"index": 0}, {"index": 1}],
        },
    ]
    asset = NS(
        id="asset",
        workspace_id="tenant",
        lifecycle_status="active",
        checksum_sha256="a" * 64,
    )
    db = NS(get=lambda model, identity: asset if model is LibraryAsset and identity == "asset" else None)

    projected_asset, receipt = _project_decomposed_visual_evidence(
        db,
        "tenant",
        {"materialHistory": history},
        NS(direction=source),
        scene,
        need,
    )

    assert projected_asset is asset
    assert receipt["status"] == "accepted"
    assert receipt["projection"]["providerSubmission"] is False
    assert all(item["result"] == "supported" for item in receipt["result"]["criteria"])


def test_equivalent_need_reuses_checksum_bound_inspection_without_provider_call():
    source = direction(kind="video", text="")
    scene = source.scenes[0]
    target = scene.elements[0]
    need = EditorialMaterialV2(
        id="second-format",
        target_id=target.id,
        kind="video",
        query="people using devices",
        purpose="Show the same content in another viewport",
        visual_description="People visibly use digital devices",
        acceptance_criteria=["People and devices are visible"],
        duration_seconds=1,
        blueprint_requirement_id="shared-format-source",
    )
    scene.material_needs = [need]
    criteria = [
        "The pixels themselves must visibly and recognizably depict this requested subject: "
        "People visibly use digital devices. Metadata, filename, a future overlay, path, animation "
        "or surrounding scene cannot satisfy this criterion.",
        "People and devices are visible",
    ]
    previous = {
        "status": "accepted",
        "assetId": "asset",
        "checksum": "a" * 64,
        "needId": "first-format",
        "sceneId": scene.id,
        "blueprintRequirementId": "shared-format-source",
        "request": {
            "purpose": need.purpose,
            "criteria": criteria,
            "requiredSeconds": 2,
            "sourceStartSeconds": 0,
        },
    }
    asset = NS(
        id="asset", workspace_id="tenant", lifecycle_status="active", checksum_sha256="a" * 64
    )
    db = NS(get=lambda model, identity: asset if model is LibraryAsset and identity == "asset" else None)

    reused_asset, receipt = _project_equivalent_visual_evidence(
        db,
        "tenant",
        {"materialHistory": [previous]},
        NS(direction=source),
        scene,
        need,
    )

    assert reused_asset is asset
    assert receipt["needId"] == "second-format"
    assert receipt["projection"]["providerSubmission"] is False


def test_repeated_visual_rejections_trigger_bounded_local_replan():
    need = EditorialMaterialV2(
        id="need", target_id="hero", kind="video", query="person using laptop",
        purpose="Show a person consuming content", visual_description="Person with headphones and laptop",
    )
    source = direction(kind="video", text="")
    state = {
        "jobs": {"direction": "original", "composition": "old", "animatic": "old"},
        "artifacts": {"plan": {"id": "old"}},
        "revision": 3,
        "materialHistory": [
            {
                "status": "requires_alternative",
                "request": {"purpose": need.purpose},
                "result": {"criteria": [{"result": "unsupported", "evidence": "No headphones visible"}]},
            }
            for _ in range(3)
        ],
    }
    requirement = {"sceneId": source.scenes[0].id}
    assert _replan_after_material_rejections(
        state, NS(direction=source), requirement, need, {"attempt": 3}
    )
    assert state["stage"] == "composition"
    assert state["correctionRounds"] == 1
    assert state["revisionRequest"]["sceneIds"] == [source.scenes[0].id]
    assert "No headphones visible" in state["revisionRequest"]["instruction"]
    assert state["jobs"] == {"direction": "original"}
    assert not _replan_after_material_rejections(
        {**state, "correctionRounds": 2}, NS(direction=source), requirement, need, {"attempt": 3}
    )


def test_material_rejections_reformulate_search_before_scene_replan(monkeypatch):
    need = EditorialMaterialV2(
        id="need",
        target_id="hero",
        kind="video",
        query="A verbose description containing several aesthetic preferences",
        purpose="Show people consuming media",
        entity="people",
        action="using phones and laptops",
        acceptance_criteria=["People and devices remain visible"],
    )
    old = [
        {"provider": "pexels", "providerId": str(index)}
        for index in range(3)
    ]
    fresh = {"provider": "pexels", "providerId": "4"}
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover_for_need",
        lambda revised, **kwargs: {
            "status": "candidates",
            "query": revised.query,
            "candidates": [old[0], fresh],
        },
    )
    monkeypatch.setattr(
        "app.services.studios.material_ranking.rank_candidates",
        lambda requirement, *_args: requirement["discovery"]["candidates"],
    )
    state = {"materialWork": {}, "correctionRounds": 0}
    work = {"attempt": 3, "candidates": old}

    assert _retry_material_discovery(
        state, {"sceneId": "scene"}, need, work, "token"
    )
    revised = state["materialWork"]["token"]
    assert revised["attempt"] == 0
    assert revised["candidates"] == [fresh]
    assert revised["reformulatedQuery"] == "people. using phones and laptops"
    assert state["correctionRounds"] == 1
    assert state["materialSearchCorrections"][0]["providerSubmission"] is False


def test_inspection_budget_failure_is_not_reported_as_pending():
    assert _inspection_job_state(
        NS(status="failed", error_message="editing_gemini_test_budget_exceeded")
    ) == ("blocked", "production_material_inspection_budget_exceeded")
    assert _inspection_job_state(NS(status="running", error_message=None)) == (
        "running", "production_material_inspection_pending"
    )


def test_duration_only_rejection_is_recoverable_without_provider_call():
    from app.services.studios.production_materials import _duration_only_rejection

    need = EditorialMaterialV2(
        id="clip",
        target_id="title",
        kind="video",
        query="Rede conectando pessoas",
        purpose="Mostrar conexão",
        source_class="generated_original",
        duration_seconds=4,
    )
    receipt = {
        "status": "requires_alternative",
        "request": {"requiredSeconds": 5.9},
        "result": {"confidence": 0.97, "criteria": [{"result": "supported"}]},
    }
    asset = NS(
        object_metadata={"editingResource": {"technical": {"durationMicroseconds": 4_000_000}}}
    )

    assert _duration_only_rejection(receipt, need, asset)


def test_unknown_duration_is_reconciled_only_when_semantics_and_ffprobe_support_it():
    need = EditorialMaterialV2(
        id="clip",
        target_id="title",
        kind="video",
        query="people with varied attention",
        purpose="Show varied attention",
    )
    receipt = {
        "status": "requires_alternative",
        "request": {
            "requiredSeconds": 6,
            "criteria": ["People are visibly attentive and distracted", "Duração suficiente"],
        },
        "result": {
            "confidence": 0.85,
            "criteria": [
                {"index": 0, "result": "supported"},
                {"index": 1, "result": "unknown"},
            ],
        },
    }
    asset = NS(
        object_metadata={"editingResource": {"technical": {"durationMicroseconds": 6_000_000}}}
    )
    assert _technical_duration_reconciliation(receipt, need, asset)
    receipt["request"]["criteria"][1] = "Facial attention must be visible"
    assert not _technical_duration_reconciliation(receipt, need, asset)


def test_unconfigured_discovery_is_retried_when_pexels_becomes_available(monkeypatch):
    from pydantic import SecretStr

    from app.services.studios import production_materials as service

    source = direction(kind="image", text="")
    need = EditorialMaterialV2(
        id="need",
        target_id="title",
        kind="image",
        query="message reaching an audience",
        purpose="Show distribution",
        acceptance_criteria=["People and a delivered message are visible"],
    )
    source.scenes[0].material_needs = [need]
    plan = NS(
        id="plan",
        revision=1,
        direction=source,
        source_assets={},
        material_requests=[
            {"id": "need", "sceneId": "scene", "required": True, "status": "awaiting_choice"}
        ],
    )
    record = NS(id="doc", workspace_id="tenant", revision=1)
    token = digest(
        {"production": "run", "documentRevision": 1, "scene": "scene", "need": need.model_dump(mode="json")}
    )
    state = {
        "id": "run",
        "artifacts": {},
        "materialWork": {
            token: {
                "candidates": [],
                "attempt": 0,
                "resolutionVersion": service.MATERIAL_RESOLUTION_VERSION,
                "discovery": {
                    "status": "unconfigured",
                    "providerReceipts": [{"provider": "pexels", "configured": False}],
                },
            }
        },
    }
    calls = []
    monkeypatch.setattr(service, "get_settings", lambda: NS(pexels_api_key=SecretStr("x" * 56)))
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover_for_need",
        lambda *_args, **_kwargs: calls.append(True)
        or {"status": "candidates", "candidates": [], "providerReceipts": []},
    )
    monkeypatch.setattr("app.services.studios.material_ranking.rank_candidates", lambda *_args: [])
    monkeypatch.setattr("app.services.studios.editorial_production.save", lambda db, rec, user, value: value)

    result = advance_materials(NS(), record, state, plan, NS(id="user"))

    assert calls == [True]
    assert result["materialWork"][token]["discovery"]["status"] == "candidates"
    assert result["blockers"] == ["production_material_source_or_evidence_required"]


def test_invalid_provider_image_rejects_candidate_without_blocking_the_run(monkeypatch):
    from app.services.studios import production_materials as service

    source = direction(kind="image", text="")
    need = EditorialMaterialV2(
        id="need",
        target_id="title",
        kind="image",
        query="single light bulb",
        purpose="Show one idea",
    )
    source.scenes[0].material_needs = [need]
    plan = NS(
        id="plan",
        revision=1,
        direction=source,
        source_assets={},
        material_requests=[
            {"id": "need", "sceneId": "scene", "required": True, "status": "awaiting_choice"}
        ],
    )
    candidate = {"provider": "pexels", "providerId": "7", "kind": "image"}
    record = NS(id="doc", workspace_id="tenant", revision=1)
    monkeypatch.setattr(service, "get_settings", lambda: NS(pexels_api_key=None))
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover_for_need",
        lambda *_args, **_kwargs: {"status": "candidates", "candidates": [candidate]},
    )
    monkeypatch.setattr("app.services.studios.material_ranking.rank_candidates", lambda *_args: [candidate])
    monkeypatch.setattr(
        service,
        "acquire_candidate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("resource_image_unsupported")),
    )
    monkeypatch.setattr("app.services.studios.editorial_production.save", lambda db, rec, user, value: value)

    result = advance_materials(NS(), record, {"id": "run", "artifacts": {}}, plan, NS(id="user"))
    work = next(iter(result["materialWork"].values()))

    assert result["status"] == "pending"
    assert result["blockers"] == []
    assert work["attempt"] == 1
    assert work["candidateRejections"][-1]["reason"] == "resource_image_unsupported"


def test_unknown_inspection_submission_advances_without_resubmitting(monkeypatch):
    from app.services.studios import production_materials as service

    source = direction(kind="image", text="")
    need = EditorialMaterialV2(
        id="need",
        target_id="title",
        kind="image",
        query="single light bulb",
        purpose="Show one idea",
    )
    source.scenes[0].material_needs = [need]
    plan = NS(
        id="plan",
        revision=1,
        direction=source,
        material_requests=[
            {"id": "need", "sceneId": "scene", "required": True, "status": "awaiting_choice"}
        ],
    )
    record = NS(id="doc", workspace_id="tenant", revision=1)
    token = digest(
        {"production": "run", "documentRevision": 1, "scene": "scene", "need": need.model_dump(mode="json")}
    )
    candidate = {"provider": "pexels", "providerId": "7", "kind": "image"}
    job = NS(
        id="job",
        document_id="doc",
        workspace_id="tenant",
        status="failed",
        error_message="editing_submission_outcome_unknown_manual_reconciliation_required",
        result_payload={"testReservationUsd": 0.1},
    )
    db = NS(get=lambda model, _identity: job if model is StudioGenerationJob else None)
    state = {
        "id": "run",
        "artifacts": {},
        "materialWork": {
            token: {
                "attempt": 0,
                "candidates": [candidate, {**candidate, "providerId": "8"}],
                "jobId": "job",
                "assetId": "asset",
                "resolutionVersion": service.MATERIAL_RESOLUTION_VERSION,
            }
        },
    }
    monkeypatch.setattr(service, "get_settings", lambda: NS(pexels_api_key=None))
    monkeypatch.setattr("app.services.studios.editorial_production.save", lambda db, rec, user, value: value)

    result = advance_materials(db, record, state, plan, NS(id="user"))
    work = result["materialWork"][token]

    assert result["status"] == "pending"
    assert work["attempt"] == 1
    assert work["candidateRejections"][-1]["resubmitted"] is False
    assert result["materialHistory"][-1]["reservationUsd"] == 0.1


def test_catalog_candidate_is_inspected_before_application_and_unknown_is_not_resent(monkeypatch):
    from app.services.studios import production_materials as service

    source = direction(kind="image", text="", asset_id="asset")
    source.scenes[0].material_needs = [
        EditorialMaterialV2(
            id="need",
            target_id="title",
            kind="image",
            query="orange",
            purpose="Show orange",
            acceptance_criteria=["Orange is visible"],
        )
    ]
    plan = NS(
        id="plan",
        revision=1,
        direction=source,
        material_requests=[
            {
                "id": "need",
                "sceneId": "scene",
                "required": True,
                "status": "awaiting_choice",
                "candidates": [{"id": "asset"}],
            }
        ],
    )
    record = NS(id="doc", workspace_id="tenant", revision=1)
    asset = NS(id="asset", workspace_id="tenant", lifecycle_status="active", checksum_sha256="a" * 64)
    job = NS(id="job", document_id="doc", workspace_id="tenant", status="queued")
    db = NS(
        get=lambda model, identity: asset if model is LibraryAsset else job if model is StudioGenerationJob else None
    )
    calls = []
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover_for_need",
        lambda *_args, **_kwargs: {"status": "candidates", "candidates": [], "providerReceipts": []},
    )
    monkeypatch.setattr(
        "app.services.studios.material_ranking.rank_candidates",
        lambda *_args: [{"catalogAssetId": "asset", "provider": "catalog"}],
    )
    monkeypatch.setattr(service, "selected_adapter", lambda *args: ("gemini", None))
    monkeypatch.setattr(service, "create_editing_job", lambda *args, **kwargs: (calls.append(args[2]) or job, True))
    monkeypatch.setattr("app.services.studios.editorial_production.save", lambda db, rec, user, state: state)

    def dispatch(db, rec, user, state, job):
        state["dispatchedJobs"] = [job.id]
        return state

    monkeypatch.setattr("app.services.studios.editorial_production.dispatch", dispatch)
    state = {"id": "run", "artifacts": {}}
    advance_materials(db, record, state, plan, NS(id="user"))
    assert calls[0].material_inspection.asset_id == "asset"
    assert "plan" not in state["artifacts"]
    job.status = "failed"
    advance_materials(db, record, state, plan, NS(id="user"))
    assert state["status"] == "blocked"
    assert len(calls) == 1
    # Only a completed, checksum-bound verdict may replace the pending plan.
    asset.object_metadata = {}
    job.status = "succeeded"
    job.request_payload = {"documentRevision": 1}
    job.result_payload = {
        "materialInspection": {
            "status": "accepted",
            "assetId": "asset",
            "checksum": "a" * 64,
            "humanReview": "pending",
            "request": calls[0].material_inspection.model_dump(mode="json", by_alias=True),
        }
    }
    selected = []
    monkeypatch.setattr(
        service,
        "select_material",
        lambda *args: (selected.append(args[3]) or NS(model_dump=lambda **kwargs: {"id": "revised"})),
    )
    advance_materials(db, record, state, plan, NS(id="user"))
    assert selected[0].asset_id == "asset"
    assert state["artifacts"]["plan"]["id"] == "revised"
    assert asset.object_metadata["materialAcquisition"]["humanReview"] == "pending"


def test_autonomous_material_resolution_dispatches_local_diffusion_from_the_need(monkeypatch):
    from app.domain.studios.hybrid_video import HybridExecutionBindingV1
    from app.services.studios import production_materials as service

    source = direction(kind="video", text="")
    source.scenes[0].material_needs = [
        EditorialMaterialV2(
            id="local-clip",
            target_id="title",
            kind="video",
            query="envelope crossing a network",
            purpose="Show one message reaching a recipient",
            source_class="generated_original",
            visual_description="One blue envelope moves through a clean network to one person",
            entity="blue envelope",
            action="moves from sender to recipient",
            appearance="centered medium shot, simple dark background",
            duration_seconds=1,
            acceptance_criteria=["One envelope remains identifiable", "Motion has a clear destination"],
        )
    ]
    plan = NS(
        id="plan",
        revision=1,
        direction=source,
        material_requests=[
            {"id": "local-clip", "sceneId": "scene", "required": True, "status": "awaiting_choice"}
        ],
    )
    record = NS(id="doc", workspace_id="tenant", revision=1)
    job = NS(id="local-job", status="queued")
    captured = []
    monkeypatch.setattr(
        "app.services.studios.material_discovery.discover_for_need",
        lambda *_args, **_kwargs: {
            "status": "generation_candidate",
            "candidates": [
                {
                    "provider": "local-diffusion",
                    "providerId": "animatediff-lightning-sd15-a-v1",
                    "durationSeconds": 1,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.services.studios.material_ranking.rank_candidates",
        lambda requirement, *_args: requirement["discovery"]["candidates"],
    )
    binding = HybridExecutionBindingV1(
        profileId="animatediff-lightning-sd15-a-v1",
        providerId="local-diffusion",
        capability="generative_video",
        operation="text_to_video",
        environment="local",
        effectiveParameters={},
        estimatedApiCostUsd=0,
        bindingDigestSha256="a" * 64,
    )
    monkeypatch.setattr(
        service,
        "select_hybrid_profile",
        lambda *_args, **_kwargs: NS(
            execution_binding=binding,
            selected_profile_id=binding.profile_id,
            blockers=[],
        ),
    )
    monkeypatch.setattr(
        service,
        "create_scene_generation_job",
        lambda _db, _record, request, _user, key: (captured.append((request, key)) or job, True),
    )
    monkeypatch.setattr("app.services.studios.editorial_production.save", lambda db, rec, user, state: state)
    monkeypatch.setattr(
        "app.services.studios.editorial_production.dispatch",
        lambda db, rec, user, state, queued: {**state, "dispatchedJobs": [queued.id]},
    )
    state = {
        "id": "run-id",
        "artifacts": {},
        "request": {
            "direction": {
                "expectedDocumentRevision": 1,
                "intent": {"objective": "Explain distribution", "script": "An idea reaches people."},
            },
            "generatedVideo": {
                "mode": "local_experimental",
                "allowedProfileIds": ["animatediff-lightning-sd15-a-v1"],
                "allowExperimental": True,
                "maxCandidates": 1,
                "maximumGeneratedSeconds": 1,
            },
        },
    }

    result = advance_materials(NS(), record, state, plan, NS(id="user"))

    request, key = captured[0]
    assert request.scene_id == "scene"
    assert request.requirement_id == "local-clip"
    assert request.profile_id == "animatediff-lightning-sd15-a-v1"
    assert request.execution_binding.binding_digest_sha256 == "a" * 64
    assert "blue envelope" in request.prompt
    assert "moves from sender to recipient" in request.prompt
    assert key.startswith("production:run-id:local-material:")
    assert result["dispatchedJobs"] == ["local-job"]
