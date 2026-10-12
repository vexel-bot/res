"""Canonical commands are atomic, author-bound, replayable and render-linked."""
# ruff: noqa: F811

import copy

import pytest
from pydantic import ValidationError
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_native_motion_recipes import choreography, direction_with

from app.database import SessionLocal
from app.domain.studios.editor_commands import EditorCommandV1
from app.domain.studios.motion import MotionKeyframeV1, evaluate_motion_graph, project_motion_graph
from app.models import CreativeDocument
from app.providers.studios.remotion_projection import compile_remotion_composition
from app.services.studios import contextual_editing as plans
from app.services.studios.compatibility import persist_contract, record_to_contract
from app.services.studios.editor_commands import evaluated_value


@pytest.fixture
def applied(client, project, request):
    # Existing interview timeline is deliberately cleared for this original graphical composition.
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        doc = record_to_contract(record)
        doc.composition.media_timeline.tracks = []
        persist_contract(record, doc)
        db.commit()
    headers = {"Authorization": "Bearer " + project["token"], "Idempotency-Key": "editor-fixture-plan"}
    base = f"/api/v1/studios/v1/documents/{project['document']}"
    direction = direction_with([choreography()]).model_dump(mode="json", by_alias=True)
    if getattr(request, "param", None) in {"shape", "rig"}:
        direction["scenes"][0]["elements"] = [{"id": "hero", "kind": "shape", "purpose": "Pixel motion proof",
            "x": 80, "y": 80, "width": 80, "height": 80, "durationFrames": 15, "fill": "#ffffff"}]
    if getattr(request, "param", None) == "rig":
        scene = direction["scenes"][0]
        scene["elements"][0].update(parentId="g1", x=10, y=20, width=56, height=56, visualRole="hero")
        for group, parent, x, y, size in [("g0", None, 10, 20, 250), ("g1", "g0", 30, 40, 180),
                                         ("g2", "g1", 50, 60, 100)]:
            scene["elements"].append({"id": group, "kind": "group", "purpose": "Explicit local hierarchy",
                "parentId": parent, "x": x, "y": y, "width": size, "height": size, "durationFrames": 15})
        for rig, target, parent in [("rig-hero", "hero", "g1"), ("rig-group", "g1", "g0")]:
            scene["motionRecipes"].append({"id": rig, "technique": "layer_rig", "targetIds": [target],
                "startFrame": 0, "endFrameExclusive": 15, "intent": "Maintain an explicit local coordinate space",
                "continuityAnchor": "Same original shape", "verification": ["One parent transform only"],
                "parameters": {"parentTargetId": parent}})
    response = client.post(base + "/editing-plans", headers=headers, json=direction)
    assert response.status_code == 200, response.text
    plan = response.json()
    assert plan["status"] == "ready", plan["blockers"]
    response = client.post(base + f"/editing-plans/{plan['id']}/apply", headers=headers,
                           json={"expectedPlanRevision": plan["revision"]})
    assert response.status_code == 200, response.text
    snapshot = client.get(base + "/editor/inspection", headers=headers)
    assert snapshot.status_code == 200, snapshot.text
    return {**project, "base": base, "headers": headers, "inspection": snapshot.json()}


def command(applied, key="change-1", **extra):
    snapshot = applied["inspection"]
    return {"commandId": key, "documentId": applied["document"], "planId": snapshot["planId"],
            "expectedDocumentRevision": snapshot["document"]["revision"],
            "expectedPlanRevision": snapshot["planRevision"],
            "actions": [{"kind": "set_recipe_keyframe", "sceneId": "action", "recipeId": "entry",
                         "targetId": "hero", "property": "y",
                         "keyframe": {"frame": 0, "value": 80, "curve": [.22, .75, .25, 1]}}], **extra}


def test_atomic_recipe_graph_projection_replay_and_undo(client, applied):
    path, headers = applied["base"] + "/editor/commands", applied["headers"]
    before = applied["inspection"]
    body = command(applied)
    body["actions"].append({"kind": "set_recipe_pivot", "sceneId": "action", "recipeId": "entry", "pivot": [.25, .75]})
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 200, response.text
    receipt = response.json()
    assert receipt["documentRevision"] == before["document"]["revision"] + 1
    assert receipt["executableCompositionDigest"] != before["hashes"]["executableComposition"]
    assert receipt["pending"] == ["render_evidence_required", "human_visual_review_required"]
    after = client.get(applied["base"] + "/editor/inspection?frame=4", headers=headers).json()
    assert after["documentDigest"] == receipt["documentDigest"]
    assert after["document"]["actorId"] == receipt["actorId"]
    assert after["document"]["review"]["status"] == "draft"
    assert after["evaluation"]["human"] == "pending"
    recipe = after["recipes"][0]
    assert recipe["parameters"]["tracks"][0]["keyframes"][0]["value"] == 80
    assert recipe["parameters"]["pivot"] == [.25, .75]
    with SessionLocal() as db:
        record = db.get(CreativeDocument, applied["document"])
        doc = record_to_contract(record)
        plan = plans.require_render_plan(db, record, doc, receipt["planId"])
        graph = plan.motion_graph
        projection = project_motion_graph(graph, "remotion", evaluate_motion_graph(doc, graph))
        manifest = compile_remotion_composition(doc, projection, {})
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        track = next(t for t in manifest["tracks"] if t["targetLayerId"] == hero["id"])
        node = next(n for n in manifest["nodes"] if n["targetLayerId"] == hero["id"])
        assert track["keyframes"][0]["value"] == 80
        assert (node["transformOriginX"], node["transformOriginY"]) == (.25, .75)
        assert graph.document_revision == doc.revision
    assert client.post(path, headers=headers, json=body).json() == receipt
    changed = copy.deepcopy(body)
    changed["actions"][0]["keyframe"]["value"] = 81
    assert client.post(path, headers=headers, json=changed).status_code == 409
    undo = command(applied, "undo-1", expectedDocumentRevision=receipt["documentRevision"],
                   expectedPlanRevision=receipt["planRevision"],
                   actions=[{"kind": "undo_command", "commandId": body["commandId"]}])
    response = client.post(path, headers=headers, json=undo)
    assert response.status_code == 200, response.text
    assert response.json()["documentRevision"] == receipt["documentRevision"] + 1
    restored = client.get(applied["base"] + "/editor/inspection", headers=headers).json()
    assert restored["hashes"]["executableComposition"] == before["hashes"]["executableComposition"]
    assert restored["recipes"] == before["recipes"]
    assert client.post(path, headers=headers, json=body).json() == receipt  # Historical, never current-state replay.
    assert client.post(path, headers=headers, json=command(applied, "stale")).status_code == 409


def test_failed_batch_preserves_document_plan_and_history(client, applied):
    body = command(applied)
    body["actions"].append({"kind": "set_recipe_pivot", "sceneId": "action", "recipeId": "missing", "pivot": [0, 0]})
    response = client.post(applied["base"] + "/editor/commands", headers=applied["headers"], json=body)
    assert response.status_code == 422, response.text
    after = client.get(applied["base"] + "/editor/inspection", headers=applied["headers"]).json()
    assert after["document"] == applied["inspection"]["document"]
    assert after["planRevision"] == applied["inspection"]["planRevision"]
    assert after["history"] == []
    body["actions"] = body["actions"][:1]
    body["actions"][0]["keyframe"]["frame"] = 50
    assert client.post(applied["base"] + "/editor/commands", headers=applied["headers"], json=body).status_code == 422


def test_revision_identity_and_author_cannot_be_supplied(client, applied):
    path, headers = applied["base"] + "/editor/commands", applied["headers"]
    assert client.post(path, headers=headers, json=command(applied, expectedPlanRevision=999)).status_code == 409
    assert client.post(path, headers=headers, json=command(applied, documentId="different")).status_code == 409
    assert client.post(path, headers=headers, json=command(applied, actorId="director")).status_code == 422
    assert client.get(applied["base"] + "/editor/inspection?frame=15", headers=headers).status_code == 422
    assert client.get(applied["base"] + "/editor/inspection?frame=-1", headers=headers).status_code == 422
    assert client.get(applied["base"] + "/editor/inspection").status_code == 401


def test_concurrent_command_receipts_and_compare_and_swap(client, applied):
    from concurrent.futures import ThreadPoolExecutor

    path, headers = applied["base"] + "/editor/commands", applied["headers"]
    body = command(applied)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post(path, headers=headers, json=body), range(2)))
    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    assert responses[0].json() == responses[1].json()
    receipt = responses[0].json()
    one = command(applied, "concurrent-a", expectedDocumentRevision=receipt["documentRevision"],
                  expectedPlanRevision=receipt["planRevision"])
    two = copy.deepcopy(one)
    two["commandId"] = "concurrent-b"
    two["actions"][0]["keyframe"]["value"] = 85
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda b: client.post(path, headers=headers, json=b), [one, two]))
    assert sorted(r.status_code for r in responses) == [200, 409], [r.text for r in responses]
    after = client.get(applied["base"] + "/editor/inspection", headers=headers).json()
    assert after["document"]["revision"] == applied["inspection"]["document"]["revision"] + 2
    assert len(after["history"]) == 2


def test_other_workspace_cannot_inspect_or_replay(client, applied):
    from conftest import register

    outsider_token, _ = register(client, "editor-outsider@example.com")
    headers = {"Authorization": "Bearer " + outsider_token}
    path = applied["base"] + "/editor/commands"
    assert client.post(path, headers=applied["headers"], json=command(applied)).status_code == 200
    # The existing workspace boundary conceals resources from non-members with 404.
    assert client.post(path, headers=headers, json=command(applied)).status_code == 404
    assert client.get(applied["base"] + "/editor/inspection", headers=headers).status_code == 404


def test_replay_is_bound_to_authenticated_author(client, applied):
    from conftest import register
    from sqlalchemy import select

    from app.models import Membership, User

    token, _ = register(client, "editor-collaborator@example.com")
    with SessionLocal() as db:
        member = db.scalar(select(User).where(User.email == "editor-collaborator@example.com"))
        db.add(Membership(workspace_id=applied["workspace"], user_id=member.id, role="owner"))
        db.commit()
    path = applied["base"] + "/editor/commands"
    response = client.post(path, headers=applied["headers"], json=command(applied))
    assert response.status_code == 200
    replay = client.post(path, headers={"Authorization": "Bearer " + token}, json=command(applied))
    assert replay.status_code == 409 and "editor_idempotency_conflict" in replay.text


@pytest.mark.parametrize("applied", ["rig"], indirect=True)
def test_parent_command_preserves_local_coordinates_and_rejects_cycles(client, applied):
    path, headers = applied["base"] + "/editor/commands", applied["headers"]
    action = {"kind": "set_recipe_parent", "sceneId": "action", "recipeId": "rig-hero",
              "parentTargetId": "g2", "coordinateSpace": "local"}
    body = command(applied, actions=[action])
    response = client.post(path, headers=headers, json=body)
    assert response.status_code == 200, response.text
    after = client.get(applied["base"] + "/editor/inspection", headers=headers).json()
    layers = after["document"]["composition"]["pages"][0]["layers"]
    hero = next(layer for layer in layers if layer["name"] == "hero")
    group = next(layer for layer in layers if layer["name"] == "g2")
    assert (hero["x"], hero["y"]) == (10, 20)
    node = next(n for n in after["nodes"] if n["targetLayerId"] == hero["id"])
    parent = next(n for n in after["nodes"] if n["targetLayerId"] == group["id"])
    assert node["parentNodeId"] == parent["nodeId"]
    assert after["hashes"]["executableComposition"] != applied["inspection"]["hashes"]["executableComposition"]
    cycle = command(applied, "parent-cycle", expectedDocumentRevision=after["document"]["revision"],
                    expectedPlanRevision=after["planRevision"], actions=[{**action, "recipeId": "rig-group"}])
    response = client.post(path, headers=headers, json=cycle)
    assert response.status_code == 422, response.text
    assert "cycle" in response.text
    current = client.get(applied["base"] + "/editor/inspection", headers=headers).json()
    assert current["documentDigest"] == after["documentDigest"]
    invalid = copy.deepcopy(body)
    invalid["actions"][0].pop("coordinateSpace")
    assert client.post(path, headers=headers, json=invalid).status_code == 422
    pivot = command(applied, "unsupported-pivot", expectedDocumentRevision=after["document"]["revision"],
                    expectedPlanRevision=after["planRevision"], actions=[{"kind": "set_recipe_pivot",
                    "sceneId": "action", "recipeId": "rig-hero", "pivot": [0, 0]}])
    response = client.post(path, headers=headers, json=pivot)
    assert response.status_code == 422 and "editor_pivot_recipe_unsupported" in response.text


@pytest.mark.parametrize("easing,expected", [("linear", 25), ("ease_in", 6.25),
                                            ("ease_out", 43.75), ("ease_in_out", 12.5), ("hold", 0)])
def test_exact_frame_local_evaluation(easing, expected):
    keys = [MotionKeyframeV1(frame=10, value=0, easing=easing), MotionKeyframeV1(frame=30, value=100)]
    assert evaluated_value(keys, 15) == expected
    assert evaluated_value(keys, 30) == 100
    assert evaluated_value(keys, 0) == 0


def test_bezier_time_inverse_not_parameter_and_no_arbitrary_code():
    keys = [MotionKeyframeV1(frame=0, value=0, easing="cubic_bezier", cubic_bezier=[0, 0, 1, 1]),
            MotionKeyframeV1(frame=100, value=100)]
    assert evaluated_value(keys, 25) == pytest.approx(25, abs=.001)
    with pytest.raises(ValidationError):
        EditorCommandV1(command_id="bad", document_id="doc", plan_id="plan", expected_document_revision=1,
                        expected_plan_revision=1, actions=[{"kind": "execute_javascript", "source": "alert(1)"}])


@pytest.mark.parametrize("applied", ["shape", "rig"], indirect=True)
def test_command_api_job_real_mp4_and_stale_review(client, applied, monkeypatch):
    """Actual local renderer; only asynchronous dispatch is held so the test can run the job."""
    import hashlib
    import json
    import os
    import shutil
    import subprocess
    import time
    from pathlib import Path

    from app.models import LibraryAsset, StudioGenerationJob
    from app.providers.studios.heavy_media_lease import _active, _read, lease_path
    from app.providers.studios.remotion_render import (
        RemotionNativeContextualRenderProvider,
        RemotionNativeGraphicsProvider,
    )
    from app.providers.studios.video_render import VIDEO_RENDER_PROVIDERS
    from app.services.object_storage import get_object_storage
    from app.services.studios.jobs import execute_job_once

    monkeypatch.setitem(VIDEO_RENDER_PROVIDERS, "remotion.contextual-v2", RemotionNativeContextualRenderProvider(
        RemotionNativeGraphicsProvider("node", "ffmpeg", 180), VIDEO_RENDER_PROVIDERS["builtin.ffmpeg-contextual-v1"],
    ))
    monkeypatch.setattr("app.tasks.execute_studio_generation.delay", lambda *_: None)
    body = command(applied)
    is_rig = any(r["technique"] == "layer_rig" for r in applied["inspection"]["recipes"])
    if is_rig:
        body["actions"].append({"kind": "set_recipe_parent", "sceneId": "action", "recipeId": "rig-hero",
                                "parentTargetId": "g2", "coordinateSpace": "local"})
    response = client.post(applied["base"] + "/editor/commands", headers=applied["headers"], json=body)
    assert response.status_code == 200, response.text
    receipt = response.json()
    snapshot = client.get(applied["base"] + "/editor/inspection", headers=applied["headers"]).json()
    headers = {**applied["headers"], "Idempotency-Key": "editor-real-render"}
    response = client.post("/api/v1/studios/v1/video-renders", headers=headers, json={
        "workspaceId": applied["workspace"], "documentId": applied["document"],
        "expectedDocumentRevision": receipt["documentRevision"], "expectedDocumentVersion": 1,
        "contextualPlanId": receipt["planId"], "provider": "remotion.contextual-v2",
        "output": {"width": 320, "height": 320, "fps": 30},
    })
    assert response.status_code == 202, response.text
    # Admission is host-wide. Wait for independent local work, rather than removing its lease.
    wait_until = time.monotonic() + 120
    while _active(_read(lease_path())):
        if time.monotonic() >= wait_until:
            pytest.skip("local heavy-media capacity occupied by another active operation")
        time.sleep(1)
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["id"])
        execute_job_once(db, job)
        assert job.status == "succeeded", job.error_message
        result = job.result_payload
        assert result["documentRevision"] == receipt["documentRevision"]
        assert result["framesRendered"] == snapshot["durationFrames"]
        asset = db.get(LibraryAsset, result["artifact"]["assetId"])
        checks = asset.object_metadata["contextualEditing"]
        assert checks["planRevision"] == receipt["planRevision"]
        assert checks["manifest"]["hashes"]["executableComposition"] == receipt["executableCompositionDigest"]
        storage = get_object_storage(asset.storage_backend)
        with storage.materialize(asset.storage_key) as media_path:
            assert hashlib.sha256(media_path.read_bytes()).hexdigest() == result["artifact"]["checksumSha256"]
            pixels = subprocess.run(["ffmpeg", "-v", "error", "-i", str(media_path), "-f", "rawvideo",
                                     "-pix_fmt", "rgb24", "pipe:1"], capture_output=True, check=True, timeout=30,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            assert len(pixels) == 15 * 320 * 320 * 3

            def pixel(frame, x, y):
                offset = (frame * 320 * 320 + y * 320 + x) * 3
                return tuple(pixels[offset:offset + 3])

            # Group transforms add once. The rig's three authored translations yield (100, 140).
            base_x, base_y = (100, 140) if is_rig else (80, 80)
            sample_x = base_x + 20
            upper_y, lower_y = base_y + 20, base_y + 100
            assert min(pixel(0, sample_x, lower_y)) > 220
            assert max(pixel(0, sample_x, upper_y)) < 60
            assert min(pixel(14, sample_x, upper_y)) > 220
            assert max(pixel(14, sample_x, lower_y)) < 60
            movement = next(t for t in snapshot["tracks"] if t["property"] == "position_y"
                            and t["keyframes"][0]["value"] == 80)
            keys = [MotionKeyframeV1.model_validate(k) for k in movement["keyframes"]]
            middle_y = round(base_y + evaluated_value(keys, 4))
            assert min(pixel(4, sample_x, middle_y + 8)) > 220
            assert max(pixel(4, sample_x, middle_y - 8)) < 60
            observed_pixels = {"frames": [0, 4, 14], "middleExpectedTopY": middle_y,
                               "baseTranslation": [base_x, base_y], "parentTransformsAppliedOnce": is_rig,
                               "beginLower": pixel(0, sample_x, lower_y), "beginUpper": pixel(0, sample_x, upper_y),
                               "endLower": pixel(14, sample_x, lower_y), "endUpper": pixel(14, sample_x, upper_y),
                               "middleInside": pixel(4, sample_x, middle_y + 8),
                               "middleOutside": pixel(4, sample_x, middle_y - 8)}
            # Optional retained evidence belongs to this explicit validation run, never normal tests.
            if output_directory := os.environ.get("EDITOR_COMMAND_EVIDENCE_DIR"):
                target = Path(output_directory) / ("rig" if is_rig else "shape")
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(media_path, target / "edited.mp4")
                (target / "evidence.json").write_text(json.dumps({
                    "scope": "API-command-job-real-local-render", "humanReview": "pending",
                    "commandReceipt": receipt, "inspection": snapshot, "renderResult": result,
                    "renderMetadata": asset.object_metadata, "decodedPixelChecks": observed_pixels,
                }, ensure_ascii=False, indent=2), encoding="utf-8")
    next_body = command(applied, "after-render", expectedDocumentRevision=receipt["documentRevision"],
                        expectedPlanRevision=receipt["planRevision"])
    next_body["actions"][0]["keyframe"]["value"] = 82
    assert client.post(applied["base"] + "/editor/commands", headers=headers, json=next_body).status_code == 200
    # Invalid binding is rejected before these deliberately inert synthetic score fields can be recorded.
    response = client.post(applied["base"] + f"/renders/{result['artifact']['assetId']}/visual-review", headers=headers,
                           json={"expectedDocumentRevision": receipt["documentRevision"],
                                 "renderChecksum": result["artifact"]["checksumSha256"], "clarity": 4, "rhythm": 4,
                                 "suitability": 4, "continuity": 4, "finish": 4, "notes": "Must reject stale render"})
    assert response.status_code in {409, 422}, response.text
    assert "visual_review_binding_conflict" in response.text
