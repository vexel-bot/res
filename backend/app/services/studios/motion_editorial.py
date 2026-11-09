"""Versioned editorial rules for the local-only Clicko experiment."""

import json
import math
import re
from pathlib import Path

from ...domain.studios.agents import AgentOutput
from ...domain.studios.contracts import CreativeCompositionV1, CreativeLayerV1
from ...domain.studios.local_composition import LocalLayerStyle
from ...providers.studios import timeline_ffmpeg
from ...providers.studios.local_composition import text_layout
from . import ad_materials, timeline_editor
from .craft import scoped_asset, workspace_files

OPERATIONS = ("layer.upsert", "timeline.replace", "keyframes", "mask")
KIT_PRECEDENCE = ("interface", "presenter", "demo", "product_cutout", "product", "state_after", "state_before")


def knowledge():
    return json.loads(Path(__file__).with_name("motion_editorial_cards.v1.json").read_text(encoding="utf-8"))


def snapshot_materials(db, record, contract):
    context = ad_materials.planning_context(db, record)
    kit = context.get("kit")
    imported = {asset.id for asset in contract.assets}
    roles = {
        material["assetId"]: material["role"]
        for material in (kit or {}).get("materials", [])
        if material["assetId"] in imported
    }
    return {
        "status": context["status"],
        "kitId": kit["id"] if kit else None,
        "kitRevision": kit["revision"] if kit else None,
        "roles": roles,
        "notImported": context.get("assetsNotImported", []),
        "checksums": {asset.id: asset.checksum for asset in contract.assets},
    }


def fingerprint(snapshot):
    return timeline_editor.digest(snapshot)


def _style(layer):
    return LocalLayerStyle.model_validate(layer.properties)


def _set_style(layer, style):
    layer.properties = style.model_dump(by_alias=True, mode="json", exclude_defaults=True)
    layer.properties["schemaVersion"] = style.schema_version


def _scene_format(selection, roles, flags, objective):
    if selection != "auto":
        return selection
    interface = "interface" in roles
    words = objective.casefold()
    if interface and any(token in words for token in ("interface", "tela", "software", "aplicativo", "fluxo")):
        return "interface"
    if flags["video"]:
        if interface:
            return "interface"
        if flags["image"] and not any(token in words for token in ("depoimento", "entrevista")):
            return "hybrid"
        return "footage"
    return "interface" if interface else "motion"


def _flags(comp, roles, refs):
    page = comp.pages[0]
    visual_clips = [
        clip for track in comp.media_timeline.tracks
        if track.kind in {"video", "overlay"}
        for clip in track.clips if clip.enabled
    ]
    visual = {clip.asset_id for clip in visual_clips}
    images = {_style(layer).asset_id for layer in page.layers if layer.kind == "image" and layer.visible}
    ids = images | visual
    # The imported kit can populate a genuinely empty project.
    usable = ids | set(roles)
    return {
        "text": any(layer.kind == "text" and layer.visible for layer in page.layers),
        "image": any((refs.get(i) or "").startswith("image/") for i in usable),
        "video": any((refs.get(i) or "").startswith("video/") for i in usable),
        "interface": any(i in usable and role == "interface" for i, role in roles.items()),
        "cutout": any(i in usable and role in {"subject_cutout", "product_cutout"} for i, role in roles.items()),
        "audio": any(track.kind == "audio" and not track.muted and any(clip.enabled for clip in track.clips)
                     for track in comp.media_timeline.tracks),
        "usedVisual": bool(ids),
    }


def _support(card, flags):
    return all(
        flags["image"] or flags["video"] if need == "image-or-video" else flags.get(need, False)
        for need in card["requires"]
    )


def _background(page, layer, style, total_frames):
    possible = []
    for item in page.layers:
        if item.kind != "shape" or not item.visible or item.z_index >= layer.z_index or item.opacity < 1:
            continue
        backing = _style(item)
        if backing.shape != "rectangle" or backing.gradient_end or backing.keyframes:
            continue
        end = style.start_frame + (style.duration_frames or total_frames)
        backing_end = backing.start_frame + (backing.duration_frames or total_frames)
        if backing.start_frame > style.start_frame or backing_end < end:
            continue
        if item.x <= layer.x and item.y <= layer.y and item.x + item.width >= layer.x + layer.width and item.y + item.height >= layer.y + layer.height:
            possible.append((item.z_index, backing.fill))
    return max(possible)[1] if possible else page.background[:7]


def contrast(a, b):
    def luminance(hex_color):
        rgb = [int(hex_color[index:index+2], 16) / 255 for index in (1, 3, 5)]
        linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
        return sum(x * w for x, w in zip(linear, (.2126, .7152, .0722), strict=True))
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def _text_boxes(page, layer, style):
    face, runs = text_layout(layer, style)
    if not runs:
        return []
    top = face.getbbox(" ".join(style.text.split()))[1]
    return [
        (math.floor(layer.x+x), math.floor(layer.y+y),
         math.ceil(layer.x+x+width), math.ceil(layer.y+y+style.font_size+top/3))
        for _word, x, y, width in runs
    ]


def _fit_text(page, layer, style, min_font):
    style.font_size = max(min_font, style.font_size)
    while style.font_size > 8:
        try:
            boxes = _text_boxes(page, layer, style)
            if all(x >= 0 and y >= 0 and right <= page.width and bottom <= page.height
                   for x, y, right, bottom in boxes):
                return
        except ValueError as error:
            if str(error) != "local_text_does_not_fit":
                raise
        style.font_size -= 1


def _text_legibility(comp):
    page = comp.pages[0]
    total = comp.media_timeline.duration_frames
    findings = []
    for layer in page.layers:
        if layer.kind != "text" or not layer.visible:
            continue
        style = _style(layer)
        meta = {"layerId": layer.id, "frame": style.start_frame}
        if style.font_size * min(1, 360/page.width) < 14:
            findings.append({"code": "text_below_phone_floor", **meta})
        try:
            boxes = _text_boxes(page, layer, style)
            if any(x < 0 or y < 0 or right > page.width or bottom > page.height for x, y, right, bottom in boxes):
                findings.append({"code": "text_outside_canvas", **meta})
        except ValueError as error:
            if str(error) != "local_text_does_not_fit":
                raise
            findings.append({"code": "text_does_not_fit", **meta})
        if contrast(style.color, _background(page, layer, style, total)) < 4.5:
            findings.append({"code": "text_contrast_below_floor", **meta})
    return findings


def _readable(comp, layer_ids):
    page = comp.pages[0]
    min_font = max(16, round(page.width * 16 / 360))
    total = comp.media_timeline.duration_frames
    for layer in page.layers:
        if layer.id not in layer_ids or layer.kind != "text" or layer.locked:
            continue
        style = _style(layer)
        background = _background(page, layer, style, total)
        if contrast(style.color, background) < 4.5:
            style.color = max(("#FFFFFF", "#080D12"), key=lambda color: contrast(color, background))
        pad = min(20, round(page.width * .04))
        layer.x = min(max(pad, layer.x), page.width - pad - 12)
        layer.y = min(max(pad, layer.y), page.height - pad - min_font * 1.3)
        layer.width = min(layer.width, page.width - layer.x - pad)
        layer.height = min(layer.height, page.height - layer.y - pad)
        _fit_text(page, layer, style, min_font)
        _set_style(layer, style)


def _animate(layer, fps, total, variant, role=None):
    style = _style(layer)
    length = style.duration_frames or total
    if length < 8:
        return
    if role == "product_cutout":
        prop, first, last = "scale", .92 if variant == "knowledge" else .83, 1
        end = min(length - 1, round(fps * .62))
    elif role == "state_after":
        prop, first, last = "x", 12 if variant == "knowledge" else 24, 0
        end = min(length - 1, round(fps * .45))
    elif layer.kind == "image":
        return  # The original photo is the reference state; hold it steady.
    else:
        prop, first, last = "y", 12 if variant == "knowledge" else 7, 0
        end = min(length - 1, max(2, round(fps * .26)))
    from ...domain.studios.timeline_editor import MotionKey
    style.keyframes = [key for key in style.keyframes if key.property != prop][:30] + [
        MotionKey(property=prop, frame=0, value=first),
        MotionKey(property=prop, frame=max(1, end), value=last, easing="ease-out"),
    ]
    _set_style(layer, style)


def _fit_proof_images(db, record, comp, kind, roles):
    """Fit logos and interface evidence within their boxes without trimming source pixels."""
    from PIL import Image

    page = comp.pages[0]
    images = [layer for layer in page.layers if layer.kind == "image" and layer.visible and not layer.locked
              and roles.get(_style(layer).asset_id) in {"logo", "interface"} and not _style(layer).crop]
    asset_ids = {_style(layer).asset_id for layer in images}
    if not asset_ids:
        return
    with workspace_files(db, record, None, extra_asset_ids=asset_ids) as (_directory, params, _manifest):
        paths = {item["assetId"]: item["path"] for item in params["media"]}
        for layer in images:
            asset_id = _style(layer).asset_id
            with Image.open(paths[asset_id]) as source:
                source_width, source_height = source.size
                if source.getexif().get(274) in {5, 6, 7, 8}:
                    source_width, source_height = source_height, source_width
            x, y, width, height = layer.x, layer.y, layer.width, layer.height
            if kind == "interface" and roles[asset_id] == "interface":
                x, y, width, height = page.width*.06, page.height*.24, page.width*.88, page.height*.70
            factor = min(width/source_width, height/source_height)
            layer.width = max(2, round(source_width*factor))
            layer.height = max(2, round(source_height*factor))
            layer.x = x + (width-layer.width)/2
            layer.y = y + (height-layer.height)/2


def _protect_reading_plane(comp, kind):
    """Keep text readable over real footage."""
    page, timeline = comp.pages[0], comp.media_timeline
    text_layers = [layer for layer in page.layers if layer.kind == "text" and layer.visible and not layer.locked]
    if kind not in {"footage", "hybrid"}:
        return
    clip_intervals = [(clip.timeline.start_frame, clip.timeline.start_frame + clip.timeline.duration_frames)
                      for track in timeline.tracks if track.kind in {"video", "overlay"}
                      for clip in track.clips if clip.enabled]
    existing_ids = {layer.id for layer in page.layers} | {
        item.id for track in timeline.tracks for item in (getattr(track, "clips", []) or getattr(track, "cues", []))
    }
    available = min(24-len(page.layers), 32-len(existing_ids))
    for layer in text_layers:
        if available <= 0:
            break
        style = _style(layer)
        end = style.start_frame + (style.duration_frames or timeline.duration_frames)
        identifier = f"editorial-backing-{layer.id}"
        if identifier in existing_ids or len(identifier) > 120 or not layer.z_index or not any(
            start < end and style.start_frame < stop for start, stop in clip_intervals
        ):
            continue
        style.color = "#FFF2DE"
        _set_style(layer, style)
        page.layers.append(CreativeLayerV1(
            id=identifier, kind="shape", name="Base do título",
            x=max(0, layer.x-10), y=max(0, layer.y-9),
            width=min(page.width-max(0, layer.x-10), layer.width+20),
            height=min(page.height-max(0, layer.y-9), layer.height+18),
            zIndex=layer.z_index-1,
            properties={"schemaVersion":"studio.local-layer.v1", "fill":"#13231D", "radius":12,
                        "startFrame":style.start_frame, "durationFrames":end-style.start_frame},
        ))
        available -= 1


def _seed(db, record, comp, roles, refs, instruction, kind):
    """Assemble the imported kit without changing a pre-existing visual or audio edit."""
    page = comp.pages[0]
    timeline = comp.media_timeline
    if page.layers or any((getattr(track, "clips", []) or getattr(track, "cues", [])) for track in timeline.tracks
                          if track.kind in {"video", "overlay", "caption"}):
        return False
    preferred = ("interface",) if kind == "interface" else tuple(role for role in KIT_PRECEDENCE if role != "interface")
    ranked = [asset_id for role in preferred for asset_id, actual in roles.items() if role == actual]
    stills = [asset_id for asset_id in ranked if (refs.get(asset_id) or "").startswith("image/")][:3]
    videos = [asset_id for asset_id in ranked if (refs.get(asset_id) or "").startswith("video/")][:3]
    total = timeline.duration_frames
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    beats = []
    if videos and kind != "motion":
        if sum(scoped_asset(db, record.workspace_id, asset_id).size_bytes or 0 for asset_id in videos) > 100 * 1024**2:
            return False
        cursor = round(total*.22) if kind == "hybrid" and stills else 0
        if cursor:
            beats.append((stills[0], 0, cursor))
        with workspace_files(db, record, None, extra_asset_ids=videos) as (_dir, params, _manifest):
            paths = {entry["assetId"]: entry["path"] for entry in params["media"]}
            for asset_id in videos:
                media = timeline_ffmpeg.probe(paths[asset_id])
                length = math.floor(float(media["format"]["duration"])*fps)-1
                if length <= 0 or not any(stream["codec_type"] == "video" for stream in media["streams"]):
                    continue
                end = min(total, cursor+length)
                beats.append((asset_id, cursor, end))
                cursor = end
                if cursor == total:
                    break
        if cursor != total:
            if stills and kind in {"hybrid", "interface"}:
                beats.append((stills[-1], cursor, total))
            else:
                return False
    elif stills and kind != "footage":
        beats = [(asset, round(total*i/len(stills)), round(total*(i+1)/len(stills))) for i, asset in enumerate(stills)]
    if not beats:
        return False
    copy = re.findall(r'["“]([^"”]{1,120})["”]', instruction)[:3]
    clips = []
    for index, (asset_id, start, end) in enumerate(beats):
        if end <= start:
            continue
        style = {"schemaVersion": "studio.local-layer.v1", "startFrame": start, "durationFrames": end-start}
        if asset_id in videos:
            clips.append({
                "id": f"editorial-video-{index}", "assetId": asset_id,
                "timeline": {"startFrame": start, "durationFrames": end-start},
                "source": {"startMicroseconds": 0, "durationMicroseconds": round((end-start)*1e6/fps)},
                "transform": {"originalAudioEnabled": False},
            })
        else:
            page.layers.append(CreativeLayerV1(
                id=f"editorial-still-{index}", kind="image", x=round(page.width*.07), y=round(page.height*.28),
                width=round(page.width*.86), height=round(page.height*.6), zIndex=1,
                properties={**style, "assetId": asset_id},
            ))
        if index < len(copy):
            page.layers.append(CreativeLayerV1(
                id=f"editorial-copy-{index}", kind="text", x=round(page.width*.07), y=round(page.height*.07),
                width=round(page.width*.86), height=round(page.height*.17), zIndex=2,
                properties={**style, "text": copy[index], "fontSize": min(56, round(page.width*.075)), "color": "#FFFFFF"},
            ))
    if clips:
        from ...domain.studios.contracts import VideoTrackV1

        identifiers = {track.id for track in timeline.tracks}
        base = "editorial-source"
        track_id = next(identifier for identifier in [base, *(f"{base}-{i}" for i in range(1, 17))]
                        if identifier not in identifiers)
        timeline.tracks.append(VideoTrackV1(id=track_id, name="Material autorizado", clips=clips))
    return bool(page.layers or clips)


def _input_receipt(comp, roles, style_format, cards):
    page = comp.pages[0]
    total = comp.media_timeline.duration_frames
    boundaries = {0, total}
    for layer in page.layers:
        if layer.visible:
            style = _style(layer)
            boundaries.update({style.start_frame, style.start_frame+(style.duration_frames or total)})
    for track in comp.media_timeline.tracks:
        if track.kind not in {"video", "overlay"}:
            continue
        for clip in track.clips:
            if clip.enabled:
                boundaries.update({clip.timeline.start_frame, clip.timeline.start_frame+clip.timeline.duration_frames})
    beats = []
    values = sorted(boundaries)
    for index, (start, end) in enumerate(zip(values, values[1:], strict=False)):
        if end <= start:
            continue
        beats.append({"startFrame": start, "endFrame": end, "intent":
                      "establish_subject" if index == 0 else "show_change_or_consequence"})
    return {"format": style_format, "beats": beats[:48], "cardIds": [card["id"] for card in cards],
            "materialRoles": sorted(set(roles.values()))}


def plan(db, record, contract, request, materials, baseline):
    if contract.content_type != "video":
        raise ValueError("editorial_experiment_video_required")
    comp = contract.composition.model_copy(deep=True)
    page, timeline = comp.pages[0], comp.media_timeline
    references = {ref.id: ref.media_type for ref in contract.assets}
    roles = materials["roles"]
    flags = _flags(comp, roles, references)
    exp = request.editorial
    caps = timeline_ffmpeg.capability()
    kb = knowledge()
    objective = exp.objective or request.instruction
    kind = _scene_format(exp.format, set(roles.values()), flags, objective)
    cards = [card for card in kb["cards"] if kind in card["formats"] and _support(card, flags)]
    used_cards = [] if exp.variant == "baseline" else cards
    chosen = {card["id"] for card in used_cards}
    gaps = []
    if materials["status"] != "bound":
        gaps.append({"code": "kit_" + materials["status"], "detail": "Vincule um kit válido para selecionar pela função do material."})
    if materials["notImported"]:
        gaps.append({"code": "kit_assets_not_imported", "assetIds": materials["notImported"]})
    if not caps.get("available"):
        gaps.append({"code": "local_renderer_unavailable"})
    if kind == "interface" and not flags["interface"]:
        gaps.append({"code": "interface_material_missing"})
    if kind in {"hybrid", "footage"} and not flags["video"]:
        gaps.append({"code": "footage_material_missing"})
    if not flags["audio"]:
        gaps.append({"code": "no_audio_track", "detail": "Nenhum áudio será gerado ou acrescentado."})
    if not flags["usedVisual"] and not flags["image"]:
        gaps.append({"code": "visual_not_placed", "detail": "Posicione o material de vídeo autorizado na timeline."})
    if not flags["cutout"] and kind in {"motion", "hybrid"}:
        gaps.append({"code": "aligned_cutout_missing", "detail": "Oclusão em profundidade indisponível sem recorte alinhado."})
    receipt = {
        "variant": exp.variant, "format": kind, "knowledgeVersion": kb["version"],
        "knowledgeDigest": timeline_editor.digest(kb),
        "cardIds": [card["id"] for card in used_cards],
        "capabilities": {"renderer": caps.get("provider", "ffmpeg.timeline-v1"), "available": caps.get("available", False),
                         "operations": list(OPERATIONS), "externalBudgetUsd": 0},
        "materialSnapshot": materials, "materialDigest": fingerprint(materials),
        "gaps": gaps, "receipts": [], "humanVerdict": "inconclusive",
        "preview": {"status": "not_requested"}, "repairCount": 0,
    }
    if exp.variant == "baseline":
        receipt["receipts"].append({"stage": "baseline", "status": "complete", "source": "current_deterministic_rules"})
        return baseline(), receipt
    assembled = _seed(db, record, comp, roles, references, request.instruction, kind)
    if assembled:
        flags = _flags(comp, roles, references)
        used_cards = [card for card in kb["cards"] if kind in card["formats"] and _support(card, flags)]
        receipt["cardIds"] = [card["id"] for card in used_cards]
        chosen = set(receipt["cardIds"])
        receipt["gaps"] = [item for item in receipt["gaps"] if item["code"] != "visual_not_placed"]
    elif not flags["usedVisual"] and flags["video"]:
        receipt["gaps"].append({"code": "usable_visual_duration_missing",
                                "detail": "O conjunto não preenche a duração ou não oferece a mídia requerida."})
    receipt["receipts"].append({
        "stage": "direction", "status": "complete", "objective": objective[:240],
        "reason": "Explicit format" if exp.format != "auto" else "Format routed by authorized media and objective",
        **_input_receipt(comp, roles, kind, used_cards),
    })
    fps = timeline.frame_rate.numerator / timeline.frame_rate.denominator
    initial_hash = timeline_editor.digest(comp.model_dump(mode="json", by_alias=True))
    if "readable-type" in chosen:
        _readable(comp, {layer.id for layer in page.layers if layer.visible})
        _fit_proof_images(db, record, comp, kind, roles)
        _protect_reading_plane(comp, kind)
    images = [layer for layer in page.layers if layer.kind == "image" and not layer.locked and layer.visible
              and roles.get(_style(layer).asset_id) in {"product_cutout", "state_after"}]
    text = [layer for layer in page.layers if layer.kind == "text" and not layer.locked and layer.visible]
    if "reveal-relationship" in chosen:
        for layer in images:
            _animate(layer, fps, timeline.duration_frames, exp.variant, roles.get(_style(layer).asset_id))
    if exp.variant == "orchestrated":
        # Keep semantic motion on the product when an asset can carry it. Where
        # footage/interface already carries the action, only guide the titles.
        for layer in text:
            _animate(layer, fps, timeline.duration_frames, exp.variant)
        receipt["receipts"].append({"stage": "design_motion", "status": "complete",
                                    "imageLayerIds": [layer.id for layer in images if "reveal-relationship" in chosen],
                                    "stableSubject": kind in {"interface", "footage"},
                                    "previewType": "canonical_motion_animatic"})
        receipt["receipts"].append({"stage": "edit_sound", "status": "complete",
                                    "preservedAudioTracks": [track.id for track in timeline.tracks if track.kind == "audio"],
                                    "durationFrames": timeline.duration_frames, "synthesizedAudio": False})
    final = comp.model_dump(mode="json", by_alias=True)
    if not assembled and initial_hash == timeline_editor.digest(final):
        return AgentOutput(rationale="Sem ajuste adicional aplicável aos materiais e às operações atuais."), receipt
    return AgentOutput.model_validate({
        "commands": [{"id": "composition.replace", "params": {"composition": final}}],
        "rationale": "Proposta local orientada pela função do material. Revisão humana de compreensão permanece em aberto.",
    }), receipt


def repair(comp, findings):
    repairs = {item["layerId"] for item in findings if item.get("layerId")}
    if not repairs:
        return None
    candidate = comp.model_copy(deep=True)
    page = candidate.pages[0]
    for layer in page.layers:
        if layer.id in repairs and not layer.locked:
            # A narrow box can force the first layout pass below the phone
            # floor. Expand only the offending box on the second pass.
            pad = min(20, round(page.width * .04))
            layer.width = max(layer.width, page.width - layer.x - pad)
            layer.height = max(layer.height, min(page.height*.2, page.height-layer.y-pad))
    _readable(candidate, repairs)
    if candidate == comp:
        return None
    return CreativeCompositionV1.model_validate(candidate.model_dump(mode="json", by_alias=True))


def verify_bound_materials(db, record, contract, expected):
    if fingerprint(snapshot_materials(db, record, contract)) != expected:
        raise ValueError("editorial_material_snapshot_conflict")
