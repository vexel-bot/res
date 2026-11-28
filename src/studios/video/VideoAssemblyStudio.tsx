import React from "react";
import { apiFetch } from "../../api";
import { productApi, type AssetRecord, type StudioDocumentRecord, type StudioDocumentCreate } from "../../api/productApi";
import { useProductData } from "../../context/ProductDataContext";
import { ProjectFiles, saveDownload, useProjectFiles } from "../shared/ProjectFiles";
import { buildCopyHandoff, type CopyData, type SavedCopy } from "./adCopy";
import { decoupageTopics, type DecoupageTopic } from "./decoupageTechniques";
import { directionNotes, type DirectionTopic } from "./directionNotes";
import { scriptFormats, scriptGuidance } from "./scriptDirection";
import { initialVideoBrief, videoDocumentInput } from "./videoModel";
import { VideoAdCopyPanel } from "./VideoAdCopyPanel";

const videoApi = "/api/v1/studios/v1/video";
type Job = Awaited<ReturnType<typeof productApi.studioGenerationJob>>;
const pending = new Set(["queued", "running", "retrying", "cancel_requested"]);

type InitialBrief = { title: string; objective: string; angle?: string; hook?: string; copyCampaign?: CopyData };

export function VideoAssemblyStudio({ initialBrief }: { initialBrief?: InitialBrief }) {
  const { activeWorkspace, status, error } = useProductData();
  if (!activeWorkspace) return <p role="status">{error || (status === "loading" ? "Carregando projetos…" : "Selecione o espaço de trabalho para abrir o estúdio.")}</p>;
  return <AssemblyWorkspace key={activeWorkspace.id} workspaceId={activeWorkspace.id} brandRevision={activeWorkspace.brandRevision || 1} initialBrief={initialBrief} />;
}

function AssemblyWorkspace({ workspaceId, brandRevision, initialBrief }: {
  workspaceId: string;
  brandRevision: number;
  initialBrief?: InitialBrief;
}) {
  const [brief, setBrief] = React.useState(() => ({
    ...initialVideoBrief(initialBrief),
    audience: initialBrief?.copyCampaign?.audience?.slice(0, 2000) || "",
  }));
  const [documents, setDocuments] = React.useState<StudioDocumentRecord[]>([]);
  const [active, setActive] = React.useState<StudioDocumentRecord>();
  const [materials, setMaterials] = React.useState<AssetRecord[]>([]);
  const [directionTopics, setDirectionTopics] = React.useState<DirectionTopic[]>([]);
  const [scriptFormat, setScriptFormat] = React.useState<typeof scriptFormats[number]>();
  const [savedCopy, setSavedCopy] = React.useState<SavedCopy>();
  const [copyLoaded, setCopyLoaded] = React.useState(false);
  const receiveCopy = React.useCallback((value?: SavedCopy) => {
    setSavedCopy(value);
    setCopyLoaded(true);
  }, []);
  const [selectedDecoupageTopics, setSelectedDecoupageTopics] = React.useState<DecoupageTopic[]>([]);
  const [plan, setPlan] = React.useState("");
  const [job, setJob] = React.useState<Job>();
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [available, setAvailable] = React.useState<boolean>();
  const [refresh, setRefresh] = React.useState(0);
  const scriptFormatId = React.useId();
  const attempt = React.useRef<{ key: string; body: string } | undefined>(undefined);
  const draft = React.useRef<StudioDocumentCreate | undefined>(undefined);
  const docId = active?.documentId;
  const { files, error: archiveError } = useProjectFiles(docId, refresh);
  const editable = active?.composition.narrative?.assemblyEngine === "moneyprinterturbo";
  const durationSeconds = (active?.composition.pages[0]?.durationMs || 15000) / 1000;
  const commercialCopy = buildCopyHandoff(savedCopy);

  const report = (cause: unknown) => setError(cause instanceof Error ? cause.message : "Não foi possível concluir a operação.");

  React.useEffect(() => {
    let current = true;
    Promise.all([
      productApi.studioDocuments(workspaceId),
      apiFetch<{ available: boolean }>(`${videoApi}/assembly-capability`),
    ]).then(([rows, capability]) => {
      if (!current) return;
      setDocuments(rows.filter(row => row.contentType === "video" || row.contentType === "presenter"));
      setAvailable(capability.available);
    }).catch(cause => { if (current) report(cause); });
    return () => { current = false; };
  }, [workspaceId, refresh]);

  React.useEffect(() => {
    if (!docId || !editable) return;
    let current = true;
    productApi.studioGenerationJobs(workspaceId, { documentId: docId, jobType: "timeline_render" })
      .then(rows => {
        if (!current) return;
        const latest = rows.find(row => row.provider === "moneyprinterturbo");
        if (latest) {
          setJob(latest);
          const assembly = latest.request?.assembly;
          if (assembly) setPlan(value => value || JSON.stringify(assembly, null, 2));
        }
      }).catch(cause => { if (current) report(cause); });
    return () => { current = false; };
  }, [docId, editable, workspaceId]);

  React.useEffect(() => {
    if (!job || !pending.has(job.status)) return;
    let current = true;
    const timer = setTimeout(() => {
      productApi.studioGenerationJob(job.id).then(next => {
        if (!current) return;
        setJob(next);
        if (!pending.has(next.status)) setRefresh(value => value + 1);
      }).catch(cause => { if (current) report(cause); });
    }, 1500);
    return () => { current = false; clearTimeout(timer); };
  }, [job]);

  async function run(task: () => Promise<void>) {
    setError("");
    setBusy(true);
    try { await task(); } catch (cause) { report(cause); } finally { setBusy(false); }
  }

  async function create() {
    if (!draft.current) {
      const input = videoDocumentInput(workspaceId, brief, []);
      input.brandRevision = brandRevision;
      input.composition.narrative = { assemblyEngine: "moneyprinterturbo" };
      if (initialBrief?.copyCampaign) {
        const { audience: _audience, ...copyCampaign } = initialBrief.copyCampaign;
        input.composition.narrative.copyCampaign = copyCampaign;
        input.brief.angle = initialBrief.angle?.slice(0, 1000) || "";
        input.brief.hook = initialBrief.hook?.slice(0, 2000) || "";
      }
      draft.current = input;
    }
    const input = draft.current;
    const saved = await productApi.createStudioDocument(input).catch(async cause => {
      const recovered = (await productApi.studioDocuments(workspaceId)).find(row => row.correlationId === input.correlationId);
      if (!recovered) throw cause;
      return recovered;
    });
    draft.current = undefined;
    open(saved);
    setRefresh(value => value + 1);
  }

  function open(project?: StudioDocumentRecord) {
    setActive(project);
    setMaterials([]);
    setDirectionTopics([]);
    setScriptFormat(undefined);
    setSavedCopy(undefined);
    setCopyLoaded(false);
    setSelectedDecoupageTopics([]);
    setPlan("");
    setJob(undefined);
    attempt.current = undefined;
  }

  async function assemble() {
    if (!active) return;
    const parsed: unknown = JSON.parse(plan);
    const assembly = parsed && typeof parsed === "object" && "assembly" in parsed ? parsed.assembly : parsed;
    const body = JSON.stringify({ expectedRevision: active.revision, assembly });
    if (!attempt.current || attempt.current.body !== body) attempt.current = { key: crypto.randomUUID(), body };
    const next = await apiFetch<Job>(`${videoApi}/documents/${encodeURIComponent(active.documentId)}/assemblies`, {
      method: "POST",
      headers: { "Idempotency-Key": attempt.current.key },
      body,
    });
    setJob(next);
    setRefresh(value => value + 1);
  }

  function exportBrief() {
    if (!active) return;
    const selectedNotes = directionNotes.filter(note => directionTopics.includes(note.id));
    const decoupageNotes = decoupageTopics.filter(topic => selectedDecoupageTopics.includes(topic.id));
    const copy = (!scriptFormat || scriptFormat.id === "ad") ? commercialCopy : undefined;
    const format = scriptFormat || (copy ? scriptFormats[0] : undefined);
    const packet = {
      briefing: active.brief,
      materials: [...new Map([
        ...files.filter(file => file.available && file.role === "material").map(file => [file.assetId, file.title] as const),
        ...materials.map(asset => [asset.id, asset.title] as const),
      ]).entries()].map(([assetId, title]) => ({ assetId, title })),
      instructions: [
        copy
          ? "Você dirige o roteiro e a edição. Use a abertura comercial escolhida como ponto de partida e decida como realizá-la em imagem e som."
          : "Você dirige o roteiro e a edição. Use o repertório como referência e escolha o gancho, a ordem da revelação, os planos, as transições e o som conforme o briefing.",
        "Entregue as decisões de roteiro, decupagem e revisão em texto separado do JSON de montagem. Crie cenas especiais à parte e devolva os clipes prontos.",
        "Use os IDs dos arquivos enviados à Clicko. Envie novos clipes à Clicko para obter seus IDs.",
        "Devolva o plano no formato abaixo. Cada corte usa quadros a 30 fps. A ordem da lista é a ordem final.",
        "Use uma mixagem final na mesma duração do vídeo. Sem audioAssetId, a montagem sai muda.",
      ],
      scriptDirection: {
        ...scriptGuidance,
        ...(copy ? { approach: [copy.direction[0], ...scriptGuidance.approach.slice(1)] } : {}),
        ...(format ? { format } : {}),
      },
      ...(copy ? { commercialCopy: { ...copy, durationSeconds } } : {}),
      ...(!copy && format?.id === "ad" ? { commercialCopy: {
        status: "pending",
        instruction: "A copy comercial do projeto está pendente. Direcione o esqueleto audiovisual com o briefing disponível. Marque as lacunas de promessa, oferta, prova e CTA.",
      } } : {}),
      ...(selectedNotes.length ? { directionNotes: selectedNotes } : {}),
      ...(decoupageNotes.length ? { decoupageNotes } : {}),
      assembly: { aspect: "9:16", clips: [{ assetId: "id-do-clipe", startFrame: 0, durationFrames: 60, fit: "contain" }], audioAssetId: null },
    };
    saveDownload(new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" }), "direcao-claude.json");
  }

  const rendering = !!job && pending.has(job.status);
  return <main className="space-y-5">
    <header>
      <h1 className="text-2xl font-semibold">Estúdio de vídeo</h1>
      <p>O Claude dirige o corte. O MoneyPrinterTurbo monta os clipes e a mixagem.</p>
    </header>
    {error && <p role="alert">{error}</p>}
    {available === false && <p role="status">O serviço de montagem está indisponível. Você ainda pode consultar os projetos.</p>}
    <div className="flex flex-wrap items-end gap-3">
      <label className="grid gap-1">Projeto
        <select value={docId || ""} disabled={busy || rendering} onChange={event => open(documents.find(row => row.documentId === event.target.value))}>
          <option value="">Novo projeto</option>
          {documents.map(row => <option key={row.documentId} value={row.documentId}>{row.title}</option>)}
        </select>
      </label>
      <button type="button" disabled={busy || rendering} onClick={() => setRefresh(value => value + 1)}>Atualizar projetos</button>
    </div>
    {!active && <form className="grid max-w-2xl gap-3" onSubmit={event => { event.preventDefault(); void run(create); }}>
      <label className="grid gap-1">Título <input required maxLength={240} value={brief.title} onChange={event => setBrief({ ...brief, title: event.target.value })} /></label>
      <label className="grid gap-1">Público <input required maxLength={2000} value={brief.audience} onChange={event => setBrief({ ...brief, audience: event.target.value })} /></label>
      <label className="grid gap-1">Briefing <textarea required rows={5} maxLength={1000} value={brief.objective} onChange={event => setBrief({ ...brief, objective: event.target.value })} /></label>
      <label className="grid gap-1">Duração desejada (segundos) <input required type="number" min={1} max={600} value={brief.duration || ""} onChange={event => setBrief({ ...brief, duration: Number(event.target.value) })} /></label>
      <button className="justify-self-start rounded-lg bg-blue-600 px-4 py-2 text-white" disabled={busy || !brief.title.trim() || !brief.audience.trim() || !brief.objective.trim()}>Salvar projeto</button>
    </form>}
    {active && <section className="space-y-4" aria-label="Detalhes do projeto">
      <h2 className="text-xl font-semibold">{active.title}</h2>
      <p>{active.brief.objective}</p>
      {editable && <>
        <VideoAdCopyPanel key={active.documentId} project={active} durationSeconds={durationSeconds} onSaved={receiveCopy} disabled={busy || rendering} />
        <label className="grid gap-1">Enviar clipes prontos e áudio
          <input type="file" multiple accept=".mp4,.wav,.mp3,.flac" disabled={busy || rendering} onChange={event => {
            const selected = Array.from(event.currentTarget.files || []);
            event.currentTarget.value = "";
            void run(async () => {
              let project = active;
              for (const file of selected) {
                const body = new FormData();
                body.set("title", file.name);
                body.set("file", file);
                const uploaded = await apiFetch<AssetRecord>(`${videoApi}/documents/${encodeURIComponent(project.documentId)}/assembly-materials`, { method: "POST", body });
                setMaterials(rows => [...rows, uploaded]);
                const assets = [...project.assets, {
                  id: uploaded.id, mediaType: uploaded.mediaType || file.type,
                  checksum: uploaded.checksumSha256, origin: "workspace" as const,
                  rightsStatus: "unknown" as const, provenance: {},
                }];
                project = await productApi.replaceStudioDocument(project.documentId, project.revision, { ...project, assets });
                setActive(project);
                setRefresh(value => value + 1);
              }
            });
          }} />
        </label>
        {materials.length > 0 && <ul>{materials.map(asset => <li key={asset.id}>{asset.title} · <code>{asset.id}</code></li>)}</ul>}
        <div className="grid max-w-sm gap-1">
          <label htmlFor={scriptFormatId}>Objetivo do roteiro no briefing</label>
          <select id={scriptFormatId} value={scriptFormat?.id ?? ""} onChange={event => {
            const id = event.currentTarget.value;
            setScriptFormat(scriptFormats.find(format => format.id === id));
          }}>
            <option value="">{commercialCopy ? "Anúncio pela copy salva" : "Claude define pelo briefing"}</option>
            {scriptFormats.map(format => <option key={format.id} value={format.id}>{format.title}</option>)}
          </select>
        </div>
        <fieldset className="space-y-2">
          <legend>Conhecimentos de direção para incluir no briefing</legend>
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {directionNotes.map(note => <label key={note.id} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={directionTopics.includes(note.id)}
                onChange={event => {
                  const checked = event.currentTarget.checked;
                  setDirectionTopics(topics => checked ? [...topics, note.id] : topics.filter(topic => topic !== note.id));
                }}
              />
              {note.title}
            </label>)}
          </div>
        </fieldset>
        <details>
          <summary className="cursor-pointer">Técnicas práticas de decupagem</summary>
          <fieldset className="mt-2 grid gap-2">
            <legend>Inclua os temas pertinentes ao corte</legend>
            {decoupageTopics.map(topic => <label key={topic.id} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selectedDecoupageTopics.includes(topic.id)}
                onChange={event => {
                  const checked = event.currentTarget.checked;
                  setSelectedDecoupageTopics(topics => checked ? [...topics, topic.id] : topics.filter(id => id !== topic.id));
                }}
              />
              {topic.title}
            </label>)}
          </fieldset>
        </details>
        <button type="button" disabled={!copyLoaded} onClick={exportBrief}>Baixar briefing e formato do plano para o Claude</button>
        <label className="grid gap-1">Importar o plano do Claude
          <input type="file" accept=".json,application/json" disabled={rendering} onChange={event => {
            const file = event.currentTarget.files?.[0];
            event.currentTarget.value = "";
            if (file) void run(async () => {
              if (file.size > 128 * 1024) throw new Error("O plano deve ter até 128 KB.");
              const data = JSON.parse(await file.text());
              setPlan(JSON.stringify(data, null, 2));
            });
          }} />
        </label>
        <label className="grid max-w-2xl gap-1">Plano de montagem do Claude (JSON)
          <textarea className="font-mono" value={plan} rows={7} disabled={rendering} onChange={event => setPlan(event.target.value)} />
        </label>
        <button type="button" className="rounded-lg bg-blue-600 px-4 py-2 text-white" disabled={!available || !plan.trim() || busy || rendering} onClick={() => void run(assemble)}>Montar vídeo</button>
        {job && <div role="status">
          {rendering ? `Montando · ${job.progress}%` : job.status === "succeeded" ? "Montagem concluída" : job.errorMessage || job.errorCode || job.status}
          {job.status === "failed" && <button className="ml-3" type="button" disabled={busy} onClick={() => void run(async () => setJob(await productApi.retryStudioGenerationJob(job.id)))}>Tentar novamente</button>}
          {(job.status === "queued" || job.status === "running" || job.status === "retrying") && <button className="ml-3" type="button" disabled={busy} onClick={() => void run(async () => setJob(await productApi.cancelStudioGenerationJob(job.id)))}>Cancelar montagem</button>}
          {rendering && <button className="ml-3" type="button" onClick={() => void run(async () => setJob(await productApi.studioGenerationJob(job.id)))}>Atualizar andamento</button>}
        </div>}
      </>}
      <h3 className="font-semibold">Vídeos e materiais</h3>
      {archiveError ? <p role="alert">{archiveError}</p> : <ProjectFiles key={docId} files={files} />}
    </section>}
  </main>;
}
