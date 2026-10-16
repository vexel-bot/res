import {Circle, Img, Line, makeScene2D, Node, Rect, Txt} from '@motion-canvas/2d';

type Key = {frame: number; value: number; easing: string; cubicBezier?: number[]};
type Track = {targetLayerId: string; propertyPath: string; keyframes: Key[]};
type Transition = {kind: 'hard_cut' | 'dissolve'; fromLayerId: string; toLayerId: string; startFrame: number; endFrameExclusive: number};
type Layer = {id: string; name?: string; kind: 'text' | 'shape' | 'image' | 'group'; x: number; y: number; width: number; height: number; rotation: number; opacity: number; zIndex: number; visible: boolean; properties: Record<string, unknown>};
type Manifest = {schemaVersion: string; width: number; height: number; durationFrames: number; background: string; layers: Layer[]; tracks: Track[]; transitions: Transition[];
  nodes: {nodeId: string; targetLayerId: string; parentNodeId?: string}[]; assets: Record<string, string>};

declare global {interface Window {__resManifest?: Manifest; __resLayoutDiagnostics?: Array<Record<string, unknown>>;
  __resGeometrySamples?: Array<Record<string, unknown>>;}}

function bezier(key: Key, progress: number): number {
  const c = key.cubicBezier;
  if (!c) return progress;
  const curve = (t: number, a: number, b: number) => 3 * (1 - t) ** 2 * t * a + 3 * (1 - t) * t ** 2 * b + t ** 3;
  let low = 0, high = 1;
  for (let i = 0; i < 18; i++) {const mid = (low + high) / 2; if (curve(mid, c[0], c[2]) < progress) low = mid; else high = mid;}
  return curve((low + high) / 2, c[1], c[3]);
}
function ease(key: Key, p: number): number {
  switch (key.easing) {
    case 'hold': return 0;
    case 'ease_in': return p * p;
    case 'ease_out': return 1 - (1 - p) ** 2;
    case 'ease_in_out': return p < 0.5 ? 2 * p * p : 1 - (-2 * p + 2) ** 2 / 2;
    case 'cubic_bezier': return bezier(key, p);
    default: return p;
  }
}
function valueAt(keys: Key[], frame: number): number {
  if (frame <= keys[0].frame) return keys[0].value;
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1];
    if (frame <= b.frame) {const p = (frame - a.frame) / (b.frame - a.frame); return a.value + (b.value - a.value) * ease(a, p);}
  }
  return keys[keys.length - 1].value;
}
function color(raw: unknown, fallback: string): string {return typeof raw === 'string' && /^#[0-9a-fA-F]{6}$/.test(raw) ? raw : fallback;}
function number(raw: unknown, fallback: number): number {return typeof raw === 'number' && Number.isFinite(raw) ? raw : fallback;}

export default makeScene2D(function* (view) {
  const spec = window.__resManifest;
  if (!spec || spec.schemaVersion !== 'res.motion-canvas-composition.v1') throw new Error('res_manifest_missing');
  window.__resLayoutDiagnostics = [];
  window.__resGeometrySamples = [];
  const nodes = new Map<string, Node>();
  const positions = new Map<string, {x: number; y: number}>();
  const parents = new Map<string, string>();
  const nodeIdToLayer = new Map(spec.nodes.map(item => [item.nodeId, item.targetLayerId]));
  const layers = [...spec.layers].sort((a, b) => a.zIndex - b.zIndex);
  for (const layer of layers) {
    const p = layer.properties;
    const parentNode = spec.nodes.find(item => item.targetLayerId === layer.id);
    const parentId = typeof p.parentId === 'string' ? p.parentId : parentNode?.parentNodeId ? nodeIdToLayer.get(parentNode.parentNodeId) : undefined;
    if (parentId) parents.set(layer.id, parentId);
    const parent = parentId ? layers.find(item => item.id === parentId) : undefined;
    const position = {x: layer.x + layer.width / 2 - (parent?.width ?? spec.width) / 2,
      y: layer.y + layer.height / 2 - (parent?.height ?? spec.height) / 2};
    positions.set(layer.id, position);
    const base = {x: position.x, y: position.y,
      rotation: layer.rotation, opacity: layer.visible ? layer.opacity : 0};
    let node: Node;
    if (layer.kind === 'text') {
      const text = String(p.text ?? '');
      const family = String(p.fontFamily ?? 'Arial');
      const weight = p.fontWeight === 'bold' ? 700 : p.fontWeight === 'normal' ? 400 : number(p.fontWeight, 700);
      const authoredSize = number(p.fontSize, 48);
      const lineHeight = number(p.lineHeight, 1.1);
      const letterSpacing = number(p.letterSpacing, 0);
      const oneLineBox = !text.includes('\n') && layer.height < 2 * authoredSize * lineHeight;
      let effectiveSize = authoredSize;
      let measuredWidth: number | null = null;
      if (oneLineBox) {
        const context = document.createElement('canvas').getContext('2d');
        if (!context) throw new Error('res_text_measurement_unavailable');
        context.font = `${weight} ${authoredSize}px "${family.replaceAll('"', '')}"`;
        measuredWidth = context.measureText(text).width + Math.max(0, text.length - 1) * letterSpacing;
        if (measuredWidth > layer.width * 0.96) {
          effectiveSize = Math.max(12, authoredSize * layer.width * 0.96 / measuredWidth);
        }
      }
      window.__resLayoutDiagnostics.push({layerId: layer.id, oneLineBox, boxWidth: layer.width,
        authoredFontSize: authoredSize, effectiveFontSize: effectiveSize, measuredWidth});
      node = new Txt({...base, text: String(p.text ?? ''), width: layer.width, height: layer.height,
        fontFamily: family, fontSize: effectiveSize,
        fontWeight: weight,
        lineHeight: effectiveSize * lineHeight, letterSpacing,
        fill: color(p.color, '#ffffff'), textAlign: p.textAlign === 'center' || p.textAlign === 'right' ? p.textAlign : 'left',
        textWrap: !oneLineBox});
    } else if (layer.kind === 'image') {
      const assetId = String(p.assetId ?? '');
      if (!spec.assets[assetId]) throw new Error(`res_asset_missing:${assetId}`);
      const naturalWidth = number(p.naturalWidth, 0);
      const naturalHeight = number(p.naturalHeight, 0);
      if (naturalWidth <= 0 || naturalHeight <= 0) throw new Error(`res_image_dimensions_missing:${assetId}`);
      const fit = String(p.objectFit ?? 'cover');
      if (!['contain', 'cover', 'fill'].includes(fit)) throw new Error(`res_image_fit_unsupported:${assetId}`);
      const scale = fit === 'cover'
        ? Math.max(layer.width / naturalWidth, layer.height / naturalHeight)
        : Math.min(layer.width / naturalWidth, layer.height / naturalHeight);
      const imageWidth = fit === 'fill' ? layer.width : naturalWidth * scale;
      const imageHeight = fit === 'fill' ? layer.height : naturalHeight * scale;
      const frame = new Rect({...base, width: layer.width, height: layer.height, clip: true});
      frame.add(new Img({x: 0, y: 0, width: imageWidth, height: imageHeight, src: spec.assets[assetId]}));
      node = frame;
    } else if (layer.kind === 'shape' && p.editorialPath) {
      const path = p.editorialPath as {points: {x: number; y: number}[]; strokeWidth?: number};
      node = new Line({...base, points: path.points.map(pt => [pt.x - layer.width / 2, pt.y - layer.height / 2]),
        stroke: color(p.color, '#ffffff'), lineWidth: number(path.strokeWidth, 4)});
    } else if (layer.kind === 'shape' && p.shape === 'ellipse') {
      node = new Circle({...base, width: layer.width, height: layer.height, fill: color(p.fill, '#ffffff')});
    } else if (layer.kind === 'shape') {
      node = new Rect({...base, width: layer.width, height: layer.height, fill: color(p.fill, '#ffffff'), radius: number(p.borderRadius, 0)});
    } else {
      node = new Node(base);
    }
    nodes.set(layer.id, node);
  }
  for (const layer of layers) {
    const parentId = parents.get(layer.id);
    const parent = parentId ? nodes.get(parentId) : undefined;
    if (parentId && !parent) throw new Error(`res_parent_missing:${parentId}`);
    (parent ?? view).add(nodes.get(layer.id)!);
  }
  for (let frame = 0; frame < spec.durationFrames; frame++) {
    const values = new Map<string, Record<string, number>>();
    for (const track of spec.tracks) {
      const target = values.get(track.targetLayerId) ?? {};
      target[track.propertyPath] = valueAt(track.keyframes, frame);
      values.set(track.targetLayerId, target);
    }
    for (const layer of layers) {
      const node = nodes.get(layer.id)!;
      const v = values.get(layer.id) ?? {};
      const timing = layer.properties.editorialTiming as {startFrame: number; durationFrames: number; reveal?: string; revealFrames?: number} | undefined;
      const active = !timing || (frame >= timing.startFrame && frame < timing.startFrame + timing.durationFrames);
      let transitionOpacity = 1;
      for (const transition of spec.transitions) {
        if (transition.fromLayerId === layer.id) {
          if (transition.kind === 'hard_cut' && frame >= transition.startFrame) transitionOpacity = 0;
          if (transition.kind === 'dissolve' && frame >= transition.startFrame) transitionOpacity *= frame >= transition.endFrameExclusive ? 0 : 1 - (frame - transition.startFrame) / (transition.endFrameExclusive - transition.startFrame);
        }
        if (transition.toLayerId === layer.id) {
          if (frame < transition.startFrame) transitionOpacity = 0;
          else if (transition.kind === 'dissolve' && frame < transition.endFrameExclusive) transitionOpacity *= (frame - transition.startFrame) / (transition.endFrameExclusive - transition.startFrame);
        }
      }
      node.position.x(positions.get(layer.id)!.x + (v['position.x'] ?? 0));
      node.position.y(positions.get(layer.id)!.y + (v['position.y'] ?? 0));
      node.scale.x(v['scale.x'] ?? 1);
      node.scale.y(v['scale.y'] ?? 1);
      node.rotation(v['rotation.degrees'] ?? layer.rotation);
      node.opacity(active && layer.visible ? (v.opacity ?? layer.opacity) * transitionOpacity : 0);
      if (timing && timing.reveal === 'words' && node instanceof Txt) {
        const tokens = String(layer.properties.text ?? '').split(/(\s+)/u);
        const wordCount = tokens.filter(token => token !== '' && !/^\s+$/u.test(token)).length;
        const elapsed = Math.max(0, frame - timing.startFrame);
        const visibleWords = Math.min(wordCount, Math.max(1, Math.ceil(wordCount * elapsed / (timing.revealFrames ?? 12))));
        let count = 0;
        node.text(tokens.filter(token => /^\s+$/u.test(token) ? count > 0 && count < visibleWords : ++count <= visibleWords).join('').trimEnd());
      }
      if (timing && timing.reveal === 'path' && node instanceof Line) {
        node.end(Math.max(0, Math.min(1, (frame - timing.startFrame) / (timing.revealFrames ?? 12))));
      }
      if (v['filters.blurPx'] !== undefined) node.filters.blur(v['filters.blurPx']);
      if (node instanceof Txt) {
        if (v['fontSize.px'] !== undefined) node.fontSize(v['fontSize.px']);
        if (v.fontWeight !== undefined) node.fontWeight(v.fontWeight);
        if (v['letterSpacing.px'] !== undefined) node.letterSpacing(v['letterSpacing.px']);
        if (v['lineHeight.ratio'] !== undefined) node.lineHeight(node.fontSize() * v['lineHeight.ratio']);
      }
    }
    const elements = layers.map(layer => {
      const node = nodes.get(layer.id)!;
      const matrix = node.localToWorld();
      const corners = [
        [-layer.width / 2, -layer.height / 2], [layer.width / 2, -layer.height / 2],
        [layer.width / 2, layer.height / 2], [-layer.width / 2, layer.height / 2],
      ].map(([x, y]) => new DOMPoint(x, y).matrixTransform(matrix));
      // Motion Canvas's view transform already maps local coordinates to
      // canvas pixels. Adding half the canvas size here would double-offset
      // every observed bound and make the auditor inspect the wrong region.
      const xs = corners.map(point => point.x);
      const ys = corners.map(point => point.y);
      const left = Math.min(...xs), top = Math.min(...ys);
      const timing = layer.properties.editorialTiming as {startFrame: number; durationFrames: number} | undefined;
      const present = !timing || (frame >= timing.startFrame && frame < timing.startFrame + timing.durationFrames);
      const opacity = node.absoluteOpacity();
      return {semanticId: layer.name || layer.id, layerId: layer.id, present,
        visible: present && opacity > 0.01, opacity: Math.round(opacity * 1000) / 1000,
        bounds: {x: Math.round(left * 1000) / 1000, y: Math.round(top * 1000) / 1000,
          width: Math.round((Math.max(...xs) - left) * 1000) / 1000,
          height: Math.round((Math.max(...ys) - top) * 1000) / 1000}};
    });
    window.__resGeometrySamples.push({frame, elements});
    yield;
  }
});
