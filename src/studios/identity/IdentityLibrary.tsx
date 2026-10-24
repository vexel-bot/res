import React from "react";
import {
  ArrowRight,
  AudioLines,
  Image,
  Plus,
  RefreshCw,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { useProductData } from "../../context/ProductDataContext";
import { productApi } from "../../api/productApi";
import {
  identityApi,
  type EnrollmentMode,
  type IdentityCatalog,
} from "./identityApi";
import "./identity.css";

const message = (e: unknown) =>
  e instanceof Error ? e.message : "Não foi possível concluir o cadastro.";
const statusLabel: Record<string, string> = {
  draft: "Em preparação",
  active: "Aprovado para seleção",
  revoked: "Autorização revogada",
  expired: "Autorização vencida",
  superseded: "Versão anterior",
  rejected: "Requer ajustes",
  deleting: "Exclusão em andamento",
  deleted: "Excluído",
};
const modeLabel: Record<EnrollmentMode, string> = {
  face: "Meu rosto",
  voice: "Minha voz",
  face_voice: "Rosto e voz",
  character: "Personagem",
  stock_voice: "Voz licenciada",
};

function Sample({
  assetId,
  audio,
  name,
}: {
  assetId?: string | null;
  audio: boolean;
  name: string;
}) {
  const [open, setOpen] = React.useState(false);
  const [url, setUrl] = React.useState<string>();
  const [error, setError] = React.useState<string>();
  React.useEffect(() => {
    if (!assetId || !open) return;
    const controller = new AbortController();
    let owned: string | undefined;
    setError(undefined);
    setUrl(undefined);
    void productApi
      .studioAssetBlob(assetId, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;
        owned = URL.createObjectURL(blob);
        setUrl(owned);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(message(e));
      });
    return () => {
      controller.abort();
      if (owned) URL.revokeObjectURL(owned);
    };
  }, [assetId, open]);
  return (
    <div className={`il-sample ${audio ? "il-audio" : ""}`}>
      {url ? (
        audio ? (
          <audio controls src={url} aria-label={`Amostra de ${name}`} />
        ) : (
          <img src={url} alt={`Amostra cadastrada de ${name}`} />
        )
      ) : (
        <>
          {audio ? <AudioLines size={35} /> : <Users size={35} />}
          <span>{name.charAt(0)}</span>
        </>
      )}
      {assetId && !open && (
        <button type="button" onClick={() => setOpen(true)}>
          {audio ? "Ouvir amostra" : "Ver aparência"}
        </button>
      )}
      {open && !url && !error && <p role="status">Carregando amostra…</p>}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}

export function IdentityLibrary({
  navigate = (url) => window.location.assign(url),
}: {
  navigate?: (url: string) => void;
}) {
  const data = useProductData();
  const workspace = data.activeWorkspace;
  if (!workspace || data.status === "guest" || data.status === "error")
    return (
      <section className="identity-library">
        <p>
          {data.status === "guest"
            ? "Entre na sua conta para acessar rostos, vozes e personagens."
            : data.status === "error"
              ? data.error
              : "Carregando a marca…"}
        </p>
      </section>
    );
  return (
    <React.Fragment key={`${data.bootstrap?.user.id}:${workspace.id}`}>
      <IdentityRoom workspaceId={workspace.id} navigate={navigate} />
    </React.Fragment>
  );
}

function IdentityRoom({
  workspaceId,
  navigate,
}: {
  workspaceId: string;
  navigate: (url: string) => void;
}) {
  const [catalog, setCatalog] = React.useState<IdentityCatalog>();
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [tab, setTab] = React.useState<"identities" | "voices">("identities");
  const [retry, setRetry] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [enrolling, setEnrolling] = React.useState(
    new URLSearchParams(window.location.search).get("enroll") === "1",
  );
  const [mode, setMode] = React.useState<EnrollmentMode>("face");
  const [saving, setSaving] = React.useState(false);
  const [name, setName] = React.useState("");
  const [purpose, setPurpose] = React.useState(
    "Criar amostras privadas para conteúdo da marca.",
  );
  const [expires, setExpires] = React.useState(() =>
    new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
  );
  const [rights, setRights] = React.useState("");
  const [declared, setDeclared] = React.useState(false);
  const [photo, setPhoto] = React.useState<File>();
  const [audio, setAudio] = React.useState<File>();
  const [evidence, setEvidence] = React.useState<File>();
  const alive = React.useRef(true);
  // The frozen submission is reused on a network retry; no second profile is minted.
  const pending = React.useRef<Parameters<typeof identityApi.enroll>[0] | undefined>(undefined);
  const uploadCache = React.useRef(new Map<File, string>());
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
    void identityApi
      .catalog(workspaceId, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setCatalog(value);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(message(e));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [workspaceId, retry]);
  const hasImage = ["face", "face_voice", "character"].includes(mode);
  const hasVoice = ["voice", "face_voice", "stock_voice"].includes(mode);
  const licensed = ["character", "stock_voice"].includes(mode);
  const resetSubmission = () => {
    pending.current = undefined;
  };
  const upload = async (file: File) => {
    const saved = uploadCache.current.get(file);
    if (saved) return saved;
    const result = await productApi.uploadStudioAsset(workspaceId, file);
    uploadCache.current.set(file, result.id);
    return result.id;
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (
      saving ||
      !declared ||
      !evidence ||
      (hasImage && !photo) ||
      (hasVoice && !audio)
    )
      return;
    setSaving(true);
    setError(undefined);
    setNotice(undefined);
    try {
      if (!pending.current) {
        const evidenceAssetId = await upload(evidence);
        const imageAssetId = hasImage ? await upload(photo!) : undefined;
        const audioAssetId = hasVoice ? await upload(audio!) : undefined;
        pending.current = {
          workspaceId,
          requestKey: crypto.randomUUID(),
          mode,
          displayName: name.trim(),
          imageAssetId,
          audioAssetId,
          evidenceAssetId,
          purpose: purpose.trim(),
          expiresAt: licensed
            ? undefined
            : new Date(`${expires}T23:59:59Z`).toISOString(),
          rightsReference: rights.trim(),
          declared: true,
        };
      }
      await identityApi.enroll(pending.current);
      if (!alive.current) return;
      pending.current = undefined;
      uploadCache.current.clear();
      setEnrolling(false);
      setName("");
      setPhoto(undefined);
      setAudio(undefined);
      setEvidence(undefined);
      setDeclared(false);
      setNotice(
        "Cadastro salvo. A aparência ou voz precisa de avaliação e revisão antes de ser usada na produção.",
      );
      setRetry((value) => value + 1);
    } catch (e) {
      if (alive.current) setError(message(e));
    } finally {
      if (alive.current) setSaving(false);
    }
  };
  const revoke = async (id: string) => {
    if (
      !window.confirm(
        "Revogar esta autorização bloqueará as versões e os próximos usos vinculados. Continuar?",
      )
    )
      return;
    try {
      await productApi.revokeStudioConsent(
        id,
        "Revogada na biblioteca de rostos e vozes",
      );
      if (alive.current) {
        setNotice("Autorização revogada.");
        setRetry((v) => v + 1);
      }
    } catch (e) {
      if (alive.current) setError(message(e));
    }
  };
  return (
    <section
      className="identity-library"
      aria-label="Rostos, vozes e personagens"
    >
      <header>
        <div>
          <small>CLICKO / ELENCO DA MARCA</small>
          <h1>
            Quem dá vida
            <br />
            <em>às suas ideias.</em>
          </h1>
          <p>Pessoas, personagens e vozes para escolher em cada criação.</p>
        </div>
        <button
          className="il-primary"
          onClick={() => setEnrolling((value) => !value)}
        >
          {enrolling ? <X size={16} /> : <Plus size={16} />}
          {enrolling ? "Fechar cadastro" : "Adicionar à biblioteca"}
        </button>
      </header>
      <div className="il-explainer">
        <ShieldCheck size={20} />
        <p>
          A aparência e a voz são escolhas independentes. Em uma imagem, a voz
          fica associada ao projeto para versões narradas; o arquivo de imagem
          permanece estático.
        </p>
        <button onClick={() => navigate("/evolution")}>
          Ver evolução <ArrowRight size={14} />
        </button>
      </div>
      {notice && (
        <p className="il-notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <div className="il-error" role="alert">
          <p>{error}</p>
          <button onClick={() => setRetry((v) => v + 1)}>
            <RefreshCw size={14} /> Recarregar biblioteca
          </button>
        </div>
      )}
      {enrolling && (
        <form
          className="il-enrollment"
          onSubmit={(event) => void submit(event)}
          onChange={resetSubmission}
        >
          <h2>Adicionar uma presença ou uma voz</h2>
          <p>
            Envie apenas o que deseja cadastrar. As amostras e o documento de
            autorização são arquivos separados.
          </p>
          <fieldset disabled={saving}>
            <legend>O que vamos cadastrar?</legend>
            <div className="il-modes">
              {(Object.keys(modeLabel) as EnrollmentMode[]).map((value) => (
                <button
                  type="button"
                  key={value}
                  aria-pressed={mode === value}
                  onClick={() => {
                    setMode(value);
                    setDeclared(false);
                    resetSubmission();
                  }}
                >
                  {modeLabel[value]}
                </button>
              ))}
            </div>
            <div className="il-form-grid">
              <label>
                Nome
                <input
                  required
                  minLength={2}
                  maxLength={160}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <label>
                Finalidade
                <textarea
                  required
                  minLength={8}
                  maxLength={2000}
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                />
              </label>
              {hasImage && (
                <label>
                  Imagem de referência
                  <input
                    required
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={(e) => setPhoto(e.target.files?.[0])}
                  />
                </label>
              )}
              {hasVoice && (
                <label>
                  Amostra de voz
                  <input
                    required
                    type="file"
                    accept="audio/wav,audio/mpeg,audio/flac"
                    onChange={(e) => setAudio(e.target.files?.[0])}
                  />
                  <small>
                    Voz limpa e isolada, sem música. O envio ainda não produz a
                    voz clonada.
                  </small>
                </label>
              )}
              <label>
                {licensed
                  ? "Comprovante de direitos"
                  : "Documento de autorização"}
                <input
                  required
                  type="file"
                  accept="application/pdf,text/plain,image/png,image/jpeg"
                  onChange={(e) => setEvidence(e.target.files?.[0])}
                />
              </label>
              {licensed ? (
                <label>
                  Origem e condições de uso
                  <textarea
                    required
                    minLength={8}
                    maxLength={2000}
                    value={rights}
                    onChange={(e) => setRights(e.target.value)}
                  />
                </label>
              ) : (
                <label>
                  Autorização válida até
                  <input
                    required
                    type="date"
                    min={new Date().toISOString().slice(0, 10)}
                    value={expires}
                    onChange={(e) => setExpires(e.target.value)}
                  />
                </label>
              )}
            </div>
            <label className="il-declaration">
              <input
                required
                type="checkbox"
                checked={declared}
                onChange={(e) => setDeclared(e.target.checked)}
              />
              {licensed
                ? "Confirmo os direitos de uso da aparência ou voz e anexei o comprovante."
                : `A pessoa autorizou o uso ${hasImage && hasVoice ? "do rosto e da voz" : hasImage ? "do rosto" : "da voz"} para a finalidade e o prazo informados.`}
            </label>
            <button type="submit" className="il-primary" disabled={!declared}>
              {saving ? "Salvando cadastro…" : "Salvar para avaliação"}
              <ArrowRight size={16} />
            </button>
          </fieldset>
        </form>
      )}
      <nav aria-label="Coleções de identidade">
        <button
          aria-pressed={tab === "identities"}
          onClick={() => setTab("identities")}
        >
          <Users size={16} /> Pessoas e personagens{" "}
          <span>{catalog?.identities.length ?? "—"}</span>
        </button>
        <button
          aria-pressed={tab === "voices"}
          onClick={() => setTab("voices")}
        >
          <AudioLines size={16} /> Vozes{" "}
          <span>{catalog?.voices.length ?? "—"}</span>
        </button>
      </nav>
      {loading ? (
        <p role="status">Carregando a biblioteca…</p>
      ) : (
        catalog && (
          <div className="il-grid">
            {(tab === "identities" ? catalog.identities : catalog.voices).map(
              (item) => {
                const active = item.versions.find(
                  (version) => version.id === item.selectedVersionId,
                );
                const latest = active || item.versions[0];
                const consent = catalog.consents.find(
                  (grant) => grant.id === latest?.consentGrantId,
                );
                const profile = item.profile;
                return (
                  <article key={profile.id}>
                    <React.Fragment key={item.previewAssetId}>
                      <Sample
                        assetId={item.previewAssetId}
                        audio={tab === "voices"}
                        name={profile.displayName}
                      />
                    </React.Fragment>
                    <div className="il-card-body">
                      <small>
                        {"identityType" in profile
                          ? profile.identityType === "synthetic_character"
                            ? "PERSONAGEM"
                            : "PESSOA"
                          : profile.voiceType === "stock"
                            ? "VOZ LICENCIADA"
                            : "VOZ PRÓPRIA"}
                      </small>
                      <h2>{profile.displayName}</h2>
                      <span
                        className={
                          item.selectedVersionId ? "il-ready" : "il-pending"
                        }
                      >
                        {item.selectedVersionId
                          ? "Disponível para escolher"
                          : statusLabel[latest?.status || profile.status] ||
                            "Em preparação"}
                      </span>
                      {item.unavailableReason && (
                        <p>
                          {consent && consent.status !== "active"
                            ? statusLabel[consent.status]
                            : "A seleção será liberada após a avaliação e revisão da versão."}
                        </p>
                      )}
                      {active && (
                        <div className="il-use">
                          {(["image", "video"] as const).map((format) => (
                            <button
                              key={format}
                              onClick={() =>
                                navigate(
                                  `${format === "image" ? "/studios/tools/editorial" : "/studios/video/create"}?format=${format}&${tab === "identities" ? "identityVersion" : "voiceVersion"}=${encodeURIComponent(active.id)}`,
                                )
                              }
                            >
                              {format === "image" ? (
                                <Image size={14} />
                              ) : (
                                <ArrowRight size={14} />
                              )}
                              {format === "image"
                                ? "Usar em imagem"
                                : "Usar em vídeo"}
                            </button>
                          ))}
                        </div>
                      )}
                      <details>
                        <summary>
                          {item.versions.length} versão(ões) · histórico
                        </summary>
                        {item.versions.map((version) => (
                          <p key={version.id}>
                            v{version.version} ·{" "}
                            {statusLabel[version.status] || version.status}
                          </p>
                        ))}
                        {consent && (
                          <p>
                            Autorização{" "}
                            {statusLabel[consent.status] || consent.status} ·
                            até{" "}
                            {new Date(consent.expiresAt).toLocaleDateString(
                              "pt-BR",
                            )}
                          </p>
                        )}
                        {consent?.status === "active" && (
                          <button onClick={() => void revoke(consent.id)}>
                            Revogar autorização
                          </button>
                        )}
                      </details>
                    </div>
                  </article>
                );
              },
            )}
            {!(tab === "identities" ? catalog.identities : catalog.voices)
              .length && (
              <div className="il-empty">
                <Users size={30} />
                <h2>
                  {tab === "voices"
                    ? "Sua coleção de vozes começa aqui."
                    : "Uma presença que representa sua marca."}
                </h2>
                <p>
                  {tab === "voices"
                    ? "Cadastre uma voz própria ou uma voz com licença de uso."
                    : "Adicione um rosto autorizado ou um personagem com seus direitos de uso."}
                </p>
                <button
                  onClick={() => {
                    setMode(tab === "voices" ? "voice" : "face");
                    setEnrolling(true);
                  }}
                >
                  Adicionar primeiro cadastro <Plus size={14} />
                </button>
              </div>
            )}
          </div>
        )
      )}
    </section>
  );
}
