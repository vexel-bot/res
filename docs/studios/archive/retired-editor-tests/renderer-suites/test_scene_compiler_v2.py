from datetime import UTC, datetime

import pytest

from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
from app.domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from app.domain.studios.motion import project_motion_graph
from app.providers.studios.hyperframes_projection import project_creative_document
from app.services.studios.scene_compiler import (
    compile_scenes,
    current_execution_versions,
    pin_current_execution_versions,
)


def document():
    now = datetime.now(UTC)
    return CreativeDocumentV1(
        document_id="doc",
        workspace_id="workspace",
        title="Distribution",
        content_type="video",
        correlation_id="test",
        brand_memory_ref={"id": "brand", "revision": 1},
        brief={"objective": "Explicar distribuição", "audience": "Creators"},
        composition={"pages": [{"id": "page", "width": 640, "height": 640}]},
        created_at=now,
        updated_at=now,
    )


def direction(**element):
    return ContextualPlanRequestV2(
        expected_document_revision=1,
        intent={"objective": "Explicar"},
        scenes=[
            {
                "id": "scene",
                "purpose": "Mostrar conexões",
                "durationFrames": 120,
                "verification": ["Conexões legíveis"],
                "elements": [
                    {
                        "id": "title",
                        "kind": "text",
                        "purpose": "Apresentar conceito",
                        "text": "Distribuição",
                        "width": 600,
                        "height": 100,
                        "durationFrames": 90,
                        **element,
                    }
                ],
            }
        ],
    )


def test_graphics_start_without_video_and_do_not_invent_human_review():
    source = document()
    draft, graph, operations, manifest = compile_scenes(source, direction(), "user", "plan")
    assert source.composition.media_timeline is None
    assert draft.composition.media_timeline.duration_frames == 120
    assert graph.status == "suggested" and graph.human_review_required
    assert manifest["humanReview"] == "pending"
    assert operations[0].target_id in {layer.id for layer in draft.composition.pages[0].layers}


def test_pinned_execution_version_is_preserved_and_unknown_runtime_is_rejected():
    request = direction()
    request.execution_versions = current_execution_versions()
    _, _, _, manifest = compile_scenes(document(), request, "user", "plan")

    assert manifest["componentLibraryVersion"] == request.execution_versions.components
    assert manifest["runtimeVersion"] == request.execution_versions.runtime

    request.execution_versions = request.execution_versions.model_copy(
        update={"runtime": "res.editorial-runtime.unavailable"}
    )
    with pytest.raises(ValueError, match="editing_v2_execution_version_unavailable"):
        compile_scenes(document(), request, "user", "plan")


def test_new_provider_output_cannot_select_an_older_execution_runtime():
    request = direction()
    request.execution_versions = current_execution_versions().model_copy(
        update={
            "compiler": "res.scene-compiler.v2.2",
            "components": "res.editorial-components.v2.2",
            "runtime": "res.editorial-runtime.v2.2",
        }
    )

    repairs = pin_current_execution_versions(request)

    assert request.execution_versions == current_execution_versions()
    assert repairs[0]["reason"] == "execution_versions_pinned_by_server"
    assert repairs[0]["requiresAlternative"] is False


def test_ordered_effect_stack_and_blend_mode_reach_shared_runtime():
    request = direction(
        effects=[
            {"id": "desaturate", "kind": "saturate", "amount": 0.4},
            {"id": "contrast", "kind": "contrast", "amount": 1.25},
            {
                "id": "contact-shadow",
                "kind": "drop_shadow",
                "amount": 8,
                "x": 0,
                "y": 5,
                "color": "#000000",
                "opacity": 0.3,
            },
        ],
        blendMode="screen",
    )
    draft, graph, _, _ = compile_scenes(document(), request, "user", "plan")
    projection = project_motion_graph(graph, "hyperframes")
    render_request = VideoRenderRequestV1.model_validate(
        {
            "workspaceId": draft.workspace_id,
            "documentId": draft.document_id,
            "documentRevision": draft.revision,
            "documentVersion": draft.version,
            "pageIds": [draft.composition.pages[0].id],
            "output": {"width": 640, "height": 640, "fps": 30, "audioCodec": "none"},
            "correlationId": "effect-stack-test",
        }
    )
    html, warnings = project_creative_document(
        draft,
        render_request,
        {},
        projection,
        automatic_draft=True,
    )

    assert warnings == ["motion:human-review-required-before-production-render"]
    assert "filter:saturate(0.4) contrast(1.25) drop-shadow(" in html
    assert "mix-blend-mode:screen" in html


def test_multiple_audio_roles_bind_independently():
    source, request = document(), direction()
    source.assets = []
    from app.domain.studios.contracts import AssetReferenceV1

    for role in ["narration", "music", "ambience", "effect"]:
        source.assets.append(
            AssetReferenceV1(id=role, media_type="audio/wav", checksum="a" * 64, rights_status="verified")
        )
        request.scenes[0].audio.append(
            __import__("app.domain.studios.contextual_editing_v2", fromlist=["EditorialAudioV2"]).EditorialAudioV2(
                id=role, role=role, purpose=role, asset_id=role, duration_frames=120
            )
        )
    draft, graph, _, manifest = compile_scenes(source, request, "user", "plan")
    assert len(draft.composition.media_timeline.tracks) == 4
    assert len(graph.audio_events) == 4
    assert not manifest["missingMaterials"]


def test_missing_media_stays_explicit_and_wrong_revision_fails():
    request = direction(kind="image", text="", asset_id="absent")
    _, _, _, manifest = compile_scenes(document(), request, "user", "plan")
    assert manifest["missingMaterials"][0]["assetId"] == "absent"
    request.expected_document_revision = 2
    with pytest.raises(ValueError, match="conflict"):
        compile_scenes(document(), request, "user", "plan")


def test_repeat_outside_scene_is_not_silently_clipped():
    with pytest.raises(ValueError, match="out_of_scene"):
        compile_scenes(document(), direction(repeat_count=3, stagger_frames=20), "user", "plan")


def test_draft_projection_is_separate_from_reviewed_render_and_escapes_text():
    draft, graph, _, _ = compile_scenes(document(), direction(text="<script>erro</script>"), "user", "plan")
    projection = project_motion_graph(graph, "hyperframes")
    request = VideoRenderRequestV1(
        workspace_id="workspace",
        document_id="doc",
        document_revision=1,
        document_version=1,
        page_ids=["page"],
        output={"width": 640, "height": 640},
        correlation_id="test",
    )
    with pytest.raises(ValueError, match="requires_review"):
        project_creative_document(draft, request, {}, projection)
    rendered, _ = project_creative_document(draft, request, {}, projection, automatic_draft=True)
    assert "&lt;script&gt;erro&lt;/script&gt;" in rendered
    assert "__resEditorialApply(t)" in rendered


def test_fact_text_cannot_be_invented():
    with pytest.raises(ValueError, match="text_source_required"):
        compile_scenes(document(), direction(text_role="fact"), "user", "plan")


def test_text_layout_expands_from_measured_estimate_and_stays_in_safe_area():
    request = direction(text="Distribuir é adaptar a mensagem e escolher os caminhos para encontrar o público.")
    element = request.scenes[0].elements[0]
    element.width = 280
    element.height = 24
    element.y = 590
    draft, _, _, _ = compile_scenes(document(), request, "user", "plan")
    layer = next(layer for layer in draft.composition.pages[0].layers if layer.name == "title")
    assert layer.properties["editorialTextFit"] is True
    assert layer.height > 24
    assert layer.y + layer.height <= 640 - 640 * 0.07 + 0.01


def test_text_layout_counts_explicit_line_breaks():
    request = direction(text="adaptar\nmensagem\ncaminhos")
    element = request.scenes[0].elements[0]
    element.width = 600
    element.height = 60
    element.font_size = 44
    draft, _, _, _ = compile_scenes(document(), request, "user", "plan")
    layer = next(layer for layer in draft.composition.pages[0].layers if layer.name == "title")

    assert layer.height >= 3 * 44 * 1.1


def test_short_visual_plan_is_retimed_with_all_nested_events():
    from app.domain.studios.production_timing import normalize_visual_duration

    request = direction()
    scene = request.scenes[0]
    scene.duration_frames = 120
    scene.elements[0].duration_frames = 120
    scene.elements[0].reveal_frames = 12
    original_cue = scene.elements[0].motion_cues
    revised, repairs = normalize_visual_duration(request, 8)

    assert revised.scenes[0].duration_frames == 240
    assert revised.scenes[0].elements[0].duration_frames == 240
    assert revised.scenes[0].elements[0].reveal_frames == 24
    assert revised.scenes[0].elements[0].motion_cues == original_cue
    assert repairs[0]["beforeFrames"] == 120
    assert repairs[0]["afterFrames"] == 240


def test_visual_only_plan_can_be_contracted_within_fifteen_percent():
    from app.domain.studios.contextual_editing_v2 import (
        EditorialObservationCueV2,
        EditorialVisualStateV2,
    )
    from app.domain.studios.production_timing import normalize_visual_duration

    request = direction()
    request.execution_scope = "visual_only"
    scene = request.scenes[0]
    scene.duration_frames = 210
    scene.elements[0].duration_frames = 210
    scene.visual_states = [
        EditorialVisualStateV2(
            id="ending",
            phase="consequence",
            frame=209,
            purpose="Verificar o encerramento",
            essential_element_ids=[scene.elements[0].id],
        )
    ]
    scene.observation_cues = [
        EditorialObservationCueV2(
            id="ending-window",
            start_frame=180,
            end_frame_exclusive=210,
            target_ids=[scene.elements[0].id],
            question="O encerramento está visível?",
        )
    ]

    revised, repairs = normalize_visual_duration(request, 6)

    assert revised.scenes[0].duration_frames == 180
    assert revised.scenes[0].elements[0].duration_frames == 180
    assert revised.scenes[0].visual_states[0].frame == 179
    assert revised.scenes[0].observation_cues[0].end_frame_exclusive == 180
    assert repairs[0]["reason"] == "visual_only_composition_bounded_to_requested_duration"


def test_audiovisual_or_large_overrun_requires_editorial_decision():
    from app.domain.studios.production_timing import normalize_visual_duration

    audiovisual = direction()
    audiovisual.scenes[0].duration_frames = 210
    audiovisual.scenes[0].elements[0].duration_frames = 210
    with pytest.raises(ValueError, match="composition_duration_exceeds_target"):
        normalize_visual_duration(audiovisual, 6)

    visual = direction()
    visual.execution_scope = "visual_only"
    visual.scenes[0].duration_frames = 240
    visual.scenes[0].elements[0].duration_frames = 240
    with pytest.raises(ValueError, match="composition_duration_exceeds_target"):
        normalize_visual_duration(visual, 6)


def test_visual_plan_repeating_project_duration_per_scene_is_normalized():
    from app.domain.studios.production_timing import normalize_visual_duration

    request = direction()
    request.execution_scope = "visual_only"
    source = request.scenes[0]
    source.duration_frames = 540
    source.elements[0].duration_frames = 540
    source.elements[0].text_spans = [
        {
            "id": "timed-word",
            "start": 0,
            "end": 4,
            "purpose": "Destacar palavra",
            "startFrame": 360,
            "durationFrames": 180,
        }
    ]
    request.scenes = [
        source.model_copy(deep=True, update={"id": f"scene-{index}"})
        for index in range(3)
    ]

    revised, repairs = normalize_visual_duration(request, 18)

    assert [scene.duration_frames for scene in revised.scenes] == [180, 180, 180]
    assert [scene.elements[0].duration_frames for scene in revised.scenes] == [180, 180, 180]
    assert revised.scenes[0].elements[0].text_spans[0].start_frame == 120
    assert revised.scenes[0].elements[0].text_spans[0].duration_frames == 60
    assert repairs[0]["reason"] == "per_scene_project_duration_normalized"


def test_declared_video_source_duration_survives_timeline_expansion():
    from app.domain.studios.contextual_editing_v2 import EditorialMaterialV2
    from app.domain.studios.production_timing import (
        bind_declared_material_durations,
        normalize_visual_duration,
    )

    request = direction(kind="video", text="")
    request.scenes[0].duration_frames = 120
    request.scenes[0].elements[0].duration_frames = 120
    request.scenes[0].material_needs = [
        EditorialMaterialV2(
            id="short-video",
            target_id=request.scenes[0].elements[0].id,
            kind="video",
            query="Fluxo original",
            purpose="Mostrar distribuição",
            source_class="generated_original",
            duration_seconds=4,
        )
    ]

    expanded, _ = normalize_visual_duration(request, 8)
    bound, repairs = bind_declared_material_durations(expanded)

    assert bound.scenes[0].duration_frames == 240
    assert bound.scenes[0].elements[0].duration_frames == 120
    assert repairs[0]["reason"] == "video_element_bound_to_declared_source_duration"


def test_repeat_operations_have_distinct_receipts():
    _, _, ops, _ = compile_scenes(
        document(), direction(repeat_count=3, durationFrames=60, stagger_frames=10), "user", "plan"
    )
    assert len({o.operation_id for o in ops}) == 3


def test_qualifier_cannot_disappear_even_with_support_text():
    request = direction(text="Distribuir garante alcance")
    request.intent.locked_facts = ["Distribuir não garante alcance"]
    with pytest.raises(ValueError, match="locked_fact_missing"):
        compile_scenes(document(), request, "user", "plan")


def test_transition_has_explicit_overlap_and_parent_space():
    request = direction()
    second = request.scenes[0].model_copy(deep=True, update={"id": "next", "entrance": "wipe"})
    request.scenes.append(second)
    draft, graph, _, manifest = compile_scenes(document(), request, "user", "plan")
    assert draft.composition.media_timeline.duration_frames == 228
    assert graph.transitions[0].start_frame == 108
    assert manifest["elements"][1]["startFrame"] == 108
    assert all(n.parent_node_id for n in graph.nodes if n.target_layer_id in {t.target_layer_id for t in graph.tracks})


def test_match_handoff_is_explicit_and_rejects_an_absent_previous_element():
    request = direction(durationFrames=120)
    second = request.scenes[0].model_copy(deep=True, update={"id": "next", "entrance": "dissolve"})
    second.elements[0].match_previous_element_id = "title"
    second.elements[0].x = 100
    request.scenes.append(second)
    draft, graph, _, _ = compile_scenes(document(), request, "user", "plan")
    matched = [p for p in draft.composition.pages[0].layers if p.properties.get("editorialMatch")]
    assert len(matched) == 1
    handoff = matched[0].properties["editorialMatch"]
    assert handoff["startFrame"] == 108
    assert handoff["endFrameExclusive"] == 120
    assert handoff["previousLayerId"] != matched[0].id
    assert handoff["previousLayerId"] in {n.target_layer_id for n in graph.nodes}
    second.elements[0].rotation = 10
    second.elements[0].width /= 2
    with pytest.raises(ValueError, match="match_transform_incompatible"):
        compile_scenes(document(), request, "user", "plan")
    second.elements[0].rotation = 0
    second.elements[0].width *= 2
    request.scenes[0].elements[0].duration_frames = 60
    with pytest.raises(ValueError, match="match_transform_incompatible"):
        compile_scenes(document(), request, "user", "plan")


def test_silence_cannot_hide_preserved_footage_audio():
    from app.domain.studios.contextual_editing_v2 import EditorialAudioV2
    from app.domain.studios.contracts import AssetReferenceV1

    source = document()
    source.assets = [
        AssetReferenceV1(id="footage", media_type="video/mp4", checksum="a" * 64, rights_status="verified")
    ]
    request = direction(kind="video", asset_id="footage", text="")
    request.scenes[0].audio = [EditorialAudioV2(id="pause", role="silence", purpose="Pausa", duration_frames=30)]
    with pytest.raises(ValueError, match="silence_overlaps_audio"):
        compile_scenes(source, request, "user", "plan")


def test_sound_event_uses_attack_sync_while_clip_starts_earlier():
    from app.domain.studios.contextual_editing_v2 import EditorialAudioV2
    from app.domain.studios.contracts import AssetReferenceV1

    source = document()
    source.assets = [AssetReferenceV1(id="effect", media_type="audio/wav", checksum="a" * 64, rights_status="verified")]
    request = direction(startFrame=20)
    request.scenes[0].audio = [
        EditorialAudioV2(
            id="accent",
            role="effect",
            purpose="Pontuar entrada",
            asset_id="effect",
            duration_frames=30,
            sync_element_id="title",
            attack_offset_frames=5,
        )
    ]
    draft, graph, _, _ = compile_scenes(source, request, "user", "plan")
    assert draft.composition.media_timeline.tracks[0].clips[0].timeline.start_frame == 15
    assert graph.audio_events[0].frame == 20


def test_semantic_motion_compiles_camera_overshoot_depth_and_keyword():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.domain.studios.visual_audit import preflight_visual
    from app.services.studios.scene_compiler import prepare_direction

    request = direction(
        visualRole="hero",
        depthTreatment={"opacity": 1, "blurPx": 0, "parallax": 0.2},
        motionCues=[
            {
                "kind": "emphasis",
                "profile": "emphasis",
                "startFrame": 0,
                "durationFrames": 18,
                "rationale": "Estabelecer o foco",
            }
        ],
    )
    raw = request.model_dump(mode="json", by_alias=True)
    raw["intent"]["script"] = "Distribuição conecta IDEIA e pessoas."
    raw["scenes"][0]["narration"] = raw["intent"]["script"]
    raw["scenes"][0]["cameraCues"] = [
        {
            "mode": "push_in",
            "targetId": "title",
            "startFrame": 0,
            "durationFrames": 60,
            "intensity": 0.08,
            "rationale": "Aproximar o foco principal",
        }
    ]
    raw["scenes"][0]["keywordCues"] = [
        {
            "id": "idea",
            "text": "IDEIA",
            "sourceExcerpt": "IDEIA",
            "purpose": "Marcar o conceito",
            "startFrame": 30,
            "durationFrames": 45,
            "profile": "emphasis",
        }
    ]
    request = ContextualPlanRequestV2.model_validate(raw)

    draft, graph, _, _ = compile_scenes(document(), request, "user", "plan")
    scale = next(track for track in graph.tracks if track.track_id.endswith("-cue-scale_x"))
    camera = [track for track in graph.tracks if "-camera-" in track.track_id]
    audit = preflight_visual(prepare_direction(request, 640, 640), graph)

    assert [keyframe.value for keyframe in scale.keyframes] == [0.92, 1.04, 1]
    assert all(track.keyframes[0].easing == "cubic_bezier" for track in camera)
    assert audit["motion"]["overshootTrackIds"]
    assert audit["motion"]["keywordCueCount"] == 1
    keyword = next(layer for layer in draft.composition.pages[0].layers if layer.properties.get("text") == "IDEIA")
    assert keyword.properties["editorialVisualRole"] == "text"


def test_keyword_inside_existing_copy_becomes_a_typed_span_without_duplicate_layer():
    raw = direction(text="Distribuição conecta IDEIA e pessoas.").model_dump(mode="json", by_alias=True)
    raw["intent"]["script"] = "Distribuição conecta IDEIA e pessoas."
    raw["scenes"][0]["narration"] = raw["intent"]["script"]
    raw["scenes"][0]["keywordCues"] = [
        {
            "id": "idea",
            "text": "IDEIA",
            "sourceExcerpt": "IDEIA",
            "purpose": "Destacar o conceito sem repetir a frase",
            "startFrame": 10,
            "durationFrames": 40,
            "profile": "emphasis",
            "highlightColor": "#ff4d6d",
        }
    ]
    request = ContextualPlanRequestV2.model_validate(raw)

    draft, _, _, manifest = compile_scenes(document(), request, "user", "plan")
    text_layers = [layer for layer in draft.composition.pages[0].layers if layer.kind == "text"]

    assert [layer.name for layer in text_layers] == ["title"]
    assert text_layers[0].properties["editorialTextSpans"] == [
        {
            "id": "keyword-idea",
            "start": 21,
            "end": 26,
            "purpose": "Destacar o conceito sem repetir a frase",
            "color": "#ff4d6d",
            "fontWeight": 800,
            "scale": 1.06,
            "startFrame": 10,
            "durationFrames": 40,
            "profile": "emphasis",
        }
    ]
    assert manifest["compilerVersion"] == current_execution_versions().compiler
    assert manifest["runtimeVersion"] == current_execution_versions().runtime
    assert manifest["hashes"]["executableDirection"]
    assert manifest["hashes"]["executableComposition"]


def test_generated_keyword_uses_an_unoccupied_safe_band():
    from app.domain.studios.contextual_editing_v2 import ContextualPlanRequestV2
    from app.services.studios.scene_compiler import prepare_direction

    raw = direction(text="FORMATO", y=280, height=100, durationFrames=90).model_dump(
        mode="json", by_alias=True
    )
    raw["intent"]["script"] = "Adaptar a mensagem muda o formato."
    raw["scenes"][0]["narration"] = raw["intent"]["script"]
    raw["scenes"][0]["keywordCues"] = [
        {
            "id": "adaptar",
            "text": "adaptar a mensagem",
            "sourceExcerpt": "adaptar a mensagem",
            "purpose": "Destacar a ação",
            "startFrame": 10,
            "durationFrames": 30,
            "position": "center",
        }
    ]
    prepared = prepare_direction(ContextualPlanRequestV2.model_validate(raw), 640, 640)
    keyword = next(element for element in prepared.scenes[0].elements if element.id == "keyword-adaptar")
    authored = next(element for element in prepared.scenes[0].elements if element.id == "title")

    assert keyword.y + keyword.height <= authored.y or authored.y + authored.height <= keyword.y


def test_keyword_timing_is_bounded_to_the_matching_text_layer():
    raw = direction(text="IDEIA", durationFrames=20).model_dump(mode="json", by_alias=True)
    raw["intent"]["script"] = "A IDEIA precisa circular."
    raw["scenes"][0]["narration"] = raw["intent"]["script"]
    raw["scenes"][0]["keywordCues"] = [
        {
            "id": "idea",
            "text": "IDEIA",
            "sourceExcerpt": "A IDEIA precisa circular.",
            "purpose": "Destacar sem duplicar",
            "startFrame": 40,
            "durationFrames": 20,
        }
    ]
    request = ContextualPlanRequestV2.model_validate(raw)

    draft, _, _, _ = compile_scenes(document(), request, "user", "plan")
    text_layer = next(layer for layer in draft.composition.pages[0].layers if layer.name == "title")
    assert text_layer.properties["editorialTextSpans"][0]["startFrame"] == 0
    assert text_layer.properties["editorialTextSpans"][0]["durationFrames"] == 20


def test_explicit_text_span_takes_precedence_over_overlapping_keyword_cue():
    raw = direction(text="A IDEIA precisa circular.", durationFrames=50).model_dump(mode="json", by_alias=True)
    raw["intent"]["script"] = "A IDEIA precisa circular."
    raw["scenes"][0]["narration"] = raw["intent"]["script"]
    raw["scenes"][0]["elements"][0]["textSpans"] = [
        {"id": "explicit", "start": 2, "end": 7, "purpose": "Destaque explícito"}
    ]
    raw["scenes"][0]["keywordCues"] = [
        {
            "id": "idea",
            "text": "IDEIA",
            "sourceExcerpt": "A IDEIA precisa circular.",
            "purpose": "Mesmo destaque",
            "startFrame": 10,
            "durationFrames": 20,
        }
    ]
    request = ContextualPlanRequestV2.model_validate(raw)

    draft, _, _, _ = compile_scenes(document(), request, "user", "plan")
    text_layer = next(layer for layer in draft.composition.pages[0].layers if layer.name == "title")
    assert [span["id"] for span in text_layer.properties["editorialTextSpans"]] == ["explicit"]


def test_explicit_visual_states_drive_checkpoint_frames():
    from app.domain.studios.visual_audit import checkpoint_frames

    request = direction()
    request.scenes[0].visual_states = [
        {"id": "initial", "phase": "initial", "frame": 2, "purpose": "Estado inicial"},
        {"id": "action", "phase": "action", "frame": 20, "purpose": "Ação"},
        {"id": "result", "phase": "consequence", "frame": 70, "purpose": "Resultado"},
        {"id": "exit", "phase": "exit", "frame": 110, "purpose": "Saída"},
    ]
    request = ContextualPlanRequestV2.model_validate(request.model_dump(mode="json", by_alias=True))

    assert checkpoint_frames(request.scenes[0]) == {
        "start": 2,
        "demonstration": 20,
        "consequence": 70,
        "exit": 110,
    }


def test_motion_cue_and_explicit_track_cannot_control_same_property():
    request = direction(
        motionCues=[
            {
                "kind": "emphasis",
                "profile": "emphasis",
                "startFrame": 0,
                "durationFrames": 18,
                "rationale": "Estabelecer o foco",
            }
        ],
        animations=[
            {
                "property": "scale_x",
                "keyframes": [{"frame": 0, "value": 1}, {"frame": 17, "value": 1.1}],
            }
        ],
    )
    with pytest.raises(ValueError, match="motion_cue_property_conflict"):
        compile_scenes(document(), request, "user", "plan")
