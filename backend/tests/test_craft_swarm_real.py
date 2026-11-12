"""Two native editors work on copies and the director alone publishes the edit."""
import json
import os
import threading
from types import SimpleNamespace

import pytest
from conftest import register

from app.database import SessionLocal
from app.domain.studios.craft import CraftAICommandRequestV1
from app.models import StudioGenerationJob, User
from app.routers.studios import owned_document
from app.services.studios import craft_agent, craft_ai, craft_swarm, llm_connections
from app.services.studios.craft_learning import project_feedback, promote_local_test, record_viewer_feedback, validated_lessons

pytestmark = pytest.mark.skipif(os.environ.get("CLICKO_TEST_REAL_CRAFT") != "1", reason="native engine")


@pytest.mark.parametrize("duration", [30, 45])
def test_parallel_motion_copies_preserve_origin_and_director_exports(client, monkeypatch, duration):
    token, workspace = register(client, f"swarm-{duration}@example.com")
    auth = {"Authorization": "Bearer " + token}
    base = "/api/v1/studios/v1"
    created = client.post(base + "/documents", headers=auth, json={
        "workspaceId": workspace, "title": "ÓRBITA swarm local", "contentType": "video",
        "brief": {"objective": "Motion with parallel specialists", "audience": "QA"},
        "composition": {"pages": [{"id": "main", "width": 320, "height": 320,
                                  "durationMs": duration * 1000, "layers": [], "background": "#0a1020"}],
                        "mediaTimeline": {"frameRate": {"numerator": 12, "denominator": 1},
                                          "durationFrames": duration * 12, "tracks": []}},
    })
    assert created.status_code == 201, created.text
    doc = created.json()
    native = client.post(base + f'/documents/{doc["documentId"]}/craft/migrate',
                         headers={**auth, "Idempotency-Key": f"swarm-migrate-{duration}"},
                         json={"engine": "effectcraft", "expectedRevision": doc["revision"]})
    assert native.status_code == 200, native.text
    connection = SimpleNamespace(id="offline-swarm", provider="anthropic", revision=1, config={
        "billingMode": "local_free", "protocol": "anthropic_messages", "enabled": True, "inputUsdPerMillion": 0,
        "outputUsdPerMillion": 0, "maxOutputTokens": 8000,
    })
    real_refresh = SessionLocal.class_.refresh
    monkeypatch.setattr(SessionLocal.class_, "refresh", lambda db, obj, *args, **kwargs:
                        real_refresh(db, obj, *args, **kwargs) if obj is not connection else None)
    barrier = threading.Barrier(2)
    specialist_stages = {}

    def specialist_turn(model, _system, messages, tools, _tokens, _seconds, **options):
        if model == craft_swarm.INDEX_MODEL:
            assert options["tool_choice_name"] == tools[0]["name"]
            name, value = "return_index", {"notes": "No external materials required."}
        else:
            assert "tool_choice_name" not in options
            scope = json.loads(messages[0]["content"])["assignment"]["scope"]
            stage = specialist_stages.get(scope, 0) + 1
            specialist_stages[scope] = stage
            if stage == 1:
                barrier.wait(timeout=30)
                name, value = "describe_commands", {"ids": ["script.run"]}
            elif stage == 2:
                name, value = "run_motion_script", {"code":
                    'var c=app.project.activeItem; var l=c.layers.addText("discarded");'
                    'var p=l.transform.opacity; p.setValueAtTime(0,0); p.setValueAtTime(0.5,100); p.setValue(50);'}
            elif stage == 3:
                assert messages[-1]["content"][0]["is_error"] is True
                name, value = "run_motion_script", {
                    "code": f'var c=app.project.activeItem; var l=c.layers.addText("{scope}");'
                            'l.property("ADBE Transform Group").property("ADBE Position").setValue([160,160,0]);'
                            'var p=l.transform.opacity; p.setValueAtTime(0,0); p.setValueAtTime(0.5,100);'
                            'p.setValueAtKey(2,90); p.setTemporalEaseAtKey(2,[new KeyframeEase(0,60)],[new KeyframeEase(0,60)]);',
                }
            else:
                name, value = "contribute_motion", {"summary": scope, "assetIds": [], "previewSeconds": [1]}
        return {"stop_reason": "tool_use", "usage": {},
                "content": [{"type": "tool_use", "id": name, "name": name, "input": value}]}

    original_init = craft_swarm.MotionSwarm.__init__

    def initialize(self, *args, **kwargs):
        original_init(self, *args, specialist_factory=lambda _model: SimpleNamespace(craft_turn=specialist_turn), **kwargs)
    monkeypatch.setattr(craft_swarm.MotionSwarm, "__init__", initialize)
    stage = 0

    def director(_model, _system, messages, tools, _tokens, _seconds):
        nonlocal stage
        stage += 1
        if stage == 1:
            name, args = "delegate_motion", {"tasks": [
                {"scope": "A", "assignment": "Add text A"}, {"scope": "B", "assignment": "Add text B"},
            ]}
        elif stage == 2:
            result = json.loads(messages[-1]["content"][0]["content"])
            assert len(result["contributions"]) == 2
            assert all(item["status"] == "previewed" for item in result["contributions"])
            name, args = "apply_contribution", {"id": result["contributions"][0]["id"]}
        elif stage == 3:
            name, args = "inspect_project", {}
        elif stage == 4:
            project = json.loads(messages[-1]["content"][0]["content"])
            assert any(item.get("name") == "A" for item in project["layers"])
            assert not any(item.get("name") == "B" for item in project["layers"])
            assert not any(item.get("name") == "discarded" for item in project["layers"])
            name, args = "inspect_project", {}
        elif stage == 5:
            reused = json.loads(messages[-1]["content"][0]["content"])
            assert reused["previousToolUseId"] == "director-3"
            name, args = ("review_clip", {"durationSeconds": 1}) if duration == 30 else (
                "preview_sequence", {"seconds": [0.5, duration - 0.5]})
        else:
            if duration == 30:
                blocks = messages[-1]["content"][0]["content"]
                assert any(block["type"] == "image" for block in blocks)
                assert "playableReview" in blocks[-1]["text"]
            name, args = "finish_project", {"rationale": "Previewed the isolated edits and final cut."}
        return {"stop_reason": "tool_use", "usage": {},
                "content": [{"type": "tool_use", "id": f"director-{stage}", "name": name, "input": args}]}

    monkeypatch.setattr(llm_connections, "planner", lambda *_: (
        connection, SimpleNamespace(craft_turn=director), "offline-director", "offline",
    ))
    with SessionLocal() as db:
        user = db.get(User, doc["actorId"])
        record = owned_document(db, user.id, doc["documentId"])
        request = CraftAICommandRequestV1(expectedRevision=native.json()["revision"],
                                         instruction="Make and export ÓRBITA", connectionId=connection.id)
        result = craft_ai.ai_commands(db, record, request, user, f"swarm-local-{duration}", motion_experiment=True)
        assert result["exportStatus"] == "succeeded"
        render = db.get(StudioGenerationJob, result["exportJobId"])
        assert render.result_payload["artifact"]["durationMs"] == pytest.approx(duration * 1000, abs=100)
        assert record.revision == native.json()["revision"] + 1
        replay = craft_ai.ai_commands(db, record, request, user, f"swarm-local-{duration}", motion_experiment=True)
        assert replay["receiptId"] == result["receiptId"]
        assert stage == 6
        assert specialist_stages == {"A": 4, "B": 4}
        parent = db.query(StudioGenerationJob).filter_by(idempotency_key=f"swarm-local-{duration}").one()
        receipts = parent.result_payload["tools"]
        if duration == 30:
            assert parent.result_payload["reviewArtifacts"][0]["jobId"] == parent.id
        assert receipts[1]["contributionId"] == receipts[0]["contributions"][0]["id"]
        assert receipts[-1] == {"name": "finish_project", "ok": True}
        lesson_id = parent.result_payload["learningKnowledgeId"]
        assert validated_lessons(db, workspace) == []
        with pytest.raises(ValueError, match="local_test_required"):
            promote_local_test(db, lesson_id, workspace, {"passed": True, "artifactChecksum": "wrong"})
        promote_local_test(db, lesson_id, workspace, {
            "passed": True, "artifactChecksum": render.result_payload["artifact"]["checksumSha256"],
            "testId": "parallel-branches-native-export", "observedResult": f"Isolated scopes, {duration}s export",
        })
        assert validated_lessons(db, workspace)[0]["state"] == "reproduced locally"
        replay = craft_ai.ai_commands(db, record, request, user, f"swarm-local-{duration}", motion_experiment=True)
        assert replay["receiptId"] == result["receiptId"]
        assert validated_lessons(db, workspace)[0]["state"] == "reproduced locally"
        record_viewer_feedback(db, parent, "The offer is unclear. Revise the story.")
        db.commit()
        assert validated_lessons(db, workspace) == []
        craft_ai.ai_commands(db, record, request, user, f"swarm-local-{duration}", motion_experiment=True)
        assert parent.result_payload["learningEvidence"]["viewerFeedback"]["comment"] == "The offer is unclear. Revise the story."
        assert parent.result_payload["learningEvidence"]["state"] == "revision requested"
        assert project_feedback(db, workspace, record.id)[0]["feedback"]["comment"] == "The offer is unclear. Revise the story."
        assert project_feedback(db, workspace, "another-project") == []
    if duration == 30:
        review = client.post(base + f'/documents/{doc["documentId"]}/craft/clip-review', headers=auth,
                             json={"expectedRevision": result["document"]["revision"], "durationSeconds": 1})
        assert review.status_code == 200, review.text
        artifact = review.json()
        assert artifact["report"]["visual"]["nativeRateRequested"]
        assert len(artifact["report"]["visual"]["sampledSeconds"]) == 12
        assert artifact["report"]["audio"]["status"] == "absent"
        playback = client.get(base + f'/documents/{doc["documentId"]}/craft/reviews/{artifact["assetId"]}', headers=auth)
        assert playback.status_code == 200 and playback.headers["content-type"].startswith("video/mp4")
        assert len(playback.content) > 100
        listed = client.get(base + f'/documents/{doc["documentId"]}/craft/reviews', headers=auth).json()
        assert listed["reviews"][0]["assetId"] == artifact["assetId"]
