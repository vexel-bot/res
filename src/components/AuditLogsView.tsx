import React from 'react';
import { Activity, Clock3, Download, FileSearch, Filter, Search, ShieldCheck, X } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import type { AuditLogEntry } from '../types';
import { localizeAuditToken, localizeResource } from '../utils/localization';
import { csvCell } from '../utils/csv';
import { ClickoLoader } from './ClickoLoader';

const formatDateTime = (value: string) => Number.isFinite(Date.parse(value)) ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : 'Data indisponível';

export const AuditLogsView: React.FC<{ embedded?: boolean }> = ({ embedded = false }) => {
  const { auditLogs, loading, workspace } = useGovernance();
  const [query, setQuery] = React.useState('');
  const [moduleFilter, setModuleFilter] = React.useState('all');
  const [actorFilter, setActorFilter] = React.useState('all');
  const [periodFilter, setPeriodFilter] = React.useState('30');
  const [selected, setSelected] = React.useState<AuditLogEntry | null>(null);
  React.useEffect(() => { setSelected(null); setQuery(''); setModuleFilter('all'); setActorFilter('all'); }, [workspace?.id]);
  const modules = React.useMemo(() => Array.from(new Set(auditLogs.map((entry) => entry.resource.split(':')[0]))), [auditLogs]);
  const actors = React.useMemo(() => Array.from(new Set(auditLogs.map((entry) => entry.actorName))), [auditLogs]);
  const visible = React.useMemo(() => {
    const cutoff = periodFilter === 'all' ? 0 : Date.now() - Number(periodFilter) * 86_400_000;
    return auditLogs.filter((entry) =>
      (moduleFilter === 'all' || entry.resource.startsWith(`${moduleFilter}:`))
      && (actorFilter === 'all' || entry.actorName === actorFilter)
      && (!cutoff || new Date(entry.createdAt).getTime() >= cutoff)
      && `${entry.actorName} ${entry.action} ${entry.detail} ${entry.resource}`.toLowerCase().includes(query.toLowerCase()),
    );
  }, [actorFilter, auditLogs, moduleFilter, periodFilter, query]);

  const exportCsv = () => {
    if (!visible.length) return;
    const rows = visible.map((entry) => [entry.actorName, workspace?.name || '', localizeAuditToken(entry.action), localizeResource(entry.resource), entry.createdAt, entry.detail].map(csvCell).join(','));
    const url = URL.createObjectURL(new Blob([['Usuário,Ambiente,Ação,Origem,Data,Detalhes', ...rows].join('\n')], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'clicko-registros-de-auditoria.csv'; anchor.click(); URL.revokeObjectURL(url);
  };

  return <div className={`clicko-audit-log w-full space-y-5 ${embedded ? 'p-0' : 'mx-auto max-w-[1400px] p-5 md:p-7'}`}>
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/[0.06] pb-5">
      <div><div className="mb-2 flex items-center gap-2 text-[8px] uppercase tracking-[0.18em] text-[#FF7F50]"><ShieldCheck className="h-3.5 w-3.5" />Segurança e rastreabilidade</div>{embedded ? <h3 className="text-[14px] font-semibold text-white">Atividades do ambiente</h3> : <h1 className="text-[22px] font-semibold text-white">Registros de auditoria</h1>}<p className="mt-1 text-[9px] leading-5 text-[#808080]">Eventos reais fornecidos pela governança de {workspace?.name || 'este ambiente'}.</p></div>
      <button type="button" onClick={exportCsv} disabled={!visible.length} className="flex h-9 items-center gap-2 rounded-lg border border-white/[0.07] px-3 text-[8px] text-[rgba(255,255,255,0.72)] hover:border-[#FF7F50]/25 hover:text-[#FF7F50] disabled:cursor-not-allowed disabled:opacity-35"><Download className="h-3.5 w-3.5" />Exportar CSV</button>
    </header>

    <div className="grid gap-2 lg:grid-cols-[minmax(240px,1fr)_160px_170px_150px]">
      <label className="flex h-10 items-center gap-2 rounded-lg border border-white/[0.07] bg-[rgba(128,128,128,0.14)] px-3"><Search className="h-3.5 w-3.5 text-[#808080]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Pesquisar usuário, evento ou detalhe" className="min-w-0 flex-1 bg-transparent text-[9px] text-white outline-none" /></label>
      <FilterSelect icon={<Clock3 className="h-3.5 w-3.5" />} value={periodFilter} onChange={setPeriodFilter}><option value="7">Últimos 7 dias</option><option value="30">Últimos 30 dias</option><option value="90">Últimos 90 dias</option><option value="all">Todo o período</option></FilterSelect>
      <FilterSelect icon={<Filter className="h-3.5 w-3.5" />} value={actorFilter} onChange={setActorFilter}><option value="all">Todos os usuários</option>{actors.map((actor) => <option key={actor} value={actor}>{actor}</option>)}</FilterSelect>
      <FilterSelect icon={<Activity className="h-3.5 w-3.5" />} value={moduleFilter} onChange={setModuleFilter}><option value="all">Todas as categorias</option>{modules.map((module) => <option key={module} value={module}>{localizeAuditToken(module)}</option>)}</FilterSelect>
    </div>

    <section className="overflow-hidden rounded-xl border border-white/[0.06]">
      <div className="flex items-center justify-between border-b border-white/[0.055] px-4 py-3"><div className="flex items-center gap-2 text-[10px] font-medium text-white"><Activity className="h-4 w-4 text-[#FF7F50]" />Atividade recente</div><span className="text-[8px] text-[#808080]">{visible.length} {visible.length === 1 ? 'evento' : 'eventos'}</span></div>
      <div className="hidden grid-cols-[145px_150px_130px_minmax(220px,1fr)_80px] border-b border-white/[0.05] px-4 py-2 text-[7px] uppercase tracking-[0.12em] text-[#808080] md:grid"><span>Data e hora</span><span>Usuário</span><span>Categoria</span><span>Evento</span><span>Status</span></div>
      {loading && !auditLogs.length ? <div className="flex min-h-36 items-center justify-center"><ClickoLoader label="Carregando eventos" message="Carregando eventos…" /></div> : <div className="divide-y divide-white/[0.045]">{visible.map((entry) => <button type="button" key={entry.id} onClick={() => setSelected(entry)} className="grid w-full gap-2 px-4 py-3.5 text-left hover:bg-white/[0.02] md:grid-cols-[145px_150px_130px_minmax(220px,1fr)_80px] md:items-center"><span className="flex items-center gap-1.5 text-[8px] text-[#808080]"><Clock3 className="h-3 w-3" />{formatDateTime(entry.createdAt)}</span><span className="truncate text-[9px] font-medium text-white">{entry.actorName}</span><span className="w-fit rounded-full bg-[#FF7F50]/[0.07] px-2 py-1 text-[7px] text-[#FF7F50]">{localizeAuditToken(entry.resource.split(':')[0])}</span><span className="min-w-0"><strong className="block truncate text-[9px] font-normal text-[rgba(255,255,255,0.72)]">{entry.detail}</strong><small className="mt-0.5 block truncate text-[7px] text-[#808080]">{localizeAuditToken(entry.action)} · {localizeResource(entry.resource)}</small></span><span className="flex items-center gap-1.5 text-[7px] text-[#808080]"><span className="h-1.5 w-1.5 rounded-full bg-[#FF7F50]" />Registrado</span></button>)}{!visible.length && <div className="grid min-h-40 place-items-center px-5 text-center"><div><FileSearch className="mx-auto h-5 w-5 text-[#808080]" /><h4 className="mt-3 text-[10px] font-medium text-white">Nenhum evento encontrado</h4><p className="mt-1 text-[8px] text-[#808080]">Ajuste os filtros ou aguarde novos registros reais do ambiente.</p></div></div>}</div>}
    </section>

    {selected && <div className="fixed inset-0 z-[90] flex justify-end bg-black/65 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Detalhes do registro" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelected(null); }}><aside className="h-full w-full max-w-md border-l border-white/[0.08] bg-[rgba(128,128,128,0.14)] p-5 shadow-2xl shadow-black/70"><header className="flex items-start justify-between gap-4 border-b border-white/[0.06] pb-5"><div><span className="text-[8px] uppercase tracking-[0.16em] text-[#FF7F50]">Registro de auditoria</span><h3 className="mt-2 text-[15px] font-semibold text-white">Detalhes do evento</h3></div><button type="button" onClick={() => setSelected(null)} className="grid h-8 w-8 place-items-center rounded-lg text-[#808080] hover:bg-white/[0.04] hover:text-white" aria-label="Fechar"><X className="h-4 w-4" /></button></header><dl className="mt-5 divide-y divide-white/[0.05]">{[['Data e hora', formatDateTime(selected.createdAt)], ['Usuário', selected.actorName], ['Ação', localizeAuditToken(selected.action)], ['Origem', localizeResource(selected.resource)], ['Ambiente', workspace?.name || 'Não informado'], ['Status', 'Registrado']].map(([term, detail]) => <div key={term} className="grid grid-cols-[110px_1fr] gap-3 py-3"><dt className="text-[8px] text-[#808080]">{term}</dt><dd className="break-words text-[9px] text-[rgba(255,255,255,0.72)]">{detail}</dd></div>)}</dl><section className="mt-5 rounded-xl border border-white/[0.06] bg-white/[0.018] p-4"><span className="text-[8px] uppercase tracking-[0.14em] text-[#808080]">Descrição</span><p className="mt-2 text-[10px] leading-5 text-[rgba(255,255,255,0.72)]">{selected.detail}</p></section></aside></div>}
  </div>;
};

const FilterSelect: React.FC<{ icon: React.ReactNode; value: string; onChange: (value: string) => void; children: React.ReactNode }> = ({ icon, value, onChange, children }) => <label className="flex h-10 min-w-0 items-center gap-2 rounded-lg border border-white/[0.07] bg-[rgba(128,128,128,0.14)] px-3 text-[#808080]">{icon}<select value={value} onChange={(event) => onChange(event.target.value)} className="min-w-0 flex-1 bg-transparent text-[8px] text-white outline-none">{children}</select></label>;
