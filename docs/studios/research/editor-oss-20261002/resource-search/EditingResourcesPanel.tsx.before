import React from "react";
import { apiFetch, apiFetchBlob } from "../api";
import type { StudioDocumentRecord } from "../api/productApi";

type Resource = { id: string; title: string; mediaType: string; checksum: string; reviewStatus?: string;
  resource: { kind?: string; description?: string }; url: string };
type Job = { id: string; status: string; errorMessage?: string; result?: {
  assetId?: string; checksumSha256?: string; status?: string } };

export function EditingResourcesPanel({ document, onDocument, disabled }: {
  document: StudioDocumentRecord; onDocument: (value: StudioDocumentRecord) => void; disabled: boolean;
}) {
  const [items, setItems] = React.useState<Resource[]>([]);
  const [query, setQuery] = React.useState("");
  const [kind, setKind] = React.useState("image");
  const [assetRole, setAssetRole] = React.useState("");
  const [motionDescription, setMotionDescription] = React.useState("");
  const [url, setUrl] = React.useState("");
  const [evidence, setEvidence] = React.useState("");
  const [official, setOfficial] = React.useState(false);
  const [autoAcquire, setAutoAcquire] = React.useState(false);
  const [preserve, setPreserve] = React.useState("rosto\nmovimento\nelementos não solicitados");
  const [prompt, setPrompt] = React.useState("");
  const [source, setSource] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [operation, setOperation] = React.useState("generate_image");
  const [targetClip, setTargetClip] = React.useState("");
  const [sourceStart, setSourceStart] = React.useState(0);
  const [duration, setDuration] = React.useState(8);
  const [fontPreview, setFontPreview] = React.useState<FontFace>();
  const [job, setJob] = React.useState<Job>();
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState("");
  const [operations, setOperations] = React.useState<string[]>([]);
  const [preview, setPreview] = React.useState<{ id: string; url: string; type: string }>();
  const [fonts, setFonts] = React.useState<{ family: string; version: string; files: Record<string, string> }[]>([]);
  const scope = `workspace_id=${encodeURIComponent(document.workspaceId)}`;
  const root = "/api/v1/studios/v1";
  const generation = React.useRef(0);
  const clips = (document.composition.mediaTimeline?.tracks ?? []).flatMap(track =>
    track.kind === "video" || track.kind === "overlay" ? track.clips : []);
  React.useEffect(() => () => { if (fontPreview) globalThis.document.fonts.delete(fontPreview); }, [fontPreview]);
  React.useEffect(() => () => { if (preview) URL.revokeObjectURL(preview.url); }, [preview]);
  React.useEffect(() => {
    generation.current++; setJob(undefined); setSource(""); setReference(""); setTargetClip("");
    setPreview(undefined); setFontPreview(undefined);
  }, [document.documentId]);
  React.useEffect(() => {
    const controller = new AbortController();
    apiFetch<{ operations: string[] }>(`${root}/editing/ai`, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setOperations(value.operations); }).catch(() => setOperations([]));
    return () => controller.abort();
  }, []);
  const refresh = React.useCallback(async () => {
    const current = generation.current;
    const value = await apiFetch<Resource[]>(`${root}/editing/resources?${scope}&query=${encodeURIComponent(query)}`);
    if (current === generation.current) setItems(value);
  }, [scope, query]);
  React.useEffect(() => { void refresh().catch(() => setMessage("Não foi possível carregar o acervo.")); }, [refresh]);
  React.useEffect(() => {
    if (!job || ["succeeded", "failed", "cancelled"].includes(job.status)) return;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      apiFetch<Job>(`${root}/jobs/${job.id}`, { signal: controller.signal })
        .then(value => { if (!controller.signal.aborted) { setJob(value); if (value.status === "succeeded") void refresh(); } })
        .catch(() => { if (!controller.signal.aborted) setMessage("Atualize o acervo para consultar o resultado."); });
    }, 3000);
    return () => { window.clearTimeout(timeout); controller.abort(); };
  }, [job, refresh]);
  async function run(action: () => Promise<void>) {
    setBusy(true); setMessage("");
    try { await action(); } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível concluir a operação.");
    } finally { setBusy(false); }
  }
  function post<T>(path: string, body: unknown) {
    return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body),
      headers: { "Content-Type": "application/json", "Idempotency-Key": `resource-${crypto.randomUUID()}` } });
  }
  async function attach(assetId: string) {
    const value = await post<StudioDocumentRecord>(`${root}/documents/${document.documentId}/editing-resources`, {
      assetId, expectedDocumentRevision: document.revision,
    });
    onDocument(value); setMessage("Material disponível na direção das cenas.");
  }
  async function show(assetId: string) {
    const current = generation.current;
    const blob = await apiFetchBlob(`/api/v1/assets/${assetId}/content`);
    if (current !== generation.current) return;
    setPreview({ id: assetId, url: URL.createObjectURL(blob), type: blob.type });
  }
  async function showFont(assetId: string) {
    const current = generation.current;
    const blob = await apiFetchBlob(`/api/v1/assets/${assetId}/content`);
    const font = new FontFace(`res-${assetId}`, await blob.arrayBuffer());
    await font.load();
    if (current !== generation.current) return;
    globalThis.document.fonts.add(font); setFontPreview(font);
  }
  return <details className="vs-editing-resources"><summary>Acervo e criação de materiais</summary>
    <label>Pesquisar recursos<input value={query} onChange={e => setQuery(e.target.value)} /></label>
    <label>Tipo de material<select value={kind} onChange={e => setKind(e.target.value)}>
      <option value="font">Fonte</option><option value="logo">Logo</option><option value="image">Imagem</option>
      <option value="video">Vídeo</option><option value="wardrobe">Referência de roupa</option>
      <option value="sound_effect">Efeito sonoro</option><option value="music">Música</option>
    </select></label>
    {["image", "video", "logo"].includes(kind) && <label>Papel visual deste material<select value={assetRole} onChange={e => setAssetRole(e.target.value)}>
      <option value="">Apoio ou indefinido</option><option value="product">Produto real</option>
      <option value="package">Embalagem real</option><option value="logo">Logotipo</option>
      <option value="brand">Identidade da marca</option><option value="action">Ação</option>
      <option value="environment">Ambiente</option>
    </select></label>}
    {kind === "video" && <label>Ação observável no vídeo<input value={motionDescription}
      onChange={e => setMotionDescription(e.target.value)} maxLength={1000}
      placeholder="Ex.: a mão abre a embalagem; o café cai na xícara" /></label>}
    {kind === "font" && <div>
      <button type="button" disabled={busy || !query.trim()} onClick={() => void run(async () => {
        setFonts(await apiFetch(`${root}/editing/fonts?family=${encodeURIComponent(query)}`));
      })}>Buscar família no Google Fonts</button>
      {fonts.map(font => <div key={font.family}>{font.family}{Object.entries(font.files).map(([variant, file]) =>
        <button type="button" key={variant} disabled={busy || !evidence.trim()} onClick={() => void run(async () => {
          await post(`${root}/editing/resources/import?${scope}`, { title: `${font.family} ${variant}`, kind: "font",
            family: font.family, variant, version: font.version, url: String(file).replace(/^http:/, "https:"), usageEvidence: evidence });
          await refresh();
        })}>Adicionar {variant}</button>)}</div>)}
    </div>}
    <label>Origem e condições de uso<input value={evidence} onChange={e => setEvidence(e.target.value)} /></label>
    <label><input type="checkbox" checked={official} onChange={e => setOfficial(e.target.checked)} /> Arquivo de origem oficial, conforme a fonte informada</label>
    <label>Adicionar arquivo<input type="file" disabled={busy || disabled || !evidence.trim()}
      accept="image/png,image/jpeg,image/webp,image/svg+xml,video/mp4,audio/*,.ttf,.otf"
      onChange={e => { const file = e.target.files?.[0]; if (!file) return;
        void run(async () => { const form = new FormData(); form.set("workspace_id", document.workspaceId);
          form.set("title", query.trim() || file.name); form.set("metadata", JSON.stringify({ kind, usageEvidence: evidence, official,
            sourceUrl: url || null, assetRole: assetRole || (kind === "logo" ? "logo" : null), motionDescription }));
          form.set("file", file); await apiFetch(`${root}/editing/resources/upload`, { method: "POST", body: form });
          await refresh(); setMessage("Arquivo adicionado ao acervo."); }); }} /></label>
    <label>URL do arquivo<input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://…" /></label>
    <button type="button" disabled={busy || disabled || !url || !evidence.trim()}
      onClick={() => void run(async () => { await post(`${root}/editing/resources/import?${scope}`, {
        title: query.trim() || "Recurso importado", kind, url, usageEvidence: evidence, official,
        assetRole: assetRole || (kind === "logo" ? "logo" : null), motionDescription,
      }); await refresh(); })}>Importar URL cadastrada</button>
    <label><input type="checkbox" checked={autoAcquire} onChange={e => setAutoAcquire(e.target.checked)} />
      Permitir obter este arquivo automaticamente quando a edição precisar dele</label>
    <button type="button" disabled={busy || disabled || !url || !query.trim() || !evidence.trim()}
      onClick={() => void run(async () => {
        await post(`${root}/editing/resource-sources?${scope}`, { title: query.trim(), kind, url,
          usageEvidence: evidence, official, autoAcquire,
          assetRole: assetRole || (kind === "logo" ? "logo" : null), motionDescription });
        setMessage("Fonte de material cadastrada para as próximas edições deste cliente.");
      })}>Cadastrar fonte de material</button>
    <ul>{items.map(item => <li key={item.id}>{item.title} · {item.resource.kind ?? item.mediaType}
      {item.resource.kind === "font" && <button type="button" disabled={busy}
        onClick={() => void run(() => showFont(item.id))}>Ver tipografia</button>}
      {/^(image|video|audio)\//.test(item.mediaType) && <button type="button" disabled={busy}
        onClick={() => void run(() => show(item.id))}>Visualizar</button>}
      {item.reviewStatus === "pending" && preview?.id === item.id && <button type="button" disabled={busy}
        onClick={() => void run(async () => { await post(`${root}/editing/resources/${item.id}/review`, {
          checksum: item.checksum, result: "passed", observation: "Material conferido visualmente no estúdio." });
          await refresh(); })}>Conferi este material</button>}
      <button type="button" disabled={busy || disabled || (!!item.reviewStatus && item.reviewStatus !== "passed") || document.assets.some(a => a.id === item.id)}
        onClick={() => void run(() => attach(item.id))}>Usar no projeto</button>
    </li>)}</ul>
    {fontPreview && <p style={{ fontFamily: fontPreview.family, fontSize: 28 }}>Criação com intenção · Aa 0123 áéíóú ãõ ç</p>}
    {preview && (preview.type.startsWith("video/") ? <video src={preview.url} controls style={{ maxWidth: "100%" }} />
      : preview.type.startsWith("audio/") ? <audio src={preview.url} controls />
      : <img src={preview.url} alt="Prévia do recurso selecionado" style={{ maxWidth: "100%" }} />)}
    <fieldset disabled={busy || disabled || (!!job && !["succeeded", "failed", "cancelled"].includes(job.status))}>
      <legend>Criar ou transformar material</legend>
      {!operations.includes(operation) && <p>Esta operação precisa de um provedor configurado com a capacidade correspondente. Você pode usar materiais do acervo.</p>}
      <label>Operação<select value={operation} onChange={e => setOperation(e.target.value)}>
        <option value="generate_image">Criar imagem</option><option value="edit_image">Alterar imagem</option>
        <option value="generate_video">Criar cena de vídeo</option><option value="edit_video">Alterar trecho de vídeo</option>
      </select></label>
      {operation.startsWith("edit_") && <label>Cena a transformar<select value={targetClip} onChange={e => {
        setTargetClip(e.target.value);
        const clip = clips.find(c => c.id === e.target.value);
        if (clip) {
          setSource(clip.assetId); setSourceStart((clip.source?.startMicroseconds ?? 0) / 1e6);
          const fps = document.composition.mediaTimeline!.frameRate;
          setDuration(Math.min(10, Math.max(3, Math.floor(clip.timeline.durationFrames * fps.denominator / fps.numerator))));
        }
      }}><option value="">Selecionar cena</option>{clips.map(clip =>
        <option key={clip.id} value={clip.id}>{clip.label || clip.id}</option>)}</select></label>}
      <label>Material de origem<select value={source} onChange={e => setSource(e.target.value)}>
        <option value="">Sem material de origem</option>{document.assets.filter(a => /^(image|video)\//.test(a.mediaType)).map(a =>
          <option key={a.id} value={a.id}>{items.find(i => i.id === a.id)?.title ?? a.id}</option>)}
      </select></label>
      <label>Imagem de referência<select value={reference} onChange={e => setReference(e.target.value)}>
        <option value="">Sem referência</option>{document.assets.filter(a => a.mediaType.startsWith("image/")).map(a =>
          <option key={a.id} value={a.id}>{items.find(i => i.id === a.id)?.title ?? a.id}</option>)}
      </select></label>
      <label>Descreva a alteração<textarea value={prompt} onChange={e => setPrompt(e.target.value)} /></label>
      <label>O que deve permanecer (um elemento por linha)<textarea value={preserve} onChange={e => setPreserve(e.target.value)} /></label>
      {operation.includes("video") && <div>
        <label>Início no vídeo de origem (segundos)<input type="number" min={0} step="0.04" value={sourceStart}
          onChange={e => setSourceStart(Number(e.target.value))} /></label>
        <label>Duração do trecho (3 a 10 segundos)<input type="number" min={3} max={10} step={1} value={duration}
          onChange={e => setDuration(Number(e.target.value))} /></label>
        <p>A transformação visual preserva o áudio original. Trechos maiores são trabalhados por partes.</p>
      </div>}
      <button type="button" disabled={!operations.includes(operation) || !prompt.trim() || (operation.startsWith("edit_") && !source)}
        onClick={() => void run(async () => { const value = await post<Job>(`${root}/documents/${document.documentId}/editing-ai-jobs`, {
          expectedDocumentRevision: document.revision, operation, prompt, sourceAssetId: source || null,
          sourceStartSeconds: sourceStart, durationSeconds: duration,
          referenceAssetIds: reference ? [reference] : [], preserve: preserve.split("\n").map(t => t.trim()).filter(Boolean),
        }); setJob(value); })}>Gerar material</button>
    </fieldset>
    {job && <p role="status">Material: {job.status}{job.errorMessage ? ` — ${job.errorMessage}` : ""}</p>}
    {job?.result?.assetId && <div>
      <p>Confira o material gerado antes de usá-lo no projeto.</p>
      <button type="button" onClick={() => void run(() => show(job.result!.assetId!))}>Abrir resultado</button>
      {targetClip && <button type="button" disabled={busy || disabled ||
        (job.result.status !== "draft_material_ready" && preview?.id !== job.result.assetId)} onClick={() => void run(async () => {
        if (job.result!.status !== "draft_material_ready") await post(`${root}/editing/resources/${job.result!.assetId}/review`, {
          checksum: job.result!.checksumSha256, result: "passed", observation: "Transformação conferida visualmente antes da aplicação." });
        const updated = await post<StudioDocumentRecord>(`${root}/documents/${document.documentId}/editing-resources/apply`, {
          expectedDocumentRevision: document.revision, assetId: job.result!.assetId, targetClipId: targetClip,
        }); onDocument(updated); setJob(undefined); setMessage("Trecho transformado aplicado à cena selecionada.");
      })}>{job.result.status === "draft_material_ready" ? "Aplicar transformação à cena" : "Conferi e quero aplicar à cena"}</button>}
      {!targetClip && <button type="button" disabled={busy || preview?.id !== job.result.assetId} onClick={() => void run(async () => {
        await post(`${root}/editing/resources/${job.result!.assetId}/review`, { checksum: job.result!.checksumSha256,
          result: "passed", observation: "Material visualmente conferido pelo usuário no estúdio." });
        await attach(job.result!.assetId!);
      })}>Conferi o resultado e quero usá-lo</button>}
    </div>}
    {message && <p role="status">{message}</p>}
  </details>;
}
