# Reuse tenant/auth/storage setup; database execution must use an isolated working directory.
# ruff: noqa: F811
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_editing_resources import upload
from test_scene_compiler_v2 import direction

from app.services.studios.editing_repertoire import rank_repertoire, seed_techniques
from app.services.studios.scene_compiler import current_execution_versions


def headers(project, key="editorial-v2-integration"):
    return {"Authorization": f"Bearer {project['token']}", "Idempotency-Key": key}


def test_font_pack_import_preserves_licenses_and_deduplicates(client, project):
    import hashlib

    from app.database import SessionLocal
    from app.models import LibraryAsset

    url = f"/api/v1/studios/v1/editing/font-packs/editorial-v1/import?workspace_id={project['workspace']}"
    first = client.post(url, headers=headers(project))
    assert first.status_code == 200, first.text
    again = client.post(url, headers=headers(project))
    assert again.status_code == 200, again.text
    fonts = first.json()["fonts"]
    assert len(fonts) == 5
    assert [font["assetId"] for font in fonts] == [font["assetId"] for font in again.json()["fonts"]]
    with SessionLocal() as db:
        for font in fonts:
            asset = db.get(LibraryAsset, font["assetId"])
            license = asset.object_metadata["fontLicense"]
            assert hashlib.sha256(license["text"].encode("utf-8")).hexdigest() == font["licenseSha256"]


def create(client, project, request=None, key="editorial-v2-integration"):
    result = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans",
        headers=headers(project, key),
        json=(request or direction(width=280)).model_dump(mode="json", by_alias=True),
    )
    assert result.status_code == 200, result.text
    return result.json()


def test_v2_persistence_idempotency_apply_and_local_revision(client, project):
    request = direction(text="Uma ideia precisa de distribuição", concise_text="Uma ideia", width=280, font_size=20)
    extra = request.scenes[0].model_copy(deep=True, update={"id": "conclusion"})
    request.scenes.append(extra)
    plan = create(client, project, request)
    assert plan["schemaVersion"] == "studio.contextual-edit-plan.v2"
    assert plan["direction"]["executionVersions"] == current_execution_versions().model_dump(
        by_alias=True, mode="json"
    )
    assert plan["status"] == "ready", plan["blockers"]
    assert create(client, project, request)["id"] == plan["id"]
    url = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}"
    applied = client.post(url + "/apply", headers=headers(project), json={"expectedPlanRevision": 1})
    assert applied.status_code == 200, applied.text
    document = applied.json()
    assert document["review"]["status"] == "draft"
    assert document["composition"]["narrative"]["editorialV2"]["motionGraph"]["documentRevision"] == 2
    feedback = client.post(
        url + "/feedback",
        headers=headers(project),
        json={"expectedPlanRevision": 2, "feedback": "menos texto", "beatIds": ["scene"]},
    )
    assert feedback.status_code == 200, feedback.text
    revised = feedback.json()
    assert revised["direction"]["scenes"][0]["elements"][0]["text"] == "Uma ideia"
    assert revised["direction"]["scenes"][1] == plan["direction"]["scenes"][1]
    assert revised["motionGraph"]["status"] == "suggested"
    assert revised["evaluation"]["human"] == "pending"
    stale = client.post(url + "/apply", headers=headers(project), json={"expectedPlanRevision": 1})
    assert stale.status_code == 409


def test_recompile_creates_a_versioned_derivative_without_new_direction(client, project):
    plan = create(client, project, direction(width=280), key="recompile-source-plan")
    url = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}/recompile"
    body = {
        "expectedDocumentRevision": 1,
        "expectedPlanRevision": plan["revision"],
    }
    response = client.post(url, headers=headers(project, "recompile-derivative"), json=body)
    assert response.status_code == 200, response.text
    derivative = response.json()
    assert derivative["id"] != plan["id"]
    assert derivative["direction"]["scenes"] == plan["direction"]["scenes"]
    assert derivative["manifest"]["recompilation"] == {
        "kind": "compiler_only",
        "sourcePlanId": plan["id"],
        "sourcePlanRevision": plan["revision"],
        "sourceCompilerVersion": current_execution_versions().compiler,
        "editorialDirectionChanged": False,
    }
    assert derivative["manifest"]["hashes"]["executableDirection"]
    replay = client.post(url, headers=headers(project, "recompile-derivative"), json=body)
    assert replay.status_code == 200
    assert replay.json()["id"] == derivative["id"]


def test_scene_generation_job_is_bound_to_a_real_video_requirement(client, project, monkeypatch):
    from app.domain.studios.contextual_editing_v2 import EditorialMaterialV2
    from app.services.studios import scene_generation as service

    monkeypatch.setattr(
        service,
        "preflight",
        lambda: {
            "status": "blocked_resources",
            "reasons": ["insufficient_vram"],
            "modelDownloadStarted": False,
        },
    )

    request = direction(kind="video", text="", width=280)
    request.scenes[0].material_needs = [
        EditorialMaterialV2(
            id="generated-background",
            target_id="title",
            kind="video",
            query="Fluxo de distribuição original",
            purpose="Criar um fundo original curto",
            acceptance_criteria=["Movimento legível e sem texto gerado"],
        )
    ]
    create(client, project, request, key="scene-generation-plan")
    capability = client.get(
        "/api/v1/studios/v1/scene-generation-capability",
        headers={"Authorization": f"Bearer {project['token']}"},
    )
    assert capability.status_code == 200
    assert capability.json()["state"] in {"unavailable", "experimental"}
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/scene-generation-jobs",
        headers=headers(project, "scene-generation-job"),
        json={
            "expectedDocumentRevision": 1,
            "sceneId": "scene",
            "requirementId": "generated-background",
            "operation": "text_to_video",
            "prompt": "Fluxos luminosos conectam uma ideia a diferentes públicos, sem texto",
            "seed": 42,
            "durationSeconds": 2,
            "profileId": "wan21-t2v-local-experimental-v1",
            "cameraIntent": {"type": "static", "control": "prompt_guidance"},
        },
    )
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["jobType"] == "scene_generation"
    assert job["provider"] == "local.wan21-diffusers"
    assert "executionId" in job["request"]
    assert all("path" not in key.casefold() for key in job["request"])
    from app.database import SessionLocal
    from app.models import StudioGenerationJob
    from app.services.studios.jobs import execute_job_once

    with SessionLocal() as db:
        stored = db.get(StudioGenerationJob, job["id"])
        if stored.status == "failed" and stored.error_code == "queue_unavailable":
            stored.status = "queued"
            stored.error_code = None
            stored.error_message = None
            db.commit()
        assert execute_job_once(db, stored) == "failed"
        db.refresh(stored)
        assert stored.result_payload["status"] == "blocked_resources"
        assert stored.error_code == "scene_generation_blocked_resources"
        assert stored.result_payload["modelDownloadStarted"] is False
        assert stored.result_payload["incorporated"] is False


def test_v2_scene_candidate_requires_human_admission_before_catalogue(client, project, tmp_path):
    from app.domain.studios.contextual_editing_v2 import EditorialMaterialV2

    request = direction(kind="video", text="", width=280)
    request.scenes[0].material_needs = [
        EditorialMaterialV2(
            id="generated-background-v2",
            target_id="title",
            kind="video",
            query="Fluxo de distribuição original",
            purpose="Criar um fundo original curto",
            acceptance_criteria=["Movimento legível e sem texto gerado"],
        )
    ]
    create(client, project, request, key="scene-generation-plan-v2")
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/scene-generation-jobs",
        headers=headers(project, "scene-generation-v2-job"),
        json={
            "schemaVersion": "studio.scene-generation-request.v2",
            "expectedDocumentRevision": 1,
            "sceneId": "scene",
            "requirementId": "generated-background-v2",
            "operation": "text_to_video",
            "prompt": "Conteúdo visual atravessa canais conectados, sem texto ou logotipos",
            "seed": 7,
            "durationSeconds": 1,
            "profileId": "animatediff-lightning-sd15-a-v1",
            "cameraIntent": {"type": "static", "control": "prompt_guidance"},
        },
    )
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["provider"] == "local.animatediff-lightning-sd15-a-v1"

    from app.database import SessionLocal
    from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
    from app.services.object_storage import get_object_storage, object_key

    source = tmp_path / "candidate.mp4"
    source.write_bytes(b"synthetic-video-candidate")
    storage = get_object_storage()
    stored = storage.put_file(
        source,
        key=object_key(project["workspace"], "temporary", ".mp4"),
        media_type="video/mp4",
    )
    with SessionLocal() as db:
        record = db.get(StudioGenerationJob, job["id"])
        record.status = "succeeded"
        record.result_payload = {
            "status": "candidate_generated",
            "candidate": {
                "storageKey": stored.key,
                "storageBackend": stored.backend,
                "mediaType": stored.media_type,
                "sizeBytes": stored.size_bytes,
                "checksumSha256": stored.checksum_sha256,
            },
            "incorporated": False,
            "admission": "pending_visual_review",
        }
        db.commit()

    preview = client.get(
        f"/api/v1/studios/v1/scene-generation-jobs/{job['id']}/candidate",
        headers={"Authorization": f"Bearer {project['token']}"},
    )
    assert preview.status_code == 200
    assert preview.content == b"synthetic-video-candidate"
    assert preview.headers["cache-control"] == "private, no-store"

    admission = client.post(
        f"/api/v1/studios/v1/scene-generation-jobs/{job['id']}/admission",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={
            "expectedDocumentRevision": 1,
            "decision": "accept",
            "comment": "Movimento e pertinência aprovados no tamanho de uso",
            "evaluation": {
                "relevance": 4,
                "subjectIdentity": 4,
                "temporalContinuity": 4,
                "actionClarity": 4,
                "sequenceInspected": True,
                "observation": "O clipe preserva o objeto e conclui uma ação legível.",
            },
        },
    )
    assert admission.status_code == 200, admission.text
    result = admission.json()["result"]
    assert result["admission"] == "accepted"
    assert result["incorporated"] is True
    with SessionLocal() as db:
        asset = db.get(LibraryAsset, result["assetId"])
        assert asset.object_metadata["syntheticContent"] is True
        assert asset.object_metadata["officialBrandAsset"] is False

    replay = client.post(
        f"/api/v1/studios/v1/scene-generation-jobs/{job['id']}/admission",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={
            "expectedDocumentRevision": 1,
            "decision": "accept",
            "evaluation": {
                "relevance": 4,
                "subjectIdentity": 4,
                "temporalContinuity": 4,
                "actionClarity": 4,
                "sequenceInspected": True,
                "observation": "O mesmo recibo permanece vinculado ao candidato.",
            },
        },
    )
    assert replay.status_code == 200
    assert replay.json()["result"]["assetId"] == result["assetId"]

    with SessionLocal() as db:
        document = db.get(CreativeDocument, project["document"])
        document.revision = 2
        db.commit()
    stale = client.post(
        f"/api/v1/studios/v1/scene-generation-jobs/{job['id']}/admission",
        headers={"Authorization": f"Bearer {project['token']}"},
        json={
            "expectedDocumentRevision": 2,
            "decision": "accept",
            "evaluation": {
                "relevance": 4,
                "subjectIdentity": 4,
                "temporalContinuity": 4,
                "actionClarity": 4,
                "sequenceInspected": True,
                "observation": "Uma revisão nova não pode herdar o candidato antigo.",
            },
        },
    )
    assert stale.status_code == 409


def test_missing_material_and_acquisition_from_catalog(client, project):
    from app.domain.studios.contextual_editing_v2 import EditorialMaterialV2

    request = direction(kind="image", text="", width=280)
    request.scenes[0].material_needs = [
        EditorialMaterialV2(
            id="brand",
            target_id="title",
            kind="logo",
            query="Marca arbitrária",
            purpose="Identificar a marca",
            acceptance_criteria=["Arquivo próprio verificado"],
        )
    ]
    plan = create(client, project, request)
    assert plan["status"] == "awaiting_choice"
    url = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}"
    assert client.post(url + "/apply", headers=headers(project), json={"expectedPlanRevision": 1}).status_code == 409
    resource = upload(client, project)
    assert resource.status_code == 200, resource.text
    selected = client.post(
        url + "/materials",
        headers=headers(project, "editorial-v2-material-choice"),
        json={"expectedPlanRevision": 1, "needId": "brand", "assetId": resource.json()["id"]},
    )
    assert selected.status_code == 200, selected.text
    resolved = selected.json()
    assert resolved["status"] == "ready", resolved["blockers"]
    assert resolved["materialRequests"][0]["status"] == "resolved"
    assert resource.json()["id"] in {a["id"] for a in resolved["draftDocument"]["assets"]}


def test_relevance_after_hundredth_card_and_capability_filter():
    base = seed_techniques()[0]
    irrelevant = [
        base.model_copy(
            update={"id": f"filler-{i}", "title": "Genérico", "purpose": "Genérico", "required_capabilities": []}
        )
        for i in range(110)
    ]
    relevant = base.model_copy(
        update={"id": "relevant", "title": "Conectores distribuição caminhos", "required_capabilities": ["paths"]}
    )
    result = rank_repertoire([*irrelevant, relevant], "distribuição caminhos", ["paths"], limit=2)
    assert result[0].id == "relevant"
    assert "relevant" not in {t.id for t in rank_repertoire([*irrelevant, relevant], "distribuição", [], limit=2)}


def test_repertoire_preserves_requested_items_and_adds_relevant_craft_diversity():
    base = seed_techniques()[0]
    techniques = [
        base.model_copy(update={"id": "requested", "group": "composition", "required_capabilities": []}),
        base.model_copy(
            update={
                "id": "montage-match",
                "group": "montage",
                "title": "Distribuição narrativa",
                "required_capabilities": [],
            }
        ),
        base.model_copy(
            update={
                "id": "sound-match",
                "group": "sound",
                "title": "Distribuição por ritmo",
                "required_capabilities": [],
            }
        ),
    ]

    result = rank_repertoire(
        techniques,
        "distribuição",
        [],
        requested_ids=["requested"],
        limit=3,
    )

    assert result[0].id == "requested"
    assert {technique.group for technique in result} == {"montage", "composition", "sound"}


def test_actual_v2_job_keeps_draft_review_and_retries_idempotently(client, project, monkeypatch):
    import os

    import pytest

    from app import tasks
    from app.database import SessionLocal
    from app.models import LibraryAsset, StudioGenerationJob
    from app.providers.studios.contextual_motion_render import ContextualMotionRenderProvider
    from app.providers.studios.contextual_render import ContextualFFmpegProvider
    from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS, HyperFramesCliVideoRenderProvider
    from app.services.studios.jobs import execute_job_once

    cli = os.getenv("RES_HYPERFRAMES_CLI")
    if not cli:
        pytest.skip("Explicit pinned HyperFrames runtime required for actual rendering")
    monkeypatch.setitem(
        VIDEO_RENDER_PROVIDERS,
        "hyperframes.contextual-v2",
        ContextualMotionRenderProvider(
            HyperFramesCliVideoRenderProvider("node", cli, 180), ContextualFFmpegProvider("ffmpeg", 180)
        ),
    )
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda _: None)
    status = client.get("/api/v1/studios/v1/editing/ai", headers=headers(project))
    assert status.status_code == 200, status.text
    assert status.json()["contextualV2"]["configured"] is True
    from app.domain.studios.contextual_editing_v2 import EditorialElementV2

    candidate = direction(
        width=280,
        font_size=20,
        text="Distribuição",
        reveal="words",
        reveal_frames=25,
        font_weight=500,
        letter_spacing=1,
        shadow={"blur": 3},
        border_width=2,
    )
    candidate.scenes[0].elements.append(
        EditorialElementV2(
            id="connector",
            kind="path",
            purpose="Conectar as etapas",
            duration_frames=120,
            x=20,
            y=160,
            width=260,
            height=100,
            path_mode="quadratic",
            reveal="path",
            reveal_frames=30,
            points=[{"x": 0, "y": 80}, {"x": 130, "y": 0}, {"x": 260, "y": 80}],
        )
    )
    plan = create(client, project, candidate)
    url = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}"
    response = client.post(url + "/apply", headers=headers(project), json={"expectedPlanRevision": 1})
    assert response.status_code == 200, response.text
    request = {
        "workspaceId": project["workspace"],
        "documentId": project["document"],
        "expectedDocumentRevision": 2,
        "expectedDocumentVersion": 1,
        "contextualPlanId": plan["id"],
        "provider": "hyperframes.contextual-v2",
        "output": {"width": 320, "height": 320, "fps": 30},
    }
    first = client.post(
        "/api/v1/studios/v1/video-renders", headers=headers(project, "v2-render-worker-test"), json=request
    )
    assert first.status_code == 202, first.text
    replay = client.post(
        "/api/v1/studios/v1/video-renders", headers=headers(project, "v2-render-worker-test"), json=request
    )
    assert replay.json()["id"] == first.json()["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, first.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        asset = db.get(LibraryAsset, job.result_payload["artifact"]["assetId"])
        assert asset.object_metadata["contextualEditing"]["editorialReview"] == "pending"
        observations = asset.object_metadata["audiovisualObservations"]
        assert observations["status"] == "partial"
        assert observations["checksum"] == asset.checksum_sha256
        assert observations["sampleCount"] > 0
        assert observations["speechIntelligibility"] == "unknown"
        audit = asset.object_metadata["visualAudit"]
        assert audit["renderChecksum"] == asset.checksum_sha256
        assert audit["coverage"]["complete"] is True
        assert audit["human"] == "pending"
        assert audit["renderedEvidence"]
        assert asset.object_metadata["contextualEditing"]["rendererChecks"]["graphics"]["ready"] is True


def test_gemini_v2_empty_timeline_schema_boundary_and_evidence(client, project, monkeypatch):
    from test_editing_resources import enable

    from app.database import SessionLocal
    from app.models import CreativeDocument, StudioGenerationJob
    from app.providers.studios.gemini_editing import GeminiEditingProvider
    from app.services.studios.compatibility import persist_contract, record_to_contract
    from app.services.studios.jobs import execute_job_once

    enable(monkeypatch)
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline = None
        doc.assets = []
        persist_contract(record, doc)
        db.commit()
    seen = []

    def planning(self, model, context, media):
        seen.append(context)
        assert not media
        assert context["outputSchema"]["properties"]["schemaVersion"]["const"] == "studio.contextual-plan-request.v2"
        candidate = direction(width=280, font_size=20)
        candidate.scenes[0].narration = "Uma ideia precisa encontrar pessoas."
        return {"candidates": [{"content": {"parts": [{"text": candidate.model_dump_json(by_alias=True)}]}}]}

    monkeypatch.setattr(GeminiEditingProvider, "plan", planning)
    response = client.post(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-ai-jobs",
        headers=headers(project, "gemini-v2-empty-test"),
        json={
            "expectedDocumentRevision": 1,
            "operation": "plan",
            "planVersion": 2,
            "prompt": "Explicar distribuição",
            "direction": {
                "expectedDocumentRevision": 1,
                "intent": {"objective": "Explicar", "script": "Uma ideia precisa encontrar pessoas."},
            },
        },
    )
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        assert job.result_payload["plan"]["status"] == "awaiting_choice"
    latest = client.get(
        f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/latest", headers=headers(project)
    ).json()
    assert any(e["type"] == "ai_direction" for e in latest["editorialEvidence"])
    assert len(seen) == 1


def test_scene_change_sampling_observes_cut_and_reports_gaps(media, tmp_path):
    from test_contextual_editing import ffmpeg

    from app.providers.studios.contextual_render import ContextualFFmpegProvider
    from app.services.studios.editorial_perception import sample_offsets

    source = tmp_path / "two-scenes.mp4"
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=black:s=320x320:r=25:d=1",
        "-f",
        "lavfi",
        "-i",
        "color=white:s=320x320:r=25:d=1",
        "-filter_complex",
        "[0:v][1:v]concat=n=2:v=1:a=0",
        "-c:v",
        "libx264",
        source,
    )
    offsets, report = sample_offsets(ContextualFFmpegProvider("ffmpeg", 30), source, tmp_path, 0, 2, lambda: False)
    assert report["detectedChanges"] >= 1
    assert any(0.8 < t < 1 for t in offsets) and any(1 < t < 1.2 for t in offsets)
    assert report["notFullVideoAnalysis"] and report["unobservedGapsSeconds"]


def test_unknown_reference_cannot_be_cleared_by_local_feedback(client, project):
    request = direction(width=280)
    request.scenes[0].technique_ids = ["unimplemented-roto"]
    plan = create(client, project, request)
    url = f"/api/v1/studios/v1/documents/{project['document']}/editing-plans/{plan['id']}"
    revised = client.post(
        url + "/feedback",
        headers=headers(project),
        json={"expectedPlanRevision": 1, "feedback": "mais calmo", "beatIds": ["scene"]},
    )
    assert revised.status_code == 200, revised.text
    assert revised.json()["status"] == "awaiting_choice"
    assert any(b["code"] == "editing_reference_unavailable" for b in revised.json()["blockers"])


def test_registered_renderer_component_is_not_treated_as_missing_reference(client, project):
    request = direction(width=280)
    request.scenes[0].technique_ids = ["typography", "groups", "paths", "depth", "panels"]
    plan = create(client, project, request)
    assert not any(b["code"] == "editing_reference_unavailable" for b in plan["blockers"])


def test_research_operation_requires_bound_material_and_knowledge_card_stays_non_executable(client, project):
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import KnowledgeDocument

    request = direction(width=280)
    request.scenes[0].technique_ids = ["action_progression", "subject_occluded_typography"]
    plan = create(client, project, request, key="research-operations-blocked")
    assert plan["status"] == "awaiting_choice"
    codes = {blocker["code"] for blocker in plan["blockers"]}
    assert "editing_operation_prerequisite_missing" in codes
    assert "editing_operation_knowledge_only" in codes
    decision = next(item for item in plan["editorialEvidence"] if item["type"] == "operation_decision")
    assert decision["techniqueId"] == "action_progression"
    assert decision["status"] == "blocked"
    assert decision["alternative"]
    with SessionLocal() as db:
        records = db.scalars(select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == project["workspace"],
            KnowledgeDocument.source_type == "editing-technique",
        )).all()
        researched = [item for item in records if (item.document_metadata or {}).get("technique", {}).get("id")
                      in {"action_progression", "motif_continuity", "gesture_occlusion_reveal", "moving_variant_mask",
                          "subject_occluded_typography", "windowed_content_scroll", "interface_evidence_overlay",
                          "world_to_world_identity", "localized_generated_event", "layer_inventory_animation",
                          "continuous_panel_canvas", "cutout_object_stack"}]
        assert len(researched) == 12
    replay = create(client, project, request, key="research-operations-blocked")
    assert replay["id"] == plan["id"]
    with SessionLocal() as db:
        assert len([item for item in db.scalars(select(KnowledgeDocument).where(
            KnowledgeDocument.workspace_id == project["workspace"],
            KnowledgeDocument.source_type == "editing-technique",
        )).all() if (item.document_metadata or {}).get("technique", {}).get("id")
            in {record.document_metadata["technique"]["id"] for record in researched}]) == 12


def test_motif_continuity_is_executable_through_the_plan_api(client, project):
    from app.domain.studios.contextual_editing_v2 import EditorialOperationBindingV1

    request = direction(width=280)
    scene = request.scenes[0]
    scene.elements[0].duration_frames = 60
    scene.elements[0].content_identity = "shape-anchor"
    repeated = scene.elements[0].model_copy(deep=True, update={
        "id": "repeated", "start_frame": 60, "duration_frames": 60,
    })
    scene.elements.append(repeated)
    scene.technique_ids = ["motif_continuity"]
    scene.operation_bindings = [EditorialOperationBindingV1(
        technique_id="motif_continuity", target_ids=[scene.elements[0].id, repeated.id],
        anchor_id="shape-anchor", cut_motivation="Retomar a mesma forma em outro enquadramento",
        new_information="A forma passa a organizar a conclusão",
    )]
    plan = create(client, project, request, key="motif-continuity-api")
    assert plan["status"] == "ready", plan["blockers"]
    decision = next(item for item in plan["editorialEvidence"] if item["type"] == "operation_decision")
    assert decision["status"] == "eligible"
    binding = plan["draftDocument"]["composition"]["narrative"]["editorialV2"]["operationBindings"][0]
    assert binding["anchorId"] == "shape-anchor"


def test_trimming_existing_footage_requires_temporal_evidence(client, project):
    request = direction(
        kind="video", text="", asset_id=project["asset"], width=280, durationFrames=30, source_start_seconds=0.5
    )
    plan = create(client, project, request)
    assert plan["status"] == "awaiting_choice"
    assert any(b["code"] == "editing_v2_reviewed_transcript_required" for b in plan["blockers"])
