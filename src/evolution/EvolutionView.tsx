import React from "react";
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Circle,
  Search,
} from "lucide-react";
import { apiFetch, apiFetchBlob } from "../api";
import "./evolution.css";

export interface EvolutionEntry {
  id: string;
  date: string;
  category: keyof typeof categories;
  status: keyof typeof statuses;
  title: string;
  summary: string;
  impact: string;
  document: string;
  requirements: string[];
  evidence: string[];
}
interface RecordDetail extends EvolutionEntry {
  markdown: string;
  checksumSha256: string;
}
const categories = {
  feature: "Funcionalidade",
  update: "Atualização",
  fix: "Correção",
  removal: "Exclusão",
  analysis: "Análise",
  pending: "Pendência",
};
const statuses = {
  integrated: "Integrado à main",
  implemented: "Implementado nesta branch",
  in_progress: "Em andamento",
  planned: "Planejado",
};
const message = (e: unknown) =>
  e instanceof Error ? e.message : "Não foi possível carregar a evolução.";
const dateLabel = (value: string) =>
  new Intl.DateTimeFormat("pt-BR", {
    timeZone: "UTC",
    dateStyle: "medium",
  }).format(new Date(`${value}T12:00:00Z`));
const normalize = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

/** A deliberately small Markdown subset: source text is always rendered as text, never HTML. */
function DocumentBody({ value }: { value: string }) {
  return (
    <div className="ev-document">
      {value.split(/\r?\n\s*\r?\n/).map((block, index) => {
        if (/^#{1,3} /.test(block)) {
          const text = block.replace(/^#{1,3} /, "");
          return block.startsWith("# ") ? (
            <h2 key={index}>{text}</h2>
          ) : (
            <h3 key={index}>{text}</h3>
          );
        }
        if (block.split("\n").every((line) => line.startsWith("- ")))
          return (
            <ul key={index}>
              {block.split("\n").map((line, i) => (
                <li key={i}>{line.slice(2)}</li>
              ))}
            </ul>
          );
        if (/^https:\/\//.test(block) && !/\s/.test(block))
          return (
            <p key={index}>
              <a href={block} target="_blank" rel="noreferrer">
                {block}
              </a>
            </p>
          );
        return <p key={index}>{block}</p>;
      })}
    </div>
  );
}

export function EvolutionView({
  navigate = (url) => window.location.assign(url),
}: {
  navigate?: (url: string) => void;
}) {
  const [entries, setEntries] = React.useState<EvolutionEntry[]>([]);
  const [updatedAt, setUpdatedAt] = React.useState("");
  const [selected, setSelected] = React.useState<string>();
  const [detail, setDetail] = React.useState<RecordDetail>();
  const [search, setSearch] = React.useState("");
  const [category, setCategory] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [error, setError] = React.useState<string>();
  const [detailError, setDetailError] = React.useState<string>();
  const [loading, setLoading] = React.useState(true);
  const [retry, setRetry] = React.useState(0);
  const [detailRetry, setDetailRetry] = React.useState(0);
  const [downloading, setDownloading] = React.useState(false);
  const alive = React.useRef(true);
  React.useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  React.useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(undefined);
    void apiFetch<{ entries: EvolutionEntry[]; updatedAt: string }>(
      "/api/v1/product-evolution",
      { signal: controller.signal },
    )
      .then((result) => {
        if (controller.signal.aborted) return;
        setEntries(result.entries);
        setUpdatedAt(result.updatedAt);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(message(e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [retry]);
  React.useEffect(() => {
    setDetail(undefined);
    setDetailError(undefined);
    if (!selected) return;
    const controller = new AbortController();
    void apiFetch<RecordDetail>(
      `/api/v1/product-evolution/${encodeURIComponent(selected)}`,
      { signal: controller.signal },
    )
      .then((value) => {
        if (!controller.signal.aborted) setDetail(value);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setDetailError(message(e));
      });
    return () => controller.abort();
  }, [selected, detailRetry]);
  const visible = entries.filter(
    (entry) =>
      (!category || entry.category === category) &&
      (!status || entry.status === status) &&
      normalize(
        [entry.title, entry.summary, ...entry.requirements].join(" "),
      ).includes(normalize(search)),
  );
  const download = async () => {
    if (!detail || downloading) return;
    setDownloading(true);
    setDetailError(undefined);
    try {
      const blob = await apiFetchBlob(
        `/api/v1/product-evolution/${encodeURIComponent(detail.id)}/document`,
      );
      if (!alive.current) return;
      const url = URL.createObjectURL(blob);
      const link = window.document.createElement("a");
      link.href = url;
      link.download = detail.document;
      window.document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) {
      if (alive.current) setDetailError(message(e));
    } finally {
      if (alive.current) setDownloading(false);
    }
  };
  return (
    <section className="evolution-view" aria-label="Evolução do sistema">
      <header>
        <div>
          <small>CLICKO / CADERNO DE EVOLUÇÃO</small>
          <h1>
            O que estamos
            <br />
            <em>construindo juntos.</em>
          </h1>
          <p>
            Entregas, decisões e próximos passos. Com contexto e evidências.
          </p>
        </div>
        <button onClick={() => navigate("/studios")}>
          Abrir Studios <ArrowRight size={16} />
        </button>
      </header>
      {error ? (
        <div className="ev-error" role="alert">
          <p>{error}</p>
          <button onClick={() => setRetry((value) => value + 1)}>
            Tentar novamente
          </button>
        </div>
      ) : loading ? (
        <p role="status">Carregando o histórico documentado…</p>
      ) : (
        <>
          <div className="ev-overview">
            <div>
              <BookOpen size={19} />
              <p>
                <b>{entries.length} registros documentados</b>
                <span>
                  {updatedAt && `Atualizado em ${dateLabel(updatedAt)}`}
                </span>
              </p>
            </div>
            <p>
              “Integrado” indica presença na main.
              <br />
              Pendências de execução continuam explícitas.
            </p>
          </div>
          <div className="ev-filters">
            <label>
              <Search size={16} />
              <input
                aria-label="Pesquisar evolução"
                placeholder="Pesquisar assunto ou demanda"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <label>
              Tipo
              <select
                aria-label="Tipo de registro"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
              >
                <option value="">Todos os tipos</option>
                {Object.entries(categories).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Situação
              <select
                aria-label="Situação do registro"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
              >
                <option value="">Todas as situações</option>
                {Object.entries(statuses).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="ev-grid">
            <div className="ev-list" aria-label="Registros de evolução">
              {!visible.length && (
                <p role="status">Nenhum registro corresponde aos filtros.</p>
              )}
              {visible.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => setSelected(entry.id)}
                  aria-pressed={selected === entry.id}
                >
                  <div>
                    <time dateTime={entry.date}>{dateLabel(entry.date)}</time>
                    <span className={`ev-badge ev-${entry.status}`}>
                      {statuses[entry.status]}
                    </span>
                  </div>
                  <small>{categories[entry.category]}</small>
                  <h2>{entry.title}</h2>
                  <p>{entry.summary}</p>
                  <span className="ev-read">
                    Ler documento <ArrowRight size={14} />
                  </span>
                </button>
              ))}
            </div>
            <article
              className="ev-reader"
              aria-label="Documento de evolução"
              aria-live="polite"
            >
              {!selected ? (
                <div className="ev-reader-empty">
                  <BookOpen size={30} />
                  <h2>Uma história que fica registrada.</h2>
                  <p>
                    Selecione uma entrega ou pendência para ler o documento,
                    seus requisitos e o que falta comprovar.
                  </p>
                  <button onClick={() => setSelected("identity-research")}>
                    Ver pesquisa de personagens <ArrowRight size={15} />
                  </button>
                </div>
              ) : (
                <>
                  <button
                    className="ev-back"
                    onClick={() => setSelected(undefined)}
                  >
                    <ArrowLeft size={14} /> Fechar documento
                  </button>
                  {detailError && (
                    <div className="ev-error" role="alert">
                      <p>{detailError}</p>
                      <button
                        onClick={() => setDetailRetry((value) => value + 1)}
                      >
                        Recarregar documento
                      </button>
                    </div>
                  )}
                  {!detail && !detailError && (
                    <p role="status">Carregando documento…</p>
                  )}
                  {detail && (
                    <>
                      <div className="ev-reader-top">
                        <span className={`ev-badge ev-${detail.status}`}>
                          {statuses[detail.status]}
                        </span>
                        <button
                          disabled={downloading}
                          onClick={() => void download()}
                        >
                          <ArrowDownToLine size={14} />{" "}
                          {downloading ? "Preparando…" : "Baixar .md"}
                        </button>
                      </div>
                      <p className="ev-impact">{detail.impact}</p>
                      <DocumentBody value={detail.markdown} />
                      <section className="ev-requirements">
                        <h3>Requisitos registrados</h3>
                        {detail.requirements.map((item) => (
                          <p key={item}>
                            <Circle size={10} aria-hidden="true" />
                            {item}
                          </p>
                        ))}
                        <small>
                          Esta lista registra o escopo solicitado; não é uma
                          declaração de conclusão.
                        </small>
                      </section>
                      <details>
                        <summary>Evidências e arquivo de origem</summary>
                        <p>{detail.document}</p>
                        <code>SHA-256 {detail.checksumSha256}</code>
                        <ul>
                          {detail.evidence.map((value) => (
                            <li key={value}>
                              {/^https:\/\//.test(value) ? (
                                <a
                                  href={value}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {value}
                                </a>
                              ) : (
                                <code>{value}</code>
                              )}
                            </li>
                          ))}
                        </ul>
                      </details>
                    </>
                  )}
                </>
              )}
            </article>
          </div>
        </>
      )}
    </section>
  );
}
