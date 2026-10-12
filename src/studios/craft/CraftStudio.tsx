import React from "react";
import { ArrowLeft, Check, Download, Film, History, Image as ImageIcon, Layers3, LoaderCircle, Plus, Redo2, RefreshCw, Save, Send, Sparkles, Undo2, Upload, WandSparkles, X } from "lucide-react";
import { useProductData } from "../../context/ProductDataContext";
import { productApi, type AssetRecord } from "../../api/productApi";
import { EditorialReviewPanel } from "../EditorialReviewPanel";
import { craftApi, type CraftCapability, type CraftEngine, type CraftInputSchema } from "./craftApi";
import { commandValidation, craftCommands, frameCount, initialCommandParams, safeCraftMode } from "./craftState";
import { craftError, useCraftStudio } from "./useCraftStudio";
import { useCraftBrowser } from "./useCraftBrowser";
import "./craft-studio.css";

interface Props {
  mode?: string;
  pathname?: string;
  search?: string;
  navigate?: (path: string, options?: { replace?: boolean }) => void;
  sourceAssetId?: string;
  returnTo?: string;
}
const engineNames: Record<CraftEngine, string> = { photocraft: "Imagens", filmcraft: "Vídeos", effectcraft: "Composição e efeitos" };
const engineExtensions: Record<CraftEngine, string> = { photocraft: "pcraft", filmcraft: "fcproj", effectcraft: "ecproj" };
const friendlyFields: Record<string, string> = { name: "Nome", text: "Texto", width: "Largura", height: "Altura", x: "Posição horizontal", y: "Posição vertical", opacity: "Opacidade", rotation: "Rotação", fontSize: "Tamanho da fonte", size: "Tamanho da fonte", color: "Cor", fill: "Preenchimento", background: "Fundo", duration: "Duração", durationMs: "Duração em ms", start: "Início", gain: "Volume", assetId: "Material", layer: "Elemento", clip: "Trecho", layerId: "Elemento", nodeId: "Elemento", clipId: "Trecho", pageId: "Página", fontFamily: "Fonte", font: "Fonte", rect: "Área do elemento", box: "Área do texto", position: "Posição", scale: "Escala", matrix: "Transformação", dx: "Deslocamento horizontal", dy: "Deslocamento vertical", visible: "Visível", locked: "Bloqueado", blend: "Mesclagem", align: "Alinhamento", kind: "Forma", track: "Trilha", audioTrack: "Trilha de áudio", seconds: "Posição em segundos", sourceIn: "Início na mídia original", deltaFrames: "Ajuste em quadros", edge: "Extremidade do corte", mode: "Modo do corte", durationSeconds: "Duração em segundos", item: "Material importado", addToComp: "Adicionar à composição" };
const friendlyCommands: Record<string, string> = { "type.create": "Adicionar texto", "type.setText": "Editar texto", "type.setStyle": "Estilo do texto", "shape.create": "Adicionar forma", "layer.setProps": "Propriedades do elemento", "layer.translate": "Mover elemento", "layer.select": "Selecionar elemento", "edit.transform": "Transformar elemento", "timeline.place": "Inserir na montagem", "timeline.trim": "Ajustar corte", "captions.add": "Adicionar legenda", "file.newColorMatte": "Adicionar fundo de cor", "inspector.transform": "Posição, escala e opacidade", "asset.import": "Inserir material" };
const commandLabel = (command: CraftCapability) => friendlyCommands[command.id] || command.label;

function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = name; anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function go(path: string) {
  window.history.pushState({}, "", path); window.dispatchEvent(new PopStateEvent("popstate"));
}
function safeReturn(value: string | null | undefined) {
  return value && /^\/(?:library\/assets|content\/[^/?#]+\/edit)(?:\?[^#]*)?$/.test(value) ? value : "/library/assets";
}

function FlexibleValue({ id, value, onChange, disabled, depth = 0 }: {
  id: string; value: unknown; onChange: (value: unknown) => void; disabled: boolean; depth?: number;
}) {
  const kind = value === undefined ? "empty" : Array.isArray(value) ? "array" : typeof value;
  const defaults: Record<string, unknown> = { empty: undefined, number: 0, string: "", boolean: false, array: [], object: {} };
  return <span className="craft-flexible-value">
    <select aria-label="Tipo de valor" value={kind} disabled={disabled} onChange={(event) => onChange(defaults[event.target.value])}>
      <option value="empty">Sem alteração</option><option value="number">Número</option><option value="string">Texto ou cor</option>
      <option value="boolean">Ativado / desativado</option><option value="array">Valores em sequência</option><option value="object">Propriedades</option>
    </select>
    {kind === "number" ? <input id={id} type="number" step="any" value={Number(value)} disabled={disabled} onChange={(event) => onChange(event.target.value === "" ? undefined : Number(event.target.value))} />
      : kind === "string" ? <input id={id} value={String(value)} disabled={disabled} onChange={(event) => onChange(event.target.value)} />
      : kind === "boolean" ? <input id={id} type="checkbox" checked={Boolean(value)} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      : depth < 8 && Array.isArray(value) ? <span>{value.map((item, index) => <span key={index}>
        <FlexibleValue id={`${id}-${index}`} value={item} disabled={disabled} depth={depth + 1} onChange={(next) => onChange(value.map((previous, i) => i === index ? next : previous))} />
        <button type="button" disabled={disabled} aria-label={`Remover valor ${index + 1}`} onClick={() => onChange(value.filter((_, i) => i !== index))}><X size={12} /></button>
      </span>)}<button type="button" disabled={disabled || value.length >= 64} onClick={() => onChange([...value, 0])}>Adicionar valor</button></span>
      : depth < 8 && kind === "object" && value ? <span>{Object.entries(value).map(([key, item]) => <span key={key}>
        <span>{friendlyFields[key] || key}</span><FlexibleValue id={`${id}-${key}`} value={item} disabled={disabled} depth={depth + 1} onChange={(next) => onChange({ ...value as Record<string, unknown>, [key]: next })} />
      </span>)}<input aria-label="Nome da propriedade" placeholder="Nome da propriedade" disabled={disabled} onKeyDown={(event) => {
        const key = event.currentTarget.value.trim();
        if (event.key === "Enter" && /^[a-zA-Z][a-zA-Z0-9_]{0,63}$/.test(key) && !["__proto__", "constructor", "prototype"].includes(key)) {
          event.preventDefault(); onChange({ ...value as Record<string, unknown>, [key]: 0 }); event.currentTarget.value = "";
        }
      }} /></span> : null}
  </span>;
}

function SchemaFields({ schema, value, onChange, disabled, assets, prefix = "craft-param" }: {
  schema: CraftInputSchema; value: Record<string, unknown>; onChange: (value: Record<string, unknown>) => void;
  disabled: boolean; assets: AssetRecord[]; prefix?: string;
}) {
  return <div className="craft-fields">{Object.entries(schema.properties ?? {}).map(([key, field]) => {
    const id = `${prefix}-${key}`;
    const label = field.title || friendlyFields[key] || key.replace(/[_-]/g, " ");
    const current = value[key];
    const set = (next: unknown) => onChange({ ...value, [key]: next });
    if (field.type === "object" && field.properties) return <fieldset key={key}><legend>{label}</legend><SchemaFields schema={field} value={current && typeof current === "object" ? current as Record<string, unknown> : {}} onChange={set} disabled={disabled} assets={assets} prefix={id} /></fieldset>;
    return <label key={key} htmlFor={id}>{label}{schema.required?.includes(key) ? " *" : ""}
      {field.enum ? <select id={id} disabled={disabled} value={current === undefined ? "" : JSON.stringify(current)} onChange={(event) => set(event.target.value ? JSON.parse(event.target.value) : undefined)}><option value="">Escolha…</option>{field.enum.map((item) => <option key={JSON.stringify(item)} value={JSON.stringify(item)}>{String(item)}</option>)}</select>
      : /^assetId$/i.test(key) ? <select id={id} disabled={disabled} value={String(current ?? "")} onChange={(event) => set(event.target.value)}><option value="">Selecione um material</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.title}</option>)}</select>
      : field.type === "boolean" ? <input id={id} type="checkbox" checked={Boolean(current)} disabled={disabled} onChange={(event) => set(event.target.checked)} />
      : field.type === "number" || field.type === "integer" ? <input id={id} type="number" min={field.minimum} max={field.maximum} step={field.type === "integer" ? 1 : "any"} value={typeof current === "number" ? current : ""} disabled={disabled} onChange={(event) => set(event.target.value === "" ? undefined : Number(event.target.value))} />
      : field.type === "array" && field.items ? <ArrayField id={id} schema={field.items} minItems={field.minItems} maxItems={field.maxItems} value={Array.isArray(current) ? current : []} onChange={set} disabled={disabled} assets={assets} />
      : !field.type || Array.isArray(field.type) || field.type === "object" || field.type === "array" ? <FlexibleValue id={id} value={current} onChange={set} disabled={disabled} />
      : <input id={id} type={/^(color|backgroundColor)$/i.test(key) && /^#[0-9a-f]{6}$/i.test(String(current)) ? "color" : "text"} value={String(current ?? "")} disabled={disabled} onChange={(event) => set(event.target.value)} />}
      {field.description && <small>{field.description}</small>}
    </label>;
  })}</div>;
}

function ArrayField({ id, schema, value, onChange, disabled, assets, minItems = 0, maxItems = 100 }: {
  id: string; schema: CraftInputSchema; minItems?: number; maxItems?: number; value: unknown[]; onChange: (value: unknown[]) => void; disabled: boolean; assets: AssetRecord[];
}) {
  const replace = (index: number, next: unknown) => onChange(value.map((item, at) => at === index ? next : item));
  return <div className="craft-array">{value.map((item, index) => <div className="craft-array-item" key={index}>
    {schema.type === "object" && schema.properties ? <SchemaFields schema={schema} value={item && typeof item === "object" ? item as Record<string, unknown> : {}} onChange={(next) => replace(index, next)} disabled={disabled} assets={assets} prefix={`${id}-${index}`} />
      : <input aria-label={`Valor ${index + 1}`} type={schema.type === "number" || schema.type === "integer" ? "number" : "text"} value={String(item ?? "")} disabled={disabled} onChange={(event) => replace(index, schema.type === "number" || schema.type === "integer" ? Number(event.target.value) : event.target.value)} />}
    <button type="button" className="craft-icon-button" aria-label={`Remover valor ${index + 1}`} disabled={disabled || value.length <= minItems} onClick={() => onChange(value.filter((_, at) => at !== index))}><X size={14} /></button>
  </div>)}<button type="button" disabled={disabled || value.length >= maxItems} onClick={() => onChange([...value, schema.type === "object" ? initialCommandParams(schema) : schema.default ?? (schema.type === "number" || schema.type === "integer" ? 0 : "")])}><Plus size={14} /> Adicionar valor</button></div>;
}

export function CraftStudio({ mode, pathname = window.location.pathname, search = window.location.search, navigate = go, sourceAssetId, returnTo }: Props) {
  const data = useProductData();
  const params = new URLSearchParams(search);
  const selectedMode = mode || params.get("mode") || "visual";
  const engine = safeCraftMode(selectedMode);
  const routePostId = /^\/content\/([^/]+)\/edit$/.exec(pathname)?.[1];
  const postId = routePostId && routePostId !== "draft" ? routePostId : undefined;
  const post = data.snapshot?.posts.find((item) => item.id === postId);
  const selectedSourceId = sourceAssetId || params.get("sourceAsset") || params.get("derivedAsset") || undefined;
  const source = data.snapshot?.assets.find((asset) => asset.id === selectedSourceId);
  const sourceDocumentId = params.get("sourceDocument") || undefined;
  const requestedDocumentId = params.get("document") || undefined;
  const userId = data.bootstrap?.user?.id;
  const [title, setTitle] = React.useState(post?.title || source?.title || `Novo projeto de ${engine === "photocraft" ? "imagens" : "vídeo"}`);
  const [format, setFormat] = React.useState("1080x1350");
  const [panel, setPanel] = React.useState<"layers" | "assets" | "history" | "review">(selectedSourceId ? "assets" : "layers");
  const [selectedLayer, setSelectedLayer] = React.useState<string>();
  const [commandId, setCommandId] = React.useState("");
  const [commandParams, setCommandParams] = React.useState<Record<string, unknown>>({});
  const [instruction, setInstruction] = React.useState("");
  const [localError, setLocalError] = React.useState<string>();
  const [frame, setFrame] = React.useState(0);
  const [zoom, setZoom] = React.useState(85);
  const [previewUrl, setPreviewUrl] = React.useState<string>();
  const [previewError, setPreviewError] = React.useState<string>();
  const [previewLoading, setPreviewLoading] = React.useState(false);
  const [exportFormat, setExportFormat] = React.useState("");
  const [outputUrl, setOutputUrl] = React.useState<string>();
  const [uploading, setUploading] = React.useState(false);
  const [uploadedAssets, setUploadedAssets] = React.useState<AssetRecord[]>([]);
  const [gateBlocked, setGateBlocked] = React.useState(false);
  const assetInput = React.useRef<HTMLInputElement>(null);
  const nativeInput = React.useRef<HTMLInputElement>(null);
  const studio = useCraftStudio({ engine, workspaceId: data.activeWorkspace?.id, userId, postId, requestedDocumentId,
    campaignId: post?.campaignId ?? params.get("campaign") ?? undefined, contentType: selectedMode === "carousel" ? "carousel" : engine === "photocraft" ? "visual" : "video", title,
    objective: post?.objective ?? undefined, audience: data.activeWorkspace?.brandProfile?.targetAudience?.[0] || "Audiência da marca", brandRevision: 1,
    enabled: data.status === "ready" || data.status === "refreshing", standalone: pathname.startsWith("/library/assets/"), onCreated: (id, linkedPostId) => {
      const next = new URLSearchParams(search); next.set("document", id);
      navigate(`${linkedPostId ? `/content/${encodeURIComponent(linkedPostId)}/edit` : pathname}?${next}`, { replace: true });
    },
  });
  const doc = studio.document;
  const native = doc?.nativeEditorState;
  const browser = useCraftBrowser(doc, studio.activePageId, Boolean(studio.engineInfo?.available));
  const commands = craftCommands(studio.inspection);
  const editingCommands = commands.filter((command) => !command.id.startsWith("host.history.") && !command.id.startsWith("host.pages."));
  const selectedCommand = editingCommands.find((command) => command.id === commandId);
  const layers = browser.inspection?.layers ?? studio.inspection?.project.layers ?? [];
  const layer = layers.find((item) => item.id === selectedLayer);
  const assets = [...uploadedAssets, ...(data.snapshot?.assets ?? [])].filter((asset, index, all) => all.findIndex((item) => item.id === asset.id) === index);
  const ready = Boolean(studio.engineInfo?.available && native?.engine === engine && studio.inspection);
  const locked = !ready || studio.busy || browser.applying || browser.state === "loading" || Boolean(studio.recovery) || studio.status === "conflict" || Boolean(studio.pending?.attempted);
  const supportedFormats = studio.engineInfo?.formats ?? [];
  const formats = supportedFormats.filter((item) => !["pcraft", "fcproj", "ecproj"].includes(item));
  const warnings = [...new Set([...(native?.migrationWarnings ?? []), ...(studio.inspection?.migrationWarnings ?? []), ...(studio.inspection?.project.warnings ?? [])])];
  const maxFrame = frameCount(studio.inspection);
  const pages = studio.inspection?.pages ?? [];
  const activePageIndex = pages.findIndex((page) => page.id === studio.activePageId);
  const jobOutput = studio.job?.request?.output;
  const renderedFormat = typeof jobOutput === "object" && jobOutput && "format" in jobOutput ? String(jobOutput.format) : exportFormat;

  React.useEffect(() => {
    setFrame(0); setSelectedLayer(undefined); setCommandId(""); setCommandParams({});
    setUploadedAssets([]); setOutputUrl(undefined); setLocalError(undefined);
  }, [engine, doc?.documentId]);
  React.useEffect(() => { setExportFormat(formats.includes(exportFormat) ? exportFormat : pages.length > 1 && formats.includes("png_set") ? "png_set" : formats[0] ?? ""); }, [formats.join(","), pages.length]);
  React.useEffect(() => {
    if (!doc || !ready) { setPreviewUrl(undefined); return; }
    const controller = new AbortController();
    let objectUrl: string | undefined;
    setPreviewLoading(true); setPreviewError(undefined); setPreviewUrl(undefined);
    const timer = window.setTimeout(() => {
      const render = browser.state === "ready" ? Promise.resolve().then(() => browser.preview(frame, Number(studio.inspection?.project.fps) || 30)!) : craftApi.preview(doc.documentId, frame, controller.signal, studio.activePageId);
      void render.then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob); setPreviewUrl(objectUrl);
      }).catch((cause) => { if (!controller.signal.aborted) setPreviewError(craftError(cause)); })
        .finally(() => { if (!controller.signal.aborted) setPreviewLoading(false); });
    }, 200);
    return () => { controller.abort(); window.clearTimeout(timer); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [doc?.documentId, doc?.revision, ready, frame, studio.activePageId, browser.state, browser.change]);
  React.useEffect(() => { setSelectedLayer(undefined); setCommandId(""); setCommandParams({}); }, [studio.activePageId]);
  React.useEffect(() => {
    setOutputUrl(undefined);
    const result = studio.job?.status === "succeeded" ? studio.job.result : undefined;
    if (!result) return;
    const artifact = result.artifact && typeof result.artifact === "object" ? result.artifact as Record<string, unknown> : result;
    const assetId = typeof artifact.assetId === "string" ? artifact.assetId : undefined;
    if (!assetId) return;
    const controller = new AbortController(); let objectUrl: string | undefined;
    void productApi.studioAssetBlob(assetId, controller.signal).then((blob) => {
      if (controller.signal.aborted) return;
      objectUrl = URL.createObjectURL(blob); setOutputUrl(objectUrl);
    }).catch((cause) => { if (!controller.signal.aborted) setLocalError(craftError(cause)); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [studio.job?.id, studio.job?.status]);

  const run = async (action: () => Promise<unknown>) => {
    setLocalError(undefined);
    try { await action(); } catch (cause) { setLocalError(craftError(cause)); }
  };
  const selectCommand = (command: CraftCapability, seed: Record<string, unknown> = {}) => {
    const defaults = initialCommandParams(command.inputSchema, selectedLayer);
    for (const [key, field] of Object.entries(command.inputSchema.properties ?? {})) {
      const current = layer?.properties?.[key];
      if (current !== undefined) defaults[key] = current;
      else if ((key === "rect" || key === "box") && field.type === "array") defaults[key] = [80, 80, Math.max(120, (studio.inspection?.project.width || 1080) / 2), Math.max(80, (studio.inspection?.project.height || 1350) / 4)];
      else if (key === "matrix" && field.type === "array") defaults[key] = [1, 0, 0, 1, 0, 0];
    }
    setCommandId(command.id); setCommandParams({ ...defaults, ...seed }); setLocalError(undefined);
  };
  const selectLayer = (id: string) => {
    setSelectedLayer(id);
    if (selectedCommand) setCommandParams({ ...commandParams, ...initialCommandParams(selectedCommand.inputSchema, id) });
  };
  const applyCommand = async () => {
    if (!selectedCommand || locked) return;
    const invalid = commandValidation(selectedCommand.inputSchema, commandParams);
    if (invalid) { setLocalError(invalid); return; }
    const command = { id: selectedCommand.id, params: commandParams };
    if (browser.state === "ready") await browser.apply(command, assets.find((asset) => asset.id === command.params.assetId));
    studio.queue(command);
  };
  const importAsset = (asset: AssetRecord) => {
    const capability = editingCommands.find((command) => Object.keys(command.inputSchema.properties ?? {}).some((key) => key === "assetId") && /import|add|insert/i.test(command.id));
    if (!capability) { setLocalError("Este motor ainda não disponibilizou a importação deste tipo de material."); return; }
    selectCommand(capability, { assetId: asset.id }); setPanel("layers");
  };
  const uploadAsset = async (file?: File) => {
    if (!file || !data.activeWorkspace?.id) return;
    setUploading(true); setLocalError(undefined);
    try { const asset = await craftApi.uploadAsset(data.activeWorkspace.id, file); setUploadedAssets((current) => [asset, ...current]); importAsset(asset); }
    catch (cause) { setLocalError(craftError(cause)); }
    finally { setUploading(false); }
  };
  const openEngine = (nextEngine: CraftEngine) => {
    const next = new URLSearchParams(search);
    next.set("mode", nextEngine === "photocraft" ? "visual" : nextEngine === "filmcraft" ? "video" : "effects");
    next.delete("document");
    if (nextEngine === "effectcraft" && doc?.nativeEditorState?.engine === "filmcraft") next.set("sourceDocument", doc.documentId);
    navigate(`${/^\/content\/[^/]+\/edit$/.test(pathname) ? pathname : "/content/draft/edit"}?${next}`);
  };
  const returnPath = safeReturn(returnTo || params.get("returnTo"));
  const statusText = studio.status === "loading" ? "Abrindo projeto…" : studio.status === "working" ? "Sincronizando…" : studio.status === "dirty" ? `${studio.pending?.commands.length ?? 0} ajustes pendentes` : studio.status === "offline" ? "Offline · recuperação guardada" : studio.status === "conflict" ? "Conflito de revisão" : studio.status === "error" ? "Sincronização interrompida" : native ? `Salvo · revisão ${doc?.revision}` : "Preparando projeto";
  const historyUndo = commands.some((command) => command.id === "host.history.undo");
  const historyRedo = commands.some((command) => command.id === "host.history.redo");

  return <section className="craft-studio" data-editor-engine={engine} aria-label={`Studio de ${engineNames[engine].toLowerCase()}`}>
    <header className="craft-header">
      <button className="craft-icon-button" aria-label="Voltar" onClick={() => navigate(sourceAssetId ? returnPath : "/content")}><ArrowLeft size={18} /></button>
      <div className="craft-heading"><span>CLICKO STUDIOS</span><h1>{doc?.title || `Studio de ${engineNames[engine].toLowerCase()}`}</h1><small aria-live="polite">{statusText}</small></div>
      <nav className="craft-engine-tabs" aria-label="Área de trabalho">{(["photocraft", "filmcraft", "effectcraft"] as CraftEngine[]).map((item) => <button key={item} aria-pressed={engine === item} disabled={studio.busy || browser.applying || Boolean(studio.pending)} onClick={() => openEngine(item)}>{engineNames[item]}</button>)}</nav>
      <div className="craft-toolbar">
        <button className="craft-icon-button" aria-label="Desfazer" disabled={locked || !historyUndo} onClick={() => void run(studio.undo)}><Undo2 size={17} /></button>
        <button className="craft-icon-button" aria-label="Refazer" disabled={locked || !historyRedo} onClick={() => void run(studio.redo)}><Redo2 size={17} /></button>
        <button disabled={!studio.pending || studio.busy || Boolean(studio.recovery) || studio.status === "conflict"} onClick={() => void run(studio.save)}><Save size={15} /> Salvar</button>
        <button disabled={locked} onClick={() => void run(async () => { download(await studio.loadNative(), `${doc?.title || "projeto"}.${pages.length > 1 ? "zip" : engineExtensions[engine]}`); })}><Download size={15} /> Projeto</button>
        <button className="craft-primary" disabled={locked || !exportFormat} onClick={() => void run(() => studio.exportProject(exportFormat, frame))}><Download size={15} /> Exportar</button>
      </div>
    </header>

    {(studio.error || localError) && <div className="craft-message craft-message--error" role="alert"><X size={16} /><span>{localError || studio.error}</span><button disabled={studio.busy || browser.applying || Boolean(studio.pending)} onClick={studio.refresh}><RefreshCw size={14} /> Recarregar</button></div>}
    {studio.notice && <div className="craft-message" role="status"><Check size={16} /> {studio.notice}</div>}
    {studio.recovery && <div className="craft-message craft-message--recovery"><History size={17} /><span>Há {studio.recovery.commands.length} alterações recuperáveis desta sessão. Revisão {studio.recovery.expectedRevision}.</span><button disabled={studio.busy} onClick={studio.recover}>Recuperar</button><button onClick={() => download(new Blob([JSON.stringify(studio.recovery, null, 2)], { type: "application/json" }), "clicko-recuperacao.json")}>Guardar cópia</button><button disabled={studio.busy} onClick={studio.discardRecovery}>Descartar</button></div>}
    {warnings.length > 0 && <details className="craft-warnings"><summary>{warnings.length} observações sobre a conversão deste projeto</summary><ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></details>}

    {!data.activeWorkspace || !userId ? <div className="craft-empty"><Layers3 size={34} /><h2>Abra seu workspace para editar</h2><p>Os projetos e materiais são privados e vinculados à sua conta.</p><button onClick={() => navigate("/login")}>Entrar</button></div>
    : studio.status === "loading" ? <div className="craft-empty" role="status"><LoaderCircle className="craft-spinner" size={32} /><h2>Abrindo seu projeto</h2><p>Recuperando materiais, revisão e recursos de edição.</p></div>
    : !studio.engineInfo?.available ? <div className="craft-empty"><EngineIcon engine={engine} /><h2>Studio aguardando o motor de edição</h2><p>{studio.engineInfo?.reason || "O serviço de edição ainda não está disponível. Seu projeto permanece preservado."}</p><button onClick={studio.refresh}><RefreshCw size={15} /> Verificar novamente</button></div>
    : !doc ? <div className="craft-create"><div className="craft-create-art"><Layers3 size={60} /><span>{engine === "photocraft" ? "Cada camada. Cada detalhe." : engine === "filmcraft" ? "Sua história, no seu ritmo." : "Movimento com intenção."}</span></div><form onSubmit={(event) => { event.preventDefault(); const [width, height] = format.split("x").map(Number); void studio.create(title, width, height); }}><span className="craft-eyebrow">UMA NOVA CRIAÇÃO</span><h2>Comece pelo seu projeto</h2><label>Nome<input required value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} /></label><label>Formato<select value={format} onChange={(event) => setFormat(event.target.value)}><option value="1080x1350">Retrato · 4:5</option><option value="1080x1080">Quadrado · 1:1</option><option value="1080x1920">Vertical · 9:16</option><option value="1920x1080">Horizontal · 16:9</option></select></label>{source && <p>Material recebido: {source.title}</p>}<button className="craft-primary" disabled={studio.busy || !title.trim()}><Plus size={16} /> Criar projeto</button>{studio.documents.filter((item) => item.nativeEditorState?.engine === engine).length > 0 && <label>Ou abra um projeto<select value="" onChange={(event) => { if (!event.target.value) return; const next = new URLSearchParams(search); next.set("document", event.target.value); navigate(`${pathname}?${next}`); }}><option value="">Escolher…</option>{studio.documents.filter((item) => item.nativeEditorState?.engine === engine).map((item) => <option key={item.documentId} value={item.documentId}>{item.title}</option>)}</select></label>}</form></div>
    : !native ? <div className="craft-empty"><Layers3 size={35} /><h2>Converter o projeto para o novo Studio</h2><p>O arquivo original será arquivado. A conversão registrará qualquer elemento que precise de ajuste.</p><button className="craft-primary" disabled={studio.busy} onClick={() => void run(studio.migrate)}>Converter e abrir</button></div>
    : native.engine !== engine ? <div className="craft-empty"><h2>Este projeto pertence a outra área de trabalho</h2><p>Abra a área correspondente para preservar sua edição.</p><button onClick={() => { const next = new URLSearchParams(search); next.set("mode", native.engine === "photocraft" ? "visual" : native.engine === "filmcraft" ? "video" : "effects"); navigate(`${pathname}?${next}`); }}>Abrir {engineNames[native.engine]}</button></div>
    : <div className="craft-workspace">
      <aside className="craft-library">
        <nav aria-label="Painéis do Studio">{([ ["layers", "Camadas", Layers3], ["assets", "Materiais", ImageIcon], ["history", "Histórico", History], ["review", "Revisão", Check] ] as const).map(([id, label, Icon]) => <button key={id} aria-pressed={panel === id} onClick={() => { setPanel(id); if (id === "history") void run(studio.loadVersions); }}><Icon size={16} /><span>{label}</span></button>)}</nav>
        {engine === "photocraft" && <div className="craft-pages">
          <div className="craft-panel-title"><h2>Páginas</h2><span>{pages.length}</span></div>
          <div className="craft-page-list" aria-label="Páginas do projeto">{pages.map((page, index) => <button key={page.id} aria-pressed={page.id === studio.activePageId} disabled={locked} onClick={() => void run(() => studio.selectPage(page.id))}><span>{String(index + 1).padStart(2, "0")}</span><strong>{page.title || `Página ${index + 1}`}</strong><small>{page.width} × {page.height}</small></button>)}</div>
          <div className="craft-page-actions">
            <button aria-label="Adicionar página" disabled={locked || !commands.some((command) => command.id === "host.pages.add")} onClick={() => void run(() => studio.pageCommand("host.pages.add", { pageId: `page-${crypto.randomUUID()}`, title: `Página ${pages.length + 1}`, width: studio.inspection?.project.width || 1080, height: studio.inspection?.project.height || 1350 }))}><Plus size={14} /></button>
            <button aria-label="Mover página para cima" disabled={locked || activePageIndex <= 0 || !commands.some((command) => command.id === "host.pages.move")} onClick={() => void run(() => studio.pageCommand("host.pages.move", { pageId: studio.activePageId, index: activePageIndex - 1 }))}>↑</button>
            <button aria-label="Mover página para baixo" disabled={locked || activePageIndex < 0 || activePageIndex >= pages.length - 1 || !commands.some((command) => command.id === "host.pages.move")} onClick={() => void run(() => studio.pageCommand("host.pages.move", { pageId: studio.activePageId, index: activePageIndex + 1 }))}>↓</button>
            <button aria-label="Remover página" disabled={locked || pages.length <= 1 || !studio.activePageId || !commands.some((command) => command.id === "host.pages.delete")} onClick={() => void run(() => studio.pageCommand("host.pages.delete", { pageId: studio.activePageId }))}><X size={14} /></button>
          </div>
        </div>}
        {panel === "layers" && <div className="craft-panel-content"><div className="craft-panel-title"><h2>Elementos</h2><span>{layers.length}</span></div>{layers.length ? layers.map((item) => <button className="craft-layer" key={item.id} aria-pressed={item.id === selectedLayer} onClick={() => selectLayer(item.id)}><Layers3 size={15} /><span>{item.name || item.id}<small>{item.kind || "Elemento"}</small></span></button>) : <p className="craft-muted">O motor ainda não retornou elementos. Use as ferramentas disponíveis para adicioná-los.</p>}{studio.inspection?.project.width && <dl className="craft-details"><dt>Formato</dt><dd>{studio.inspection.project.width} × {studio.inspection.project.height}</dd><dt>Revisão</dt><dd>{doc.revision}</dd></dl>}</div>}
        {panel === "assets" && <div className="craft-panel-content"><div className="craft-panel-title"><h2>Materiais</h2><button className="craft-icon-button" aria-label="Enviar material" disabled={locked || uploading} onClick={() => assetInput.current?.click()}><Upload size={16} /></button></div><p className="craft-muted">Escolha um arquivo da biblioteca para inserir no projeto.</p>{assets.filter((asset) => ["image", "video", "audio", "document"].includes(asset.type)).map((asset) => <button className="craft-asset" key={asset.id} disabled={locked} aria-pressed={asset.id === selectedSourceId} onClick={() => importAsset(asset)}><span className="craft-asset-icon">{asset.type === "video" ? <Film size={21} /> : <ImageIcon size={21} />}</span><span>{asset.title}<small>{asset.type}</small></span><Plus size={14} /></button>)}{!assets.length && <p className="craft-muted">Sua biblioteca ainda está vazia.</p>}{uploading && <p role="status">Enviando arquivo…</p>}</div>}
        {panel === "history" && <div className="craft-panel-content"><h2>Histórico do projeto</h2><p className="craft-muted">Cada salvamento conserva uma revisão. Desfazer e refazer usam o histórico do motor.</p>{studio.versions.map((version) => <div className="craft-version" key={version.number}><strong>Versão {version.number}</strong><small>{version.label || "Alteração salva"}</small><time>{new Date(version.createdAt).toLocaleString("pt-BR")}</time></div>)}{!studio.versions.length && <p className="craft-muted">Nenhuma versão adicional registrada.</p>}</div>}
        {panel === "review" && <div className="craft-panel-content"><h2>Revisão e publicação</h2><p className="craft-muted">{doc.postRef?.id ? "Envie a exportação da revisão atual para aprovação." : "Este projeto pertence à biblioteca. A exportação ficará disponível entre seus materiais."}</p><button disabled={!doc.postRef?.id || locked || gateBlocked || studio.job?.status !== "succeeded" || studio.jobRevision !== doc.revision || Boolean(studio.pending)} onClick={() => void run(async () => { const review = await studio.review(); navigate(`/approvals/${doc.postRef?.id || doc.documentId}?review=${encodeURIComponent(review.id)}`); })}><Send size={15} /> Enviar para revisão</button><button disabled={!doc.postRef?.id} onClick={() => navigate(`/publish/${doc.postRef?.id || doc.documentId}`)}>Abrir publicação</button></div>}
      </aside>

      <main className="craft-stage" data-craft-browser-state={browser.state}>
        {browser.state === "unavailable" && browser.error && <p className="craft-browser-state" role="status">A edição interativa no navegador não está disponível nesta sessão. A prévia usa a revisão salva no servidor.</p>}
        <div className="craft-stage-toolbar"><span>{engineNames[engine]}<small>{studio.inspection?.project.width || "—"} × {studio.inspection?.project.height || "—"}</small></span><label>Zoom<select value={zoom} onChange={(event) => setZoom(Number(event.target.value))}>{[50, 70, 85, 100].map((value) => <option key={value} value={value}>{value}%</option>)}</select></label><button className="craft-icon-button" aria-label="Importar projeto nativo" disabled={locked} onClick={() => nativeInput.current?.click()}><Upload size={16} /></button></div>
        <div className="craft-preview" aria-label="Prévia renderizada pelo motor">
          {previewLoading ? <div className="craft-preview-state" role="status"><LoaderCircle className="craft-spinner" size={24} /><p>Renderizando prévia…</p></div> : previewError ? <div className="craft-preview-state" role="alert"><ImageIcon size={30} /><p>{previewError}</p></div> : previewUrl ? <img src={previewUrl} alt={`Prévia do projeto ${doc.title}, revisão ${doc.revision}`} style={{ maxWidth: `${zoom}%`, maxHeight: `${zoom}%` }} /> : <div className="craft-preview-state"><ImageIcon size={30} /><p>Aguardando a prévia do projeto</p></div>}
          {studio.pending && <span className="craft-pending-preview">{browser.state === "ready" && browser.appliedCount === studio.pending.commands.length ? "Prévia das alterações · salvamento pendente" : `Prévia da revisão ${doc.revision} · salve para atualizar`}</span>}
        </div>
        {engine !== "photocraft" && <div className="craft-timeline"><header><strong>Timeline</strong><label>Quadro<input type="number" min={0} max={maxFrame} value={frame} onChange={(event) => setFrame(Math.max(0, Math.min(maxFrame, Number(event.target.value))))} /></label><span>{studio.inspection?.project.fps || 30} fps</span></header><input className="craft-seek" type="range" aria-label="Posição da prévia em quadros" min={0} max={maxFrame} value={frame} onChange={(event) => setFrame(Number(event.target.value))} />{(browser.inspection?.timeline ?? studio.inspection?.project.timeline ?? []).map((track, index) => <div key={String(track.id ?? index)} className="craft-track"><strong>{String(track.name || track.label || `Trilha ${index + 1}`)}</strong>{Array.isArray(track.clips) ? track.clips.map((clip: Record<string, unknown>, at: number) => <button key={String(clip.id ?? at)} onClick={() => selectLayer(String(clip.id ?? ""))} aria-pressed={clip.id === selectedLayer}>{String(clip.name || clip.label || `Trecho ${at + 1}`)}</button>) : <button onClick={() => selectLayer(String(track.id ?? ""))}>{String(track.label || track.kind || "Elemento")}</button>}</div>)}{!(browser.inspection?.timeline ?? studio.inspection?.project.timeline)?.length && <p className="craft-muted">Adicione materiais e use os comandos de montagem para criar trilhas.</p>}</div>}
        {studio.job && <div className="craft-export" role="status"><div><strong>Exportação · {({ queued: "na fila", running: "processando", retrying: "nova tentativa", cancel_requested: "cancelando", cancelled: "cancelada", succeeded: "concluída", failed: "falhou" })[studio.job.status]}</strong><progress max={100} value={studio.job.progress <= 1 ? studio.job.progress * 100 : studio.job.progress} /></div>{!["succeeded", "failed", "cancelled"].includes(studio.job.status) && <button disabled={studio.job.status === "cancel_requested"} onClick={() => void run(studio.cancelJob)}>Cancelar</button>}{studio.job.errorMessage && <p>{studio.job.errorMessage}</p>}{outputUrl && <a href={outputUrl} download={`clicko-${doc.documentId}.${renderedFormat === "png_set" ? "zip" : renderedFormat}`}>Baixar resultado</a>}</div>}
        {outputUrl && engine !== "photocraft" && ["mp4", "webm"].includes(renderedFormat) && <video className="craft-output-video" controls src={outputUrl} aria-label="Resultado renderizado da exportação" />}
        {panel === "review" && <EditorialReviewPanel document={doc} disabled={locked} active onGateChange={(state) => setGateBlocked(state.blocked)} />}
      </main>

      <aside className="craft-inspector"><div className="craft-panel-title"><h2>{layer ? layer.name || "Elemento selecionado" : "Ferramentas"}</h2><WandSparkles size={16} /></div>
        <label>Operação<select value={commandId} disabled={locked} onChange={(event) => { const command = editingCommands.find((item) => item.id === event.target.value); if (command) selectCommand(command); else setCommandId(""); }}><option value="">Escolha uma ferramenta</option>{editingCommands.map((command) => <option key={command.id} value={command.id}>{commandLabel(command)}</option>)}</select></label>
        {selectedCommand && <div className="craft-command"><h3>{commandLabel(selectedCommand)}</h3><SchemaFields schema={selectedCommand.inputSchema} value={commandParams} onChange={setCommandParams} disabled={locked} assets={assets} /><button className="craft-primary" disabled={locked} onClick={() => void run(applyCommand)}><Check size={15} /> Aplicar ajuste</button></div>}
        {!editingCommands.length && <p className="craft-muted">As ferramentas desta versão do motor ainda não estão disponíveis.</p>}
        {layer?.properties && <details className="craft-properties"><summary>Propriedades atuais</summary><dl>{Object.entries(layer.properties).filter(([, value]) => typeof value === "string" || typeof value === "number" || typeof value === "boolean").map(([key, value]) => <React.Fragment key={key}><dt>{friendlyFields[key] || key}</dt><dd>{String(value)}</dd></React.Fragment>)}</dl></details>}
        <div className="craft-ai"><div><Sparkles size={17} /><h2>Direção com IA</h2></div><p>Descreva a mudança. A IA usa as mesmas ferramentas e registra suas alterações no histórico.</p><label htmlFor="craft-instruction" className="craft-sr-only">Pedido de edição com IA</label><textarea id="craft-instruction" value={instruction} onChange={(event) => setInstruction(event.target.value)} placeholder={engine === "photocraft" ? "Ajuste o título e deixe a composição mais leve…" : "Ajuste os cortes e crie uma abertura mais direta…"} disabled={locked} /><button disabled={locked || !instruction.trim()} onClick={() => void run(async () => { await studio.applyAI(instruction.trim()); setInstruction(""); })}><Sparkles size={15} /> Aplicar direção</button></div>
        <div className="craft-export-options"><h2>Saída</h2><label>Formato<select value={exportFormat} onChange={(event) => setExportFormat(event.target.value)} disabled={locked || !formats.length}>{formats.map((item) => <option key={item} value={item}>{item === "png_set" ? "Todas as páginas · PNG em ZIP" : item.toUpperCase()}</option>)}</select></label><small>Exportações são processadas no servidor a partir da revisão salva.</small></div>
        {engine === "effectcraft" && sourceDocumentId && <button disabled={locked} onClick={() => void run(async () => { await studio.save(); const montage = await productApi.studioDocument(sourceDocumentId); await craftApi.linkComposition(montage.documentId, montage.revision, doc.documentId, crypto.randomUUID()); const next = new URLSearchParams(search); next.set("mode", "video"); next.set("document", montage.documentId); next.delete("sourceDocument"); navigate(`${pathname}?${next}`); })}><Film size={15} /> Usar na montagem</button>}
      </aside>
    </div>}
    <input ref={assetInput} type="file" hidden onChange={(event) => { void uploadAsset(event.target.files?.[0]); event.target.value = ""; }} />
    <input ref={nativeInput} type="file" hidden accept={`.${engineExtensions[engine]}`} onChange={(event) => { const file = event.target.files?.[0]; if (file) void run(() => studio.saveNative(file)); event.target.value = ""; }} />
  </section>;
}

function EngineIcon({ engine }: { engine: CraftEngine }) { return engine === "photocraft" ? <ImageIcon size={35} /> : <Film size={35} />; }
