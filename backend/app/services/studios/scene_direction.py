"""Opus directs editorial beats. Clicko compiles and checks the edit locally."""

import json
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from ...domain.studios.contracts import StudioContract
from ...domain.studios.local_composition import LocalLayerStyle
from ...providers.studios import timeline_ffmpeg
from ...providers.studios.local_composition import text_layout
from . import llm_connections, motion_claude as cut, motion_editorial
from .craft import workspace_files
from .gemini_editing import measured_request_cost
from .motion_editorial_review import _raw

BEATS = ("hook", "proof", "action")
PALETTES = {
    "warm": ("#151821", "#FFE092", "#FFF7EC", "#303B52"),
    "cool": ("#111B2C", "#9AF0D0", "#F4F9FF", "#294665"),
    "contrast": ("#17141C", "#FFD349", "#FFF8E9", "#413044"),
}


class Scene(StudioContract):
    role: Literal["hook", "proof", "action"]
    weight: int = Field(ge=2, le=5)
    text: str = Field(min_length=1, max_length=64)
    transition: Literal["cut", "match", "carry"]
    intent: str = Field(min_length=8, max_length=220)
    shot_id: str | None = Field(default=None, max_length=120)
    source_second: float | None = Field(default=None, ge=0, le=1800, allow_inf_nan=False)
    framing: Literal["wide", "medium", "detail"] = "wide"
    focus: Literal["left", "center", "right"] = "center"
    illustration: bool = False
    opening: Literal["scatter", "float", "still"] = "scatter"


class Direction(StudioContract):
    palette: Literal["warm", "cool", "contrast"] = "contrast"
    pace: Literal["wave", "sequence", "snap"] = "sequence"
    scenes: list[Scene] = Field(min_length=3, max_length=3)
    rationale: str = Field(min_length=1, max_length=900)


class ProofCheck(StudioContract):
    visible_operation: bool
    legible_at_phone_size: bool
    finding: str = Field(min_length=8, max_length=1200)


class Review(StudioContract):
    observation: str = Field(min_length=8, max_length=2000)
    revision: Direction | None = None


def _frames(total, scenes):
    if tuple(s.role for s in scenes) != BEATS or total < 72:
        raise ValueError("scene_direction_beat_order_invalid")
    weights = sum(s.weight for s in scenes)
    first = round(total * scenes[0].weight / weights)
    end = round(total * (scenes[0].weight + scenes[1].weight) / weights)
    return ((0, first), (first, end), (end, total))


def _key(prop, frame, value):
    return {"property":prop, "frame":frame, "value":value, "easing":"ease-in-out"}


def _style(layer, **updates):
    style = LocalLayerStyle.model_validate({**layer.properties, **updates})
    layer.properties = style.model_dump(by_alias=True, mode="json", exclude_defaults=True)
    layer.properties["schemaVersion"] = style.schema_version


def _graphic(page, name, x, y, w, h, color, start, length, z, radius=8, keys=()):
    if any(layer.id == name for layer in page.layers):
        raise ValueError("scene_direction_graphic_id_conflict")
    page.layers.append(cut.CreativeLayerV1(id=name, name=name, kind="shape", x=round(x), y=round(y),
        width=round(w), height=round(h), z_index=z, properties={
            "schemaVersion":"studio.local-layer.v1","fill":color,"radius":radius,
            "startFrame":start,"durationFrames":length,"keyframes":list(keys),
        }))


def _motion(page, ranges, direction, colors):
    shapes = [layer for layer in page.layers if layer.kind == "shape" and layer.visible and not layer.locked]
    if len(shapes) != 4:
        raise ValueError("scene_direction_requires_three_graphics_and_track")
    rail = max(shapes, key=lambda layer: layer.width)
    cards = sorted((layer for layer in shapes if layer.id != rail.id), key=lambda layer: layer.x)
    w, h = page.width, page.height
    proof_start, proof_end = ranges[1]
    rail.x, rail.y, rail.width, rail.height, rail.z_index = round(.08*w), round(.59*h), round(.84*w), round(.14*h), 1
    _style(rail, fill=colors[3], startFrame=0, durationFrames=ranges[-1][1], keyframes=[])
    total = ranges[-1][1]
    card_width, card_height = .22*w, .075*h
    fractions = {"wave":(.08,.31,.55), "sequence":(.05,.28,.51), "snap":(.08,.15,.22)}[direction.pace]
    if direction.scenes[1].transition == "cut":
        fractions = tuple(min(value,.34) for value in fractions)
    span = proof_end - proof_start
    for i, card in enumerate(cards):
        target_x, target_y = round((.11+i*.28)*w), round(.622*h)
        _graphic(page, f"direction-slot-{i}", target_x-4, target_y-5, card_width+8, card_height+10,
                 colors[0], 0, total, 2)
        opening = direction.scenes[0].opening
        column = (2,0,1)[i] if opening == "scatter" else i
        card.x = round((.10+.29*column)*w)
        card.y = round((.40-(i%2)*.075)*h)
        card.width, card.height, card.z_index = round(card_width), round(card_height), 4
        depart = proof_start + round(span*fractions[i])
        land = min(proof_end-4, depart+max(5, round(span*(.23 if direction.pace!="snap" else .16))))
        keys = []
        for prop, value in (("x",target_x-card.x),("y",target_y-card.y),("rotation",0)):
            initial = (i-1)*-9 if prop == "rotation" else 0
            keys.append(_key(prop,0,initial))
            if opening != "still" and prop == "y":
                keys.append(_key(prop,max(1,round(proof_start*(.22+i*.13))),-(i+1)*3))
            keys.extend((_key(prop,depart,initial),_key(prop,land,value)))
        keys.extend((_key("scale",land,1),_key("scale",land+2,.96),_key("scale",land+4,1)))
        fills = (colors[1], "#F6A765" if direction.palette!="cool" else "#69BFEE", "#FFEEBB")
        _style(card, fill=fills[i], startFrame=0, durationFrames=total, keyframes=keys)
        translation=[key for key in keys if key["property"] in {"x","y"}]
        _graphic(page,f"direction-card-mark-{i}",card.x+.026*w,card.y+.025*h,.028*w,.018*h,colors[0],
                 0,total,5,4,translation)
        _graphic(page,f"direction-card-detail-{i}",card.x+.071*w,card.y+.032*h,.103*w,.009*h,colors[0],
                 0,total,5,3,translation)
    start = ranges[2][0]
    _graphic(page,"direction-playhead",.105*w,.572*h,max(4,.008*w),.175*h,colors[2],
             start,total-start,5,3,[_key("x",0,0),
             {**_key("x",round((total-start-1)*.76),round(.79*w)),"easing":"linear"}])


def _footage(candidate, ranges, direction, clips, source_limits, colors, proof_asset_id=None):
    page = candidate.pages[0]
    eligible = list(clips.values())
    ids = {clip.id:clip for clip in eligible}
    proof = next((clip for clip in eligible if clip.asset_id == proof_asset_id),None)
    live = [clip for clip in eligible if clip.asset_id != proof_asset_id]
    if proof_asset_id and (proof is None or not live):
        raise ValueError("scene_direction_timeline_proof_requires_two_sources")
    tracks = [track for track in candidate.media_timeline.tracks if track.kind == "video" and track.clips]
    if len(tracks)!=1 or len(eligible)!=len(tracks[0].clips):
        raise ValueError("scene_direction_requires_one_editable_video_track")
    track = tracks[0]
    fps = candidate.media_timeline.frame_rate
    edits = []
    previous = None
    previous_focus = None
    for i, (scene, (start,end)) in enumerate(zip(direction.scenes,ranges,strict=True)):
        source = ids.get(scene.shot_id) if scene.shot_id else eligible[min(i,len(eligible)-1)]
        if proof is not None:
            if scene.role=="proof":
                source=proof
            elif source is None or source.asset_id==proof_asset_id:
                source=live[0 if i==0 else -1]
        if source is None:
            raise ValueError("scene_direction_shot_invalid")
        shot = source.model_copy(deep=True)
        shot.id = f"directed-shot-{i}"
        length = round((end-start)*fps.denominator/fps.numerator*shot.playback_rate*1e6)
        limit = source_limits[shot.asset_id]
        if length > limit:
            raise ValueError("scene_direction_shot_too_short")
        anchor = shot.source.start_microseconds if scene.source_second is None else round(scene.source_second*1e6)
        if shot.asset_id==proof_asset_id:
            anchor=0
        elif scene.transition == "carry" and previous is not None and previous.asset_id == shot.asset_id:
            anchor = previous.source.start_microseconds + previous.source.duration_microseconds
        shot.source = cut.SourceTimeRangeV1(start_microseconds=min(anchor,limit-length),duration_microseconds=length)
        shot.timeline = cut.TimelineFrameRangeV1(start_frame=start,duration_frames=end-start)
        scale = {"wide":1,"medium":.78,"detail":.59}[scene.framing]
        focus = {"left":.24,"center":.5,"right":.72}[scene.focus]
        if scene.transition == "match" and previous is not None and previous.asset_id == shot.asset_id:
            focus = previous_focus
        motion = cut.VisualMotion.model_validate(shot.transform)
        motion.crop = None if shot.asset_id==proof_asset_id else cut.CropWindow(width=scale,height=scale,x=focus,y=.34)
        shot.transform = motion.model_dump(mode="json",by_alias=True,exclude_defaults=True)
        edits.append(shot)
        previous, previous_focus = shot, focus
    track.clips = edits
    if direction.scenes[1].illustration and not proof_asset_id:
        w,h = page.width,page.height
        start,end = ranges[1]
        _graphic(page,"direction-film-rail",.12*w,.66*h,.76*w,.073*h,colors[3],start,end-start,4)
        for i in range(3):
            step = start + round((end-start)*i*.19)
            _graphic(page,f"direction-film-card-{i}",(.16+i*.235)*w,.678*h,.2*w,.035*h,colors[1],
                     step,end-step,5,5)


def compile_direction(source, direction, roles, source_limits, cta, proof_asset_id=None):
    candidate = source.model_copy(deep=True)
    page = candidate.pages[0]
    timeline = candidate.media_timeline
    ranges = _frames(timeline.duration_frames,direction.scenes)
    if proof_asset_id:
        minimum = round(4.5 * timeline.frame_rate.numerator / timeline.frame_rate.denominator)
        total = timeline.duration_frames
        if total - minimum < round(4 * timeline.frame_rate.numerator / timeline.frame_rate.denominator):
            raise ValueError("scene_direction_timeline_proof_duration_too_short")
        if ranges[1][1] - ranges[1][0] < minimum:
            remaining = total - minimum
            first = round(remaining * direction.scenes[0].weight / (direction.scenes[0].weight + direction.scenes[2].weight))
            ranges = ((0, first), (first, first + minimum), (first + minimum, total))
    colors = PALETTES[direction.palette]
    page.background = colors[0]
    titles = sorted((layer for layer in page.layers if layer.kind=="text" and layer.visible and not layer.locked),
                    key=lambda layer: LocalLayerStyle.model_validate(layer.properties).start_frame)
    if len(titles)!=3:
        raise ValueError("scene_direction_requires_three_titles")
    clips = cut._editable_clips(candidate, roles)
    is_film = bool(clips)
    if is_film:
        _footage(candidate,ranges,direction,clips,source_limits,colors,proof_asset_id)
        for layer in page.layers:
            if layer.kind=="shape" and layer.visible and not layer.locked and layer.id.startswith("tarja"):
                layer.visible=False
    elif any(track.kind=="video" and track.clips for track in candidate.media_timeline.tracks):
        raise ValueError("scene_direction_requires_muted_video")
    else:
        _motion(page,ranges,direction,colors)
    w,h = page.width,page.height
    for i,(scene,title,(start,end)) in enumerate(zip(direction.scenes,titles,ranges,strict=True)):
        length=end-start
        is_cta=i==2
        plate_y=round(h*(.79 if is_film else .23 if is_cta else .12))
        pad=round(w*.08)
        plate_height=round(h*(.117 if is_film else .124))
        plate_color=colors[1] if is_cta else colors[0]
        text_color=colors[0] if is_cta else colors[2]
        _graphic(page,f"direction-title-plate-{i}",pad,plate_y,w-pad*2,plate_height,
                 plate_color,start,length,7,17)
        title.x,title.y,title.width,title.height,title.z_index = pad+12,plate_y+12,w-pad*2-24,plate_height-20,9
        keys=[] if scene.transition=="cut" else [_key("opacity",0,.76),_key("opacity",min(6,length-1),1)]
        _style(title,text=cta if is_cta else "Divida clipes na timeline." if proof_asset_id and i==1 else scene.text.strip(),color=text_color,align="center",
               fontSize=round(w*(.078 if is_cta else .082 if i==0 else .068)),startFrame=start,
               durationFrames=length,keyframes=keys)
        style=LocalLayerStyle.model_validate(title.properties)
        motion_editorial._fit_text(page,title,style,round(w*14/360))
        _,runs=text_layout(title,style)
        text_height=max((y for _,_,y,_ in runs),default=0)+style.font_size*1.3
        shift=max(0,int((title.height-text_height)/2))
        title.y+=shift
        title.height-=shift
        _style(title,fontSize=style.font_size)
    return candidate,ranges


def _wire_schema(value):
    """Keep the provider grammar portable. Pydantic checks full bounds locally."""
    if isinstance(value,list):
        return [_wire_schema(item) for item in value]
    if not isinstance(value,dict):
        return value
    ignored={"minimum","maximum","minLength","maxLength","minItems","maxItems","default","title"}
    return {key:_wire_schema(item) for key,item in value.items() if key not in ignored}


def _request(db, job, adapter, context, media, stage, config, ceiling):
    context={**context,"wireSchema":_wire_schema(context["outputSchema"])}
    size=len(json.dumps(context,ensure_ascii=False).encode())+len(json.dumps(context["wireSchema"]).encode())+2048+len(media)*6000
    upper=(size*config["inputUsdPerMillion"]+context["maxOutputTokens"]*config["outputUsdPerMillion"])/1e6
    if upper>ceiling:
        raise ValueError("scene_direction_stage_budget_exceeded")
    db.refresh(job,attribute_names=["status"])
    if job.status!="running":
        raise InterruptedError("scene_direction_cancelled")
    job.result_payload={**(job.result_payload or {}),"submissionStarted":True,"submissionOutcome":"unknown","activeDirectionStage":stage}
    db.commit()
    response=adapter.plan(cut.MODEL,context,media)
    cost=measured_request_cost(job,response["usage"])
    stages=[*job.result_payload.get("directionUsage",[]),{"stage":stage,"costUsd":cost,"usage":response["usage"]}]
    total=round(sum(item["costUsd"] or 0 for item in stages),8)
    job.result_payload={**(job.result_payload or {}),"submissionOutcome":"response_received","measuredCostUsd":total,"directionUsage":stages}
    db.commit()
    if cost is None or total>cut.CUT_BUDGET_USD:
        raise ValueError("scene_direction_cost_unverified")
    if adapter.credential and adapter.credential in response["text"]:
        raise ValueError("editorial_claude_response_credential_rejected")
    return response["text"],total


def _scene_receipt(direction, ranges):
    return [{**scene.model_dump(mode="json",by_alias=True),"startFrame":start,"endFrame":end}
            for scene,(start,end) in zip(direction.scenes,ranges,strict=True)]


def direct(db, record, job, connection, adapter, contract, evidence, instruction, effort, replay=None, proof_asset_id=None):
    comp=contract.composition
    page=comp.pages[0]
    roles=evidence["materialSnapshot"]["roles"]
    clips=cut._editable_clips(comp,roles)
    titles=sorted((layer for layer in page.layers if layer.kind=="text" and layer.visible and not layer.locked),
                  key=lambda layer: LocalLayerStyle.model_validate(layer.properties).start_frame)
    if len(titles)!=3:
        raise ValueError("scene_direction_requires_three_titles")
    shapes=[layer for layer in page.layers if layer.kind=="shape" and layer.visible and not layer.locked]
    tracks=[track for track in comp.media_timeline.tracks if track.kind=="video" and track.clips]
    if tracks:
        if len(tracks)!=1 or len(clips)!=len(tracks[0].clips):
            raise ValueError("scene_direction_requires_one_editable_video_track")
    elif len(shapes)!=4:
        raise ValueError("scene_direction_requires_three_graphics_and_track")
    cta=LocalLayerStyle.model_validate(titles[-1].properties).text
    source_ids=list(dict.fromkeys(clip.asset_id for clip in clips.values()))
    if proof_asset_id and (proof_asset_id not in source_ids or len(source_ids)<2):
        raise ValueError("scene_direction_timeline_proof_requires_two_sources")
    cfg=connection.config
    if cfg["inputUsdPerMillion"]<4 or cfg["outputUsdPerMillion"]<20:
        raise ValueError("editorial_claude_cut_pricing_invalid")
    # One reservation covers both stages. Each call is bounded against the remaining reservation.
    max_tokens=min(24000,cfg["maxOutputTokens"])
    original_cost=0
    if replay is None:
        llm_connections.reserve_request(db,job,connection,50000,max_tokens,max_amount=cut.CUT_BUDGET_USD,reserve_full=True)
        db.commit()
    else:
        original_cost=replay.result_payload.get("measuredCostUsd")
        if original_cost is None or not 0 < original_cost < cut.CUT_BUDGET_USD:
            raise ValueError("scene_direction_recovery_cost_unverified")
    limits={}
    def cancelled():
        db.refresh(job,attribute_names=["status"])
        return job.status!="running"
    with tempfile.TemporaryDirectory() as folder, workspace_files(db,record,None,extra_asset_ids=source_ids) as (_,params,_):
        media,frames,source_hash=cut._cut_samples(db,record,contract,evidence,folder,cancelled)
        for asset in params["media"]:
            info=timeline_ffmpeg.probe(asset["path"])
            duration=float(info["format"]["duration"])
            limits[asset["assetId"]]=int(duration*1e6)
            if len(media)>=6:
                continue
            path=Path(folder)/f"raw-{len(media)}.jpg"
            data=_raw(asset["path"],["-an","-vf",f"fps=8/{duration},scale=180:-2,tile=4x2",
                                     "-frames:v","1","-c:v","mjpeg","-f","image2pipe"])
            if data:
                path.write_bytes(data)
                media.append((path,"image/jpeg"))
        common={"editorialMotion":True,"sceneDirection":True,"creativeCut":True,"editorialCutEffort":effort,
                "maxOutputTokens":max_tokens,"instruction":instruction,"cta":cta,
                "timelineProofAssetId":proof_asset_id,
                **({"editorialCutEffort":"xhigh"} if proof_asset_id else {}),
                "frameRate":comp.media_timeline.frame_rate.model_dump(by_alias=True),
                "timelineFrames":comp.media_timeline.duration_frames}
        context={**common,"outputSchema":Direction.model_json_schema(by_alias=True),
                 "cutFrames":frames,"sourceDurationMicroseconds":limits,
                 "shotIds":[{"id":clip.id,"assetId":clip.asset_id} for clip in clips.values()],
                 "captions":[LocalLayerStyle.model_validate(layer.properties).text for layer in page.layers if layer.kind=="text"],
                 "structuredPlanningInstruction":(
                    "Direct exactly three beats in order: hook, proof, action. The images start with samples of the current cut "
                    "in frame order (three per strip). Subsequent images show ordered samples across each raw video. "
                    "Choose what changes for the viewer, the relative time, the transition and truthful short Brazilian Portuguese copy. "
                    "For motion, choose the hook opening: scatter changes the order, float keeps order but animates, still holds position. "
                    "Clicko moves the same cards into slots on proof and scans them on action. "
                    "For footage, choose sourceSecond, framing, focus and shotId from the available source. Cut changes shot, "
                    "match maintains attention on the same subject, carry continues source time when possible. "
                    "On the proof beat you may request an abstract timeline illustration (illustration=true), "
                    "which adds a small vector timeline to clarify the connection with editing. Never claim it is app footage. "
                    "Choose a compelling visual progression, avoid generic copy and invented claims. Use the authorized CTA. "
                    "Plan scenes and transitions. Clicko owns geometry, easing, type, audio and final duration."
                 )}
        total=0
        if replay is None:
            raw,total=_request(db,job,adapter,context,media,"direction",cfg,cut.CUT_BUDGET_USD/2)
            direction=Direction.model_validate_json(raw)
        else:
            direction=Direction.model_validate(replay.result_payload["initialSceneDirection"])
        job.result_payload={**(job.result_payload or {}),"initialSceneDirection":direction.model_dump(mode="json",by_alias=True)}
        db.commit()
        candidate,ranges=compile_direction(comp,direction,roles,limits,cta,proof_asset_id)
        with tempfile.TemporaryDirectory() as revision_folder:
            draft=contract.model_copy(update={"composition":candidate})
            summary={}
            strips,review_frames,draft_hash=cut._cut_samples(db,record,draft,evidence,revision_folder,cancelled,summary=summary)
            context={**common,"outputSchema":Review.model_json_schema(by_alias=True),
                     "cutFrames":review_frames,"sceneRanges":ranges,
                     "direction":direction.model_dump(mode="json",by_alias=True),"technicalFindings":summary.get("findings",[]),
                     "sourceDurationMicroseconds":limits,"shotIds":[clip.id for clip in clips.values()],
                     "structuredPlanningInstruction":(
                        "Review the first Clicko render, shown in chronological strips. Assess hook, visible proof, "
                        "visual continuity and mobile CTA against the instruction. Identify specific frame evidence. "
                        "Return observation and a full revised three-beat direction only if it improves a visible issue. "
                        "You may adjust scene weights, copy, palette, pace, transition, permitted illustration and source anchors. "
                        "If proof lacks a shot, state the gap instead of inventing one. Keep the authorized CTA. "
                        "Do not return coordinates. The render samples are stills and cannot prove exact audio sync."
                     )}
            if replay is not None and effort=="high":
                context["editorialCutEffort"]="xhigh"
            verdict="kept"
            try:
                review_text,total=_request(db,job,adapter,context,strips,"render_review",cfg,
                                           cut.CUT_BUDGET_USD-original_cost-total)
                review=Review.model_validate_json(review_text)
            except ValidationError as error:
                job.result_payload={**(job.result_payload or {}),"directionReviewIssues":[
                    {"field":list(issue["loc"]),"type":issue["type"]} for issue in error.errors(include_input=False)]}
                db.commit()
                review=Review(observation="A resposta da revisão não respeitou o formato. Primeira montagem preservada.")
                verdict="review_invalid"
            except ValueError as error:
                code=str(error)
                if not (code.startswith("llm_provider_") or code=="scene_direction_stage_budget_exceeded"):
                    raise
                job.result_payload={**(job.result_payload or {}),"directionReviewError":code}
                db.commit()
                review=Review(observation="A revisão não concluiu. Primeira montagem preservada.")
                verdict="review_unavailable"
            if review.revision and review.revision!=direction:
                try:
                    updated,new_ranges=compile_direction(comp,review.revision,roles,limits,cta,proof_asset_id)
                    if motion_editorial._text_legibility(updated):
                        raise ValueError("scene_direction_revision_legibility")
                except ValueError:
                    verdict="revision_rejected"
                else:
                    direction,candidate,ranges=review.revision,updated,new_ranges
                    verdict="revised"
    if proof_asset_id and (job.result_payload or {}).get("submissionOutcome")=="response_received":
        with tempfile.TemporaryDirectory() as quality_folder:
            draft=contract.model_copy(update={"composition":candidate})
            strips,quality_frames,quality_hash=cut._cut_samples(db,record,draft,evidence,quality_folder,cancelled)
            context={**common,"maxOutputTokens":min(20000,cfg["maxOutputTokens"]),
                     "outputSchema":ProofCheck.model_json_schema(by_alias=True),
                     "cutFrames":quality_frames,"sceneRanges":ranges,
                     "structuredPlanningInstruction":(
                        "Audit the actual final render of a portrait ad at phone size. The middle is a genuine screen recording "
                        "of the Clicko multipiste timeline: look for a single clip becoming two around the playhead. "
                        "Check if the operation is visible from the sampled frames, if UI details are readable and if the CTA "
                        "and return to real footage close the promise. Give a candid concrete finding in Brazilian Portuguese. "
                        "Do not infer motion that is not sampled or say that viewers tested it."
                     )}
            try:
                raw,total=_request(db,job,adapter,context,strips,"final_proof_review",cfg,
                                   cut.CUT_BUDGET_USD-original_cost-total)
                quality=ProofCheck.model_validate_json(raw).model_dump(by_alias=True)
            except ValidationError:
                quality={"finding":"A resposta da verificação final não respeitou o formato."}
            except ValueError as error:
                if not (str(error).startswith("llm_provider_") or str(error)=="scene_direction_stage_budget_exceeded"):
                    raise
                quality={"finding":"A verificação final não concluiu.","errorCode":str(error)}
            evidence["timelineProofReview"]={**quality,"sampledFrames":quality_frames,"renderChecksum":quality_hash}
    job.result_payload={**(job.result_payload or {}),"finalSceneDirection":direction.model_dump(mode="json",by_alias=True)}
    evidence["sceneDirection"]={"initialSourceChecksum":source_hash,"firstRenderChecksum":draft_hash,
        "firstRenderFrames":review_frames,"firstRenderTechnicalStatus":summary.get("status"),
        "review":review.observation,"reviewOutcome":verdict,"scenes":_scene_receipt(direction,ranges)}
    evidence["claude"]={"provider":"anthropic","model":cut.MODEL,"cutEffort":effort,"sceneDirection":True,
                       "generationBudgetUsd":cut.CUT_BUDGET_USD,"measuredCostUsd":total}
    if replay is not None:
        evidence["claude"].update(replayedTaskId=replay.id,originalMeasuredCostUsd=original_cost,
                                  totalGenerationCostUsd=round(original_cost+total,8))
    evidence["receipts"].extend([{"stage":"scene_direction","status":"complete"},
                                 {"stage":"compiled_render_review","status":verdict}])
    return cut._cut_output(candidate,direction)
