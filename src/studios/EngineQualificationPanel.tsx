import React from "react";
import { apiFetch, apiFetchBlob } from "../api";
import type { StudioDocumentRecord } from "../api/productApi";
import type { AlightApplicationProbe } from "./alightEngine";

type Language = "action_product" | "kinetic_type" | "interface_service";
type Reference = { documentId: string; documentRevision: number; assetId: string; checksum: string };
type Candidate = { reference: Reference; provider: string; title: string; visualApproved: boolean };
type Comparison = { id: string; mode: string; language: Language; status: string; blockers: string[];
  labels: { label: string; assetId: string; checksum: string }[] };
type Engine = { provider: string; available: boolean; blockers?: string[]; capabilities: string[];
  applicationProbe?: AlightApplicationProbe | null };
type Campaign = { id: string; title: string; revision: number; technicalStatus: string; visualStatus: string;
  apiBudget?: { committedOrReservedUsd: number; remainingUsd: number; attempts: number };
  autonomyStatus: string; promotionStatus: string; availability: Engine;
  trials: { registered: number; completedAutomatically: number; p95Ms: number | null; perLanguage: Record<Language, number> };
  cases: { language: Language; documentId: string | null; status: string; blockers: string[]; visualStatus: string; sessions: Comparison[] }[] };

const languages: Record<Language, string> = {
  action_product: "Ação e produto", kinetic_type: "Motion tipográfico", interface_service: "Interface ou serviço",
};
const reasons: Record<string, string> = {
  adb_unavailable: "Conexão Android ainda não configurada", physical_device_missing: "Dispositivo Android real pendente",
  validated_import_missing: "Importação editável ainda não validada", validated_compiler_missing: "Compilador do aplicativo ainda não validado",
  device_profile_missing: "Perfil do dispositivo pendente", device_not_authorized_or_connected: "Dispositivo desconectado ou não autorizado",
  profile_or_calibration_invalid: "Calibração precisa ser conferida", app_version_changed: "Versão do aplicativo mudou",
  android_version_changed: "Versão do Android mudou", device_locale_changed: "Idioma do dispositivo mudou",
  device_resolution_changed: "Resolução do dispositivo mudou",
  device_busy: "Dispositivo ocupado", device_quarantined: "Dispositivo aguarda recuperação após falha",
  emulator_excluded: "Este worker exige Android físico; configure o modo de emulador para a prova no PC",
  emulator_missing: "Emulador Android pendente", execution_mode_profile_conflict: "Perfil homologado para outro ambiente",
  emulator_runtime_changed: "Ambiente Android do emulador mudou; revalide o perfil",
  alight_app_missing: "Alight Motion ainda não instalado no ambiente conectado",
  alight_application_probe_failed: "Não foi possível confirmar a instalação; confira a conexão e os logs",
  device_selection_required: "Mais de um Android conectado; vincule o dispositivo no perfil",
  case_document_missing: "Projeto de estudo pendente",
  case_materials_missing: "Materiais pendentes", engine_document_revision_stale: "Projeto mudou; vincule a revisão atual",
  case_materials_unverified_or_changed: "Materiais mudaram ou precisam de autorização",
  case_snapshot_changed: "Briefing ou materiais mudaram",
};
const statuses: Record<string, string> = { pending: "pendente", not_assessed: "não avaliado", approved: "aprovado",
  passed: "aprovado", demonstrated: "demonstrada", eligible: "elegível", stale: "versão obsoleta", reviewed: "revisado", rejected: "reprovado" };

function BlindEngineReview({ session, base, onRecorded }: { session: Comparison; base: string; onRecorded: () => void }) {
  const [urls, setUrls] = React.useState<Record<string, string>>({});
  const [ended, setEnded] = React.useState<Record<string, boolean>>({});
  const [preferred, setPreferred] = React.useState("");
  const [mobile, setMobile] = React.useState(false);
  const [blind, setBlind] = React.useState(false);
  const [control, setControl] = React.useState(false);
  const [manualChecked, setManualChecked] = React.useState(false);
  const [fidelity, setFidelity] = React.useState(false);
  const [notes, setNotes] = React.useState("");
  const [actionSeconds, setActionSeconds] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const playback = React.useRef<Record<string, { last: number; covered: number; clock: number }>>({});
  const signature = session.labels.map(item => item.checksum).join(":");
  React.useEffect(() => {
    const controller = new AbortController();
    const created: string[] = [];
    playback.current = {};
    setUrls({}); setEnded({}); setPreferred(""); setMobile(false); setBlind(false); setControl(false);
    setManualChecked(false); setFidelity(false); setNotes(""); setActionSeconds(""); setError(""); setBusy(false);
    Promise.all(session.labels.map(async item => {
      const blob = await apiFetchBlob(`/api/v1/assets/${encodeURIComponent(item.assetId)}/content`, controller.signal);
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob); created.push(url);
      setUrls(old => ({ ...old, [item.label]: url }));
    })).catch(() => { if (!controller.signal.aborted) setError("Não foi possível carregar todos os vídeos."); });
    return () => { controller.abort(); created.forEach(url => URL.revokeObjectURL(url)); };
  }, [session.id, signature, base]);
  const inspected = session.labels.every(item => ended[item.label]);
  return <article aria-label="Comparação cega entre motores">
    <h4>Comparação {session.mode === "technical_fidelity" ? "de fidelidade" : "editorial"}</h4>
    <p>Assista a todas as versões completas em velocidade normal. A preferência não substitui as notas da revisão visual.</p>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>{session.labels.map(item => <div key={item.label}>
      <b>Versão {item.label}</b>
      {urls[item.label] && <video controls src={urls[item.label]} aria-label={`Versão ${item.label}`} style={{ width: 240, maxWidth: "100%" }}
        onPlay={event => {
          const video = event.currentTarget;
          const prior = playback.current[item.label];
          playback.current[item.label] = { last: video.currentTime,
            covered: video.currentTime < 0.1 ? 0 : prior?.covered ?? 0, clock: performance.now() };
        }}
        onRateChange={event => { if (event.currentTarget.playbackRate !== 1) {
          delete playback.current[item.label]; setEnded(old => ({ ...old, [item.label]: false }));
        } }}
        onSeeking={() => { delete playback.current[item.label]; setEnded(old => ({ ...old, [item.label]: false })); }}
        onTimeUpdate={event => {
          const video = event.currentTarget, prior = playback.current[item.label], now = performance.now();
          if (!prior || video.paused || video.seeking || video.playbackRate !== 1) return;
          const delta = video.currentTime - prior.last;
          // Count only uninterrupted playback consistent with elapsed wall time.
          if (delta >= 0 && delta <= (now - prior.clock) / 1000 + 0.15) prior.covered += delta;
          else prior.covered = 0;
          prior.last = video.currentTime; prior.clock = now;
        }}
        onEnded={event => {
          const video = event.currentTarget, prior = playback.current[item.label];
          if (video.playbackRate === 1 && Number.isFinite(video.duration) && prior &&
              prior.covered >= video.duration - 0.5) setEnded(old => ({ ...old, [item.label]: true }));
        }} />}
    </div>)}</div>
    <label>Preferência<select value={preferred} onChange={event => setPreferred(event.target.value)}>
      <option value="">Selecione após assistir</option>{session.labels.map(item => <option key={item.label}>{item.label}</option>)}
    </select></label>
    <label><input type="checkbox" checked={mobile} onChange={event => setMobile(event.target.checked)} /> Conferi a leitura em tamanho de celular</label>
    <label><input type="checkbox" checked={blind} onChange={event => setBlind(event.target.checked)} /> Fiz a comparação sem consultar a identidade dos motores</label>
    <label><input type="checkbox" checked={manualChecked} onChange={event => setManualChecked(event.target.checked)} /> Confirmei que não houve correções manuais sem registro</label>
    {session.mode === "editorial_result" && <label><input type="checkbox" checked={control} onChange={event => setControl(event.target.checked)} /> Confirmei o controle simples com os mesmos materiais</label>}
    {session.mode === "technical_fidelity" && <label><input type="checkbox" checked={fidelity} onChange={event => setFidelity(event.target.checked)} /> Conferi a mesma receita: intervalos, proporção, movimentos, texto e máscaras</label>}
    {session.language === "action_product" && <label>Segundos de ação dentro da imagem<input type="number" min="0" max="15" step="0.1" value={actionSeconds} onChange={event => setActionSeconds(event.target.value)} /></label>}
    <label>Achados e correções executáveis<textarea value={notes} onChange={event => setNotes(event.target.value)} /></label>
    {error && <p role="alert">{error}</p>}
    <button disabled={busy || !inspected || !preferred || !mobile || !blind || !manualChecked ||
      (session.mode === "editorial_result" && !control) || !notes.trim() || session.status === "stale"}
      onClick={() => { setBusy(true); setError(""); void apiFetch(`${base}/comparisons/${session.id}/review`, {
        method: "POST", body: JSON.stringify({ preferredLabel: preferred, fullVideoInspected: inspected,
          mobileInspected: mobile, blindReviewCompleted: blind, unrecordedManualCorrections: false,
          controlSimplicityConfirmed: control, notes, executableFindings: [notes],
          technicalFidelityConfirmed: fidelity,
          actionSeconds: actionSeconds === "" ? null : Number(actionSeconds) }),
      }).then(onRecorded).catch(() => setError("A sessão mudou ou a avaliação não pôde ser registrada. Atualize antes de tentar novamente."))
        .finally(() => setBusy(false)); }}>Registrar comparação</button>
  </article>;
}

export function EngineQualificationPanel({ document, disabled, onAlightStatus }: {
  document?: StudioDocumentRecord; disabled: boolean; onAlightStatus?: (engine: Engine | undefined) => void;
}) {
  const [engines, setEngines] = React.useState<Engine[]>();
  const [campaigns, setCampaigns] = React.useState<Campaign[]>([]);
  const [selected, setSelected] = React.useState("");
  const [language, setLanguage] = React.useState<Language>("action_product");
  const [mode, setMode] = React.useState("editorial_result");
  const [candidates, setCandidates] = React.useState<Candidate[]>([]);
  const [choices, setChoices] = React.useState<string[]>([]);
  const [session, setSession] = React.useState<Comparison>();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [refresh, setRefresh] = React.useState(0);
  const [loadedScope, setLoadedScope] = React.useState("");
  const scope = `${document?.workspaceId}:${document?.documentId}:${document?.revision}`;
  const activeScope = React.useRef(scope);
  activeScope.current = scope;
  const workspaceBase = `/api/v1/studios/v1/workspaces/${encodeURIComponent(document?.workspaceId ?? "")}`;
  const campaign = campaigns.find(item => item.id === selected) ?? campaigns[0];
  const base = `${workspaceBase}/engine-campaigns/${campaign?.id}`;
  const comparisonContext = `${scope}:${campaign?.id}:${language}:${mode}`;
  const activeComparison = React.useRef(comparisonContext);
  activeComparison.current = comparisonContext;
  React.useEffect(() => {
    if (!document) return;
    const controller = new AbortController();
    setSession(undefined); setChoices([]); setCandidates([]); setError(""); setBusy(false);
    Promise.all([apiFetch<{ engines: Engine[] }>(`${workspaceBase}/render-engines`, { signal: controller.signal }),
      apiFetch<Campaign[]>(`${workspaceBase}/engine-campaigns`, { signal: controller.signal })])
      .then(([value, rows]) => { if (!controller.signal.aborted) {
        setEngines(value.engines); setCampaigns(rows); setLoadedScope(scope);
        onAlightStatus?.(value.engines.find(item => item.provider === "alight-motion.contextual-v1"));
      } })
      .catch(cause => { if (!controller.signal.aborted) {
        setEngines(undefined); setCampaigns([]); setLoadedScope(scope);
        onAlightStatus?.(undefined);
        if (cause?.status !== 403 && cause?.status !== 404) setError("Não foi possível consultar a qualificação dos motores.");
      } });
    return () => controller.abort();
  }, [scope, workspaceBase, refresh, onAlightStatus]);
  React.useEffect(() => {
    setChoices([]); setSession(undefined); setCandidates([]);
    if (!campaign) return;
    const controller = new AbortController();
    apiFetch<Candidate[]>(`${base}/candidates?language=${language}`, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setCandidates(value); })
      .catch(() => {});
    return () => controller.abort();
  }, [base, language, mode, refresh]);
  if (!document || loadedScope !== scope || (!engines && !error)) return null;
  const alight = engines?.find(item => item.provider === "alight-motion.contextual-v1");
  const binding = document.composition.narrative?.editorialV2 as { renderer?: string } | undefined;
  const run = async (action: () => Promise<unknown>) => {
    const initialScope = scope;
    setBusy(true); setError("");
    try { await action(); if (activeScope.current === initialScope) setRefresh(value => value + 1); }
    catch { if (activeScope.current === initialScope) setError("Não foi possível registrar a operação. Confira a revisão e os materiais do projeto."); }
    finally { if (activeScope.current === initialScope) setBusy(false); }
  };
  return <section className="vs-visual-quality" aria-label="Qualificação experimental de motores">
    <h3>Alight Motion · motor candidato</h3>
    <p>Motor do projeto: {binding?.renderer ?? "a definir no plano"}.</p>
    {alight?.applicationProbe && <div aria-label="Conexão real com Alight Motion">
      <p>{alight.applicationProbe.connectedDevices} ambiente(s) Android conectado(s).</p>
      <p>{alight.applicationProbe.installed === true
        ? `Alight instalado · versão ${alight.applicationProbe.version}.`
        : alight.applicationProbe.installed === false
          ? "Instalação do Alight não encontrada."
          : "Instalação do Alight ainda não confirmada."}</p>
      <p>A instalação não confirma composição, exportação ou qualidade visual.</p>
    </div>}
    <button disabled={disabled || busy} onClick={() => setRefresh(value => value + 1)}>Atualizar conexão com Alight</button>
    <p>{alight?.available ? "Dispositivo e importação disponíveis para teste." : "Render no aplicativo pendente."} O motor principal só muda após evidências de qualidade e autonomia.</p>
    {alight?.blockers?.map(code => <p key={code}>{reasons[code] ?? code}.</p>)}
    {error && <p role="alert">{error}</p>}
    {engines && <>
      <p>API da fase: teto compartilhado de US$ 10. Sem compra automática de dispositivo ou assinatura.</p>
      <button disabled={disabled || busy} onClick={() => void run(async () => {
        const next = await apiFetch<{ id: string }>(`${workspaceBase}/engine-campaigns`, { method: "POST", body: JSON.stringify({ title: "Alight Motion · três linguagens" }) });
        if (activeScope.current === scope) setSelected(next.id);
      })}>Criar campanha de estudo</button>
      {campaign && <>
        {campaign.apiBudget && <p>APIs: US$ {campaign.apiBudget.committedOrReservedUsd.toFixed(2)} comprometidos ou reservados;
          saldo de US$ {campaign.apiBudget.remainingUsd.toFixed(2)}. Tentativas: {campaign.apiBudget.attempts}.</p>}
        <label>Campanha<select value={campaign.id} onChange={event => setSelected(event.target.value)}>{campaigns.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
        <dl><div><dt>Funcionamento técnico</dt><dd>{statuses[campaign.technicalStatus]}</dd></div>
          <div><dt>Qualidade visual</dt><dd>{statuses[campaign.visualStatus]}</dd></div>
          <div><dt>Autonomia</dt><dd>{statuses[campaign.autonomyStatus]}</dd></div>
          <div><dt>Jobs reais automáticos</dt><dd>{campaign.trials.completedAutomatically}/30</dd></div>
          <div><dt>Promoção</dt><dd>{statuses[campaign.promotionStatus]}</dd></div></dl>
        {campaign.promotionStatus === "eligible" && <button disabled={disabled || busy} onClick={() => void run(() =>
          apiFetch(`${base}/promote`, { method: "POST" }))}>Promover para novos projetos dos perfis qualificados</button>}
        <label>Linguagem<select value={language} onChange={event => setLanguage(event.target.value as Language)}>{Object.entries(languages).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <button disabled={disabled || busy} onClick={() => void run(() => apiFetch(`${base}/cases`, { method: "POST", body: JSON.stringify({
          language, documentId: document.documentId, expectedDocumentRevision: document.revision, expectedCampaignRevision: campaign.revision,
        }) }))}>Vincular projeto atual a este estudo</button>
        {campaign.cases.map(item => <article key={item.language}><b>{languages[item.language]}</b><p>{item.documentId ? "Projeto vinculado" : "Projeto pendente"} · visual: {statuses[item.visualStatus]}.</p>
          {item.blockers.map(code => <p key={code}>{reasons[code] ?? code}.</p>)}</article>)}
        <details><summary>Comparar renders dos motores</summary>
          {!session && <>
          <label>Finalidade<select value={mode} onChange={event => setMode(event.target.value)}><option value="editorial_result">Resultado editorial e controle</option><option value="technical_fidelity">Fidelidade da mesma receita</option></select></label>
          {!candidates.length && <p>Ainda não há renders elegíveis de 15 segundos, com áudio e materiais comuns. A revisão permanece pendente.</p>}
          {candidates.map(item => <label key={item.reference.assetId}><input type="checkbox" checked={choices.includes(item.reference.assetId)}
            onChange={event => setChoices(old => event.target.checked ? [...old, item.reference.assetId] : old.filter(id => id !== item.reference.assetId))} />
            {item.title} · {item.provider} · {item.visualApproved ? "revisão visual aprovada" : "revisão visual pendente"}</label>)}
          <button disabled={busy || disabled || choices.length !== (mode === "editorial_result" ? 3 : 2)} onClick={() => {
            setBusy(true); setError(""); void apiFetch<Comparison>(`${base}/comparisons`, { method: "POST", body: JSON.stringify({
              language, mode, variants: candidates.filter(item => choices.includes(item.reference.assetId)).map(item => item.reference),
            }) }).then(value => { if (activeComparison.current === comparisonContext) setSession(value); })
              .catch(() => { if (activeComparison.current === comparisonContext) setError("A comparação exige motores, receita e materiais compatíveis, vinculados às versões atuais."); })
              .finally(() => { if (activeComparison.current === comparisonContext) setBusy(false); });
          }}>Preparar comparação cega</button>
          </>}
          {session && <BlindEngineReview session={session} base={base} onRecorded={() => setRefresh(value => value + 1)} />}
          {campaign.cases.flatMap(item => item.sessions).map(item => <p key={item.id}>Comparação {item.mode === "technical_fidelity" ? "de fidelidade" : "editorial"}: {statuses[item.status]}.</p>)}
        </details>
      </>}
    </>}
  </section>;
}
