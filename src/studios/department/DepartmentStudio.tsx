import React from "react";
import {
  ArrowDownToLine,
  Upload,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  FlaskConical,
  Image,
  Layers,
  Plus,
  RefreshCw,
  Send,
  Target,
  X,
} from "lucide-react";
import { useProductData } from "../../context/ProductDataContext";
import {
  productApi,
  type StudioDocumentRecord,
  type StudioGenerationJobRecord,
  type StudioReviewRecord,
  type AssetRecord,
} from "../../api/productApi";
import { craftApi } from "../craft/craftApi";
import { ReviewSnapshotPreview } from "../ReviewSnapshotPreview";
import {
  departmentApi,
  type DepartmentProject,
  type ProjectInput,
  type StudioFormat,
} from "./departmentApi";
import "./department.css";

export interface DepartmentStudioProps {
  pathname?: string;
  search?: string;
  navigate?: (url: string) => void;
  mode?: string;
  sourceAssetId?: string;
  campaignId?: string;
  initialBrief?: { title: string; objective: string };
}
const labels = { image: "Imagem", carousel: "Carrossel", video: "Vídeo" };
const statuses: Record<string, string> = {
  queued: "Na fila de produção",
  running: "Produzindo",
  retrying: "Tentando novamente",
  cancel_requested: "Cancelando",
  cancelled: "Cancelado",
  succeeded: "Primeira versão pronta",
  failed: "Produção interrompida",
};
const message = (error: unknown) =>
  error instanceof Error
    ? error.message
    : "Não foi possível concluir. Recarregue para conferir o estado salvo.";
const isTerminal = (job?: StudioGenerationJobRecord) =>
  !job || ["failed", "cancelled", "succeeded"].includes(job.status);

export function DepartmentStudio(props: DepartmentStudioProps) {
  const data = useProductData();
  const workspace = data.activeWorkspace;
  if (!workspace || data.status === "guest" || data.status === "error")
    return (
      <section className="department-studio">
        <div className="ds-access">
          <FlaskConical size={32} />
          <small>CLICKO STUDIOS</small>
          <h1>Seu departamento criativo.</h1>
          <p>
            {data.status === "error"
              ? data.error
              : data.status === "guest"
                ? "Entre na sua conta para criar e retomar os projetos da sua marca."
                : "Carregando o contexto da marca…"}
          </p>
          {data.status === "error" && (
            <button onClick={() => void data.refresh()}>
              Tentar novamente
            </button>
          )}
        </div>
      </section>
    );
  // An account/workspace change destroys all pending UI and object URLs.
  return (
    <React.Fragment key={`${data.bootstrap?.user.id}:${workspace.id}`}>
      <StudioRoom
        {...props}
        workspaceId={workspace.id}
        brandName={workspace.name}
      />
    </React.Fragment>
  );
}

function StudioRoom({
  workspaceId,
  brandName,
  pathname = window.location.pathname,
  search = window.location.search,
  navigate = (url) => {
    window.location.assign(url);
  },
  mode,
  sourceAssetId,
  campaignId,
  initialBrief,
}: DepartmentStudioProps & { workspaceId: string; brandName: string }) {
  const data = useProductData();
  const query = new URLSearchParams(search);
  const linkedPost = /^\/content\/([^/]+)\/edit/.exec(pathname)?.[1];
  const post = data.snapshot?.posts.find((p) => p.id === linkedPost);
  const linkedCampaign =
    campaignId && campaignId !== "active"
      ? campaignId
      : query.get("campaign") || undefined;
  const requestedFormat =
    query.get("format") || query.get("mode") || query.get("type") || mode || "";
  const initialFormat: StudioFormat = [
    "video",
    "presenter",
    "effects",
    "filmcraft",
    "effectcraft",
  ].includes(requestedFormat)
    ? "video"
    : ["image", "visual", "photocraft"].includes(requestedFormat) ||
        sourceAssetId
      ? "image"
      : "carousel";
  const [projects, setProjects] = React.useState<DepartmentProject[]>([]);
  const [project, setProject] = React.useState<DepartmentProject>();
  const [step, setStep] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [contextOpen, setContextOpen] = React.useState(false);
  const contextTrigger = React.useRef<HTMLButtonElement>(null);
  const openContext = (event: React.MouseEvent<HTMLButtonElement>) => {
    contextTrigger.current = event.currentTarget;
    setContextOpen(true);
  };
  const contextRef = React.useRef<HTMLElement>(null);
  React.useEffect(() => {
    if (!contextOpen) return;
    const previous = contextTrigger.current;
    contextRef.current?.querySelector<HTMLElement>("button")?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setContextOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const items = contextRef.current?.querySelectorAll<HTMLElement>(
        'button:not(:disabled), a[href], [tabindex="0"]',
      );
      if (!items?.length) return;
      const first = items[0],
        last = items[items.length - 1];
      if (event.shiftKey && window.document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && window.document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.document.addEventListener("keydown", trap);
    return () => {
      window.document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [contextOpen]);
  const [form, setForm] = React.useState<
    Omit<ProjectInput, "workspaceId" | "requestKey">
  >({
    title: initialBrief?.title || post?.title || "",
    objective: initialBrief?.objective || post?.copy?.slice(0, 1000) || "",
    audience: "",
    tone: "Claro e preciso",
    evidence: "",
    front: query.get("front") === "ads" ? "ads" : "content",
    intent: "education",
    format: initialFormat,
    campaignId: linkedCampaign,
    postId: post?.id,
    sourceAssetId,
  });
  const requestKey = React.useRef(crypto.randomUUID());
  const alive = React.useRef(true);
  const operation = React.useRef(0);
  React.useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      operation.current++;
    };
  }, []);
  const [document, setDocument] = React.useState<StudioDocumentRecord>();
  const [job, setJob] = React.useState<StudioGenerationJobRecord>();
  const [review, setReview] = React.useState<StudioReviewRecord>();
  const [history, setHistory] = React.useState<
    { version: number; label?: string | null }[]
  >([]);
  const [page, setPage] = React.useState(0);
  const [previewUrl, setPreviewUrl] = React.useState<string>();
  const [previewError, setPreviewError] = React.useState<string>();
  const [previewAttempt, setPreviewAttempt] = React.useState(0);
  const [mediaReady, setMediaReady] = React.useState(false);
  const [uploadedAssets, setUploadedAssets] = React.useState<AssetRecord[]>([]);
  const materialInput = React.useRef<HTMLInputElement>(null);
  const [comment, setComment] = React.useState("");
  const [position, setPosition] = React.useState(0);
  const [versionsOpen, setVersionsOpen] = React.useState(false);
  const activeId = React.useRef<string | undefined>(undefined);
  activeId.current = project?.id;
  const chooseProject = React.useCallback((next?: DepartmentProject) => {
    operation.current++;
    setBusy(false);
    setProject(next);
    setStep(next?.documentId ? 2 : next ? 1 : 0);
    setDocument(undefined);
    setJob(undefined);
    setReview(undefined);
    setPage(0);
    setHistory([]);
    setError(undefined);
    setNotice(undefined);
    setComment("");
    setMediaReady(false);
  }, []);
  React.useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    void departmentApi
      .list(workspaceId, controller.signal)
      .then((rows) => {
        if (controller.signal.aborted) return;
        setProjects(rows);
        const id = new URLSearchParams(search).get("project");
        const requested = id
          ? rows.find((row) => row.id === id)
          : post
            ? rows.find((row) => row.postId === post.id)
            : undefined;
        if (id && !requested)
          setError(
            "Projeto não encontrado neste workspace. Selecione outro projeto ou faça um novo pedido.",
          );
        if (requested) chooseProject(requested);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(message(e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [workspaceId, search, post?.id, chooseProject]);

  const remember = (next: DepartmentProject) => {
    setProject(next);
    setProjects((rows) => [next, ...rows.filter((row) => row.id !== next.id)]);
  };
  const run = async (action: () => Promise<void>) => {
    if (busy) return;
    const ticket = ++operation.current;
    setBusy(true);
    setError(undefined);
    setNotice(undefined);
    try {
      await action();
    } catch (e) {
      if (alive.current && ticket === operation.current) setError(message(e));
    } finally {
      if (alive.current && ticket === operation.current) setBusy(false);
    }
  };
  const loadDelivery = React.useCallback(
    async (current: DepartmentProject) => {
      if (!current.documentId) return;
      const [doc, jobs, reviews, versions] = await Promise.allSettled([
        productApi.studioDocument(current.documentId),
        current.jobId
          ? productApi.studioGenerationJob(current.jobId)
          : Promise.resolve(undefined),
        productApi.latestStudioReview(workspaceId, {
          documentId: current.documentId,
        }),
        productApi.studioDocumentVersions(current.documentId),
      ]);
      if (!alive.current || activeId.current !== current.id) return;
      if (doc.status === "fulfilled") setDocument(doc.value);
      else setError(message(doc.reason));
      if (jobs.status === "fulfilled") setJob(jobs.value);
      else setError(message(jobs.reason));
      if (reviews.status === "fulfilled") setReview(reviews.value);
      if (versions.status === "fulfilled") setHistory(versions.value.map(item => ({ version: item.number, label: item.label })));
    },
    [workspaceId],
  );
  React.useEffect(() => {
    if (project) void loadDelivery(project);
  }, [project?.id, project?.documentId, project?.jobId, loadDelivery]);
  React.useEffect(() => {
    if (!project || isTerminal(job)) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await productApi.studioGenerationJob(job!.id);
        if (cancelled) return;
        setJob(next);
        if (!isTerminal(next)) timer = setTimeout(poll, 2500);
        else await loadDelivery(project);
      } catch (e) {
        if (!cancelled) setError(message(e));
      }
    };
    timer = setTimeout(poll, 2500);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [job?.id, job?.status, project?.id, loadDelivery]);

  const pages =
    review?.snapshot.composition.pages || document?.composition.pages || [];
  const pageId = pages[page]?.id;
  const video = project?.format === "video";
  React.useEffect(() => {
    setPreviewUrl(undefined);
    setPreviewError(undefined);
    setMediaReady(false);
    if (!document || review) return;
    const controller = new AbortController();
    let url: string | undefined;
    const load = async () => {
      try {
        let blob: Blob;
        if (video) {
          if (job?.status !== "succeeded") return;
          const result = job.result || {};
          const artifact = (result.artifact || result) as Record<
            string,
            unknown
          >;
          if (typeof artifact.assetId !== "string")
            throw new Error("A produção não retornou um arquivo reproduzível.");
          blob = await productApi.studioAssetBlob(
            artifact.assetId,
            controller.signal,
          );
        } else
          blob = await craftApi.preview(
            document.documentId,
            0,
            controller.signal,
            pageId,
          );
        if (controller.signal.aborted) return;
        url = URL.createObjectURL(blob);
        setPreviewUrl(url);
      } catch (e) {
        if (!controller.signal.aborted) setPreviewError(message(e));
      }
    };
    void load();
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [
    document?.documentId,
    document?.revision,
    job?.id,
    job?.status,
    review?.id,
    pageId,
    video,
    previewAttempt,
  ]);

  const direction = project?.directions.find(
    (d) => d.id === project.directionId,
  );
  const assets = [...uploadedAssets, ...(data.snapshot?.assets || [])].filter((asset) =>
    (asset.mediaType || "").startsWith(
      form.format === "video" ? "video/" : "image/",
    ),
  );
  const update = <K extends keyof typeof form>(
    key: K,
    value: (typeof form)[K],
  ) => {
    requestKey.current = crypto.randomUUID();
    setForm((current) => ({ ...current, [key]: value }));
  };
  const canApprove =
    !!review &&
    review.status === "requested" &&
    mediaReady &&
    !comment.trim() &&
    review.documentVersion === document?.version;
  const reload = async () => {
    if (!project) {
      setProjects(await departmentApi.list(workspaceId));
      return;
    }
    const next = await departmentApi.get(project.id);
    if (!alive.current) return;
    remember(next);
    await loadDelivery(next);
    setPreviewAttempt((value) => value + 1);
  };

  return (
    <section
      className="department-studio"
      data-testid="department-studio"
      aria-label="Sala de direção Clicko Studios"
    >
      <header className="ds-top">
        <div className="ds-wordmark">
          <FlaskConical size={20} />
          <b>
            clicko<span>studios</span>
          </b>
          <i /> <small>SALA DE DIREÇÃO</small>
        </div>
        <div className="ds-brand">
          <span className="ds-dot" />
          {brandName}
          <button
            className="ds-icon"
            aria-label="Ver contexto da marca"
            onClick={openContext}
          >
            <Layers size={16} />
          </button>
        </div>
      </header>
      <div className="ds-layout">
        <aside className="ds-sidebar">
          <div className="ds-sidebar-heading">
            <small>DEPARTAMENTO CRIATIVO</small>
            <span>01—03</span>
          </div>
          <h2>
            Uma boa ideia.
            <br />
            <em>Uma direção clara.</em>
          </h2>
          <p>
            Você traz a intenção.
            <br />O Studio organiza a criação.
          </p>
          <nav className="ds-steps" aria-label="Etapas do projeto">
            {["Pedido", "Direção", "Entrega"].map((title, i) => (
              <button
                key={title}
                disabled={
                  busy ||
                  (i > 0 && !project) ||
                  (i === 2 && !project?.documentId)
                }
                className={step === i ? "is-active" : ""}
                aria-current={step === i ? "step" : undefined}
                onClick={() => setStep(i)}
              >
                <span>
                  {i + 1 < step + 1 ? <Check size={13} /> : `0${i + 1}`}
                </span>
                <div>
                  <strong>{title}</strong>
                  <small>
                    {
                      [
                        "O que vamos criar",
                        "O caminho da ideia",
                        "Olhar, ajustar e aprovar",
                      ][i]
                    }
                  </small>
                </div>
                <ArrowRight size={14} />
              </button>
            ))}
          </nav>
          <div className="ds-projects">
            <div>
              <small>SEUS PROJETOS</small>
              <button
                className="ds-icon"
                aria-label="Novo pedido"
                disabled={busy}
                onClick={() => {
                  chooseProject();
                  requestKey.current = crypto.randomUUID();
                  setForm((f) => ({
                    ...f,
                    title: "",
                    objective: "",
                    postId: undefined,
                    evidence: "",
                  }));
                }}
              >
                <Plus size={16} />
              </button>
            </div>
            {loading && <p role="status">Carregando projetos…</p>}
            {!loading && !projects.length && (
              <p>Seu próximo conteúdo começa aqui.</p>
            )}
            {projects.map((item) => (
              <button
                key={item.id}
                className={item.id === project?.id ? "is-active" : ""}
                disabled={busy}
                onClick={() => chooseProject(item)}
              >
                <span>{item.title}</span>
                <small>
                  {labels[item.format]} ·{" "}
                  {item.front === "ads" ? "Anúncio" : "Conteúdo"}
                </small>
              </button>
            ))}
          </div>
          <button className="ds-context-link" onClick={openContext}>
            <Layers size={15} /> Contexto da marca <ArrowRight size={14} />
          </button>
        </aside>
        <main className="ds-main">
          <div className="ds-toolbar">
            <div className="ds-fronts" aria-label="Frente criativa">
              {(["content", "ads"] as const).map((front) => (
                <button
                  key={front}
                  aria-pressed={(project?.front || form.front) === front}
                  disabled={!!project || busy}
                  onClick={() => {
                    update("front", front);
                    update("intent", front === "ads" ? "offer" : "education");
                  }}
                >
                  {front === "content"
                    ? "Criação de conteúdo"
                    : "Criação de anúncios"}
                </button>
              ))}
            </div>
            <button
              className="ds-icon"
              aria-label="Atualizar projeto"
              disabled={busy}
              onClick={() => void run(reload)}
            >
              <RefreshCw size={16} />
            </button>
          </div>
          {error && (
            <div className="ds-alert" role="alert">
              {error}
              <button disabled={busy} onClick={() => void run(reload)}>
                Recarregar
              </button>
            </div>
          )}
          {notice && (
            <div className="ds-notice" role="status">
              {notice}
            </div>
          )}
          {step === 0 && (
            <div className="ds-intake">
              <small className="ds-eyebrow">
                01 / PEDIDO · {form.front === "ads" ? "ANÚNCIO" : "CONTEÚDO"}
              </small>
              <h1>
                O que a sua marca
                <br />
                <em>precisa dizer agora?</em>
              </h1>
              <p>Comece pelo resultado que deseja. A forma vem depois.</p>
              {project ? (
                <div className="ds-summary">
                  <h3>{project.title}</h3>
                  <p>{project.objective}</p>
                  <dl>
                    <dt>Público</dt>
                    <dd>{project.audience}</dd>
                    <dt>Base informada</dt>
                    <dd>
                      {project.evidence ||
                        "Nenhum material de apoio informado."}
                    </dd>
                  </dl>
                  <button
                    className="ds-primary"
                    onClick={() => setStep(project.documentId ? 2 : 1)}
                  >
                    Continuar projeto <ArrowRight size={16} />
                  </button>
                </div>
              ) : (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void run(async () => {
                      const next = await departmentApi.create({
                        ...form,
                        workspaceId,
                        requestKey: requestKey.current,
                      });
                      if (!alive.current) return;
                      remember(next);
                      setStep(1);
                    });
                  }}
                >
                  <label>
                    Assunto
                    <input
                      name="title"
                      required
                      minLength={3}
                      maxLength={180}
                      placeholder="Qual ideia merece ganhar forma?"
                      value={form.title}
                      onChange={(event) => update("title", event.target.value)}
                    />
                  </label>
                  <label>
                    O que você quer que o público entenda ou faça?
                    <textarea
                      name="objective"
                      required
                      minLength={8}
                      maxLength={1000}
                      rows={3}
                      placeholder="Descreva uma mudança concreta que este conteúdo deve provocar."
                      value={form.objective}
                      onChange={(event) =>
                        update("objective", event.target.value)
                      }
                    />
                  </label>
                  <div className="ds-form-row">
                    <label>
                      Para quem?
                      <input
                        required
                        minLength={3}
                        maxLength={1000}
                        placeholder="Quem vive essa dúvida ou situação?"
                        value={form.audience}
                        onChange={(event) =>
                          update("audience", event.target.value)
                        }
                      />
                    </label>
                    <label>
                      Intenção
                      <select
                        value={form.intent}
                        onChange={(event) =>
                          update(
                            "intent",
                            event.target.value as typeof form.intent,
                          )
                        }
                      >
                        <option value="education">Ensinar algo útil</option>
                        <option value="authority">
                          Demonstrar conhecimento
                        </option>
                        <option value="offer">Apresentar uma oferta</option>
                      </select>
                    </label>
                  </div>
                  <fieldset>
                    <legend>Como você imagina a entrega?</legend>
                    <div className="ds-formats">
                      {(["image", "carousel", "video"] as const).map(
                        (format, index) => {
                          const Icon = [Image, Layers, Clapperboard][index];
                          return (
                            <button
                              type="button"
                              key={format}
                              aria-pressed={form.format === format}
                              onClick={() => {
                                update("format", format);
                                update("sourceAssetId", undefined);
                              }}
                            >
                              <Icon size={19} />
                              <b>{labels[format]}</b>
                              <small>
                                {
                                  [
                                    "Uma mensagem visual",
                                    "Uma ideia em sequência",
                                    "Uma história em movimento",
                                  ][index]
                                }
                              </small>
                            </button>
                          );
                        },
                      )}
                    </div>
                  </fieldset>
                  <label>
                    Material de origem {form.format !== "video" && "(opcional)"}
                    <select
                      aria-label="Material de origem"
                      value={form.sourceAssetId || ""}
                      onChange={(event) =>
                        update("sourceAssetId", event.target.value || undefined)
                      }
                      required={form.format === "video"}
                    >
                      <option value="">
                        {form.format === "video"
                          ? "Selecione um vídeo da biblioteca"
                          : "Sem imagem de apoio"}
                      </option>
                      {assets.map((asset) => (
                        <option key={asset.id} value={asset.id}>
                          {asset.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  {form.format === "video" && (
                    <p className="ds-help">
                      A primeira montagem utiliza o vídeo selecionado. O roteiro
                      organiza a direção; novas cenas e locução dependem de
                      produção adicional.
                    </p>
                  )}
                  <input ref={materialInput} type="file" hidden accept={form.format === "video" ? "video/mp4,video/quicktime,video/webm" : "image/png,image/jpeg,image/webp"} onChange={(event) => {
                    const file = event.target.files?.[0]; event.target.value = "";
                    if (!file) return;
                    void run(async () => {
                      const asset = await craftApi.uploadAsset(workspaceId, file);
                      if (!alive.current) return;
                      setUploadedAssets(rows => [asset, ...rows.filter(item => item.id !== asset.id)]);
                      update("sourceAssetId", asset.id);
                    });
                  }} />
                  <button type="button" className="ds-secondary" disabled={busy} onClick={() => materialInput.current?.click()}><Upload size={15} />Adicionar material</button>
                  <details>
                    <summary>Acrescentar contexto e referências</summary>
                    <label>
                      Tom de voz
                      <input
                        maxLength={500}
                        value={form.tone}
                        onChange={(event) => update("tone", event.target.value)}
                      />
                    </label>
                    <label>
                      O que podemos afirmar? Quais referências devemos
                      considerar?
                      <textarea
                        maxLength={1500}
                        rows={3}
                        placeholder="Fatos, exemplos próprios, condições e links de referência. Links são referências informadas; não são pesquisados automaticamente."
                        value={form.evidence}
                        onChange={(event) =>
                          update("evidence", event.target.value)
                        }
                      />
                    </label>
                  </details>
                  <footer>
                    <span>
                      Conteúdo com contexto,
                      <br />
                      antes de qualquer produção.
                    </span>
                    <button
                      className="ds-primary"
                      disabled={busy || loading}
                      type="submit"
                    >
                      {busy ? "Salvando pedido…" : "Explorar direções"}
                      <ArrowRight size={17} />
                    </button>
                  </footer>
                </form>
              )}
            </div>
          )}
          {step === 1 && project && (
            <div className="ds-direction">
              <small className="ds-eyebrow">
                02 / DIREÇÃO · {labels[project.format]}
              </small>
              <h1>
                Uma ideia pode seguir
                <br />
                <em>mais de um caminho.</em>
              </h1>
              <p>
                Escolha o ponto de partida que melhor representa a sua intenção.
              </p>
              <div className="ds-direction-grid">
                {project.directions.map((item, index) => (
                  <article
                    key={item.id}
                    className={
                      project.directionId === item.id ? "is-selected" : ""
                    }
                  >
                    <div className="ds-direction-art">
                      <span>
                        {String(index + 1).padStart(2, "0")} /{" "}
                        {index ? "DEMONSTRAR" : "ORGANIZAR"}
                      </span>
                      <h2>{item.opening}</h2>
                      <small>
                        {project.brandName} · {labels[project.format]}
                      </small>
                    </div>
                    <div className="ds-direction-body">
                      <h3>
                        {index
                          ? "Mostrar como acontece"
                          : "Dar clareza ao assunto"}
                      </h3>
                      <p>{item.rationale}</p>
                      <ol>
                        {item.beats.filter(Boolean).map((beat, i) => (
                          <li key={i}>{beat}</li>
                        ))}
                      </ol>
                      <button
                        disabled={busy || !!project.documentId}
                        aria-pressed={project.directionId === item.id}
                        onClick={() =>
                          void run(async () => {
                            const next = await departmentApi.choose(
                              project,
                              item.id,
                            );
                            if (alive.current) remember(next);
                          })
                        }
                      >
                        {project.directionId === item.id ? (
                          <Check size={16} />
                        ) : (
                          <ArrowRight size={16} />
                        )}
                        {project.directionId === item.id
                          ? "Direção escolhida"
                          : "Escolher direção"}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              <p className="ds-help">
                {project.planningBasis} As direções são esboços editoriais,
                sujeitos à sua revisão.
              </p>
              <div className="ds-production-bar">
                <div>
                  <b>
                    {direction
                      ? "Podemos preparar a primeira versão."
                      : "Qual caminho faz mais sentido?"}
                  </b>
                  <p>
                    {direction
                      ? "O pedido e a direção ficam preservados no projeto."
                      : "Escolha uma direção para seguir para a entrega."}
                  </p>
                </div>
                <button
                  className="ds-primary"
                  disabled={!direction || busy}
                  onClick={() =>
                    project.documentId
                      ? setStep(2)
                      : void run(async () => {
                          try {
                            const next = await departmentApi.produce(project);
                            if (!alive.current) return;
                            remember(next);
                            setStep(2);
                          } finally {
                            if (alive.current) {
                              const saved = await departmentApi.get(project.id);
                              if (alive.current) {
                                remember(saved);
                                if (saved.documentId) setStep(2);
                              }
                            }
                          }
                        })
                  }
                >
                  {busy
                    ? "Preparando…"
                    : project.documentId
                      ? "Ver entrega"
                      : "Preparar primeira versão"}
                  <ArrowRight size={17} />
                </button>
              </div>
            </div>
          )}
          {step === 2 && project && (
            <div className="ds-delivery">
              <div className="ds-delivery-head">
                <div>
                  <small className="ds-eyebrow">
                    03 / ENTREGA · {labels[project.format]}
                  </small>
                  <h1>{project.title}</h1>
                </div>
                <button
                  disabled={!history.length}
                  onClick={() => setVersionsOpen((v) => !v)}
                >
                  Versões {document ? `· ${document.version}` : ""}
                </button>
              </div>
              <div className="ds-review-grid">
                <div className="ds-preview-column">
                  <div className={`ds-media-stage ${video ? "is-video" : ""}`}>
                    {review ? (
                      <ReviewSnapshotPreview
                        review={review}
                        pageId={pageId}
                        onReady={setMediaReady}
                        onPositionChange={setPosition}
                      />
                    ) : previewUrl ? (
                      video ? (
                        <video
                          controls
                          src={previewUrl}
                          onLoadedData={() => setMediaReady(true)}
                          onTimeUpdate={(event) =>
                            setPosition(event.currentTarget.currentTime)
                          }
                          onError={() => {
                            setMediaReady(false);
                            setPreviewUrl(undefined);
                            setPreviewError(
                              "Não foi possível reproduzir este arquivo.",
                            );
                          }}
                          aria-label="Primeira montagem do projeto"
                        />
                      ) : (
                        <img
                          src={previewUrl}
                          alt={`Página ${page + 1} da entrega ${project.title}`}
                          onLoad={() => setMediaReady(true)}
                          onError={() => {
                            setMediaReady(false);
                            setPreviewUrl(undefined);
                            setPreviewError(
                              "Não foi possível exibir esta página.",
                            );
                          }}
                        />
                      )
                    ) : (
                      <div className="ds-media-empty">
                        <FlaskConical size={30} />
                        <h3>
                          {previewError
                            ? "A prévia precisa de atenção."
                            : "A sua ideia está nos bastidores."}
                        </h3>
                        <p>
                          {previewError ||
                            (job
                              ? statuses[job.status]
                              : "Conferindo o documento e a disponibilidade da produção…")}
                        </p>
                        <button
                          disabled={busy}
                          onClick={() => void run(reload)}
                        >
                          Conferir produção
                        </button>
                      </div>
                    )}
                  </div>
                  {!video && pages.length > 1 && (
                    <div className="ds-pagination">
                      <button
                        aria-label="Página anterior"
                        disabled={page <= 0}
                        onClick={() => setPage((p) => p - 1)}
                      >
                        <ChevronLeft size={18} />
                      </button>
                      <span>
                        {page + 1} / {pages.length}
                      </span>
                      {pages.map((item, i) => (
                        <button
                          className="ds-page-dot"
                          key={item.id}
                          aria-label={`Página ${i + 1}`}
                          aria-current={page === i ? "page" : undefined}
                          onClick={() => setPage(i)}
                        />
                      ))}
                      <button
                        aria-label="Próxima página"
                        disabled={page >= pages.length - 1}
                        onClick={() => setPage((p) => p + 1)}
                      >
                        <ChevronRight size={18} />
                      </button>
                    </div>
                  )}
                  {job && (
                    <div className="ds-job" role="status">
                      <span>
                        {statuses[job.status]} · {job.progress}%
                      </span>
                      <progress max={100} value={job.progress} />
                      {job.errorCode && (
                        <p>
                          {job.errorCode}: {job.errorMessage}
                        </p>
                      )}
                      {!isTerminal(job) && (
                        <button
                          disabled={busy || job.status === "cancel_requested"}
                          onClick={() =>
                            void run(async () => {
                              const next =
                                await productApi.cancelStudioGenerationJob(
                                  job.id,
                                );
                              if (alive.current) setJob(next);
                            })
                          }
                        >
                          Cancelar produção
                        </button>
                      )}
                      {["failed", "cancelled"].includes(job.status) && (
                        <button
                          disabled={busy}
                          onClick={() =>
                            void run(async () => {
                              const next =
                                await productApi.retryStudioGenerationJob(
                                  job.id,
                                );
                              if (alive.current) setJob(next);
                            })
                          }
                        >
                          Tentar produção novamente
                        </button>
                      )}
                    </div>
                  )}
                  {!job && project.status === "production_failed" && (
                    <button
                      disabled={busy}
                      onClick={() =>
                        void run(async () => {
                          const next = await departmentApi.produce(project);
                          if (alive.current) remember(next);
                        })
                      }
                    >
                      Retomar preparação
                    </button>
                  )}
                  {job?.status === "succeeded" &&
                    typeof (job.result?.artifact as Record<string, unknown>)
                      ?.assetId === "string" && (
                      <button
                        className="ds-download"
                        disabled={busy}
                        onClick={() =>
                          void run(async () => {
                            const artifact = job.result!.artifact as Record<
                              string,
                              unknown
                            >;
                            const blob = await productApi.studioAssetBlob(
                              artifact.assetId as string,
                            );
                            if (!alive.current) return;
                            const url = URL.createObjectURL(blob);
                            const link = window.document.createElement("a");
                            link.href = url;
                            link.download = `clicko-${project.id}.${video ? "mp4" : project.format === "carousel" ? "zip" : "png"}`;
                            window.document.body.appendChild(link);
                            link.click();
                            link.remove();
                            window.setTimeout(
                              () => URL.revokeObjectURL(url),
                              30000,
                            );
                          })
                        }
                      >
                        <ArrowDownToLine size={15} /> Baixar entrega{" "}
                        {project.format === "carousel" ? "completa (ZIP)" : ""}
                      </button>
                    )}
                  {document && <button className="ds-secondary" onClick={() => navigate(`/studios/native?document=${encodeURIComponent(document.documentId)}&mode=${video ? 'video' : 'visual'}`)}>Abrir edição avançada</button>}
                  {previewUrl && mediaReady && (
                    <a
                      className="ds-download"
                      href={previewUrl}
                      download={`clicko-${project.id}${video ? ".mp4" : `-pagina-${page + 1}.png`}`}
                    >
                      <ArrowDownToLine size={15} /> Baixar{" "}
                      {video ? "vídeo" : "página"} · prévia para revisão
                    </a>
                  )}
                </div>
                <aside className="ds-review-panel">
                  <small className="ds-eyebrow">SEU OLHAR, SUA DIREÇÃO</small>
                  <h2>
                    O que você vê
                    <br />
                    <em>nesta entrega?</em>
                  </h2>
                  <div className="ds-intention">
                    <Target size={17} />
                    <div>
                      <b>A intenção</b>
                      <p>{project.objective}</p>
                    </div>
                  </div>
                  <details>
                    <summary>Por que este caminho?</summary>
                    <p>{direction?.rationale}</p>
                    <p>Público: {project.audience}</p>
                    <p>
                      {project.evidence ||
                        "Nenhuma evidência adicional foi informada."}
                    </p>
                  </details>
                  <label>
                    Seu pedido de ajuste
                    <textarea
                      rows={4}
                      maxLength={4000}
                      placeholder="Diga o que precisa mudar e por quê."
                      value={comment}
                      onChange={(event) => setComment(event.target.value)}
                    />
                  </label>
                  <small>
                    {video
                      ? `Comentário vinculado a ${position.toFixed(1)}s do vídeo.`
                      : `Comentário vinculado à página ${page + 1}.`}
                  </small>
                  <button
                    className="ds-secondary"
                    disabled={
                      busy || !comment.trim() || !document || !isTerminal(job)
                    }
                    onClick={() =>
                      void run(async () => {
                        let fixed = review;
                        if (!fixed || fixed.status !== "requested")
                          fixed = await productApi.requestStudioReview(
                            document!.documentId,
                            undefined,
                            video ? job?.id : undefined,
                          );
                        const next = await productApi.decideStudioReview(
                          fixed.id,
                          "request_changes",
                          `${video ? `[${position.toFixed(1)}s]` : `[Página ${page + 1}]`} ${comment.trim()}`,
                        );
                        if (!alive.current) return;
                        setReview(next);
                        setComment("");
                        setNotice(
                          "Pedido de ajuste registrado na revisão. Ele aguarda execução; a mídia ainda não foi alterada.",
                        );
                      })
                    }
                  >
                    <Send size={15} /> Enviar pedido de ajuste
                  </button>
                  {!review || review.status !== "requested" ? (
                    <button
                      className="ds-primary"
                      disabled={
                        busy ||
                        !mediaReady ||
                        !document ||
                        job?.status !== "succeeded"
                      }
                      onClick={() =>
                        void run(async () => {
                          const next = await productApi.requestStudioReview(
                            document!.documentId,
                            undefined,
                            video ? job?.id : undefined,
                          );
                          if (alive.current) {
                            setReview(next);
                            setNotice(
                              "Versão fixada para revisão. Confira a mídia antes de aprovar.",
                            );
                          }
                        })
                      }
                    >
                      Iniciar revisão <ArrowRight size={16} />
                    </button>
                  ) : video ? (
                    <button
                      className="ds-primary"
                      disabled={busy || !mediaReady || !!comment.trim()}
                      onClick={() =>
                        navigate(
                          `/approvals/${encodeURIComponent(project.postId || "")}?review=${encodeURIComponent(review.id)}`,
                        )
                      }
                    >
                      Revisar e aprovar vídeo <ArrowRight size={16} />
                    </button>
                  ) : (
                    <button
                      className="ds-primary"
                      disabled={busy || !canApprove}
                      onClick={() =>
                        void run(async () => {
                          const next = await productApi.decideStudioReview(
                            review.id,
                            "approve",
                          );
                          if (alive.current) {
                            setReview(next);
                            setNotice(
                              "Entrega aprovada. A publicação continua no fluxo de distribuição.",
                            );
                          }
                        })
                      }
                    >
                      <Check size={16} /> Aprovar entrega
                    </button>
                  )}
                  <p className="ds-help">
                    {review?.status === "approved"
                      ? "Esta versão foi aprovada."
                      : comment.trim()
                        ? "Envie ou remova o pedido de ajuste antes de aprovar."
                        : video
                          ? "A aprovação de vídeo inclui a conferência de áudio na revisão."
                          : "A revisão preserva a versão exata que você avaliou."}
                  </p>
                  {project.postId && (
                    <button
                      className="ds-text-button"
                      onClick={() =>
                        navigate(
                          `/content/${encodeURIComponent(project.postId!)}`,
                        )
                      }
                    >
                      Abrir conteúdo <ArrowRight size={14} />
                    </button>
                  )}
                </aside>
              </div>
              {versionsOpen && (
                <section className="ds-history">
                  <h3>Histórico preservado</h3>
                  {history.map((item) => (
                    <p key={item.version}>
                      Versão {item.version} · {item.label || "Alteração salva"}
                    </p>
                  ))}
                  <p className="ds-help">
                    A aprovação se refere à versão fixada na revisão. O
                    histórico mantém os documentos anteriores.
                  </p>
                </section>
              )}
            </div>
          )}
          <footer className="ds-room-footer">
            <span>
              <span className="ds-dot" />{" "}
              {project
                ? "Projeto salvo no workspace"
                : "Seu contexto, sua autoria"}
            </span>
            <span>CLICKO / CREATIVE DEPARTMENT</span>
          </footer>
        </main>
      </div>
      {contextOpen && (
        <div
          className="ds-modal-backdrop"
          onClick={() => setContextOpen(false)}
        >
          <section
            ref={contextRef}
            className="ds-context"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ds-context-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              autoFocus
              className="ds-icon"
              aria-label="Fechar contexto"
              onClick={() => setContextOpen(false)}
            >
              <X size={20} />
            </button>
            <small className="ds-eyebrow">O PONTO DE PARTIDA</small>
            <h2 id="ds-context-title">{brandName}</h2>
            <p>
              Este projeto pertence ao workspace ativo. O contexto orienta o
              pedido; a criação acontece nos Studios.
            </p>
            {project && (
              <dl>
                <dt>Objetivo</dt>
                <dd>{project.objective}</dd>
                <dt>Público</dt>
                <dd>{project.audience}</dd>
                <dt>Referências informadas</dt>
                <dd>{project.evidence || "Nenhuma referência adicional."}</dd>
              </dl>
            )}
            <button
              className="ds-secondary"
              onClick={() => navigate("/brand-memory")}
            >
              <ArrowLeft size={15} /> Abrir memória da marca
            </button>
          </section>
        </div>
      )}
    </section>
  );
}
