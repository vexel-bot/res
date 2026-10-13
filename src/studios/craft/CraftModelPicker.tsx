import React from "react";
import { Plus, Save, X } from "lucide-react";
import { craftApi, type LLMConnection, type LLMConnectionInput, type LLMCatalog, type LLMProtocol } from "./craftApi";

export interface ModelSelection { connectionId?: string; model?: string; available: boolean }
interface Props {
  workspaceId: string; userId: string; disabled: boolean;
  onChange: (value: ModelSelection) => void;
}
const protocolNames: Record<LLMProtocol, string> = {
  openai_chat: "Chat Completions", openai_responses: "Responses", anthropic_messages: "Claude Messages",
  gemini_generate: "Gemini", cohere_chat: "Cohere Chat", ollama_chat: "Ollama", custom_json: "HTTP com JSON personalizado",
};
const empty: LLMConnectionInput = {
  label: "", provider: "custom", protocol: "openai_chat", baseUrl: "", models: [],
  authHeader: "Authorization", authPrefix: "Bearer", enabled: false, billingMode: "metered",
  budgetUsd: 0, inputUsdPerMillion: 0, outputUsdPerMillion: 0, maxOutputTokens: 4000,
};

export function CraftModelPicker({ workspaceId, userId, disabled, onChange }: Props) {
  const [catalog, setCatalog] = React.useState<LLMCatalog>();
  const [connections, setConnections] = React.useState<LLMConnection[]>([]);
  const [canManage, setCanManage] = React.useState(false);
  const [choice, setChoice] = React.useState("");
  const [model, setModel] = React.useState("");
  const [editing, setEditing] = React.useState<LLMConnection | "new">();
  const [form, setForm] = React.useState<LLMConnectionInput>(empty);
  const [modelsText, setModelsText] = React.useState("");
  const [templateText, setTemplateText] = React.useState("{}");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string>();
  const [generation, reload] = React.useState(0);
  const preference = `clicko:studio-model:${encodeURIComponent(userId)}:${encodeURIComponent(workspaceId)}`;

  React.useEffect(() => {
    const controller = new AbortController();
    setConnections([]); setCatalog(undefined); setEditing(undefined); setForm(empty); setError(undefined);
    void Promise.all([craftApi.llmCatalog(controller.signal), craftApi.llmConnections(workspaceId, controller.signal)])
      .then(([available, saved]) => {
        if (controller.signal.aborted) return;
        setCatalog(available); setConnections(saved.connections || []); setCanManage(saved.canManage);
        let previous: { connectionId?: string; model?: string } = {};
        try { previous = JSON.parse(localStorage.getItem(preference) || "{}"); } catch { /* Private choice is optional. */ }
        const selected = (saved.connections || []).find((item) => item.config.enabled && item.id === previous.connectionId)
          || (available.legacyPlanningAvailable === false ? (saved.connections || []).find((item) => item.config.enabled) : undefined);
        setChoice(selected?.id || "");
        setModel(selected?.config.models.includes(previous.model || "") ? previous.model! : selected?.config.models[0] || "");
      }).catch(() => { if (!controller.signal.aborted) setError("Não foi possível carregar as conexões de IA."); });
    return () => controller.abort();
  }, [workspaceId, userId, generation, preference]);

  const selected = connections.find((item) => item.id === choice && item.config.enabled);
  React.useEffect(() => {
    const active = selected && selected.config.models.includes(model);
    const available = Boolean(active || (!choice && catalog?.legacyPlanningAvailable === true));
    onChange({ connectionId: active ? selected.id : undefined, model: active ? model : undefined, available });
    if (catalog) {
      try { localStorage.setItem(preference, JSON.stringify({ connectionId: selected?.id, model })); } catch { /* No credentials are stored here. */ }
    }
  }, [selected?.id, selected?.revision, model, choice, catalog?.legacyPlanningAvailable, preference, onChange]);

  const begin = (connection?: LLMConnection) => {
    setEditing(connection || "new"); setError(undefined);
    setForm(connection ? { ...connection.config, label: connection.label, provider: connection.provider,
      expectedRevision: connection.revision, apiKey: "" } : { ...empty });
    setModelsText(connection?.config.models.join("\n") || "");
    setTemplateText(JSON.stringify(connection?.config.requestTemplate || {}, null, 2));
  };
  const preset = (id: string) => {
    const provider = catalog?.providers?.find((item) => item.id === id);
    if (!provider) return;
    setForm((current) => ({ ...current, provider: id, label: provider.label, protocol: provider.protocol,
      baseUrl: provider.baseUrl, authHeader: provider.authHeader || "Authorization", authPrefix: provider.authPrefix ?? "Bearer",
      billingMode: provider.billingMode || "metered", apiKey: "", requestPath: null,
      requestTemplate: null, responseTextPath: null }));
    setModelsText(provider.models.map((item) => item.id).join("\n"));
  };
  const save = async () => {
    setError(undefined); setBusy(true);
    try {
      let template: Record<string, unknown> | undefined;
      if (form.protocol === "custom_json") {
        try { template = JSON.parse(templateText); } catch { throw new Error("O modelo de requisição precisa ser um objeto JSON válido."); }
        if (!template || typeof template !== "object" || Array.isArray(template)) throw new Error("Use um objeto JSON para a requisição.");
      }
      const saved = await craftApi.saveLLMConnection(workspaceId, { ...form,
        apiKey: form.apiKey || undefined, models: modelsText.split(/\n/).map((id) => id.trim()).filter(Boolean),
        requestTemplate: template,
      }, editing && editing !== "new" ? editing.id : undefined);
      setForm(empty); setEditing(undefined);
      try { localStorage.setItem(preference, JSON.stringify({ connectionId: saved.id, model: saved.config.models[0] })); } catch { /* Optional preference. */ }
      reload((value) => value + 1);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível salvar a conexão."); }
    finally { setBusy(false); }
  };

  return <div className="craft-model-picker">
    <label>Conexão<select aria-label="Conexão de IA" value={choice} disabled={disabled || busy} onChange={(event) => {
      const next = connections.find((item) => item.id === event.target.value); setChoice(next?.id || ""); setModel(next?.config.models[0] || "");
    }}><option value="">{catalog?.legacyPlanningAvailable === false ? "Escolha uma conexão" : "Configuração do servidor"}</option>
      {connections.filter((item) => item.config.enabled).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
    </select></label>
    {selected && <label>Modelo<select aria-label="Modelo de IA" value={model} disabled={disabled || busy} onChange={(event) => setModel(event.target.value)}>
      {selected.config.models.map((id) => <option key={id} value={id}>{id}</option>)}
    </select></label>}
    {error && <p role="alert">{error}</p>}
    {canManage && <details className="craft-model-manager"><summary>Conexões de IA</summary>
      {connections.map((item) => <div key={item.id} className="craft-connection-row"><span>{item.label} · {item.config.enabled ? "Ativa" : "Desativada"}</span>
        <button disabled={busy || disabled} onClick={() => begin(item)}>Configurar</button>
        <button aria-label={`Remover conexão ${item.label}`} disabled={busy || disabled} onClick={async () => {
          setBusy(true); setError(undefined);
          try { await craftApi.removeLLMConnection(workspaceId, item); reload((value) => value + 1); }
          catch { setError("Não foi possível remover a conexão. Atualize antes de tentar novamente."); }
          finally { setBusy(false); }
        }}><X size={13} /></button>
      </div>)}
      <button disabled={busy || disabled} onClick={() => begin()}><Plus size={13} /> Adicionar conexão</button>
      {editing && <div className="craft-connection-form">
        <label>Provedor<select value={form.provider} disabled={busy} onChange={(event) => preset(event.target.value)}>
          {(catalog?.providers || []).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select></label>
        <label>Nome<input maxLength={120} value={form.label} onChange={(event) => setForm({ ...form, label: event.target.value })} disabled={busy} /></label>
        <label>Endpoint<input type="url" value={form.baseUrl} onChange={(event) => setForm({ ...form, baseUrl: event.target.value })} disabled={busy} /></label>
        <label>Protocolo<select value={form.protocol} onChange={(event) => setForm({ ...form, protocol: event.target.value as LLMProtocol })} disabled={busy}>
          {(Object.keys(protocolNames) as LLMProtocol[]).map((id) => <option key={id} value={id}>{protocolNames[id]}</option>)}
        </select></label>
        <label>Modelos · um identificador por linha<textarea aria-label="Modelos da conexão" value={modelsText} onChange={(event) => setModelsText(event.target.value)} disabled={busy} /></label>
        <label>Chave da API{editing !== "new" && editing.hasCredential && <small>Deixe em branco para manter a chave.</small>}
          <input type="password" autoComplete="off" value={form.apiKey || ""} onChange={(event) => setForm({ ...form, apiKey: event.target.value })} disabled={busy || !catalog?.credentialStorageReady} />
        </label>
        {!catalog?.credentialStorageReady && <p>Configure a chave de cifragem do servidor para cadastrar credenciais.</p>}
        <label>Autenticação · cabeçalho<input value={form.authHeader} onChange={(event) => setForm({ ...form, authHeader: event.target.value })} disabled={busy} /></label>
        <label>Prefixo da chave<input value={form.authPrefix} onChange={(event) => setForm({ ...form, authPrefix: event.target.value })} disabled={busy} /></label>
        <label>Cobrança<select value={form.billingMode} onChange={(event) => setForm({ ...form, billingMode: event.target.value as LLMConnectionInput["billingMode"] })} disabled={busy}>
          <option value="metered">API com cobrança</option><option value="local_free">Modelo local sem cobrança</option>
        </select></label>
        {form.billingMode === "metered" && <>
          <label>Limite total · US$<input type="number" min={0} step="0.01" value={form.budgetUsd} onChange={(event) => setForm({ ...form, budgetUsd: Number(event.target.value) })} disabled={busy} /></label>
          <label>Maior preço de entrada entre os modelos · US$ por milhão<input type="number" min={0} step="0.01" value={form.inputUsdPerMillion} onChange={(event) => setForm({ ...form, inputUsdPerMillion: Number(event.target.value) })} disabled={busy} /></label>
          <label>Maior preço de saída entre os modelos · US$ por milhão<input type="number" min={0} step="0.01" value={form.outputUsdPerMillion} onChange={(event) => setForm({ ...form, outputUsdPerMillion: Number(event.target.value) })} disabled={busy} /></label>
          <small>O limite usa os preços informados. Confira também o limite de cobrança no provedor.</small>
        </>}
        <label>Máximo de tokens de saída<input type="number" min={128} max={32000} value={form.maxOutputTokens} onChange={(event) => setForm({ ...form, maxOutputTokens: Number(event.target.value) })} disabled={busy} /></label>
        {form.protocol === "custom_json" && <>
          <label>Caminho da requisição<input placeholder="/generate" value={form.requestPath || ""} onChange={(event) => setForm({ ...form, requestPath: event.target.value })} disabled={busy} /></label>
          <label>Requisição JSON<textarea value={templateText} onChange={(event) => setTemplateText(event.target.value)} disabled={busy} /></label>
          <small>Use valores completos como {"${model}, ${prompt}, ${system}, ${max_tokens} e ${credential}"}.</small>
          <label>Caminho do texto na resposta<input placeholder="/output/text" value={form.responseTextPath || ""} onChange={(event) => setForm({ ...form, responseTextPath: event.target.value })} disabled={busy} /></label>
        </>}
        <label><input type="checkbox" checked={form.enabled} onChange={(event) => setForm({ ...form, enabled: event.target.checked })} disabled={busy} /> Ativar conexão</label>
        <button disabled={busy || !form.label.trim() || !form.baseUrl.trim() || !modelsText.trim()} onClick={() => void save()}><Save size={13} /> Salvar conexão</button>
        <button disabled={busy} onClick={() => { setEditing(undefined); setForm(empty); }}>Cancelar</button>
      </div>}
    </details>}
  </div>;
}
