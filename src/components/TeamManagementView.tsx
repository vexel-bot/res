import React from 'react';
import { Ban, Check, ChevronDown, Clock3, Mail, MoreHorizontal, RefreshCw, Search, ShieldCheck, Trash2, UserPlus, Users, X } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { useOffers } from '../context/OfferContext';
import { roleLabel, workspaceModules } from '../security/accessControl';
import type { WorkspaceMember, WorkspaceModule } from '../types';

const formatDate = (value?: string) => {
  if (!value) return '—';
  if (!value.includes('T')) return value;
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value));
};

const statusLabel = { active: 'Ativo', invited: 'Convite pendente', disabled: 'Desativado' } as const;
const statusStyle = {
  active: 'border-emerald-400/20 bg-emerald-400/[0.08] text-emerald-300',
  invited: 'border-amber-400/20 bg-amber-400/[0.08] text-amber-300',
  disabled: 'border-white/[0.07] bg-white/[0.03] text-[#747d82]',
} as const;

export const TeamManagementView: React.FC = () => {
  const { users, workspace, plans, loading, inviteUser, updateUser, deleteUser, resendInvite } = useGovernance();
  const { openOffer } = useOffers();
  const [query, setQuery] = React.useState('');
  const [status, setStatus] = React.useState<'all' | WorkspaceMember['status']>('all');
  const [showInvite, setShowInvite] = React.useState(false);
  const [editing, setEditing] = React.useState<WorkspaceMember | null>(null);
  const [editName, setEditName] = React.useState('');
  const [confirmDelete, setConfirmDelete] = React.useState<string | null>(null);
  const [invite, setInvite] = React.useState({ name: '', email: '', modules: ['dashboard', 'create-image', 'create-copy', 'ai-chat', 'templates', 'calendar'] as WorkspaceModule[] });
  const [editModules, setEditModules] = React.useState<WorkspaceModule[]>([]);

  const plan = plans.find((item) => item.id === workspace?.planId);
  const occupiedSeats = users.filter((user) => user.status !== 'disabled').length;
  const maxUsers = workspace?.maxUsers;
  const atSeatLimit = maxUsers !== null && maxUsers !== undefined && occupiedSeats >= maxUsers;
  const seatsPercent = maxUsers ? Math.min(100, Math.round((occupiedSeats / maxUsers) * 100)) : 36;
  const filtered = users.filter((user) => {
    const matchesQuery = `${user.name} ${user.email}`.toLowerCase().includes(query.toLowerCase());
    return matchesQuery && (status === 'all' || user.status === status);
  });

  const toggleModule = (module: WorkspaceModule, current: WorkspaceModule[], setValue: (modules: WorkspaceModule[]) => void) => {
    setValue(current.includes(module) ? current.filter((item) => item !== module) : [...current, module]);
  };

  const openEditor = (member: WorkspaceMember) => {
    setEditing(member);
    setEditName(member.name);
    setEditModules(member.modules);
  };

  const openSeatOffer = (source: string) => openOffer({
    context: atSeatLimit ? 'limit_reached' : 'seat_increase',
    source,
    reason: atSeatLimit
      ? `Os ${maxUsers} assentos do plano ${plan?.name || 'atual'} já estão ocupados.`
      : `Seu ambiente utiliza ${occupiedSeats} de ${maxUsers ?? 'capacidade personalizada'} assentos do plano ${plan?.name || 'atual'}.`,
  });

  const beginInvite = () => {
    if (atSeatLimit && openSeatOffer('team.invite-limit')) return;
    setShowInvite(true);
  };

  const sendInvite = async (event: React.FormEvent) => {
    event.preventDefault();
    if (atSeatLimit && openSeatOffer('team.invite-submit-limit')) {
      setShowInvite(false);
      return;
    }
    const ok = await inviteUser(invite);
    if (ok) {
      setInvite({ name: '', email: '', modules: ['dashboard', 'create-image', 'create-copy', 'ai-chat', 'templates', 'calendar'] });
      setShowInvite(false);
    }
  };

  if (loading && users.length === 0) return <div className="p-8 text-[11px] text-[#7C7C7C]">Carregando gestão de usuários…</div>;

  return (
    <div className="mx-auto w-full max-w-[1500px] space-y-5 p-5 md:p-7">
      <header className="flex flex-col gap-4 border-b border-white/[0.06] pb-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.2em] text-[#7C7C7C]"><ShieldCheck className="h-3.5 w-3.5" /> Governança do ambiente de trabalho</div>
          <h1 className="text-[22px] font-semibold tracking-[-0.035em] text-white">Equipe e permissões</h1>
          <p className="mt-1 text-[10px] text-[#7f888d]">Controle usuários, convites e módulos liberados em um só lugar.</p>
        </div>
        <button onClick={beginInvite} className="flex h-10 items-center justify-center gap-2 rounded-lg bg-white px-4 text-[10px] font-semibold text-[#0B0B0B] transition hover:scale-[1.01]"><UserPlus className="h-4 w-4" />{atSeatLimit ? 'Aumentar capacidade' : 'Convidar colaborador'}</button>
      </header>

      <section className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/[0.065] bg-[#131313] p-4"><div className="flex items-center justify-between text-[9px] text-[#7C7C7C]"><span>Plano atual</span><span className="rounded-full bg-white/[0.05] px-2 py-1 text-[#B8B8B8]">{plan?.name || '—'}</span></div><div className="mt-4 text-[20px] font-semibold text-white">{occupiedSeats}<span className="text-[12px] font-normal text-[#656b6f]"> / {maxUsers ?? '∞'} assentos</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.055]"><div className="h-full rounded-full bg-[#ff5c5c]" style={{ width: `${seatsPercent}%` }} /></div>{maxUsers !== null && maxUsers !== undefined && <button onClick={() => openSeatOffer('team.capacity-card')} className="mt-3 text-[8px] font-medium text-[#ff8a8a] transition hover:text-[#ffb078]">{atSeatLimit ? 'Limite atingido · ver opções' : 'Ver mais capacidade'}</button>}</div>
        <div className="rounded-xl border border-white/[0.065] bg-[#131313] p-4"><div className="text-[9px] text-[#7C7C7C]">Usuários ativos</div><div className="mt-4 flex items-end justify-between"><strong className="text-[20px] font-semibold text-white">{users.filter((item) => item.status === 'active').length}</strong><Users className="h-5 w-5 text-[#7C7C7C]" /></div><p className="mt-2 text-[9px] text-[#5f676b]">Inclui o administrador do ambiente</p></div>
        <div className="rounded-xl border border-white/[0.065] bg-[#131313] p-4"><div className="text-[9px] text-[#7C7C7C]">Convites pendentes</div><div className="mt-4 flex items-end justify-between"><strong className="text-[20px] font-semibold text-white">{users.filter((item) => item.status === 'invited').length}</strong><Mail className="h-5 w-5 text-[#7C7C7C]" /></div><p className="mt-2 text-[9px] text-[#5f676b]">Expiram em {workspace?.settings.inviteExpiryDays || 7} dias</p></div>
      </section>

      <section className="overflow-hidden rounded-xl border border-white/[0.065] bg-[#111111]">
        <div className="flex flex-col gap-3 border-b border-white/[0.055] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full max-w-[340px]"><Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#666e72]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por nome ou e-mail" className="h-9 w-full rounded-lg border border-white/[0.07] bg-[#0B0B0B] pl-9 pr-3 text-[10px] text-white outline-none focus:border-white/20" /></div>
          <label className="relative"><select value={status} onChange={(event) => setStatus(event.target.value as typeof status)} className="h-9 appearance-none rounded-lg border border-white/[0.07] bg-[#0B0B0B] pl-3 pr-8 text-[9px] text-[#aeb4b7] outline-none"><option value="all">Todos os status</option><option value="active">Ativos</option><option value="invited">Convites pendentes</option><option value="disabled">Desativados</option></select><ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#687075]" /></label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] border-collapse text-left">
            <thead><tr className="border-b border-white/[0.05] text-[8px] uppercase tracking-[0.13em] text-[#626b70]"><th className="px-4 py-3 font-medium">Usuário</th><th className="px-4 py-3 font-medium">Tipo</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Último acesso</th><th className="px-4 py-3 font-medium">Criado em</th><th className="px-4 py-3 font-medium">Módulos</th><th className="px-4 py-3 text-right font-medium">Ações</th></tr></thead>
            <tbody>{filtered.map((member) => <tr key={member.id} className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.018]"><td className="px-4 py-3.5"><div className="flex items-center gap-3">{member.avatar ? <img src={member.avatar} alt="" className="h-8 w-8 rounded-lg object-cover grayscale-[35%]" /> : <span className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.06] text-[10px] font-semibold text-[#B8B8B8]">{member.name.split(' ').map((word) => word[0]).slice(0, 2).join('')}</span>}<div><div className="text-[10px] font-medium text-white">{member.name}</div><div className="mt-0.5 text-[8px] text-[#697277]">{member.email}</div></div></div></td><td className="px-4 py-3.5"><span className={`text-[9px] ${member.role === 'master' ? 'text-white' : 'text-[#9ca4a8]'}`}>{roleLabel(member.role)}</span></td><td className="px-4 py-3.5"><span className={`inline-flex rounded-full border px-2 py-1 text-[8px] ${statusStyle[member.status]}`}>{statusLabel[member.status]}</span></td><td className="px-4 py-3.5 text-[9px] text-[#899297]">{formatDate(member.lastAccess)}</td><td className="px-4 py-3.5 text-[9px] text-[#899297]">{formatDate(member.createdAt)}</td><td className="px-4 py-3.5"><div className="flex items-center gap-1.5"><span className="text-[9px] text-[#c1c6c9]">{member.role === 'master' ? 'Todos' : member.modules.length}</span>{member.role !== 'master' && <span className="text-[8px] text-[#646d71]">liberados</span>}</div></td><td className="px-4 py-3.5"><div className="flex items-center justify-end gap-1">{member.role !== 'master' && <><button onClick={() => openEditor(member)} title="Editar módulos" className="rounded-md p-2 text-[#778085] hover:bg-white/[0.05] hover:text-white"><MoreHorizontal className="h-4 w-4" /></button>{member.status === 'invited' ? <button onClick={() => void resendInvite(member.id)} title="Reenviar convite" className="rounded-md p-2 text-[#778085] hover:bg-white/[0.05] hover:text-white"><RefreshCw className="h-3.5 w-3.5" /></button> : <button onClick={() => void updateUser(member.id, { status: member.status === 'active' ? 'disabled' : 'active' })} title={member.status === 'active' ? 'Desativar' : 'Ativar'} className="rounded-md p-2 text-[#778085] hover:bg-white/[0.05] hover:text-white">{member.status === 'active' ? <Ban className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}</button>}{confirmDelete === member.id ? <button onClick={() => { void deleteUser(member.id); setConfirmDelete(null); }} className="rounded-md bg-red-400/10 px-2 py-1.5 text-[8px] text-red-300">Confirmar</button> : <button onClick={() => setConfirmDelete(member.id)} title="Excluir" className="rounded-md p-2 text-[#778085] hover:bg-red-400/[0.08] hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button>}</>}</div></td></tr>)}</tbody>
          </table>
        </div>
        {filtered.length === 0 && <div className="p-10 text-center text-[10px] text-[#687075]">Nenhum usuário encontrado com esses filtros.</div>}
      </section>

      {(showInvite || editing) && <div className="fixed inset-0 z-[90] flex justify-end bg-black/65 backdrop-blur-sm"><button aria-label="Fechar painel" onClick={() => { setShowInvite(false); setEditing(null); }} className="absolute inset-0" /><aside className="relative h-full w-full max-w-[480px] overflow-y-auto border-l border-white/[0.08] bg-[#101010] p-6 shadow-2xl"><div className="flex items-start justify-between"><div><div className="text-[9px] uppercase tracking-[0.18em] text-[#70787c]">{editing ? 'Permissões do colaborador' : 'Novo acesso'}</div><h2 className="mt-1 text-[18px] font-semibold text-white">{editing ? editing.name : 'Convidar colaborador'}</h2></div><button onClick={() => { setShowInvite(false); setEditing(null); }} className="rounded-lg p-2 text-[#6f777b] hover:bg-white/[0.05] hover:text-white"><X className="h-4 w-4" /></button></div>{editing ? <div className="mt-7"><label><span className="mb-1.5 block text-[9px] text-[#a7adb0]">Nome completo</span><input value={editName} onChange={(event) => setEditName(event.target.value)} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#0B0B0B] px-3 text-[10px] text-white outline-none focus:border-white/25" /></label><p className="mt-4 rounded-lg border border-white/[0.06] bg-white/[0.025] p-3 text-[9px] leading-relaxed text-[#879095]">O colaborador verá apenas os módulos selecionados. Publicação, aprovações, assinatura, integrações, APIs e configurações críticas permanecem exclusivas do administrador.</p><ModuleSelector selected={editModules} onToggle={(module) => toggleModule(module, editModules, setEditModules)} /><button onClick={async () => { if (await updateUser(editing.id, { name: editName, modules: editModules })) setEditing(null); }} className="mt-6 h-10 w-full rounded-lg bg-white text-[10px] font-semibold text-[#0B0B0B]">Salvar alterações</button></div> : <form onSubmit={sendInvite} className="mt-7"><div className="grid gap-3"><label><span className="mb-1.5 block text-[9px] text-[#a7adb0]">Nome completo</span><input required value={invite.name} onChange={(event) => setInvite((current) => ({ ...current, name: event.target.value }))} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#0B0B0B] px-3 text-[10px] text-white outline-none focus:border-white/25" /></label><label><span className="mb-1.5 block text-[9px] text-[#a7adb0]">E-mail</span><input required type="email" value={invite.email} onChange={(event) => setInvite((current) => ({ ...current, email: event.target.value }))} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#0B0B0B] px-3 text-[10px] text-white outline-none focus:border-white/25" /></label></div><ModuleSelector selected={invite.modules} onToggle={(module) => toggleModule(module, invite.modules, (modules) => setInvite((current) => ({ ...current, modules })))} /><div className="mt-5 flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.025] p-3 text-[9px] text-[#81898e]"><Clock3 className="h-4 w-4 shrink-0" />O convite expira automaticamente em {workspace?.settings.inviteExpiryDays || 7} dias.</div><button className="mt-5 h-10 w-full rounded-lg bg-white text-[10px] font-semibold text-[#0B0B0B]">Enviar convite</button></form>}</aside></div>}
    </div>
  );
};

const ModuleSelector: React.FC<{ selected: WorkspaceModule[]; onToggle: (module: WorkspaceModule) => void }> = ({ selected, onToggle }) => (
  <div className="mt-6"><div className="mb-3 text-[9px] font-medium uppercase tracking-[0.13em] text-[#727b7f]">Módulos liberados</div><div className="grid gap-2 sm:grid-cols-2">{workspaceModules.map((module) => { const checked = selected.includes(module.id); return <button key={module.id} type="button" onClick={() => onToggle(module.id)} className={`flex items-start gap-3 rounded-lg border p-3 text-left transition ${checked ? 'border-white/20 bg-white/[0.06]' : 'border-white/[0.055] bg-[#0B0B0B]'}`}><span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border ${checked ? 'border-white bg-white text-black' : 'border-white/15'}`}>{checked && <Check className="h-3 w-3" />}</span><span><span className={`block text-[9px] font-medium ${checked ? 'text-white' : 'text-[#9ba2a6]'}`}>{module.label}</span><span className="mt-0.5 block text-[8px] leading-relaxed text-[#626b70]">{module.description}</span></span></button>; })}</div></div>
);
