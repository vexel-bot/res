import React from "react";
import { APIError, apiFetch } from "../api";
import type { StudioDocumentRecord } from "../api/productApi";
import "./editor-inspection.css";

type Keyframe = { frame: number; value: number; curve: [number, number, number, number] };
type RecipeTrack = { targetId: string; property: "x" | "y" | "z" | "rotation" | "scale_x" | "scale_y" | "opacity" | "stroke_progress";
  keyframes: Keyframe[] };
type Recipe = { id: string; sceneId: string; technique: string; targetIds: string[]; startFrame: number;
  endFrameExclusive: number; parameters: { pivot: [number, number]; tracks: RecipeTrack[]; parentTargetId?: string;
    temporalSamples: number; shutterDegrees: number; temporalExposure?: { sampling: string } } };
type Action = { kind: "set_recipe_keyframe"; sceneId: string; recipeId: string; targetId: string;
  property: RecipeTrack["property"]; keyframe: Keyframe }
  | { kind: "set_recipe_pivot"; sceneId: string; recipeId: string; pivot: [number, number] }
  | { kind: "set_recipe_parent"; sceneId: string; recipeId: string; parentTargetId: string; coordinateSpace: "local" }
  | { kind: "undo_command"; commandId: string };
type Receipt = { commandId: string; documentRevision: number; planRevision: number; documentDigest: string;
  previousDocumentRevision: number; pending: string[] };
type Inspection = { document: StudioDocumentRecord; renderer: string; planId: string; planRevision: number; documentDigest: string;
  graphDigest: string; frame: number; durationFrames: number; layerScenes: Record<string, string>;
  frameRate: { numerator: number; denominator: number };
  nodes: { nodeId: string; targetLayerId: string; parentNodeId?: string; transformOriginX: number; transformOriginY: number }[];
  tracks: { trackId: string; targetLayerId: string; property: string; unit: string; evaluatedLocalValue: number;
    keyframes: { frame: number; value: number; easing: string; cubicBezier?: number[] }[] }[];
  scenes: { sceneId: string; purpose: string; startFrame: number; durationFrames: number }[];
  recipes: Recipe[]; parentCandidates: { sceneId: string; targetId: string }[];
  versions: Record<string, string>; hashes: Record<string, string>; history: Receipt[] };

function errorMessage(error: unknown) {
  if (error instanceof APIError && error.status === 409) return "O documento ou plano mudou. Atualize a inspeção antes de reaplicar o ajuste.";
  return error instanceof Error ? `Ajuste não aplicado: ${error.message}` : "Não foi possível carregar a inspeção.";
}

export function EditorInspectionPanel({ document, frame, active, disabled, onSeek, onChanged, onRender, render, playbackRef, onPreviewPlay }: {
  document: StudioDocumentRecord; frame: number; active: boolean; disabled: boolean;
  onSeek: (frame: number) => void; onChanged: () => Promise<unknown>;
  onRender: (document: StudioDocumentRecord, planId: string) => Promise<unknown>;
  playbackRef?: React.RefObject<HTMLVideoElement>;
  onPreviewPlay?: () => void;
  render?: { documentId?: string; documentRevision?: number; documentVersion?: number; providerVersion?: string;
    checksum?: string; url?: string };
}) {
  const [snapshot, setSnapshot] = React.useState<Inspection>();
  const [sceneId, setSceneId] = React.useState("");
  const [layerId, setLayerId] = React.useState("");
  const [recipeId, setRecipeId] = React.useState("");
  const [trackIndex, setTrackIndex] = React.useState(0);
  const [keyIndex, setKeyIndex] = React.useState(0);
  const [key, setKey] = React.useState<Keyframe>({ frame: 0, value: 0, curve: [.2, 0, .2, 1] });
  const [pivot, setPivot] = React.useState<[number, number]>([.5, .5]);
  const [parentTargetId, setParentTargetId] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const pendingRequest = React.useRef<{ commandId: string; documentId: string; planId: string;
    expectedDocumentRevision: number; expectedPlanRevision: number; actions: Action[] }>();
  const localVideo = React.useRef<HTMLVideoElement>(null);
  const video = playbackRef ?? localVideo;
  const base = `/api/v1/studios/v1/documents/${encodeURIComponent(document.documentId)}/editor`;
  const load = React.useCallback(async (at: number, signal?: AbortSignal) => {
    const next = await apiFetch<Inspection>(`${base}/inspection?frame=${Math.max(0, at)}`, { signal });
    if (!signal?.aborted) setSnapshot(next);
    return next;
  }, [base]);

  React.useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      void load(Math.min(frame, Math.max(0, (document.composition.mediaTimeline?.durationFrames ?? 1) - 1)), controller.signal)
        .catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); });
    }, 100);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [load, active, frame, document.revision, document.composition.mediaTimeline?.durationFrames]);

  const layers = snapshot?.document.composition.pages.flatMap(page => page.layers) ?? [];
  const scenes = snapshot?.scenes ?? [];
  const selectedScene = scenes.find(s => s.sceneId === sceneId) ?? scenes[0];
  const sceneLayers = layers.filter(l => snapshot?.layerScenes[l.id] === selectedScene?.sceneId);
  const layer = sceneLayers.find(l => l.id === layerId) ?? sceneLayers[0];
  const node = snapshot?.nodes.find(n => n.targetLayerId === layer?.id);
  const parent = snapshot?.nodes.find(n => n.nodeId === node?.parentNodeId);
  const recipes = (snapshot?.recipes ?? []).filter(r => r.sceneId === selectedScene?.sceneId && r.targetIds.includes(layer?.name ?? ""));
  const recipe = recipes.find(r => r.id === recipeId) ?? recipes[0];
  const track = recipe?.parameters.tracks[trackIndex] ?? recipe?.parameters.tracks[0];
  const selectedKey = track?.keyframes[keyIndex] ?? track?.keyframes[0];
  const selectedKeySignature = JSON.stringify(selectedKey);
  React.useEffect(() => { if (selectedKey) setKey(structuredClone(selectedKey)); }, [selectedKeySignature, recipe?.id]);
  React.useEffect(() => { if (recipe) setPivot([...recipe.parameters.pivot]); }, [recipe?.id, recipe?.parameters.pivot.join(",")]);
  React.useEffect(() => { setParentTargetId(recipe?.parameters.parentTargetId ?? ""); }, [recipe?.id, recipe?.parameters.parentTargetId]);
  const properties = (layer?.properties ?? {}) as Record<string, unknown>;
  const timing = properties.editorialTiming as { startFrame: number; durationFrames: number } | undefined;
  const shadow = properties.editorialShadow as { x: number; y: number; blur: number; color: string; opacity: number } | null | undefined;
  const depth = properties.editorialDepth as { blurPx: number; opacity: number; parallax: number } | undefined;
  const blurTrack = snapshot?.tracks.find(t => t.targetLayerId === layer?.id && t.property === "blur_px");
  const centerBlur = blurTrack?.evaluatedLocalValue ?? depth?.blurPx ?? 0;
  const ancestry = new Set<string>();
  let ancestor = node;
  while (ancestor && !ancestry.has(ancestor.nodeId)) {
    ancestry.add(ancestor.nodeId);
    ancestor = snapshot?.nodes.find(n => n.nodeId === ancestor?.parentNodeId);
  }
  const exposureRecipes = (snapshot?.recipes ?? []).filter(r => r.sceneId === selectedScene?.sceneId
    && r.technique === "velocity_blur" && r.targetIds.some(target => snapshot?.nodes.some(n =>
      ancestry.has(n.nodeId) && layers.find(l => l.id === n.targetLayerId)?.name === target)));
  const exposure = exposureRecipes.find(r => r.startFrame <= (snapshot?.frame ?? 0)
    && (snapshot?.frame ?? 0) < r.endFrameExclusive) ?? exposureRecipes[0];
  const matte = properties.recipeAssetMatte as { sourceLayerId: string; assetId: string; mode: "alpha" | "luminance";
    invert: boolean; objectFit: "contain" | "cover"; startFrame: number; endFrameExclusive: number } | undefined;
  const matteSource = layers.find(l => l.id === matte?.sourceLayerId);
  const sourceNode = snapshot?.nodes.find(n => n.targetLayerId === matteSource?.id);
  const sourceParent = snapshot?.nodes.find(n => n.nodeId === sourceNode?.parentNodeId);
  const sourceOpacity = snapshot?.tracks.find(t => t.targetLayerId === matteSource?.id && t.property === "opacity")
    ?.evaluatedLocalValue ?? matteSource?.opacity;
  const assets = snapshot?.document.assets ?? [];
  const matteAsset = assets.find(a => a.id === matte?.assetId);
  const font = assets.find(a => a.id === properties.fontAssetId);
  const latest = snapshot?.history.find(h => h.documentRevision === snapshot.document.revision && h.planRevision === snapshot.planRevision);
  const sameRender = render?.documentId === snapshot?.document.documentId
    && render?.documentRevision === snapshot?.document.revision
    && render?.documentVersion === snapshot?.document.version && !!render?.checksum && !!render?.url;
  React.useEffect(() => {
    if (sameRender && video.current && snapshot) {
      video.current.pause();
      video.current.currentTime = snapshot.frame * snapshot.frameRate.denominator / snapshot.frameRate.numerator;
    }
  }, [sameRender, snapshot?.frame, snapshot?.frameRate]);

  async function submit(actions?: Action[]) {
    if (!snapshot || busy) return;
    if (actions) pendingRequest.current = { commandId: crypto.randomUUID(), documentId: document.documentId,
      planId: snapshot.planId, expectedDocumentRevision: snapshot.document.revision,
      expectedPlanRevision: snapshot.planRevision, actions };
    if (!pendingRequest.current) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const receipt = await apiFetch<Receipt>(`${base}/commands`, { method: "POST", body: JSON.stringify(pendingRequest.current) });
      pendingRequest.current = undefined;
      setNotice(`Ajuste salvo na revisão ${receipt.documentRevision}. Render e avaliação visual pendentes.`);
      await load(Math.min(frame, snapshot.durationFrames - 1));
      await onChanged();
    } catch (e) {
      // Retain the exact envelope after an uncertain network result; retry never creates a second edit.
      if (e instanceof APIError) pendingRequest.current = undefined;
      setError(errorMessage(e));
    } finally { setBusy(false); }
  }

  return <section className="editor-inspection" aria-label="Inspeção da composição canônica">
    <h3>Composição e movimento</h3>
    <p>Revisão {snapshot?.document.revision ?? document.revision} · plano {snapshot?.planRevision ?? "…"}</p>
    <button type="button" disabled={busy || disabled} onClick={() => {
      setError(""); void load(Math.min(frame, (snapshot?.durationFrames ?? 1) - 1)).then(onChanged).catch(e => setError(errorMessage(e)));
    }}>Atualizar inspeção</button>
    {error && <p role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {pendingRequest.current && <button type="button" disabled={busy || disabled} onClick={() => void submit()}>Reenviar o mesmo comando</button>}
    {snapshot && <>
      <label>Frame da composição<input aria-label="Frame da composição" type="number" min={0} max={snapshot.durationFrames - 1}
        value={Math.min(frame, snapshot.durationFrames - 1)} onChange={e => {
          if (e.target.value !== "") onSeek(Math.max(0, Math.min(snapshot.durationFrames - 1, Math.round(Number(e.target.value)))));
        }} /></label>
      <p>Propriedades calculadas no frame {snapshot.frame}. Valores locais ao nó; posição final e limites do texto dependem do render.</p>
      <label>Cena<select aria-label="Cena" value={selectedScene?.sceneId ?? ""} onChange={e => { setSceneId(e.target.value); setLayerId(""); setRecipeId(""); setTrackIndex(0); setKeyIndex(0); }}>
        {scenes.map(s => <option key={s.sceneId} value={s.sceneId}>{s.sceneId} · [{s.startFrame}, {s.startFrame + s.durationFrames})</option>)}
      </select></label>
      <label>Camada<select aria-label="Camada" value={layer?.id ?? ""} onChange={e => { setLayerId(e.target.value); setRecipeId(""); setTrackIndex(0); setKeyIndex(0); }}>
        {sceneLayers.map(l => <option key={l.id} value={l.id}>{l.name} · {l.kind} · {l.id.slice(-6)}</option>)}
      </select></label>
      {layer && <>
        <p>Target: <code>{layer.id}</code><br />Pai: {layers.find(l => l.id === parent?.targetLayerId)?.name ?? "raiz"}<br />
          Intervalo: {timing ? `[${timing.startFrame}, ${timing.startFrame + timing.durationFrames})` : "composição"}<br />
          Base: x {layer.x}, y {layer.y}, {layer.width} × {layer.height}, rotação {layer.rotation}°, opacidade {layer.opacity}<br />
          Pivô: {node?.transformOriginX ?? "—"}, {node?.transformOriginY ?? "—"}</p>
        {layer.kind === "text" && <p>Fonte: {font ? `${font.id} · ${font.checksum ?? "checksum ausente"}` : "fonte padrão do renderer, sem asset vinculado"}</p>}
        {matte && <div role="group" aria-label="Máscara da camada">
          <h4>Máscara</h4>
          <p>Fonte: {matteSource?.name ?? "camada fonte indisponível"} · <code>{matte.sourceLayerId}</code><br />
            Pai da fonte: {layers.find(l => l.id === sourceParent?.targetLayerId)?.name ?? "raiz"}<br />
            Modo: {matte.mode === "alpha" ? "alpha" : "luminância"}; inversão: {matte.invert ? "sim" : "não"};
            ajuste da imagem: {matte.objectFit}.<br />
            Intervalo: [{matte.startFrame}, {matte.endFrameExclusive}).<br />
            Opacidade da fonte no frame {snapshot.frame}: {sourceOpacity === undefined ? "indisponível" : Number(sourceOpacity.toFixed(4))}.</p>
          <p>Asset: {matte.assetId}<br /><code>{matteAsset?.checksum ?? "checksum indisponível"}</code></p>
          <p>A fonte é posicionada no espaço da composição. Só a opacidade da camada fonte participa da máscara;
            a opacidade dos pais da fonte não altera sua cobertura.
            {exposure && " Durante a exposição, a camada ou grupo exposto usa subframes; ancestrais e referências externos ficam no instante central. Cobertura e tempos efetivos são observados no render."}</p>
        </div>}
        <div role="group" aria-label="Efeitos espaciais da camada">
          <h4>Efeitos espaciais</h4>
          <p>Desfoque estático authored: {depth?.blurPx ?? 0} px.<br />
            Desfoque no instante central do frame {snapshot.frame}: {Number(centerBlur.toFixed(4))} px
            {blurTrack ? " · track blur_px calculada pela API." : " · valor estático."}</p>
          <p>{shadow ? <>Sombra authored: deslocamento local x {shadow.x} px, y {shadow.y} px;
            desfoque {shadow.blur} px; cor {shadow.color}; opacidade {shadow.opacity}.
            {shadow.opacity === 0 && " A sombra é transparente."}</> : "Sem sombra authored."}</p>
          {depth && <p>Profundidade authored: opacidade {depth.opacity}; parallax {depth.parallax}.
            A consequência composta é observada no render.</p>}
          {exposure && <p>Exposição temporal: {exposure.parameters.temporalSamples} amostras solicitadas;
            obturador {exposure.parameters.shutterDegrees}°; intervalo [{exposure.startFrame}, {exposure.endFrameExclusive}).
            {exposure.parameters.temporalExposure ? " A exposição usa subframes; o valor central acima não representa a média do MP4."
              : " Política temporal legada."}
            {" Amostras efetivamente usadas e redução no repouso constam do recibo do render."}</p>}
          {exposure && !exposure.targetIds.includes(layer.name ?? "") && <p>Exposição herdada do rig: {exposure.targetIds.join(", ")}.</p>}
        </div>
        <table><caption>Tracks do target no frame {snapshot.frame}</caption><thead><tr><th>Propriedade</th><th>Avaliada</th><th>Keyframes authored</th></tr></thead>
          <tbody>{snapshot.tracks.filter(t => t.targetLayerId === layer.id).map(t => <tr key={t.trackId}>
            <td>{t.property}</td><td>{Number(t.evaluatedLocalValue.toFixed(4))} {t.unit}</td>
            <td>{t.keyframes.map(k => `${k.frame}: ${k.value} (${k.easing}${k.cubicBezier ? "; " + k.cubicBezier.join(", ") : ""})`).join(" · ")}</td>
          </tr>)}</tbody></table>
      </>}
      {recipes.length > 0 ? <fieldset disabled={busy || disabled || !!pendingRequest.current}>
        <legend>Ajustar receita existente</legend>
        <label>Receita<select value={recipe?.id ?? ""} onChange={e => { setRecipeId(e.target.value); setTrackIndex(0); setKeyIndex(0); }}>
          {recipes.map(r => <option key={r.id} value={r.id}>{r.id} · {r.technique}</option>)}
        </select></label>
        {recipe && <>
          <p>Frames locais à receita [{recipe.startFrame}, {recipe.endFrameExclusive}).</p>
          {track && <>
            <p>Salvar substitui o keyframe nesse frame local. Um frame diferente insere outro keyframe.</p>
            <label>Track<select value={Math.min(trackIndex, recipe.parameters.tracks.length - 1)} onChange={e => { setTrackIndex(Number(e.target.value)); setKeyIndex(0); }}>
              {recipe.parameters.tracks.map((t, i) => <option key={i} value={i}>{t.targetId} · {t.property}</option>)}
            </select></label>
            <label>Keyframe<select value={Math.min(keyIndex, track.keyframes.length - 1)} onChange={e => setKeyIndex(Number(e.target.value))}>
              {track.keyframes.map((k, i) => <option key={k.frame} value={i}>Frame {k.frame} · {k.value}</option>)}
            </select></label>
            <label>Frame local<input type="number" min={0} max={recipe.endFrameExclusive - recipe.startFrame} value={key.frame}
              onChange={e => setKey(k => ({ ...k, frame: Number(e.target.value) }))} /></label>
            <label>Valor<input type="number" step="any" value={key.value} onChange={e => setKey(k => ({ ...k, value: Number(e.target.value) }))} /></label>
            <div className="editor-control-grid">{key.curve.map((v, i) => <label key={i}>{["Curva x1", "Curva y1", "Curva x2", "Curva y2"][i]}
              <input type="number" step=".01" min={i % 2 === 0 ? 0 : undefined} max={i % 2 === 0 ? 1 : undefined} value={v}
                onChange={e => setKey(k => ({ ...k, curve: k.curve.map((n, j) => j === i ? Number(e.target.value) : n) as Keyframe["curve"] }))} /></label>)}</div>
            <button type="button" onClick={() => void submit([{ kind: "set_recipe_keyframe", sceneId: recipe.sceneId,
              recipeId: recipe.id, targetId: track.targetId, property: track.property, keyframe: key }])}>Salvar keyframe</button>
          </>}
          {recipe.technique === "motion_choreography" && <><div className="editor-control-grid">{pivot.map((v, i) => <label key={i}>Pivô {i ? "y" : "x"}<input type="number" min={0} max={1} step=".01" value={v}
            onChange={e => setPivot(p => p.map((n, j) => j === i ? Number(e.target.value) : n) as [number, number])} /></label>)}</div>
          <button type="button" onClick={() => void submit([{ kind: "set_recipe_pivot", sceneId: recipe.sceneId, recipeId: recipe.id, pivot }])}>Salvar pivô</button></>}
          {recipe.technique === "layer_rig" && <>
            <label>Pai do rig<select value={parentTargetId} onChange={e => setParentTargetId(e.target.value)}>
              {(snapshot.parentCandidates ?? []).filter(p => p.sceneId === recipe.sceneId && !recipe.targetIds.includes(p.targetId))
                .map(p => <option key={p.targetId} value={p.targetId}>{p.targetId}</option>)}
            </select></label>
            <p>Os targets do rig conservam suas coordenadas locais. A posição na composição pode mudar com o novo pai.</p>
            <button type="button" disabled={!parentTargetId} onClick={() => void submit([{ kind: "set_recipe_parent",
              sceneId: recipe.sceneId, recipeId: recipe.id, parentTargetId, coordinateSpace: "local" }])}>Salvar pai do rig</button>
          </>}
        </>}
      </fieldset> : <p>Esta camada não tem receita editável. Os tracks acima pertencem à composição atual.</p>}
      {latest && <button type="button" disabled={busy || disabled || !!pendingRequest.current}
        onClick={() => void submit([{ kind: "undo_command", commandId: latest.commandId }])}>Desfazer comando da revisão atual</button>}
      <button type="button" disabled={busy || disabled || !!pendingRequest.current} onClick={async () => {
        setBusy(true); setError(""); try { await onRender(snapshot.document, snapshot.planId); }
        catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
      }}>Renderizar esta revisão</button>
      <p>{sameRender ? `Render associado à revisão ${render?.documentRevision} · ${render?.checksum}` : "A revisão inspecionada ainda não tem MP4 associado neste painel."}</p>
      {sameRender && <p>Renderer do MP4: {snapshot.renderer} · versão {render?.providerVersion ?? "não informada"}.</p>}
      {sameRender && <video ref={video} src={render?.url} controls preload="metadata" aria-label="Render da revisão inspecionada" onPlay={onPreviewPlay} />}
      <details><summary>Versões, digests e materiais</summary>
        <p>Renderer: {snapshot.renderer}</p>
        <p>Documento: <code>{snapshot.documentDigest}</code><br />Grafo: <code>{snapshot.graphDigest}</code><br />
          Composição: <code>{snapshot.hashes.executableComposition}</code></p>
        <p>{Object.entries(snapshot.versions).map(([k, v]) => `${k}: ${v}`).join(" · ")}</p>
        {assets.map(a => <p key={a.id}>{a.id} · {a.mediaType} · {a.rightsStatus}<br /><code>{a.checksum ?? "checksum pendente"}</code></p>)}
        <p>QC técnico e avaliação visual permanecem separados. Alterar a revisão exige novo render e nova avaliação.</p>
      </details>
    </>}
  </section>;
}
