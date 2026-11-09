"""Durable local preparation -> generated materials -> editable composition -> real render."""
import json
import tempfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from ...domain.studios.contracts import AssetReferenceV1, CreateGenerationJobRequest, CreateStudioDocumentRequest, CreativeDocumentV1, MediaTimelineV1
from ...domain.studios.material_effects import EffectRequest, JOB_TYPE, PROVIDER
from ...models import BrandProfile, CreativeDocument, LibraryAsset, StudioGenerationJob, User, WorkspaceResource
from ...providers.studios import material_effects as local, timeline_ffmpeg as ff
from ..brand import brand_readiness
from ..object_storage import get_object_storage, sha256_file
from . import ad_materials, timeline_editor
from .compatibility import record_to_contract
from .craft import scoped_asset, write_asset
from .kernel import create_document, emit_event


def validate_admission(db,request):
    effect=EffectRequest.model_validate(request.request["effect"])
    record=db.get(CreativeDocument,request.document_id)
    if not record or record.workspace_id!=request.workspace_id:
        raise ValueError("material_effect_document_unavailable")
    contract=record_to_contract(record)
    timeline_editor.editable(contract)
    if effect.expected_revision!=record.revision or request.request["document"]!=contract.model_dump(mode="json",by_alias=True):
        raise ValueError("material_effect_document_conflict")
    kit=ad_materials.selected_kit(db,record.workspace_id,"document",record.id)
    if not kit or effect.kit_revision!=kit["revision"] or request.request["kit"]!=kit:
        raise ValueError("material_effect_kit_conflict")
    if not any(m["assetId"]==effect.source_asset_id for m in kit["materials"]):
        raise ValueError("material_effect_source_not_in_kit")
    expected_provider=PROVIDER if effect.operation=="segment_person" else "local.material-generative-v1"
    if request.provider!=expected_provider:
        raise ValueError("material_effect_provider_invalid")
    asset=scoped_asset(db,record.workspace_id,effect.source_asset_id,request.request["sourceChecksum"])
    if not (asset.media_type or "").startswith("video/"):
        raise ValueError("material_effect_video_required")
    if (asset.object_metadata or {}).get("rightsStatus")=="restricted" or any(a.id==asset.id and a.rights_status=="restricted" for a in contract.assets):
        raise ValueError("material_effect_source_restricted")
    caps=local.capability()
    if not caps["segmentationAvailable"] or effect.operation!="segment_person" and not caps["generativeWeightsInstalled"]:
        raise ValueError("material_effect_model_not_installed")


def create(db,record,effect,user):
    from .jobs import create_job
    previous=db.scalar(select(StudioGenerationJob).where(StudioGenerationJob.workspace_id==record.workspace_id,
        StudioGenerationJob.job_type==JOB_TYPE,StudioGenerationJob.idempotency_key==effect.request_key))
    if previous:
        if previous.document_id!=record.id or previous.request_payload["effect"]!=effect.model_dump(mode="json",by_alias=True):
            raise ValueError("material_effect_idempotency_conflict")
        return previous,False
    asset=scoped_asset(db,record.workspace_id,effect.source_asset_id)
    request=CreateGenerationJobRequest(workspaceId=record.workspace_id,documentId=record.id,jobType=JOB_TYPE,
        provider=PROVIDER if effect.operation=="segment_person" else "local.material-generative-v1",
        request={"effect":effect.model_dump(mode="json",by_alias=True),"document":record_to_contract(record).model_dump(mode="json",by_alias=True),
                 "sourceChecksum":asset.checksum_sha256,"kit":ad_materials.selected_kit(db,record.workspace_id,"document",record.id)})
    return create_job(db,request,effect.request_key,user)


def composition(effect,assets):
    n=effect.duration_seconds*24
    def clip(identifier,asset,audio=False,keys=None):
        return {"id":identifier,"assetId":asset.id,"timeline":{"startFrame":0,"durationFrames":n},
                "transform":{"originalAudioEnabled":audio},"keyframes":keys or []}
    tracks=[]
    if effect.operation!="segment_person":
        tracks.append({"id":"original-world","kind":"video","clips":[clip("source",assets["source"],True)]})
        if "generated_moving" not in assets:
            return MediaTimelineV1.model_validate({"frameRate":{"numerator":24,"denominator":1},"durationFrames":n,"tracks":tracks})
        tracks.append({"id":"generated-world","kind":"overlay","clips":[clip("generated",assets["generated_moving"],keys=[
            {"property":"revealProgress","frame":0,"value":0},{"property":"revealProgress","frame":24,"value":0},
            {"property":"revealProgress","frame":min(72,n-24),"value":1,"easing":"ease-in-out"}])]})
    tracks.append({"id":"person","kind":"video","clips":[clip("moving-person",assets.get("foreground",assets["source"]),effect.operation=="segment_person")]})
    tracks.append({"id":"person-matte","kind":"mask","targetTrackId":"person","artifactAssetId":assets["matte"].id})
    return MediaTimelineV1.model_validate({"frameRate":{"numerator":24,"denominator":1},"durationFrames":n,"tracks":tracks})


def execute(db,job,progress,is_cancelled):
    effect=EffectRequest.model_validate(job.request_payload["effect"])
    record=db.get(CreativeDocument,job.document_id)
    if not record or record.workspace_id!=job.workspace_id:
        raise ValueError("material_effect_document_unavailable")
    asset=scoped_asset(db,job.workspace_id,effect.source_asset_id,job.request_payload["sourceChecksum"])
    admitted=CreativeDocumentV1.model_validate(job.request_payload["document"])
    if (asset.object_metadata or {}).get("rightsStatus")=="restricted" or any(a.id==asset.id and a.rights_status=="restricted" for a in admitted.assets):
        raise ValueError("material_effect_source_restricted")
    # A committed receipt is authoritative after interruption; never regenerate it.
    for cached in db.scalars(select(LibraryAsset).where(LibraryAsset.workspace_id==job.workspace_id,LibraryAsset.asset_type=="video")).all():
        metadata=cached.object_metadata or {}
        if metadata.get("materialEffectJobId")==job.id and metadata.get("receipt"):
            with get_object_storage(cached.storage_backend).materialize(cached.storage_key) as path:
                if sha256_file(path)!=cached.checksum_sha256:
                    raise ValueError("material_effect_cached_checksum_mismatch")
            return metadata["receipt"]
    written=[]
    try:
        with tempfile.TemporaryDirectory(prefix="clicko-material-effect-") as directory, get_object_storage(asset.storage_backend).materialize(asset.storage_key) as source:
            directory=Path(directory)
            if sha256_file(source)!=asset.checksum_sha256:
                raise ValueError("material_effect_source_checksum_mismatch")
            info=ff.probe(source)
            if effect.start_seconds+effect.duration_seconds>float(info["format"]["duration"])+1/24:
                raise ValueError("material_effect_source_range_exceeded")
            video=next((s for s in info["streams"] if s["codec_type"]=="video"),None)
            if not video or video["width"]*video["height"]>3840*2160:
                raise ValueError("material_effect_source_dimensions_unsupported")
            report=local.prepare(source,directory,effect,job.id,progress,is_cancelled)
            if is_cancelled():
                return {"cancelled":True}
            outputs={"source":("source.mp4","video/mp4","video"),"matte":("matte.mkv","video/x-matroska","video"),
                "subject":("subject.png","image/png","image"),"plate":("clean-plate.png","image/png","image")}
            if report.get("camera",{}).get("applied"):
                outputs["generated"]=("generated.png","image/png","image")
                outputs["generated_moving"]=("generated-moving.mkv","video/x-matroska","video")
                outputs["foreground"]=("foreground.mkv","video/x-matroska","video")
            derived={}
            for name,(filename,mime,kind) in outputs.items():
                output,storage,key=write_asset(db,record,directory/filename,suffix=Path(filename).suffix,media_type=mime,asset_type=kind,
                    title=f"Preparação automática · {name}",metadata={"materialEffectJobId":job.id,"sourceAssetId":asset.id,
                    "sourceChecksum":asset.checksum_sha256,"sourceStartSeconds":effect.start_seconds,"sourceDurationSeconds":effect.duration_seconds,
                    "preparationRole":name,"reviewRequired":True,"rightsStatus":"unknown","localOnly":True})
                written.append((storage,key));derived[name]=output
            db.flush()
            timeline=composition(effect,derived)
            snapshot=CreativeDocumentV1.model_validate(job.request_payload["document"])
            source_info=ff.probe(directory/"source.mp4")
            stream=next(s for s in source_info["streams"] if s["codec_type"]=="video")
            page=snapshot.composition.pages[0].model_copy(update={"width":stream["width"],"height":stream["height"],"duration_ms":effect.duration_seconds*1000,"layers":[],"background":"#112833"})
            references=[AssetReferenceV1(id=a.id,media_type=a.media_type,checksum=a.checksum_sha256,origin="workspace",rights_status="unknown") for a in derived.values()]
            comp=snapshot.composition.model_copy(update={"pages":[page],"media_timeline":timeline,"tracks":[],
                "narrative":{**snapshot.composition.narrative,"localMaterialEffect":{"jobId":job.id,"operation":effect.operation,"report":report,"reviewRequired":True}}})
            candidate=snapshot.model_copy(update={"composition":comp,"assets":references})
            timeline_editor.validate(candidate,require_content=True)
            paths={a.id:directory/outputs[name][0] for name,a in derived.items()}
            media={derived[name].id:source_info if name=="source" else ff.probe(directory/filename)
                   for name,(filename,_,kind) in outputs.items() if kind=="video"}
            output,metadata=ff.render(candidate,paths,directory,media,is_cancelled)
            progress(95)
            if is_cancelled():
                raise ValueError("material_effect_cancelled")
            user=db.get(User,job.requested_by)
            brand=db.scalar(select(BrandProfile).where(BrandProfile.workspace_id==job.workspace_id))
            created=create_document(db,CreateStudioDocumentRequest(workspaceId=job.workspace_id,title=f"Efeito local · {effect.operation}",
                contentType="video",brandRevision=brand_readiness(brand)["revision"],brief=snapshot.brief,composition=comp,assets=references),user,
                creation_key="material-effect:"+job.id,commit=False)
            db.flush()
            final,storage,key=write_asset(db,created,output,suffix=".mp4",media_type="video/mp4",asset_type="video",title=created.title,
                metadata={"materialEffectJobId":job.id,"localOnly":True,"reviewRequired":True})
            written.append((storage,key));db.flush()
            kit_id=str(uuid4())
            materials=[{"assetId":derived[name].id,"role":role,"label":role,"alignmentGroup":job.id} for name,role in
                [("source","presenter"),("matte","matte"),("subject","subject_cutout"),("plate","clean_plate")]]
            if "generated" in derived:
                role="generated_background" if effect.operation=="replace_background" else "generated_patch"
                materials.append({"assetId":derived["generated"].id,"role":role,"label":"Cenário gerado" if role=="generated_background" else "Região gerada","alignmentGroup":job.id})
            kit={"id":kit_id,"revision":1,"name":"Preparação automática · "+job.id[:8],"category":job.request_payload["kit"]["category"],
                "goal":"transformation","description":"Materiais preparados localmente; revisar bordas e cenário antes de usar no anúncio.",
                "visualIdentity":job.request_payload["kit"].get("visualIdentity",""),"materials":materials}
            db.add(WorkspaceResource(id=str(uuid4()),workspace_id=job.workspace_id,kind=ad_materials.KIT,resource_key=kit_id,payload=kit,created_by=user.id))
            db.add(WorkspaceResource(id=str(uuid4()),workspace_id=job.workspace_id,kind=ad_materials.BINDING,resource_key="document:"+created.id,
                payload={"revision":1,"kitId":kit_id,"kitRevision":1},created_by=user.id))
            receipt={"assetId":final.id,"downloadUrl":f"/api/v1/assets/{final.id}/content","documentId":created.id,"preparedKitId":kit_id,
                "checksumSha256":final.checksum_sha256,"sizeBytes":final.size_bytes,"mediaType":"video/mp4",
                "operation":effect.operation,"sourceAssetId":asset.id,"report":report,"apiCalls":0,"externalCostUsd":0,"reviewRequired":True,
                "preparedAssets":{name:a.id for name,a in derived.items()},**metadata}
            final.object_metadata={**final.object_metadata,"receipt":receipt}
            emit_event(db,workspace_id=job.workspace_id,event_type="studio.ad.material_effect.completed",aggregate_type="generation_job",
                aggregate_id=job.id,correlation_id=job.id,actor_id=user.id,payload=receipt)
            db.commit()
            return receipt
    except Exception:
        db.rollback()
        for storage,key in written:
            storage.delete(key)
        raise
