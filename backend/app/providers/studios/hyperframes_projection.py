# ruff: noqa: E501
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path

from ...domain.studios.contracts import CreativeDocumentV1, VideoRenderRequestV1
from ...domain.studios.motion import MotionGraphProjectionV1

# HTML/CSS/JS is emitted as a single auditable projection; wrapping it changes output bytes.

SAFE_COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\([0-9., %]+\)|[a-zA-Z]{1,24})$")


def _seconds(frames: int, numerator: int, denominator: int) -> float:
    return frames * denominator / numerator


def _number(value: object, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _color(value: object, default: str) -> str:
    candidate = str(value or "")
    return candidate if SAFE_COLOR.fullmatch(candidate) else default


def _source(asset_id: str, manifest: dict[str, str]) -> str:
    if asset_id not in manifest:
        raise ValueError(f"hyperframes_asset_not_materialized:{asset_id}")
    return html.escape(manifest[asset_id], quote=True)


def _text_content(text: str, spans: list[dict], reveal_words: bool) -> str:
    """Render typed ranges without turning model output into markup."""
    word_index = 0

    def fragment(value: str) -> str:
        nonlocal word_index
        if not reveal_words:
            return html.escape(value)
        parts = []
        for token in re.findall(r"\S+|\s+", value):
            escaped = html.escape(token)
            if token.isspace():
                parts.append(escaped)
            else:
                parts.append(f'<span data-res-word="{word_index}">{escaped}</span>')
                word_index += 1
        return "".join(parts)

    def emphasized(value: str, span_id: str, style: str) -> str:
        nonlocal word_index
        parts = []
        for token in re.findall(r"\S+|\s+", value):
            escaped = html.escape(token)
            if token.isspace():
                parts.append(escaped)
                continue
            reveal_attr = f' data-res-word="{word_index}"' if reveal_words else ""
            if reveal_words:
                word_index += 1
            parts.append(
                '<span data-res-text-span="'
                + html.escape(span_id, quote=True)
                + '"'
                + reveal_attr
                + ' style="display:inline-block;transform-origin:50% 60%;">'
                + escaped
                + "</span>"
            )
        return '<span style="' + style + '">' + "".join(parts) + "</span>"

    rendered = []
    cursor = 0
    for span in spans:
        start, end = int(span["start"]), int(span["end"])
        if start < cursor or end <= start or end > len(text):
            raise ValueError("hyperframes_text_span_invalid")
        while start > cursor and text[start - 1].isalnum() and text[start].isalnum():
            start -= 1
        while end < len(text) and text[end - 1].isalnum() and text[end].isalnum():
            end += 1
        if start < cursor:
            raise ValueError("hyperframes_text_span_word_overlap")
        rendered.append(fragment(text[cursor:start]))
        style = ""
        if span.get("color"):
            style += "color:" + _color(span["color"], "#ffffff") + ";"
        if span.get("fontWeight") is not None:
            style += f"font-weight:{int(_number(span['fontWeight'], 700, 100, 900))};"
        rendered.append(emphasized(text[start:end], str(span["id"]), style))
        cursor = end
    rendered.append(fragment(text[cursor:]))
    return "".join(rendered)


def _layer(layer, manifest: dict[str, str]) -> tuple[str, list[str]]:
    if not layer.visible:
        return "", []
    props = layer.properties or {}
    font_id = props.get("fontAssetId")
    family = (
        "res-font-" + hashlib.sha256(str(font_id).encode()).hexdigest()[:16]
        if font_id
        else "Arial,Helvetica,sans-serif"
    )
    base = (
        f"position:absolute;left:{layer.x}px;top:{layer.y}px;width:{layer.width}px;"
        f"height:{layer.height}px;opacity:{layer.opacity};z-index:{layer.z_index};"
        f"transform:rotate({layer.rotation}deg);overflow:hidden;"
    )
    filters = []
    shadow = props.get("editorialShadow")
    if shadow:
        color = _color(shadow.get("color"), "#000000")
        opacity = _number(shadow.get("opacity"), 0.18, 0, 1)
        # An SVG filter uses an explicit opacity; no generated CSS or scripts.
        if len(color) == 7 and color.startswith("#"):
            rgb = ",".join(str(int(color[i : i + 2], 16)) for i in (1, 3, 5))
            filters.append(
                f"drop-shadow({_number(shadow.get('x'), 0, -100, 100)}px "
                f"{_number(shadow.get('y'), 6, -100, 100)}px "
                f"{_number(shadow.get('blur'), 12, 0, 100)}px rgba({rgb},{opacity}))"
            )
    depth = props.get("editorialDepth") or {}
    depth_blur = _number(depth.get("blurPx"), 0, 0, 40)
    if depth_blur:
        filters.append(f"blur({depth_blur}px)")
    for effect in props.get("editorialEffects") or []:
        kind = effect.get("kind")
        amount = _number(effect.get("amount"), 0, -360, 360)
        if kind == "blur":
            filters.append(f"blur({_number(amount, 0, 0, 40)}px)")
        elif kind in {"brightness", "contrast", "saturate"}:
            filters.append(f"{kind}({_number(amount, 1, 0, 4)})")
        elif kind == "hue_rotate":
            filters.append(f"hue-rotate({_number(amount, 0, -360, 360)}deg)")
        elif kind == "drop_shadow":
            color = _color(effect.get("color"), "#000000")
            opacity = _number(effect.get("opacity"), 1, 0, 1)
            rgb = ",".join(str(int(color[i : i + 2], 16)) for i in (1, 3, 5))
            filters.append(
                f"drop-shadow({_number(effect.get('x'), 0, -100, 100)}px "
                f"{_number(effect.get('y'), 0, -100, 100)}px "
                f"{_number(amount, 0, 0, 100)}px rgba({rgb},{opacity}))"
            )
    if filters:
        base += "filter:" + " ".join(filters) + ";"
    blend_mode = props.get("editorialBlendMode", "normal")
    if blend_mode in {"multiply", "screen", "overlay", "darken", "lighten"}:
        base += f"mix-blend-mode:{blend_mode};"
    border = props.get("editorialBorder") or {}
    if border.get("width"):
        base += f"box-sizing:border-box;border:{_number(border['width'], 0, 0, 80)}px solid {_color(border.get('color'), '#ffffff')};"
    element_id = html.escape(layer.id, quote=True)
    motion_attrs = (
        f'data-clicko-motion-layer="{element_id}" '
        f'data-clicko-base-rotation="{layer.rotation}" '
        f'data-clicko-base-opacity="{layer.opacity}"'
    )
    mask_id = props.get("maskAssetId")
    if mask_id:
        # JSON string quoting plus HTML escaping prevents a path escaping the CSS url.
        source = _source(str(mask_id), manifest)
        base += f"mask-image:url(&quot;{source}&quot;);mask-size:100% 100%;mask-mode:luminance;"
    if layer.kind == "group":
        return f'<div id="{element_id}" {motion_attrs} style="{base}overflow:visible"></div>', []
    if props.get("editorialPath"):
        from ...domain.studios.contextual_editing_v2 import EditorialPointV2

        geometry = props["editorialPath"]
        points = [EditorialPointV2.model_validate(p) for p in geometry["points"]]
        coordinates = " ".join(f"{p.x},{p.y}" for p in points)
        stroke = _number(geometry.get("strokeWidth"), 4, 0.1, 100)
        reveal = props.get("editorialTiming", {}).get("reveal") == "path"
        dash = 'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"' if reveal else ""
        tag = "polyline"
        geometry_attr = f'points="{coordinates}"'
        if geometry.get("mode") == "quadratic":
            if len(points) != 3:
                raise ValueError("hyperframes_quadratic_requires_three_points")
            a, b, c = points
            tag = "path"
            geometry_attr = f'd="M {a.x} {a.y} Q {b.x} {b.y} {c.x} {c.y}"'
        return (
            f'<svg id="{element_id}" {motion_attrs} style="{base}" viewBox="0 0 {layer.width} {layer.height}">'
            f'<{tag} {geometry_attr} fill="none" stroke="{_color(props.get("color"), "#ffffff")}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" {dash}/></svg>'
        ), []
    if layer.kind == "text":
        align = str(props.get("textAlign") or props.get("align") or "left")
        if align not in {"left", "center", "right"}:
            align = "left"
        raw_weight = props.get("fontWeight", 700)
        font_weight = (
            700 if raw_weight == "bold" else 400 if raw_weight == "normal" else int(_number(raw_weight, 700, 100, 900))
        )
        style = (
            f"{base}font-family:{family};"
            f"font-size:{_number(props.get('fontSize'), 48, 8, 800)}px;"
            f"line-height:{_number(props.get('lineHeight'), 1.1, 0.5, 4)};"
            f"letter-spacing:{_number(props.get('letterSpacing'), 0, -10, 50)}px;"
            f"font-weight:{font_weight};"
            f"color:{_color(props.get('color'), '#ffffff')};text-align:{align};"
            "white-space:pre-wrap;overflow-wrap:normal;word-break:normal;hyphens:none;"
        )
        if props.get("editorialCard"):
            style += f"background:{_color(props.get('fill'), '#183343')};border-radius:{_number(props.get('borderRadius'), 16, 0, 512)}px;padding:16px;"
        content = _text_content(
            str(props.get("text") or ""),
            list(props.get("editorialTextSpans") or []),
            props.get("editorialTiming", {}).get("reveal") == "words",
        )
        return f'<div id="{element_id}" {motion_attrs} style="{style}">{content}</div>', []
    if layer.kind == "shape":
        radius = (
            "50%"
            if props.get("shape") == "ellipse"
            else (f"{_number(props.get('borderRadius', props.get('radius')), 0, 0, 8192)}px")
        )
        style = f"{base}background:{_color(props.get('fill'), '#ffffff')};border-radius:{radius}"
        return f'<div id="{element_id}" {motion_attrs} style="{style}"></div>', []
    if layer.kind in {"image", "video"}:
        asset_id = str(props.get("assetId") or "")
        if not asset_id:
            raise ValueError(f"hyperframes_layer_asset_required:{layer.id}")
        fit = str(props.get("objectFit") or "cover")
        if fit not in {"cover", "contain", "fill"}:
            fit = "cover"
        source = _source(asset_id, manifest)
        timing = props.get("editorialTiming", {})
        temporal = ""
        if timing:
            temporal = (
                f' data-start="{timing["startFrame"] / timing["fps"]:.9f}"'
                f' data-duration="{timing["durationFrames"] / timing["fps"]:.9f}"'
                f' data-media-start="{_number(props.get("sourceStartSeconds"), 0, 0, 86400):.9f}"'
            )
        if layer.kind == "image":
            return (
                f'<img id="{element_id}" {motion_attrs} src="{source}" {temporal} style="{base}object-fit:{fit}" />',
                [],
            )
        return (
            f'<video id="{element_id}" {motion_attrs} src="{source}" muted playsinline '
            f'{temporal} style="{base}object-fit:{fit}"></video>',
            [],
        )
    return "", [f"unsupported_layer:{layer.id}:{layer.kind}"]


def _motion_runtime(projection: MotionGraphProjectionV1) -> str:
    payload = projection.model_dump(mode="json", by_alias=True, exclude_none=True)
    encoded = (
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return f"""<script id="clicko-motion-spec" type="application/json">{encoded}</script>
<script>(function(){{'use strict';var spec=JSON.parse(document.getElementById('clicko-motion-spec').textContent);var fps=spec.frameRate.numerator/spec.frameRate.denominator,nodes=spec.nodes||[],transitions=spec.transitions||[],events=spec.audioEvents||[],nodeById={{}},nodeByLayer={{}};nodes.forEach(function(n){{nodeById[n.nodeId]=n;nodeByLayer[n.targetLayerId]=n}});
function bezier(k,p){{var c=k.cubicBezier;if(!c)return p;function b(t,a,b){{var u=1-t;return 3*u*u*t*a+3*u*t*t*b+t*t*t}}var lo=0,hi=1,t=p;for(var i=0;i<16;i++){{var x=b(t,c[0],c[2]);if(x<p)lo=t;else hi=t;t=(lo+hi)/2}}return b(t,c[1],c[3])}}
function ease(k,p){{if(k.easing==='hold')return 0;if(k.easing==='ease_in')return p*p;if(k.easing==='ease_out')return 1-(1-p)*(1-p);if(k.easing==='ease_in_out')return p<.5?2*p*p:1-Math.pow(-2*p+2,2)/2;if(k.easing==='cubic_bezier')return bezier(k,p);return p}}
function valueAt(keys,frame){{if(frame<=keys[0].frame)return keys[0].value;var last=keys[keys.length-1];if(frame>=last.frame)return last.value;for(var i=0;i<keys.length-1;i++){{var a=keys[i],b=keys[i+1];if(frame>=a.frame&&frame<=b.frame){{var p=(frame-a.frame)/(b.frame-a.frame);return a.value+(b.value-a.value)*ease(a,p)}}}}return last.value}}
function transitionState(id,frame){{var opacity=1,clip='none';transitions.forEach(function(t){{if(t.fromLayerId!==id&&t.toLayerId!==id)return;var p=Math.max(0,Math.min(1,(frame-t.startFrame)/(t.endFrameExclusive-t.startFrame)));if(t.kind==='hard_cut'){{if(t.fromLayerId===id&&frame>=t.startFrame)opacity=0;if(t.toLayerId===id&&frame<t.startFrame)opacity=0;return}}if(t.toLayerId===id&&frame<t.startFrame)opacity=0;if(t.fromLayerId===id&&frame>=t.endFrameExclusive)opacity=0;if(frame>=t.startFrame&&frame<t.endFrameExclusive){{if(t.kind==='wipe'&&t.toLayerId===id)clip='inset(0 '+((1-p)*100)+'% 0 0)';else if(t.toLayerId===id)opacity*=p}}}});return{{opacity:opacity,clip:clip}}}}
window.__clickoMotionAudioEventsAt=function(frame){{var rounded=Math.max(0,Math.min(spec.durationFrames-1,Math.round(frame)));return events.filter(function(e){{return e.frame===rounded}})}};
window.__clickoMotionApply=function(seconds){{var frame=Math.max(0,Math.min(spec.durationFrames-1,seconds*fps)),states={{}},ids={{}};spec.tracks.forEach(function(track){{var state=states[track.targetLayerId]||(states[track.targetLayerId]={{}});state[track.propertyPath]=valueAt(track.keyframes,frame);ids[track.targetLayerId]=1}});nodes.forEach(function(n){{ids[n.targetLayerId]=1}});transitions.forEach(function(t){{ids[t.fromLayerId]=1;ids[t.toLayerId]=1}});
function composed(id){{var el=document.getElementById(id),s=states[id]||{{}};return{{tx:s['transform.translateX']||0,ty:s['transform.translateY']||0,sx:s['transform.scaleX']===undefined?1:s['transform.scaleX'],sy:s['transform.scaleY']===undefined?1:s['transform.scaleY'],r:s['transform.rotateDegrees']===undefined?Number(el&&el.dataset.clickoBaseRotation||0):s['transform.rotateDegrees'],o:s['style.opacity']===undefined?Number(el&&el.dataset.clickoBaseOpacity||1):s['style.opacity']}}}}
nodes.forEach(function(n){{if(!n.parentNodeId)return;var parent=nodeById[n.parentNodeId],el=document.getElementById(n.targetLayerId),container=parent&&document.getElementById(parent.targetLayerId);if(el&&container&&el.parentElement!==container)container.appendChild(el)}});
Object.keys(ids).forEach(function(id){{var el=document.getElementById(id),s=states[id]||{{}};if(!el)return;var c=composed(id),tr=transitionState(id,frame),n=nodeByLayer[id];el.style.opacity=String(c.o*tr.opacity);el.style.clipPath=tr.clip;if(s['style.blurPx']!==undefined){{if(el.dataset.resBaseFilter===undefined)el.dataset.resBaseFilter=el.style.filter;el.style.filter=el.dataset.resBaseFilter+' blur('+s['style.blurPx']+'px)'}};if(s['typography.fontSizePx']!==undefined)el.style.fontSize=s['typography.fontSizePx']+'px';if(s['typography.letterSpacingPx']!==undefined)el.style.letterSpacing=s['typography.letterSpacingPx']+'px';if(s['typography.lineHeightRatio']!==undefined)el.style.lineHeight=String(s['typography.lineHeightRatio']);if(s['typography.fontWeight']!==undefined)el.style.fontWeight=String(Math.round(s['typography.fontWeight']));if(n)el.style.transformOrigin=(n.transformOriginX*100)+'% '+(n.transformOriginY*100)+'%';el.style.transform='translate('+c.tx+'px,'+c.ty+'px) scale('+c.sx+','+c.sy+') rotate('+c.r+'deg)'}});var active=window.__clickoMotionAudioEventsAt(frame).map(function(e){{return e.eventId}});document.getElementById('root').dataset.clickoMotionAudioEvents=active.join(',')}};
window.__clickoMotionApply(0)}})();</script>"""


def project_creative_document(
    document: CreativeDocumentV1,
    request: VideoRenderRequestV1,
    manifest: dict[str, str],
    motion_projection: MotionGraphProjectionV1 | None = None,
    *,
    automatic_draft: bool = False,
) -> tuple[str, list[str]]:
    timeline = document.composition.media_timeline
    if timeline is None:
        raise ValueError("video_media_timeline_required")
    pages_by_id = {page.id: page for page in document.composition.pages}
    pages = [pages_by_id[page_id] for page_id in request.page_ids]
    if any(page.width != request.output.width or page.height != request.output.height for page in pages):
        raise ValueError("hyperframes_page_output_dimensions_mismatch")
    numerator = timeline.frame_rate.numerator
    denominator = timeline.frame_rate.denominator
    total_seconds = _seconds(timeline.duration_frames, numerator, denominator)
    if motion_projection is not None:
        if motion_projection.target != "hyperframes":
            raise ValueError("hyperframes_motion_projection_target_mismatch")
        if motion_projection.preview_only and not automatic_draft:
            raise ValueError("hyperframes_motion_projection_requires_review")
        if motion_projection.frame_rate != timeline.frame_rate:
            raise ValueError("hyperframes_motion_projection_frame_rate_mismatch")
        if motion_projection.duration_frames != timeline.duration_frames:
            raise ValueError("hyperframes_motion_projection_duration_mismatch")
        layer_ids = {layer.id for page in pages for layer in page.layers}
        missing_layers = sorted({track.target_layer_id for track in motion_projection.tracks} - layer_ids)
        if missing_layers:
            raise ValueError(f"hyperframes_motion_projection_unknown_layers:{missing_layers}")
    if len(pages) == 1:
        durations = [total_seconds]
    else:
        if any(page.duration_ms is None for page in pages):
            raise ValueError("hyperframes_multi_page_duration_required")
        durations = [page.duration_ms / 1000 for page in pages if page.duration_ms is not None]
        if abs(sum(durations) - total_seconds) > denominator / numerator:
            raise ValueError("hyperframes_page_duration_timeline_mismatch")

    warnings: list[str] = []
    if motion_projection is not None:
        warnings.extend(f"motion:{warning}" for warning in motion_projection.warnings)
    page_nodes: list[str] = []
    page_start = 0.0
    for page, duration in zip(pages, durations, strict=True):
        layer_nodes: list[str] = []
        for layer in sorted(page.layers, key=lambda item: item.z_index):
            node, layer_warnings = _layer(layer, manifest)
            if node:
                layer_nodes.append(node)
            warnings.extend(layer_warnings)
        if automatic_draft:
            # Editorial scene gates live in the shared runtime. A timed ancestor
            # would prevent HyperFrames from seeking the nested video elements.
            page_nodes.append(
                f'<section id="page-{html.escape(page.id, quote=True)}" class="page" '
                f'style="background:{page.background}">{"".join(layer_nodes)}</section>'
            )
        else:
            page_nodes.append(
                f'<section id="page-{html.escape(page.id, quote=True)}" class="clip page" '
                f'data-start="{page_start:.9f}" data-duration="{duration:.9f}" data-track-index="0" '
                f'style="background:{page.background}">{"".join(layer_nodes)}</section>'
            )
        page_start += duration

    media_nodes: list[str] = []
    for track_index, track in enumerate(timeline.tracks, start=1):
        if track.kind in {"video", "audio", "overlay"}:
            for clip in track.clips:
                if not clip.enabled:
                    continue
                start = _seconds(clip.timeline.start_frame, numerator, denominator)
                duration = _seconds(clip.timeline.duration_frames, numerator, denominator)
                media_start = clip.source.start_microseconds / 1_000_000 if clip.source else 0
                common = (
                    f'id="{html.escape(clip.id, quote=True)}" src="{_source(clip.asset_id, manifest)}" '
                    f'data-start="{start:.9f}" data-duration="{duration:.9f}" '
                    f'data-media-start="{media_start:.9f}"'
                )
                if track.kind in {"video", "overlay"}:
                    media_nodes.append(
                        f'<video {common} data-track-index="{track_index}" muted playsinline '
                        'style="position:absolute;inset:0;'
                        'width:100%;height:100%;object-fit:cover"></video>'
                    )
                    if track.kind == "video" and not track.muted and request.output.audio_codec != "none":
                        media_nodes.append(
                            f'<audio {common} data-track-index="{track_index + 100}" data-volume="1"></audio>'
                        )
                elif request.output.audio_codec != "none":
                    volume = math.pow(10, clip.gain_db / 20)
                    media_nodes.append(
                        f'<audio {common} data-track-index="{track_index}" data-volume="{volume:.6f}"></audio>'
                    )
        elif track.kind == "caption":
            for cue in track.cues:
                caption_family = (
                    "res-font-" + hashlib.sha256(cue.style.font_asset_id.encode()).hexdigest()[:16]
                    if cue.style.font_asset_id
                    else "Arial,sans-serif"
                )
                start = _seconds(cue.timeline.start_frame, numerator, denominator)
                duration = _seconds(cue.timeline.duration_frames, numerator, denominator)
                media_nodes.append(
                    f'<div id="{html.escape(cue.id, quote=True)}" class="clip caption" '
                    f'data-start="{start:.9f}" data-duration="{duration:.9f}" '
                    f'data-track-index="{track_index}" '
                    f'style="font-family:{caption_family};color:{_color(cue.style.color, "#ffffff")};'
                    'background:rgba(0,0,0,0.72)">'
                    f"{html.escape(cue.text)}</div>"
                )
        elif track.kind in {"mask", "marker"}:
            warnings.append(f"hyperframes_unsupported_track:{track.id}:{track.kind}")

    composition_id = html.escape(document.document_id, quote=True)
    fps = f"{numerator}/{denominator}" if denominator != 1 else str(numerator)
    output = request.output
    font_ids = {layer.properties.get("fontAssetId") for page in pages for layer in page.layers} - {None, ""}
    font_ids.update(
        c.style.font_asset_id for t in timeline.tracks if t.kind == "caption" for c in t.cues if c.style.font_asset_id
    )
    font_css = "".join(
        "@font-face{font-family:res-font-"
        + hashlib.sha256(str(font_id).encode()).hexdigest()[:16]
        + ';src:url("'
        + _source(str(font_id), manifest)
        + '");font-display:block;}'
        for font_id in sorted(font_ids)
    )
    editorial_spec = [
        {
            "id": layer.id,
            "timing": layer.properties["editorialTiming"],
            "text": layer.kind == "text",
            "match": layer.properties.get("editorialMatch"),
            "connector": layer.properties.get("editorialConnector"),
            "semanticId": layer.name,
            "contentIdentity": layer.properties.get("editorialContentIdentity"),
            "contentReferenceId": layer.properties.get("editorialContentReferenceId"),
            "contentPartId": layer.properties.get("editorialContentPartId"),
            "visualRole": layer.properties.get("editorialVisualRole"),
            "regionOfInterest": layer.properties.get("editorialRegionOfInterest"),
            "cropIntentional": layer.properties.get("editorialCropIntentional", False),
            "textSpans": layer.properties.get("editorialTextSpans", []),
            "auditFrames": layer.properties.get("editorialAuditFrames", []),
            "fitText": layer.properties.get("editorialTextFit", False),
            "minimumFontSize": page.width * 16 / 300,
        }
        for page in pages
        for layer in page.layers
        if "editorialTiming" in layer.properties
    ]
    editorial_json = json.dumps(editorial_spec, ensure_ascii=True).replace("<", "\\u003c")
    editorial_runtime = (
        (
            '<script id="res-editorial-spec" type="application/json">'
            + editorial_json
            + "</script><script>"
            + Path(__file__).with_name("editorial_runtime.js").read_text(encoding="utf-8")
            + "</script>"
        )
        if editorial_spec
        else ""
    )
    projected = f"""<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'self' data: blob:; connect-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'" />
<meta name="viewport" content="width={output.width},height={output.height}" />
<style>*{{box-sizing:border-box;margin:0;padding:0}}html,body,#root{{width:{output.width}px;height:{output.height}px;overflow:hidden;background:#000}}#root{{position:relative}}.clip{{visibility:hidden}}.page{{position:absolute;inset:0;overflow:hidden}}.caption{{position:absolute;left:7%;right:7%;bottom:8%;padding:18px 24px;border-radius:16px;text-align:center;font:700 48px/1.12 Arial,sans-serif;z-index:9000}}</style></head>
<body><main id="root" data-composition-id="{composition_id}" data-start="0" data-duration="{total_seconds:.9f}" data-width="{output.width}" data-height="{output.height}" data-fps="{fps}">{"".join(page_nodes)}{"".join(media_nodes)}</main>
{_motion_runtime(motion_projection) if motion_projection is not None else ""}
<script>(function(){{var t=0,p=true,d={total_seconds:.9f};function s(v){{if(typeof v==='number')t=Math.max(0,Math.min(d,v));if(window.__clickoMotionApply)window.__clickoMotionApply(t);return t}}window.__timelines=window.__timelines||{{}};window.__timelines['{composition_id}']={{play:function(){{p=false}},pause:function(){{p=true}},seek:s,totalTime:s,time:function(){{return t}},duration:function(){{return d}},add:function(){{}},paused:function(v){{if(typeof v==='boolean')p=v;return p}},timeScale:function(){{}},set:function(){{}},getChildren:function(){{return[]}}}};if(window.__clickoMotionApply)window.__clickoMotionApply(0)}})();</script></body></html>"""
    projected = projected.replace("<style>*", "<style>" + font_css + "*")
    projected = projected.replace("<script>(function(){var t=0", editorial_runtime + "<script>(function(){var t=0")
    projected = projected.replace(
        "if(window.__clickoMotionApply)window.__clickoMotionApply(t);return t",
        "if(window.__clickoMotionApply)window.__clickoMotionApply(t);if(window.__resEditorialApply)window.__resEditorialApply(t);return t",
    )
    return projected, warnings
