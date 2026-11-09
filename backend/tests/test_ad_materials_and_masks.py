"""Real pixels, scoped materials, staleness and recipes. Paid models must never run."""

from copy import deepcopy
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from test_clicko_studio_bridge import headers
from test_video_timeline_real import setup, create, pixels, command

from app.domain.studios.contracts import CaptionCueV1, CreativeDocumentV1, MediaTimelineV1
from app.domain.studios.timeline_editor import MotionKey
from app.providers.studios import timeline_ffmpeg as ff
from app.providers.studios.universal_llm import UniversalLLMPlanner
from app.services.studios import ad_editing_recipes as recipes, timeline_editor
from app.studio_app import app


def upload(client, auth, workspace, image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    r = client.post("/api/v1/studios/v1/craft/assets", params={"workspace_id":workspace,"title":"fixture","filename":"fixture.png","media_type":"image/png"},
                    headers={**auth,"Content-Type":"image/png"},content=buffer.getvalue())
    assert r.status_code == 201, r.text
    return r.json()["id"]


def forbidden(*args, **kwargs):
    raise AssertionError("Materials and local composition must not invoke an LLM")


def test_materials_cutout_scope_binding_selection_and_stale_plan(monkeypatch,tmp_path):
    auth=setup(monkeypatch,tmp_path)
    monkeypatch.setattr(UniversalLLMPlanner,"plan",forbidden)
    with TestClient(app) as client:
        workspace,doc=create(client,auth)
        url=f"/api/v1/studios/v1/materials/document/{doc['documentId']}"
        opaque=upload(client,auth,workspace,Image.new("RGB",(320,320),"red"))
        cut=client.post(url+"/cutout",headers=auth,json={"sourceAssetId":opaque,"points":[[.2,.2],[.8,.2],[.8,.8],[.2,.8]],"featherPixels":0})
        assert cut.status_code == 200,cut.text
        result=client.get(f"/api/v1/assets/{cut.json()['assetId']}/content",headers=auth)
        image=Image.open(BytesIO(result.content))
        assert image.getpixel((0,0))[3]==0 and image.getpixel((160,160))[3]==255
        assert client.post(url+"/cutout",headers=auth,json={"sourceAssetId":opaque,"points":[[-1,0],[1,0],[1,1]]}).status_code==422
        kit={"expectedRevision":0,"name":"Coleção","category":"physical","goal":"showcase","materials":[
            {"assetId":opaque,"role":"clean_plate","label":"Cenário"},
            {"assetId":cut.json()["assetId"],"role":"product_cutout","label":"Recorte A"}]}
        assert client.put(url+"/kits/kit-one",headers=auth,json=kit).status_code==200
        # One cutout cannot stand in for two distinct inventory objects.
        bound=client.put(url+"/binding",headers=auth,json={"expectedRevision":0,"kitId":"kit-one","kitRevision":1})
        assert bound.status_code==200,bound.text
        assert next(r for r in bound.json()["recipes"] if r["id"]=="cutout_object_stack")["status"]=="blocked"
        bad=deepcopy(kit)
        bad["expectedRevision"]=1
        bad["materials"][0]["role"]="product_cutout"
        assert client.put(url+"/kits/kit-one",headers=auth,json=bad).status_code==422
        kit["expectedRevision"]=1
        assert client.put(url+"/kits/kit-one",headers=auth,json=kit).status_code==200
        assert client.post(url+"/preview",headers=auth,json={"recipeId":"cutout_object_stack","requestKey":"preview-001"}).status_code==409
        foreign=headers(module="create-video",client="foreign")
        assert client.get(url,headers=foreign).status_code==404


def test_import_and_apply_require_current_kit_and_preview_without_provider(monkeypatch,tmp_path):
    from app.database import SessionLocal
    from app.models import CreativeDocument
    from app.services.studios.ad_materials import planning_context
    auth=setup(monkeypatch,tmp_path)
    monkeypatch.setattr(UniversalLLMPlanner,"plan",forbidden)
    with TestClient(app) as client:
        workspace,doc=create(client,auth)
        url=f"/api/v1/studios/v1/materials/document/{doc['documentId']}"
        asset=upload(client,auth,workspace,Image.new("RGB",(320,320),"blue"))
        data={"expectedRevision":0,"name":"Aplicativo","category":"software","goal":"explain","materials":[
            {"assetId":asset,"role":"presenter","label":"Fonte de teste"},
            {"assetId":asset,"role":"interface","label":"Interface de teste"}]}
        assert client.put(url+"/kits/app",headers=auth,json=data).status_code==200
        bound=client.put(url+"/binding",headers=auth,json={"expectedRevision":0,"kitId":"app","kitRevision":1})
        assert bound.json()["recommendedRecipeId"]=="interface_evidence_overlay"
        request={"recipeId":"interface_evidence_overlay","requestKey":"preview-current-001"}
        plan=client.post(url+"/preview",headers=auth,json=request).json()
        imported=client.post(url+"/import",headers=auth,json={"expectedRevision":1,"requestKey":"import-materials-001"})
        assert imported.status_code==200,imported.text
        assert imported.json()["document"]["revision"]==2
        assert client.post(url+"/apply",headers=auth,json={**request,"planDigest":plan["planDigest"]}).status_code==409
        with SessionLocal() as db:
            context=planning_context(db,db.get(CreativeDocument,doc["documentId"]))
            assert context["status"]=="bound" and not context["assetsNotImported"]
        plan=client.post(url+"/preview",headers=auth,json=request).json()
        result=client.post(url+"/apply",headers=auth,json={**request,"planDigest":plan["planDigest"]})
        assert result.status_code==200,result.text
        assert result.json()["document"]["revision"]==3
        plan=client.post(url+"/preview",headers=auth,json=request).json()
        assert not plan["canApply"]
        assert client.post(url+"/apply",headers=auth,json={**request,"planDigest":plan["planDigest"]}).status_code==422


@pytest.mark.skipif(not ff.capability()["available"],reason="Real FFmpeg required")
def test_real_mask_alpha_multiplication_reveal_and_scroll(monkeypatch,tmp_path):
    auth=setup(monkeypatch,tmp_path)
    with TestClient(app) as client:
        _, doc=create(client,auth)
    base=CreativeDocumentV1.model_validate(doc)
    # Transparent source and a luma matte intersect in a single quadrant.
    source=Image.new("RGBA",(320,320),(255,0,0,0))
    ImageDraw.Draw(source).rectangle((0,0,159,319),fill=(255,0,0,255))
    source.save(tmp_path/"source.png")
    matte=Image.new("RGB",(320,320),"black")
    ImageDraw.Draw(matte).rectangle((0,0,319,159),fill="white")
    matte.save(tmp_path/"matte.png")
    def rendered(tracks,name,paths,info=None):
        directory=tmp_path/name
        directory.mkdir()
        timeline=MediaTimelineV1.model_validate({"durationFrames":48,"frameRate":{"numerator":24,"denominator":1},"tracks":tracks})
        contract=base.model_copy(update={"composition":base.composition.model_copy(update={"media_timeline":timeline})})
        timeline_editor.validate(contract,require_content=True)
        return ff.render(contract,paths,directory,info or {},lambda:False)[0]
    def clip(asset,transform=None,keys=None):
        return {"id":"item","assetId":asset,"timeline":{"startFrame":0,"durationFrames":48},"transform":transform or {},"keyframes":keys or []}
    paths={"source":tmp_path/"source.png","matte":tmp_path/"matte.png"}
    tracks=[{"id":"v","kind":"overlay","clips":[clip("source")]},{"id":"m","kind":"mask","targetTrackId":"v","artifactAssetId":"matte"}]
    frame=pixels(rendered(tracks,"mask",paths),.5)
    assert frame.getpixel((80,80))[0]>180
    assert max(frame.getpixel((240,80)))<20, "Mask must preserve original transparent source pixels"
    assert max(frame.getpixel((80,240)))<20, "Black luma must remove source pixels"
    tracks[1]["invert"]=True
    frame=pixels(rendered(tracks,"inverse",paths),.5)
    assert max(frame.getpixel((80,80)))<20 and frame.getpixel((80,240))[0]>180
    Image.new("RGB",(320,320),"red").save(tmp_path/"opaque.png")
    keys=[{"property":"revealProgress","frame":0,"value":0},{"property":"revealProgress","frame":47,"value":1}]
    video=rendered([{"id":"v","kind":"overlay","clips":[clip("source",keys=keys)]}],"reveal",{"source":tmp_path/"opaque.png"})
    assert max(pixels(video,.25).getpixel((240,160)))<20
    assert pixels(video,1.8).getpixel((240,160))[0]>180
    tall=Image.new("RGB",(320,640),"blue")
    ImageDraw.Draw(tall).rectangle((0,0,319,319),fill="red")
    tall.save(tmp_path/"tall.png")
    keys=[{"property":"cropY","frame":0,"value":0},{"property":"cropY","frame":47,"value":1}]
    video=rendered([{"id":"v","kind":"overlay","clips":[clip("tall",{"crop":{"height":.5}},keys)]}],"scroll",{"tall":tmp_path/"tall.png"})
    assert pixels(video,.1).getpixel((160,160))[0]>180
    assert pixels(video,1.8).getpixel((160,160))[2]>180
    # A real moving video matte, not a constant PNG posing as a motion mask.
    command(["-f","lavfi","-i","color=c=black:s=320x320:r=24:d=2","-vf","geq=lum='if(lt(X,W*T/2),255,0)':cb=128:cr=128", "-c:v",ff.capability()["encoder"],str(tmp_path/"moving.mp4")])
    tracks[1].update(invert=False,artifactAssetId="moving")
    video=rendered(tracks,"video-matte",{**paths,"moving":tmp_path/"moving.mp4"},{"moving":ff.probe(tmp_path/"moving.mp4")})
    assert max(pixels(video,.1).getpixel((80,160)))<20
    assert pixels(video,1.5).getpixel((80,160))[0]>180


def test_all_research_recipes_compile_with_explicit_prerequisites():
    materials=[]
    for role in sorted({role for roles in recipes.REQUIREMENTS.values() for role in roles}):
        for i in range(max(roles.count(role) for roles in recipes.REQUIREMENTS.values())):
            materials.append({"assetId":f"{role}-{i}","role":role,"alignmentGroup":"identity-01"})
    kit={"goal":"showcase","category":"physical","materials":materials}
    assert len(recipes.cards(kit))==12
    for identifier in recipes.REQUIREMENTS:
        assert recipes.compose(identifier,kit,"A mensagem").duration_frames==144
    with pytest.raises(ValueError):
        recipes.compose("moving_variant_mask",{"materials":[]},"Título")
    with pytest.raises(ValueError):
        MotionKey(property="cropX",frame=0,value=2)


def test_default_caption_font_has_a_portable_render_path(tmp_path):
    cue=CaptionCueV1(id="title",text="Clicko",timeline={"startFrame":0,"durationFrames":24})
    ff.title_png(cue,640,640,tmp_path/"title.png")
    with Image.open(tmp_path/"title.png") as image:
        assert image.getchannel("A").getextrema()==(0,255)
