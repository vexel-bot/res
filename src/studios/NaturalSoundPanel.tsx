import React from "react";
import type { StudioAssetRightsReviewInput, StudioDocumentRecord } from "../api/productApi";
import { NATURAL_SOUND_TRACK_ID, type NaturalSoundPlacement } from "./naturalSoundTimeline";

export function NaturalSoundPanel({ document, disabled, save, notify, toggle, reviewRights, undo, canUndo, selectionRequest }: {
  document?: StudioDocumentRecord;
  disabled: boolean;
  save: (file: File | undefined, source: string, license: string, placement: NaturalSoundPlacement, clipId: string, reuseAssetId?: string) => Promise<unknown>;
  toggle: (clipId: string, enabled: boolean) => Promise<unknown>;
  reviewRights: (
    assetId: string,
    input: Omit<StudioAssetRightsReviewInput, "expectedDocumentRevision" | "assetChecksumSha256">,
    idempotencyKey: string,
  ) => Promise<unknown>;
  undo: () => Promise<unknown>;
  canUndo: boolean;
  selectionRequest?: { clipId: string; nonce: number };
  notify: (message: string) => void;
}) {
  const [file, setFile] = React.useState<File>();
  const [source, setSource] = React.useState("");
  const [license, setLicense] = React.useState("");
  const [start, setStart] = React.useState("0");
  const [offset, setOffset] = React.useState("0");
  const [duration, setDuration] = React.useState("1");
  const [gain, setGain] = React.useState("-6");
  const [fade, setFade] = React.useState("0");
  const [error, setError] = React.useState<string>();
  const [selectedId, setSelectedId] = React.useState<string | null>();
  const [newId, setNewId] = React.useState(() => `natural-${crypto.randomUUID()}`);
  const [reuseAssetId, setReuseAssetId] = React.useState<string>();
  const [pendingSelection, setPendingSelection] = React.useState<{ id: string | null }>();
  const [rightsOpen, setRightsOpen] = React.useState(false);
  const [rightsDecision, setRightsDecision] = React.useState<"verified" | "restricted">("verified");
  const [rightsBasis, setRightsBasis] = React.useState<"open-license" | "owned" | "written-permission">("owned");
  const [sourceReference, setSourceReference] = React.useState("");
  const [rightsReference, setRightsReference] = React.useState("");
  const [rightsExpiration, setRightsExpiration] = React.useState("");
  const [noExpiration, setNoExpiration] = React.useState(true);
  const [rightsNotes, setRightsNotes] = React.useState("");
  const [rightsError, setRightsError] = React.useState<string>();
  const [rightsKey, setRightsKey] = React.useState(() => `sound-rights-${crypto.randomUUID()}`);
  const [selectionEpoch, setSelectionEpoch] = React.useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const dirty = React.useRef(false);
  const timeline = document?.composition.mediaTimeline;
  const rate = timeline?.frameRate ?? { numerator: 30, denominator: 1 };
  const fps = rate.numerator / rate.denominator;
  const track = timeline?.tracks?.find((item) => item.id === NATURAL_SOUND_TRACK_ID);
  const clips = track?.kind === "audio" ? track.clips ?? [] : [];
  const clip = selectedId === undefined ? clips[0] : clips.find((item) => item.id === selectedId);
  const soundAssets = document?.assets.filter((asset) => asset.provenance?.purpose === "natural-sound-candidate") ?? [];
  const ref = soundAssets.find((asset) => asset.id === (reuseAssetId ?? clip?.assetId));
  const targetId = clip?.id ?? newId;

  const select = React.useCallback((id: string | null) => {
    dirty.current = false;
    setSelectedId(id);
    setSelectionEpoch((value) => value + 1);
    if (id === null) setNewId(`natural-${crypto.randomUUID()}`);
    setFile(undefined);
    if (inputRef.current) inputRef.current.value = "";
    setReuseAssetId(undefined);
    setSource(""); setLicense(""); setStart("0"); setOffset("0"); setDuration("1"); setGain("-6"); setFade("0");
    setError(undefined); setPendingSelection(undefined);
  }, []);

  const requestSelection = React.useCallback((id: string | null) => {
    if (dirty.current) {
      setPendingSelection({ id });
      setError("Há ajustes não aplicados. Aplique ou descarte antes de trocar de som.");
    } else select(id);
  }, [select]);

  React.useEffect(() => {
    if (selectionRequest) requestSelection(selectionRequest.clipId);
  }, [selectionRequest, requestSelection]);

  React.useEffect(() => {
    if (selectedId && !clips.some((item) => item.id === selectedId) && !dirty.current) setSelectedId(undefined);
  }, [clips, selectedId]);

  React.useEffect(() => {
    if (dirty.current || !ref) return;
    setSource(String(ref.provenance?.sourceDeclaration ?? ""));
    setLicense(String(ref.provenance?.licenseDeclaration ?? ""));
    if (clip) {
      setStart(String(clip.timeline.startFrame / fps));
      setDuration(String(clip.timeline.durationFrames / fps));
      setOffset(String((clip.source?.startMicroseconds ?? 0) / 1_000_000));
      setGain(String(clip.gainDb ?? 0));
      setFade(String((clip.fadeInFrames ?? 0) / fps));
    }
  }, [clip, ref, fps, selectionEpoch]);

  React.useEffect(() => {
    setRightsOpen(false);
    setRightsError(undefined);
    setRightsDecision(ref?.rightsStatus === "restricted" ? "restricted" : "verified");
    setRightsBasis("owned"); setSourceReference(""); setRightsReference(""); setRightsExpiration("");
    setNoExpiration(true); setRightsNotes(""); setRightsKey(`sound-rights-${crypto.randomUUID()}`);
  }, [ref?.id]);

  const change = (setter: (value: string) => void) => (event: React.ChangeEvent<HTMLInputElement>) => {
    dirty.current = true;
    setter(event.target.value);
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(undefined);
    if ([start, offset, duration, gain, fade].some((value) => !value.trim() || !Number.isFinite(Number(value)))) {
      setError("Preencha os tempos e o volume com números válidos.");
      return;
    }
    try {
      await save(file, source, license, {
        startFrame: Math.round(Number(start) * fps), sourceStartFrame: Math.round(Number(offset) * fps),
        durationFrames: Math.round(Number(duration) * fps), gainDb: Number(gain), fadeFrames: Math.round(Number(fade) * fps),
      }, targetId, reuseAssetId);
      dirty.current = false;
      setFile(undefined);
      if (inputRef.current) inputRef.current.value = "";
      setSelectedId(targetId);
      setReuseAssetId(undefined);
      setPendingSelection(undefined);
      notify("Som salvo na edição. Renderize para conferir o mix; escuta e direitos ainda pendentes.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Não foi possível salvar o som.");
    }
  };

  const mutate = async (action: () => Promise<unknown>, message: string) => {
    setError(undefined);
    try { await action(); notify(message); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Não foi possível ajustar o som."); }
  };

  const changeRights = (change: () => void) => {
    change();
    setRightsError(undefined);
    setRightsKey(`sound-rights-${crypto.randomUUID()}`);
  };
  const submitRights = async () => {
    if (!ref) return;
    setRightsError(undefined);
    if (!sourceReference.trim() || !rightsReference.trim()) {
      setRightsError("Informe as duas referências verificáveis antes de registrar a decisão.");
      return;
    }
    if (rightsDecision === "verified" && !noExpiration && !rightsExpiration) {
      setRightsError("Informe o vencimento ou confirme que o direito não expira.");
      return;
    }
    try {
      await reviewRights(ref.id, {
        decision: rightsDecision,
        basis: rightsBasis,
        sourceReference: sourceReference.trim(),
        rightsReference: rightsReference.trim(),
        expiresAt: rightsDecision === "verified" && !noExpiration
          ? `${rightsExpiration}T23:59:59.000Z`
          : null,
        noExpirationConfirmed: rightsDecision === "verified" && noExpiration,
        notes: rightsNotes.trim() || null,
      }, rightsKey);
      setRightsOpen(false);
      notify(rightsDecision === "verified"
        ? "Direitos verificados para este arquivo. Renderize novamente antes de enviar para revisão."
        : "Arquivo marcado como restrito. Ele não poderá seguir para entrega.");
    } catch (requestError) {
      setRightsError(requestError instanceof Error ? requestError.message : "Não foi possível registrar a revisão de direitos.");
    }
  };

  return <form className="vs-natural-sound" onSubmit={(event) => void submit(event)}>
    <h3>Som natural</h3>
    <p>Adicione ambiente ou foley, sem fala nem música. O arquivo é candidato: análise técnica não valida seu conteúdo ou licença.</p>
    <div className="vs-sound-cues" aria-label="Sons da montagem">
      {clips.map((item, index) => <button key={item.id} type="button" data-action-id="VIDEO-SOUND-SELECT"
        aria-pressed={clip?.id === item.id} disabled={disabled} title={disabled ? "Aguarde a operação atual" : "Editar este som sem alterar os demais"}
        onClick={() => requestSelection(item.id)}>Som {index + 1} · {(item.timeline.startFrame / fps).toFixed(2)} s · {item.enabled === false ? "desativado" : "ativo"}</button>)}
    </div>
    <button type="button" data-action-id="VIDEO-SOUND-NEW" className="vs-secondary-action" disabled={disabled || clips.length >= 32}
      title={disabled ? "Adicione um take autenticado e aguarde a operação atual" : clips.length >= 32 ? "Limite de 32 sons nesta composição" : "Adicionar um som sem substituir os anteriores"}
      onClick={() => requestSelection(null)}>Adicionar outro som</button>
    {pendingSelection && <button type="button" data-action-id="VIDEO-SOUND-DISCARD" className="vs-secondary-action"
      onClick={() => select(pendingSelection.id)}>Descartar ajustes e trocar</button>}
    <p>{clip ? `Editando som ${clips.findIndex((item) => item.id === clip.id) + 1}` : "Novo som"}</p>
    <fieldset disabled={disabled} className="vs-sound-fields">
    {ref && <p>Atual: {String(ref.provenance?.originalFilename ?? "som enviado")} · SHA-256 {ref.checksum?.slice(0, 12)}…</p>}
    <label>Arquivo WAV, MP3 ou FLAC — até 20 MB
      <input ref={inputRef} data-action-id="VIDEO-SOUND-FILE" type="file" accept=".wav,.mp3,.flac" disabled={disabled}
        title={disabled ? "Adicione um take autenticado e aguarde a operação atual" : "Escolher som candidato"}
        onChange={(event) => { dirty.current = true; setFile(event.target.files?.[0]); setSource(""); setLicense(""); }} />
    </label>
    {!!soundAssets.length && <label>Arquivo já importado
      <select data-action-id="VIDEO-SOUND-REUSE" value={reuseAssetId ?? clip?.assetId ?? ""} disabled={disabled || !!file}
        title={file ? "Limpe o arquivo escolhido para reutilizar outro" : disabled ? "Aguarde a operação atual" : "Usa o mesmo arquivo sem novo upload"}
        onChange={(event) => {
          dirty.current = true; setReuseAssetId(event.target.value);
          const chosen = soundAssets.find((asset) => asset.id === event.target.value);
          setSource(String(chosen?.provenance?.sourceDeclaration ?? ""));
          setLicense(String(chosen?.provenance?.licenseDeclaration ?? ""));
        }}>
        <option value="">Enviar novo arquivo</option>
        {soundAssets.map((asset) => <option key={asset.id} value={asset.id}>{String(asset.provenance?.originalFilename ?? asset.id)}</option>)}
      </select>
    </label>}
    <label>Origem e autoria do som
      <input data-action-id="VIDEO-SOUND-SOURCE" value={source} maxLength={1000} required onChange={change(setSource)} />
    </label>
    <label>Licença ou autorização declarada
      <input data-action-id="VIDEO-SOUND-LICENSE" value={license} maxLength={1000} required onChange={change(setLicense)} />
    </label>
    <div className="vs-sound-grid">
      <label>Início no vídeo (s)<input data-action-id="VIDEO-SOUND-START" type="number" step="any" min="0" value={start} onChange={change(setStart)} required /></label>
      <label>Início no arquivo (s)<input data-action-id="VIDEO-SOUND-OFFSET" type="number" step="any" min="0" value={offset} onChange={change(setOffset)} required /></label>
      <label>Duração do som (s)<input data-action-id="VIDEO-SOUND-DURATION" type="number" step="any" min={1 / fps} value={duration} onChange={change(setDuration)} required /></label>
      <label>Volume do som (dB)<input data-action-id="VIDEO-SOUND-GAIN" type="number" step="any" min="-96" max="0" value={gain} onChange={change(setGain)} required /></label>
      <label>Fade de entrada/saída (s)<input data-action-id="VIDEO-SOUND-FADE" type="number" step="any" min="0" value={fade} onChange={change(setFade)} required /></label>
    </div>
    </fieldset>
    <p>Aplicar altera apenas o som selecionado. Ouça a edição salva no Preview; cortes acompanham a montagem. Confira também o MP4 em Saída.</p>
    <button data-action-id="VIDEO-SOUND-APPLY" className="vs-secondary-action" type="submit" disabled={disabled || (!file && !ref)}
      title={disabled ? "Adicione um take autenticado e aguarde a operação atual" : !file && !ref ? "Escolha um arquivo de som" : "Salvar na timeline; não aprova nem publica"}>Aplicar som natural</button>
    {clip && <button type="button" data-action-id="VIDEO-SOUND-TOGGLE" className="vs-secondary-action"
      disabled={disabled || dirty.current} title={dirty.current ? "Aplique ou descarte os ajustes locais primeiro" : disabled ? "Aguarde a operação atual" : "Preserva arquivo e posição do som"}
      onClick={() => void mutate(() => toggle(clip.id, clip.enabled === false), "Estado do som salvo; renderize novamente para conferir o mix.")}>
      {clip.enabled === false ? "Reativar som selecionado" : "Desativar som selecionado"}
    </button>}
    <button type="button" data-action-id="VIDEO-SOUND-UNDO" className="vs-secondary-action" disabled={disabled || !canUndo || dirty.current}
      title={dirty.current ? "Aplique ou descarte os ajustes locais primeiro" : !canUndo ? "Disponível só para o último ajuste nesta sessão, sem edições posteriores" : disabled ? "Aguarde a operação atual" : "Desfaz o último ajuste de som na revisão exata"}
      onClick={() => void mutate(undo, "Último ajuste de som desfeito. Originais preservados.")}>Desfazer último ajuste de som</button>
    {ref && <section className="vs-sound-rights" data-status={ref.rightsStatus}>
      <div>
        <b>Direitos do arquivo</b>
        <span>{ref.rightsStatus === "verified" ? "Verificados" : ref.rightsStatus === "restricted" ? "Restritos" : "Não verificados"}</span>
      </div>
      <small>Declarações de origem e licença não bastam. Owner ou Admin deve conferir referências e o arquivo exato.</small>
      {!rightsOpen ? <button type="button" className="vs-secondary-action" data-action-id="VIDEO-SOUND-RIGHTS-OPEN"
        disabled={disabled} title={disabled ? "Aguarde a operação atual" : "Abrir a revisão vinculada ao SHA-256 deste som"}
        onClick={() => setRightsOpen(true)}>{ref.rightsStatus === "unknown" ? "Revisar direitos deste som" : "Revisar ou alterar decisão"}</button> :
        <fieldset disabled={disabled} onKeyDown={(event) => { if (event.key === "Enter") event.preventDefault(); }}>
          <legend>Revisão de direitos</legend>
          <label>Decisão
            <select data-action-id="VIDEO-SOUND-RIGHTS-EDIT" value={rightsDecision}
              onChange={(event) => changeRights(() => setRightsDecision(event.target.value as "verified" | "restricted"))}>
              <option value="verified">Uso comercial verificado</option>
              <option value="restricted">Uso comercial restrito</option>
            </select>
          </label>
          <label>Base do direito
            <select data-action-id="VIDEO-SOUND-RIGHTS-EDIT" value={rightsBasis}
              onChange={(event) => changeRights(() => setRightsBasis(event.target.value as typeof rightsBasis))}>
              <option value="owned">Arquivo próprio</option>
              <option value="open-license">Licença aberta</option>
              <option value="written-permission">Autorização escrita</option>
            </select>
          </label>
          <label>Referência verificável da origem
            <input data-action-id="VIDEO-SOUND-RIGHTS-EDIT" value={sourceReference} maxLength={2000}
              placeholder="URL, manifesto ou registro interno" onChange={(event) => changeRights(() => setSourceReference(event.target.value))} />
          </label>
          <label>Referência da licença ou autorização
            <input data-action-id="VIDEO-SOUND-RIGHTS-EDIT" value={rightsReference} maxLength={2000}
              placeholder="URL da licença, contrato ou termo" onChange={(event) => changeRights(() => setRightsReference(event.target.value))} />
          </label>
          {rightsDecision === "verified" && <>
            <label className="vs-rights-checkbox"><input data-action-id="VIDEO-SOUND-RIGHTS-EDIT" type="checkbox" checked={noExpiration}
              onChange={(event) => changeRights(() => setNoExpiration(event.target.checked))} />Direito sem vencimento confirmado</label>
            {!noExpiration && <label>Vencimento<input data-action-id="VIDEO-SOUND-RIGHTS-EDIT" type="date" value={rightsExpiration}
              onChange={(event) => changeRights(() => setRightsExpiration(event.target.value))} /></label>}
          </>}
          <label>Notas da conferência
            <input data-action-id="VIDEO-SOUND-RIGHTS-EDIT" value={rightsNotes} maxLength={2000}
              onChange={(event) => changeRights(() => setRightsNotes(event.target.value))} />
          </label>
          <div>
            <button type="button" className="vs-secondary-action" data-action-id="VIDEO-SOUND-RIGHTS-CANCEL" onClick={() => setRightsOpen(false)}>Cancelar</button>
            <button type="button" className="vs-secondary-action" data-action-id="VIDEO-SOUND-RIGHTS-SAVE" onClick={() => void submitRights()}>Registrar decisão</button>
          </div>
        </fieldset>}
      {rightsError && <p role="alert">{rightsError}</p>}
    </section>}
    {error && <p role="alert">{error}</p>}
  </form>;
}
