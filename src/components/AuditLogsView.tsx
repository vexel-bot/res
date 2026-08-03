import React from 'react';
import { Activity, Clock3, Download, FileSearch, Filter, Search, ShieldCheck } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { localizeAuditToken, localizeResource } from '../utils/localization';

const formatDateTime = (value: string) => new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value));

export const AuditLogsView: React.FC = () => {
  const { auditLogs, loading, workspace } = useGovernance();
  const [query, setQuery] = React.useState('');
  const [moduleFilter, setModuleFilter] = React.useState('all');
  const modules = Array.from(new Set(auditLogs.map((entry) => entry.resource.split(':')[0])));
  const visible = auditLogs.filter((entry) =>
    (moduleFilter === 'all' || entry.resource.startsWith(`${moduleFilter}:`))
    && `${entry.actorName} ${entry.action} ${entry.detail} ${entry.resource}`.toLowerCase().includes(query.toLowerCase()),
  );

  const exportCsv = () => {
    const rows = visible.map((entry) => [
      entry.actorName,
      workspace?.name || '',
      localizeAuditToken(entry.action),
      localizeResource(entry.resource),
      entry.createdAt,
      entry.detail,
    ].map((value) => `"${String(value).replaceAll('"', '""')}"`).join(','));
    const csv = ['Usuário,Empresa,Ação,Módulo,Data,Detalhes', ...rows].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'clicko-registros-de-auditoria.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return <div className="mx-auto w-full max-w-[1400px] space-y-5 p-5 md:p-7">
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/[0.06] pb-5">
      <div><div className="mb-2 flex items-center gap-2 text-[9px] uppercase tracking-[0.2em] text-[#8bd132]"><ShieldCheck className="h-3.5 w-3.5" />Segurança e rastreabilidade</div><h1 className="text-[22px] font-semibold tracking-[-0.035em] text-white">Registros de auditoria</h1><p className="mt-1 text-[10px] text-[#7f888d]">Registro pesquisável de ações, módulos, usuários e empresas.</p></div>
      <button onClick={exportCsv} className="flex items-center gap-2 rounded-lg border border-white/[0.07] bg-[#182126] px-4 py-2.5 text-[9px] text-[#c7ced1] hover:border-[#8bd132]/25 hover:text-[#8bd132]"><Download className="h-3.5 w-3.5" />Exportar CSV</button>
    </header>

    <div className="flex flex-wrap gap-2">
      <label className="flex h-10 min-w-[260px] flex-1 items-center gap-2 rounded-lg border border-white/[0.07] bg-[#182126] px-3"><Search className="h-4 w-4 text-[#748087]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Pesquisar usuário, ação ou detalhe…" className="w-full bg-transparent text-[9px] text-white outline-none" /></label>
      <label className="flex h-10 items-center gap-2 rounded-lg border border-white/[0.07] bg-[#182126] px-3"><Filter className="h-3.5 w-3.5 text-[#748087]" /><select value={moduleFilter} onChange={(event) => setModuleFilter(event.target.value)} className="bg-transparent text-[9px] text-white outline-none"><option value="all">Todos os módulos</option>{modules.map((module) => <option key={module} value={module}>{localizeAuditToken(module)}</option>)}</select></label>
    </div>

    <section className="overflow-hidden rounded-xl border border-white/[0.065] bg-[#111111]">
      <div className="flex items-center justify-between border-b border-white/[0.055] p-4"><div className="flex items-center gap-2 text-[10px] font-medium text-white"><Activity className="h-4 w-4 text-[#8bd132]" />Atividade recente</div><span className="text-[8px] text-[#636b6f]">{visible.length} eventos · {workspace?.name}</span></div>
      {loading && auditLogs.length === 0 ? <div className="p-8 text-[10px] text-[#71797d]">Carregando eventos…</div> : <div className="divide-y divide-white/[0.045]">
        {visible.map((entry) => <div key={entry.id} className="grid gap-3 p-4 sm:grid-cols-[36px_160px_110px_1fr_auto] sm:items-center">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.045] text-[#8bd132]"><FileSearch className="h-4 w-4" /></span>
          <div><div className="text-[9px] font-medium text-white">{entry.actorName}</div><div className="mt-0.5 text-[7px] text-[#60686c]">{workspace?.name}</div></div>
          <span className="w-fit rounded-full bg-[#8bd132]/[0.07] px-2 py-1 text-[7px] text-[#8bd132]">{localizeAuditToken(entry.resource.split(':')[0])}</span>
          <div><div className="text-[9px] text-[#a3aaad]">{entry.detail}</div><div className="mt-0.5 text-[7px] text-[#596166]">{localizeAuditToken(entry.action)} · {localizeResource(entry.resource)}</div></div>
          <div className="flex items-center gap-1.5 text-[7px] text-[#636b6f]"><Clock3 className="h-3 w-3" />{formatDateTime(entry.createdAt)}</div>
        </div>)}
        {visible.length === 0 && <div className="p-8 text-center text-[9px] text-[#687277]">Nenhum evento encontrado com estes filtros.</div>}
      </div>}
    </section>
  </div>;
};
