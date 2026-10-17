# ruff: noqa: F811
import json
import os

import pytest
from test_contextual_editing import ffmpeg
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_editing_resources import enable
from test_editorial_production import brief, endpoint, headers, storyboard
from test_scene_compiler_v2 import direction

from app.domain.studios.production_timing import bind_narration


def test_automatic_corrections_are_bounded_and_uncertainty_keeps_human_review():
    from app.domain.studios.editorial_production import ProductionCritiqueV1, automatic_corrections

    critique = ProductionCritiqueV1.model_validate(
        {
            "coverage": "full",
            "summary": "Texto cobre a imagem.",
            "findings": [
                {
                    "sceneId": "scene",
                    "startSeconds": 0,
                    "endSeconds": 1,
                    "severity": "correction",
                    "observation": "Texto sobreposto",
                    "evidence": "Título cobre o produto",
                    "correction": "Mover título para a área vazia",
                    "confidence": 0.9,
                    "uncertainty": "Legibilidade estimada",
                }
            ],
        }
    )
    assert len(automatic_corrections(critique, 0)) == 1
    assert automatic_corrections(critique, 2) == []
    critique.coverage = "partial"
    assert automatic_corrections(critique, 0) == []
    assert critique.human_review == "pending"


def test_local_revision_rejects_changes_outside_selected_scene():
    from app.domain.studios.production_timing import validate_local_revision

    original = direction()
    original.scenes.append(original.scenes[0].model_copy(deep=True, update={"id": "conclusion"}))
    candidate = original.model_copy(deep=True)
    candidate.scenes[0].elements[0].text = "Ideia"
    validate_local_revision(original, candidate, ["scene"])
    candidate.scenes[1].elements[0].text = "Mudança indevida"
    with pytest.raises(ValueError, match="unselected_scene"):
        validate_local_revision(original, candidate, ["scene"])


def test_local_revision_projects_unselected_scenes_from_original():
    from app.domain.studios.production_timing import (
        preserve_unselected_scenes,
        validate_local_revision,
    )

    original = direction()
    original.scenes.append(original.scenes[0].model_copy(deep=True, update={"id": "conclusion"}))
    candidate = original.model_copy(deep=True)
    candidate.scenes[0].elements[0].text = "Nova apresentação"
    candidate.scenes[1].elements[0].text = "Alteração indesejada"
    projected = preserve_unselected_scenes(original, candidate, ["scene"])
    assert projected.scenes[1] == original.scenes[1]
    validate_local_revision(original, projected, ["scene"])


def test_compact_local_revision_is_merged_by_selected_scene_identity():
    from app.domain.studios.production_timing import (
        merge_partial_local_revision,
        validate_local_revision,
    )

    original = direction()
    original.scenes.append(original.scenes[0].model_copy(deep=True, update={"id": "conclusion"}))
    proposal = original.model_copy(deep=True)
    proposal.scenes = [proposal.scenes[1]]
    proposal.scenes[0].elements[0].text = "Conclusão mais clara"

    merged, repairs = merge_partial_local_revision(original, proposal, ["conclusion"])

    assert [scene.id for scene in merged.scenes] == ["scene", "conclusion"]
    assert merged.scenes[0] == original.scenes[0]
    assert merged.scenes[1].elements[0].text == "Conclusão mais clara"
    assert repairs[0]["reason"] == "partial_local_revision_merged_with_bound_plan"
    validate_local_revision(original, merged, ["conclusion"])


def test_compact_local_revision_rejects_unrequested_scene():
    from app.domain.studios.production_timing import merge_partial_local_revision

    original = direction()
    proposal = original.model_copy(deep=True)
    proposal.scenes[0].id = "invented"
    with pytest.raises(ValueError, match="revision_scene_binding"):
        merge_partial_local_revision(original, proposal, ["scene"])


def test_local_material_replan_rebinds_only_selected_blueprint_requirements():
    from app.domain.studios.contextual_editing_v2 import EditorialMaterialV2
    from app.domain.studios.editorial_production import (
        EditorialDirectionV1,
        rebind_selected_blueprint_materials,
    )

    approved = storyboard()
    approved["beats"][0]["id"] = "scene"
    approved["beats"][0]["visualBlueprint"] = {
        "message": "A mensagem encontra públicos diferentes.",
        "evidence": "Pessoas recebem formatos distintos.",
        "representation": "mixed",
        "rejectedAlternatives": ["Ícones sem ação"],
        "primaryMaterialQuery": "três pessoas com dispositivos",
        "regionOfInterest": "pessoas e telas",
        "hierarchy": ["pessoas", "telas"],
        "completionCriteria": ["formatos distinguíveis"],
        "visualRegister": "editorial",
        "shotSequence": [
            {
                "id": "shot",
                "function": "demonstrate",
                "subject": "públicos",
                "observableAction": "Pessoas recebem formatos distintos.",
                "shotScale": "medium",
                "angle": "eye_level",
                "regionOfInterest": "pessoas e telas",
                "attentionStart": "telas",
                "attentionEnd": "pessoas",
                "lighting": {
                    "quality": "soft",
                    "direction": "front",
                    "contrast": "medium",
                    "temperatureRelationship": "neutral",
                    "subjectSeparation": "clear",
                    "executionMode": "select_existing_footage",
                },
                "cutMotivation": "demonstrar",
                "materialRequirementIds": ["old-video"],
                "verification": ["públicos visíveis"],
            }
        ],
        "demonstration": {
            "observableAction": "A mesma mensagem chega em formatos distintos.",
            "intendedUnderstanding": "Distribuição adapta a mensagem.",
            "proofElements": ["pessoas", "dispositivos"],
            "indispensableMaterials": [
                {
                    "id": "old-video",
                    "kind": "video",
                    "query": "três pessoas em um vídeo",
                    "purpose": "mostrar públicos",
                    "acceptanceCriteria": ["três pessoas visíveis"],
                    "sourceClass": "licensed_stock",
                }
            ],
            "genericFailureSignals": ["associação abstrata"],
        },
    }
    approved = EditorialDirectionV1.model_validate(approved)
    candidate = direction(kind="image", visualRole="hero")
    candidate.scenes[0].material_needs = [
        EditorialMaterialV2(
            id="new-collage",
            target_id="title",
            kind="image",
            query="colagem com públicos e dispositivos distintos",
            purpose="demonstrar públicos sem fingir uma única filmagem",
            required=False,
            source_class="licensed_stock",
            acceptance_criteria=["três segmentos visíveis"],
            blueprint_requirement_id="collage-route",
            requirement_class="mandatory",
        )
    ]
    candidate.scenes[0].shot_plan = [
        {
            "id": "shot",
            "function": "demonstrate",
            "subject": "públicos",
            "observableAction": "Pessoas recebem formatos distintos.",
            "shotScale": "medium",
            "angle": "eye_level",
            "regionOfInterest": "pessoas e telas",
            "attentionStart": "telas",
            "attentionEnd": "pessoas",
            "lighting": {
                "quality": "soft",
                "direction": "front",
                "contrast": "medium",
                "temperatureRelationship": "neutral",
                "subjectSeparation": "clear",
                "executionMode": "select_existing_footage",
            },
            "cutMotivation": "demonstrar",
            "materialRequirementIds": ["collage-route"],
            "executionComponentIds": ["focus"],
            "targetElementIds": ["title"],
            "verification": ["públicos visíveis"],
            "startFrame": 0,
            "endFrameExclusive": 120,
        }
    ]
    candidate.scenes[0].technique_ids = ["focus"]
    candidate = type(candidate).model_validate(candidate.model_dump(mode="json", by_alias=True))

    revised, repairs = rebind_selected_blueprint_materials(approved, candidate, ["scene"])

    materials = revised.beats[0].visual_blueprint.demonstration.indispensable_materials
    assert [item.id for item in materials] == ["collage-route"]
    assert materials[0].kind == "image"
    assert candidate.scenes[0].material_needs[0].required is True
    shot = revised.beats[0].visual_blueprint.shot_sequence[0]
    assert shot.material_requirement_ids == ["collage-route"]
    assert shot.execution_component_ids == ["focus"]
    assert approved.beats[0].visual_blueprint.demonstration.indispensable_materials[0].id == "old-video"
    assert repairs[0]["classification"] == "localized_direction_revision"


def test_local_revision_rejects_silent_downstream_timing_change():
    from app.domain.studios.production_timing import validate_local_revision

    original = direction()
    candidate = original.model_copy(deep=True)
    candidate.scenes[0].duration_frames += 10
    with pytest.raises(ValueError, match="temporal_dependency"):
        validate_local_revision(original, candidate, ["scene"])


def test_stock_voice_uses_existing_job_and_measures_generated_file(client, project, monkeypatch):
    from test_speech_synthesis_execution import FakeSpeechProvider, _admit_fake_provider

    from app.database import SessionLocal
    from app.domain.studios.editorial_production import ProductionRequestV1
    from app.domain.studios.providers import SPEECH_PROVIDERS
    from app.models import CreativeDocument, LibraryAsset, User
    from app.services.studios.contextual_editing import generated_asset_admitted
    from app.services.studios.jobs import execute_job_once
    from app.services.studios.production_narration import prepare_narration

    provider = FakeSpeechProvider()
    monkeypatch.setitem(SPEECH_PROVIDERS, provider.name, provider)
    request = ProductionRequestV1.model_validate({**brief(), "stockVoiceProvider": provider.name})
    state = {"id": "test-stock-production", "jobs": {}, "artifacts": {"direction": storyboard()}}
    with SessionLocal() as db:
        _admit_fake_provider(db, provider.name)
        db.commit()
        record = db.get(CreativeDocument, project["document"])
        user = db.get(User, record.created_by)
        measurements, job = prepare_narration(db, record, state, request, user)
        assert measurements is None and job.job_type == "stock_voice"
        _, same_job = prepare_narration(db, record, state, request, user)
        assert same_job.id == job.id
        assert execute_job_once(db, job) == "succeeded", job.error_message
        measurements, pending = prepare_narration(db, record, state, request, user)
        assert pending is None
        assert measurements[0]["durationSeconds"] == 0.1
        assert state["documentRevision"] == 2
        assert generated_asset_admitted(db, db.get(LibraryAsset, measurements[0]["assetId"]))


def test_measured_narration_blocks_short_scene_and_preserves_other_sounds():
    plan = direction()
    plan.scenes[0].narration = "Fala completa."
    with pytest.raises(ValueError, match="shorter_than_narration"):
        bind_narration(plan, {"scene": {"assetId": "voice", "durationSeconds": 10}})
    measured = bind_narration(plan, {"scene": {"assetId": "voice", "durationSeconds": 1.05}})
    assert measured.scenes[0].audio[0].duration_frames == 32
    assert measured.scenes[0].audio[0].source_start_seconds == 0
