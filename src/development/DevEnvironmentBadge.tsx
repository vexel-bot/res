import React from 'react';
import { useAuth } from '../context/AuthContext';
import './development.css';

type Status = { services: { express: string; studios: string; bridge: boolean }; costs: { externalBudgetUsd: number };
  models?: { roles?: Record<string, {mode:string;model?:string}>; klicConfigured?:boolean } };

export function DevEnvironmentBadge() {
  const { development } = useAuth();
  const [status, setStatus] = React.useState<Status>();
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  if (!development?.enabled) return null;
  async function refresh() {
    setLoading(true); setError('');
    try {
      const response = await fetch('/api/development/status', { credentials: 'same-origin' });
      if (!response.ok) throw new Error('Não foi possível consultar os serviços.');
      setStatus(await response.json());
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Serviço indisponível.'); }
    finally { setLoading(false); }
  }
  return <details className="clicko-dev-environment" onToggle={event => { if (event.currentTarget.open) void refresh(); }}>
    <summary title="Ambiente de Desenvolvimento"><span className="clicko-dev-short">DEV</span><span className="clicko-dev-label">Ambiente de Desenvolvimento</span></summary>
    <section aria-label="Serviços do ambiente DEV"><strong>Clicko DEV · somente local</strong>
      <p>Dados de teste isolados. Sessão local temporária. Não é uma conta comercial.</p>
      {loading && <p role="status">Consultando serviços…</p>}{error && <p role="alert">{error}</p>}
      {status && <ul><li>Express: {status.services.express === 'available' ? 'disponível' : 'indisponível'}</li>
        <li>Studios / FFmpeg: {status.services.studios === 'ready' ? 'disponíveis' : 'indisponíveis'}</li>
        <li>Ponte DEV: {status.services.bridge ? 'validada' : 'indisponível'}</li></ul>}
      <p>Composição de imagens, edição de vídeo e motion 2D usam ferramentas locais.</p>
      <p>Agentes: regras locais por padrão, sem inferência. Confira conexões configuradas no Studio.</p>
      {status?.models?.roles && <ul>{Object.entries(status.models.roles).map(([role,value]) => <li key={role}>
        {role === 'image' ? 'Agente visual' : 'Agente audiovisual'}: {value.mode === 'configured_not_verified' ? `modelo configurado (${value.model}) · não homologado` : 'modelo desativado · regras locais'}</li>)}</ul>}
      {status?.models && <p>KLIC: {status.models.klicConfigured ? 'configuração preservada' : 'modelo externo não configurado'} · chamadas externas bloqueadas.</p>}
      <p>Modelos generativos e motores Craft: dependem de configuração e homologação. Recursos “Em breve” não estão implementados.</p>
      <p>Chamadas pagas e integrações externas desativadas · orçamento R$ 0.</p>
      <button type="button" disabled={loading} onClick={() => void refresh()}>Atualizar indicadores</button>
    </section>
  </details>;
}
