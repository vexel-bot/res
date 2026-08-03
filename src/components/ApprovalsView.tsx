import React from 'react';
import { CalendarClock, Check, ChevronRight, Clock3, History, MessageSquare, Send, ShieldCheck, ThumbsDown, Wrench, X } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import type { ApprovalStage, ContentApprovalItem } from '../types';

const stageMeta: Record<ApprovalStage, { label: string; className: string }> = {
  draft: { label: 'Rascunho', className: 'text-[#92999d] bg-white/[0.04]' },
  in_review: { label: 'Em revisão', className: 'text-sky-300 bg-sky-400/[0.08]' },
  pending_approval: { label: 'Aguardando aprovação', className: 'text-amber-300 bg-amber-400/[0.08]' },
  approved: { label: 'Aprovado', className: 'text-emerald-300 bg-emerald-400/[0.08]' },
  changes_requested: { label: 'Ajustes solicitados', className: 'text-orange-300 bg-orange-400/[0.08]' },
  rejected: { label: 'Reprovado', className: 'text-red-300 bg-red-400/[0.08]' },
  published: { label: 'Publicado', className: 'text-[#B8B8B8] bg-white/[0.06]' },
};

const formatDateTime = (value: string) => new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value));

export const ApprovalsView: React.FC<{ onStatusChange?: (contentId: string, stage: ApprovalStage) => void }> = ({ onStatusChange }) => {
  const { approvals, approvalAction, loading } = useGovernance();
  const [selectedId, setSelectedId] = React.useState<string>();
  const [comment, setComment] = React.useState('');
  const [scheduleAt, setScheduleAt] = React.useState('2026-08-03T18:30');
  const [filter, setFilter] = React.useState<'queue' | 'all'>('queue');

  React.useEffect(() => {
    if (!selectedId && approvals[0]) setSelectedId(approvals[0].id);
  }, [approvals, selectedId]);

  const visibleApprovals = filter === 'all' ? approvals : approvals.filter((item) => ['in_review', 'pending_approval', 'approved'].includes(item.stage));
  const selected = approvals.find((item) => item.id === selectedId) || visibleApprovals[0];

  const act = async (action: Parameters<typeof approvalAction>[1], requiredComment = false) => {
    if (!selected) return;
    if (requiredComment && !comment.trim()) return;
    const result = await approvalAction(selected.id, action, comment, action === 'schedule' ? new Date(scheduleAt).toISOString() : undefined);
    if (result) {
      onStatusChange?.(result.contentId, result.stage);
      setComment('');
    }
  };

  if (loading && approvals.length === 0) return <div className="p-8 text-[11px] text-[#7C7C7C]">Carregando central de aprovações…</div>;

  return (
    <div className="mx-auto w-full max-w-[1500px] p-5 md:p-7">
      <header className="mb-5 flex flex-col gap-4 border-b border-white/[0.06] pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div><div className="mb-2 flex items-center gap-2 text-[9px] uppercase tracking-[0.2em] text-[#7C7C7C]"><ShieldCheck className="h-3.5 w-3.5" /> Exclusivo do administrador</div><h1 className="text-[22px] font-semibold tracking-[-0.035em] text-white">Central de aprovações</h1><p className="mt-1 text-[10px] text-[#7f888d]">Revise, comente, aprove e publique conteúdos com rastreabilidade completa.</p></div>
        <div className="flex rounded-lg border border-white/[0.07] bg-[#111] p-1"><button onClick={() => setFilter('queue')} className={`rounded-md px-3 py-2 text-[9px] ${filter === 'queue' ? 'bg-white text-black' : 'text-[#858d91]'}`}>Fila ativa</button><button onClick={() => setFilter('all')} className={`rounded-md px-3 py-2 text-[9px] ${filter === 'all' ? 'bg-white text-black' : 'text-[#858d91]'}`}>Histórico completo</button></div>
      </header>

      <div className="grid min-h-[650px] overflow-hidden rounded-xl border border-white/[0.065] bg-[#111111] lg:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="border-b border-white/[0.06] lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between border-b border-white/[0.055] px-4 py-3"><span className="text-[9px] font-medium uppercase tracking-[0.14em] text-[#727a7e]">Conteúdos</span><span className="grid h-5 min-w-5 place-items-center rounded-full bg-white/[0.06] px-1.5 text-[8px] text-[#B8B8B8]">{visibleApprovals.length}</span></div>
          <div className="max-h-[610px] overflow-y-auto">{visibleApprovals.map((item) => <button key={item.id} onClick={() => setSelectedId(item.id)} className={`w-full border-b border-white/[0.045] p-4 text-left transition ${selected?.id === item.id ? 'bg-white/[0.055]' : 'hover:bg-white/[0.025]'}`}><div className="flex items-center justify-between gap-2"><span className={`rounded-full px-2 py-1 text-[7px] ${stageMeta[item.stage].className}`}>{stageMeta[item.stage].label}</span><span className="text-[7px] uppercase text-[#5d666a]">{item.platform}</span></div><h3 className="mt-3 line-clamp-2 text-[10px] font-medium leading-relaxed text-[#e4e7e8]">{item.title}</h3><div className="mt-3 flex items-center justify-between text-[8px] text-[#697277]"><span>{item.authorName}</span><span>{formatDateTime(item.createdAt)}</span></div></button>)}</div>
        </aside>

        {selected ? <main className="min-w-0"><div className="grid gap-5 p-5 xl:grid-cols-[minmax(0,1fr)_300px]"><div className="space-y-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><div className="text-[8px] uppercase tracking-[0.14em] text-[#697277]">{selected.platform} · {selected.format}</div><h2 className="mt-2 max-w-[760px] text-[18px] font-semibold leading-snug text-white">{selected.title}</h2><p className="mt-2 text-[9px] text-[#777f84]">Criado por <span className="text-[#B8B8B8]">{selected.authorName}</span> em {formatDateTime(selected.createdAt)}</p></div><span className={`shrink-0 rounded-full px-2.5 py-1.5 text-[8px] ${stageMeta[selected.stage].className}`}>{stageMeta[selected.stage].label}</span></div>
                <div className="overflow-hidden rounded-xl border border-white/[0.065] bg-[#0B0B0B]">{selected.previewUrl && <img src={selected.previewUrl} alt="Prévia do conteúdo" className="h-[250px] w-full object-cover opacity-75 grayscale-[25%]" />}<div className="p-4"><p className="whitespace-pre-line text-[10px] leading-6 text-[#c1c6c8]">{selected.copy}</p></div></div>
                <div className="rounded-xl border border-white/[0.065] bg-[#0E0E0E] p-4"><div className="flex items-center gap-2 text-[10px] font-medium text-white"><MessageSquare className="h-4 w-4 text-[#8b9498]" />Comentários</div><div className="mt-4 space-y-2">{selected.comments.length === 0 ? <p className="py-3 text-center text-[9px] text-[#5e676b]">Nenhum comentário nesta revisão.</p> : selected.comments.map((item) => <div key={item.id} className="rounded-lg border border-white/[0.05] bg-white/[0.025] p-3"><div className="flex items-center justify-between"><span className="text-[9px] font-medium text-[#d7dbdd]">{item.authorName}</span><span className="text-[7px] text-[#60696d]">{formatDateTime(item.createdAt)}</span></div><p className="mt-1.5 text-[9px] leading-relaxed text-[#90989c]">{item.message}</p></div>)}</div><div className="mt-3 flex gap-2"><input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Adicionar comentário ou orientação…" className="h-10 min-w-0 flex-1 rounded-lg border border-white/[0.07] bg-[#0B0B0B] px-3 text-[9px] text-white outline-none focus:border-white/20" /><button onClick={() => void act('comment', true)} disabled={!comment.trim()} className="grid h-10 w-10 place-items-center rounded-lg bg-white text-black disabled:opacity-30"><Send className="h-3.5 w-3.5" /></button></div></div>
              </div>
              <aside className="space-y-4"><div className="rounded-xl border border-white/[0.065] bg-[#0E0E0E] p-4"><h3 className="text-[10px] font-medium text-white">Decisão do administrador</h3><p className="mt-1 text-[8px] leading-relaxed text-[#687175]">A publicação só será liberada depois da aprovação registrada.</p><div className="mt-4 space-y-2"><button onClick={() => void act('approve')} disabled={selected.stage === 'approved' || selected.stage === 'published'} className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-white text-[9px] font-semibold text-black disabled:opacity-30"><Check className="h-3.5 w-3.5" />Aprovar conteúdo</button><button onClick={() => void act('request_changes', true)} disabled={!comment.trim()} className="flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-amber-400/15 bg-amber-400/[0.05] text-[8px] text-amber-200 disabled:opacity-30"><Wrench className="h-3.5 w-3.5" />Solicitar ajustes</button><button onClick={() => void act('reject', true)} disabled={!comment.trim()} className="flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-red-400/15 bg-red-400/[0.04] text-[8px] text-red-300 disabled:opacity-30"><ThumbsDown className="h-3.5 w-3.5" />Reprovar</button></div></div>
                <div className="rounded-xl border border-white/[0.065] bg-[#0E0E0E] p-4"><h3 className="text-[10px] font-medium text-white">Publicação</h3><div className="mt-3"><label className="text-[8px] text-[#717a7e]">Data e horário</label><input type="datetime-local" value={scheduleAt} onChange={(event) => setScheduleAt(event.target.value)} className="mt-1.5 h-9 w-full rounded-lg border border-white/[0.07] bg-[#0B0B0B] px-2 text-[8px] text-[#c6cbcd] outline-none" /></div><div className="mt-3 grid grid-cols-2 gap-2"><button onClick={() => void act('schedule')} disabled={selected.stage !== 'approved'} className="flex h-9 items-center justify-center gap-1.5 rounded-lg border border-white/[0.08] text-[8px] text-[#B8B8B8] disabled:opacity-25"><CalendarClock className="h-3.5 w-3.5" />Agendar</button><button onClick={() => void act('publish')} disabled={selected.stage !== 'approved'} className="flex h-9 items-center justify-center gap-1.5 rounded-lg bg-[#B8B8B8] text-[8px] font-semibold text-black disabled:opacity-25"><Send className="h-3.5 w-3.5" />Publicar agora</button></div>{selected.stage !== 'approved' && <p className="mt-2 flex items-start gap-1.5 text-[7px] leading-relaxed text-[#636b6f]"><X className="mt-0.5 h-3 w-3 shrink-0" />Bloqueado até a aprovação do administrador.</p>}</div>
                <div className="rounded-xl border border-white/[0.065] bg-[#0E0E0E] p-4"><div className="flex items-center gap-2 text-[10px] font-medium text-white"><History className="h-3.5 w-3.5" />Histórico</div><div className="mt-4 space-y-3">{selected.history.slice(0, 5).map((entry) => <div key={entry.id} className="relative border-l border-white/[0.08] pl-3"><span className="absolute -left-[3px] top-1 h-1.5 w-1.5 rounded-full bg-[#7C7C7C]" /><div className="text-[8px] text-[#b4babd]">{entry.detail}</div><div className="mt-1 text-[7px] text-[#5f686c]">{entry.actorName} · {formatDateTime(entry.createdAt)}</div></div>)}</div></div>
                <div className="rounded-xl border border-white/[0.065] bg-[#0E0E0E] p-4"><div className="flex items-center justify-between"><span className="text-[10px] font-medium text-white">Versões</span><span className="text-[8px] text-[#8bd132]">{selected.versions?.length || 1} registrada(s)</span></div><div className="mt-3 space-y-2">{(selected.versions || [{ id: 'initial', number: 1, label: 'Versão inicial', author: selected.authorName, createdAt: selected.createdAt }]).map((version) => <div key={version.id} className="rounded-lg border border-white/[0.05] bg-black/20 p-2.5"><div className="flex justify-between"><span className="text-[8px] text-[#d0d5d7]">v{version.number} · {version.label}</span><span className="text-[7px] text-[#626c70]">{formatDateTime(version.createdAt)}</span></div><p className="mt-1 text-[7px] text-[#707a7f]">{version.author}</p></div>)}</div></div>
              </aside></div></main> : <div className="grid place-items-center p-10 text-center"><div><Clock3 className="mx-auto h-6 w-6 text-[#50585c]" /><p className="mt-3 text-[10px] text-[#70787c]">Nenhum conteúdo nesta fila.</p></div></div>}
      </div>
      <div className="mt-4 flex items-center gap-2 rounded-lg border border-white/[0.055] bg-white/[0.018] px-4 py-3 text-[8px] text-[#687175]"><ChevronRight className="h-3.5 w-3.5" />Toda decisão registra autor, horário e alteração no registro de auditoria do ambiente de trabalho.</div>
    </div>
  );
};
