"""Admission is local-only, scoped, bounded and replayable. Real ML acceptance is separate."""

from fastapi.testclient import TestClient
import pytest
from test_video_timeline_real import setup,create,command
from test_clicko_studio_bridge import headers

from app.domain.studios.material_effects import EffectRequest
from app.domain.studios.contracts import CreateGenerationJobRequest
from app.domain.studios.execution import execution_profile
from app.providers.studios import material_effects as provider
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.studio_app import app


def request(**changes):
    return {"expectedRevision":1,"kitRevision":1,"requestKey":"effect-test-0001","sourceAssetId":"source",
            "operation":"segment_person","durationSeconds":2,**changes}


@pytest.mark.parametrize("changes",[
    {"operation":"cloud-generation"},{"operation":"replace_background","prompt":""},{"durationSeconds":10000},
    {"operation":"localized_edit","prompt":"studio","region":[.8,.1,.5,.5]},
    {"operation":"localized_edit","prompt":"studio","region":[0,0,float('nan'),1]},
    {"model":"arbitrary"},{"baseUrl":"https://provider.example"},
])
def test_effect_contract_rejects_remote_or_invalid_inputs(changes):
    with pytest.raises(ValueError):
        EffectRequest.model_validate(request(**changes))


def test_local_job_resource_profiles_are_explicit():
    assert execution_profile("material_effect","local.material-effects-v1").capability=="media_cpu"
    assert execution_profile("material_effect","local.material-generative-v1").capability=="vision_gpu"
    with pytest.raises(ValueError):
        CreateGenerationJobRequest(workspaceId="test",jobType="material_effect",provider="openrouter")


def test_effect_admission_and_replay_never_call_models(monkeypatch,tmp_path):
    auth=setup(monkeypatch,tmp_path)
    def forbidden(*args,**kwargs):
        raise AssertionError("Admission must not call a provider")
    monkeypatch.setattr(UniversalLLMPlanner,"plan",forbidden)
    monkeypatch.setattr(provider,"prepare",forbidden)
    monkeypatch.setattr(provider,"capability",lambda:{"segmentationAvailable":True,"generativeWeightsInstalled":True})
    source=tmp_path/"source.mp4"
    command(["-f","lavfi","-i","color=c=blue:s=320x320:r=24:d=2","-c:v","libx264",str(source)])
    with TestClient(app) as client:
        ws,doc=create(client,auth)
        url="/api/v1/studios/v1/materials/document/"+doc["documentId"]
        upload=client.post("/api/v1/studios/v1/craft/assets",params={"workspace_id":ws,"title":"source","filename":"source.mp4","media_type":"video/mp4"},
            headers={**auth,"Content-Type":"video/mp4"},content=source.read_bytes())
        assert upload.status_code==201,upload.text
        asset=upload.json()["id"]
        kit={"expectedRevision":0,"name":"Test","category":"service","goal":"explain","materials":[{"assetId":asset,"role":"presenter","label":"Source"}]}
        assert client.put(url+"/kits/kit",headers=auth,json=kit).status_code==200
        assert client.put(url+"/binding",headers=auth,json={"expectedRevision":0,"kitId":"kit","kitRevision":1}).status_code==200
        payload=request(sourceAssetId=asset)
        admitted=client.post(url+"/effects",headers=auth,json=payload)
        assert admitted.status_code==202,admitted.text
        assert admitted.json()["provider"]=="local.material-effects-v1"
        assert client.post(url+"/effects",headers=auth,json=payload).json()["id"]==admitted.json()["id"]
        assert client.post(url+"/effects",headers=auth,json={**payload,"durationSeconds":3}).status_code==409
        foreign=headers(module="create-video",client="foreign")
        assert client.post(url+"/effects",headers=foreign,json=payload).status_code==404
        assert client.post(url+"/effects",headers=auth,json={**payload,"requestKey":"effect-stale-01","kitRevision":99}).status_code==409


def test_dynamic_typography_prefers_the_moving_matte():
    from app.services.studios.ad_editing_recipes import compose
    kit={"category":"service","goal":"explain","materials":[{"assetId":"source","role":"presenter","alignmentGroup":"aligned"},
        {"assetId":"mask","role":"matte","alignmentGroup":"aligned"}]}
    timeline=compose("subject_occluded_typography",kit,"Título")
    assert timeline.tracks[-1].kind=="mask"
    assert timeline.tracks[-1].artifact_asset_id=="mask"
    assert timeline.tracks[-2].clips[0].asset_id=="source"


def test_worker_does_not_receive_api_credentials(monkeypatch,tmp_path):
    captured={}
    class Finished:
        returncode=0
        def poll(self):return 0
    def spawn(command,**kwargs):
        captured.update(kwargs)
        return Finished()
    monkeypatch.setenv("ANTHROPIC_API_KEY","test-value-never-forward")
    monkeypatch.setenv("OPENROUTER_API_KEY","test-value-never-forward")
    monkeypatch.setattr(provider.subprocess,"Popen",spawn)
    provider.run_worker("runtime/Scripts/python.exe","matte",{},tmp_path,lambda:False,10)
    assert "ANTHROPIC_API_KEY" not in captured["env"]
    assert "OPENROUTER_API_KEY" not in captured["env"]
    assert captured["stdin"]==provider.subprocess.DEVNULL
