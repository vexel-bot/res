import React from 'react';
import { createPortal } from 'react-dom';
import { ProfileAvatar } from './ProfileAvatar';
import { CreativeLoadingState } from './CreativeFeedback';
import { Ban, Check, ChevronDown, Clock3, Mail, MoreHorizontal, RefreshCw, Search, ShieldCheck, Trash2, UserPlus, Users, X } from 'lucide-react';
import { useGovernance } from '../context/GovernanceContext';
import { useOperations } from '../context/OperationsContext';
import { klicPageScope, useKlicPageDetails } from '../klic/pageContext';
import { useOffers } from '../context/OfferContext';
import { effectivePermissions, hasPermission, isPrivilegedRole, roleLabel, rolePresets, workspaceModules } from '../security/accessControl';
import type { AccessScope, OrganizationPermission, UserRole, WorkspaceMember, WorkspaceModule } from '../types';
import './TeamManagementView.css';

const formatDate = (value?: string) => {
  if (!value) return '—';
  if (!value.includes('T')) return value;
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value));
};

const statusLabel = { active: 'Ativo', invited: 'Convite pendente', disabled: 'Desativado' } as const;
const statusStyle = {
  active: 'border-[#FF7F50]/20 bg-[#FF7F50]/[0.08] text-[#FF7F50]',
  invited: 'border-[#F28500]/20 bg-[#F28500]/[0.08] text-[#F28500]',
  disabled: 'border-white/[0.07] bg-white/[0.03] text-[#808080]',
} as const;

export const TeamManagementView: React.FC = () => {
  const { users, workspace, plans, licenses, loading, currentUser, inviteUser, updateUser, deleteUser, resendInvite } = useGovernance();
  const { clients, connectedAccounts, activeWorkspace, activeClient } = useOperations();
  const { openOffer } = useOffers();
  const [query, setQuery] = React.useState('');
  const [status, setStatus] = React.useState<'all' | WorkspaceMember['status']>('all');
  const [showInvite, setShowInvite] = React.useState(false);
  const [editing, setEditing] = React.useState<WorkspaceMember | null>(null);
  const [editName, setEditName] = React.useState('');
  const [editRole, setEditRole] = React.useState<UserRole>('custom');
  const [editPermissions, setEditPermissions] = React.useState<OrganizationPermission[]>([]);
  const [editScope, setEditScope] = React.useState<AccessScope>(() => defaultScope());
  const [confirmDelete, setConfirmDelete] = React.useState<string | null>(null);
  const [invite, setInvite] = React.useState({ name: '', email: '', role: 'social_media' as UserRole, reserveSeat: false, modules: ['dashboard', 'create-image', 'create-copy', 'ai-chat', 'library', 'calendar'] as WorkspaceModule[], permissions: [...rolePresets.social_media.permissions] as OrganizationPermission[], scope: defaultScope() });
  const [editModules, setEditModules] = React.useState<WorkspaceModule[]>([]);
  useKlicPageDetails('team', klicPageScope(activeWorkspace.id, activeClient?.id), {
    view: editing ? 'Editar integrante' : showInvite ? 'Convidar integrante' : 'Equipe',
    filters: { busca: query, status },
    selected: editing ? { kind: 'integrante', id: editing.id } : undefined,
  });

  const plan = plans.find((item) => item.id === workspace?.planId);
  const occupiedSeats = licenses.filter((license) => license.status === 'in_use' || license.status === 'reserved').length;
  const maxUsers = workspace?.maxUsers;
  const atSeatLimit = maxUsers !== null && maxUsers !== undefined && occupiedSeats >= maxUsers;
  const seatsPercent = maxUsers ? Math.min(100, Math.round((occupiedSeats / maxUsers) * 100)) : 36;
  const filtered = users.filter((user) => {
    const matchesQuery = `${user.name} ${user.email}`.toLowerCase().includes(query.toLowerCase());
    return matchesQuery && (status === 'all' || user.status === status);
  });
  const canManageMembers = hasPermission(currentUser, 'members.manage');
  const canManagePermissions = hasPermission(currentUser, 'permissions.manage');
  const portalHost = typeof document === 'undefined' ? null : document.querySelector('.clicko-app-shell');

  const toggleModule = (module: WorkspaceModule, current: WorkspaceModule[], setValue: (modules: WorkspaceModule[]) => void) => {
    setValue(current.includes(module) ? current.filter((item) => item !== module) : [...current, module]);
  };

  const openEditor = (member: WorkspaceMember) => {
    setEditing(member);
    setEditName(member.name);
    setEditRole(member.role);
    setEditModules(member.modules);
    setEditPermissions([...effectivePermissions(member)]);
    setEditScope(member.scope ? { ...member.scope, clientIds: [...member.scope.clientIds], socialAccountIds: [...member.scope.socialAccountIds], projectIds: [...member.scope.projectIds], resourceIds: [...member.scope.resourceIds] } : defaultScope());
  };

  const openSeatOffer = (source: string) => openOffer({
    context: atSeatLimit ? 'limit_reached' : 'seat_increase',
    source,
    reason: atSeatLimit
      ? `Os ${maxUsers} assentos do plano ${plan?.name || 'atual'} já estão ocupados.`
      : `Seu ambiente utiliza ${occupiedSeats} de ${maxUsers ?? 'capacidade personalizada'} assentos do plano ${plan?.name || 'atual'}.`,
  });

  const beginInvite = () => {
    setShowInvite(true);
  };

  const sendInvite = async (event: React.FormEvent) => {
    event.preventDefault();
    const ok = await inviteUser(invite);
    if (ok) {
      setInvite({ name: '', email: '', role: 'social_media', reserveSeat: false, modules: ['dashboard', 'create-image', 'create-copy', 'ai-chat', 'library', 'calendar'], permissions: [...rolePresets.social_media.permissions], scope: defaultScope() });
      setShowInvite(false);
    }
  };

  if (loading && users.length === 0) return <CreativeLoadingState label="Carregando equipe e permissões" variant="table" />;

  return (
    <div className="mx-auto w-full max-w-[1500px] space-y-5 p-5 md:p-7">
      <header className="flex flex-col gap-4 border-b border-white/[0.06] pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.2em] text-[#808080]"><ShieldCheck className="h-3.5 w-3.5" /> Governança do ambiente de trabalho</div>
          <h1 className="text-[22px] font-semibold tracking-[-0.035em] text-white">Equipe e permissões</h1>
          <p className="mt-1 text-[10px] text-[#808080]">Controle usuários, convites e módulos liberados em um só lugar.</p>
        </div>
        {canManageMembers && <button onClick={beginInvite} className="flex h-10 items-center justify-center gap-2 rounded-lg bg-white px-4 text-[10px] font-semibold text-[#000000] transition hover:scale-[1.01]"><UserPlus className="h-4 w-4" />Convidar colaborador</button>}
      </header>

      <section className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/[0.065] bg-[rgba(128,128,128,0.14)] p-4"><div className="flex items-center justify-between text-[9px] text-[#808080]"><span>Plano atual</span><span className="rounded-full bg-white/[0.05] px-2 py-1 text-[rgba(255,255,255,0.72)]">{plan?.name || '—'}</span></div><div className="mt-4 text-[20px] font-semibold text-white">{occupiedSeats}<span className="text-[12px] font-normal text-[#808080]"> / {maxUsers ?? '∞'} assentos</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.055]"><div className="h-full rounded-full bg-[#FF7F50]" style={{ width: `${seatsPercent}%` }} /></div>{maxUsers !== null && maxUsers !== undefined && <button onClick={() => openSeatOffer('team.capacity-card')} className="mt-3 text-[8px] font-medium text-[#FF7F50] transition hover:text-[#F28500]">{atSeatLimit ? 'Limite atingido · ver opções' : 'Ver mais capacidade'}</button>}</div>
        <div className="rounded-xl border border-white/[0.065] bg-[rgba(128,128,128,0.14)] p-4"><div className="text-[9px] text-[#808080]">Usuários ativos</div><div className="mt-4 flex items-end justify-between"><strong className="text-[20px] font-semibold text-white">{users.filter((item) => item.status === 'active').length}</strong><Users className="h-5 w-5 text-[#808080]" /></div><p className="mt-2 text-[9px] text-[#808080]">Inclui o administrador do ambiente</p></div>
        <div className="rounded-xl border border-white/[0.065] bg-[rgba(128,128,128,0.14)] p-4"><div className="text-[9px] text-[#808080]">Convites pendentes</div><div className="mt-4 flex items-end justify-between"><strong className="text-[20px] font-semibold text-white">{users.filter((item) => item.status === 'invited').length}</strong><Mail className="h-5 w-5 text-[#808080]" /></div><p className="mt-2 text-[9px] text-[#808080]">{licenses.filter(item => item.status === 'available').length} licenças disponíveis · expiram em {workspace?.settings.inviteExpiryDays || 7} dias</p></div>
      </section>

      <section className="overflow-hidden rounded-xl border border-white/[0.065] bg-[rgba(128,128,128,0.14)]">
        <div className="flex flex-col gap-3 border-b border-white/[0.055] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full max-w-[340px]"><Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#808080]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por nome ou e-mail" className="h-9 w-full rounded-lg border border-white/[0.07] bg-[#000000] pl-9 pr-3 text-[10px] text-white outline-none focus:border-white/20" /></div>
          <label className="relative"><select value={status} onChange={(event) => setStatus(event.target.value as typeof status)} className="h-9 appearance-none rounded-lg border border-white/[0.07] bg-[#000000] pl-3 pr-8 text-[9px] text-[rgba(255,255,255,0.72)] outline-none"><option value="all">Todos os status</option><option value="active">Ativos</option><option value="invited">Convites pendentes</option><option value="disabled">Desativados</option></select><ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#808080]" /></label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] border-collapse text-left">
            <thead><tr className="border-b border-white/[0.05] text-[8px] uppercase tracking-[0.13em] text-[#808080]"><th className="px-4 py-3 font-medium">Usuário</th><th className="px-4 py-3 font-medium">Tipo</th><th className="px-4 py-3 font-medium">Status</th><th className="px-4 py-3 font-medium">Último acesso</th><th className="px-4 py-3 font-medium">Criado em</th><th className="px-4 py-3 font-medium">Módulos</th><th className="px-4 py-3 text-right font-medium">Ações</th></tr></thead>
            <tbody>{filtered.map((member) => <tr key={member.id} className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.018]"><td className="px-4 py-3.5"><div className="flex items-center gap-3"><ProfileAvatar src={member.avatar} className="h-8 w-8 rounded-lg object-cover grayscale-[35%]" fallback={<span className="grid h-8 w-8 place-items-center rounded-lg bg-white/[0.06] text-[10px] font-semibold text-[rgba(255,255,255,0.72)]">{member.name.split(' ').map((word) => word[0]).slice(0, 2).join('')}</span>} /><div><div className="text-[10px] font-medium text-white">{member.name}</div><div className="mt-0.5 text-[8px] text-[#808080]">{member.email}</div></div></div></td><td className="px-4 py-3.5"><span className={`text-[9px] ${isPrivilegedRole(member.role) ? 'text-white' : 'text-[rgba(255,255,255,0.72)]'}`}>{roleLabel(member.role)}</span></td><td className="px-4 py-3.5"><span className={`inline-flex rounded-full border px-2 py-1 text-[8px] ${statusStyle[member.status]}`}>{statusLabel[member.status]}</span></td><td className="px-4 py-3.5 text-[9px] text-[#808080]">{formatDate(member.lastAccess)}</td><td className="px-4 py-3.5 text-[9px] text-[#808080]">{formatDate(member.createdAt)}</td><td className="px-4 py-3.5"><div className="flex items-center gap-1.5"><span className="text-[9px] text-[rgba(255,255,255,0.72)]">{isPrivilegedRole(member.role) ? 'Todos' : member.modules.length}</span>{!isPrivilegedRole(member.role) && <span className="text-[8px] text-[#808080]">liberados</span>}</div></td><td className="px-4 py-3.5"><div className="flex items-center justify-end gap-1">{canManageMembers && !isPrivilegedRole(member.role) && <><button onClick={() => openEditor(member)} title="Editar acesso" className="rounded-md p-2 text-[#808080] hover:bg-white/[0.05] hover:text-white"><MoreHorizontal className="h-4 w-4" /></button>{member.status === 'invited' ? <button onClick={() => void resendInvite(member.id)} title="Reenviar convite" className="rounded-md p-2 text-[#808080] hover:bg-white/[0.05] hover:text-white"><RefreshCw className="h-3.5 w-3.5" /></button> : <button onClick={() => void updateUser(member.id, { status: member.status === 'active' ? 'disabled' : 'active' })} title={member.status === 'active' ? 'Desativar' : 'Ativar'} className="rounded-md p-2 text-[#808080] hover:bg-white/[0.05] hover:text-white">{member.status === 'active' ? <Ban className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}</button>}{confirmDelete === member.id ? <button onClick={() => { void deleteUser(member.id); setConfirmDelete(null); }} className="rounded-md bg-[#FF7F50]/10 px-2 py-1.5 text-[8px] text-[#FF7F50]">Confirmar</button> : <button onClick={() => setConfirmDelete(member.id)} title="Excluir" className="rounded-md p-2 text-[#808080] hover:bg-white/[0.05] hover:text-[#FF7F50]"><Trash2 className="h-3.5 w-3.5" /></button>}</>}</div></td></tr>)}</tbody>
          </table>
        </div>
        {filtered.length === 0 && <div className="p-10 text-center"><strong className="text-[12px] font-semibold">Nenhum usuário encontrado</strong><p className="mt-2 text-[10px] text-[#808080]">Revise a busca ou os status selecionados.</p><button type="button" onClick={() => { setQuery(''); setStatus('all'); }} className="mt-4 rounded-lg border border-white/[0.1] px-4 py-2 text-[10px] font-medium transition hover:bg-white/[0.06]">Limpar filtros</button></div>}
      </section>

      {(showInvite || editing) && portalHost && createPortal(<div className="team-access-drawer-backdrop fixed inset-0 z-[180] flex justify-end bg-black/65 backdrop-blur-sm"><button aria-label="Fechar painel" onClick={() => { setShowInvite(false); setEditing(null); }} className="absolute inset-0" /><aside className="team-access-drawer relative h-full w-full max-w-[520px] overflow-y-auto border-l border-white/[0.08] shadow-2xl"><div className="team-access-drawer-header flex items-start justify-between"><div><div className="text-[9px] uppercase tracking-[0.18em] text-[#808080]">{editing ? 'Permissões do colaborador' : 'Novo acesso'}</div><h2 className="mt-1 text-[18px] font-semibold text-white">{editing ? editing.name : 'Convidar colaborador'}</h2></div><button onClick={() => { setShowInvite(false); setEditing(null); }} className="rounded-lg p-2 text-[#808080] hover:bg-white/[0.05] hover:text-white"><X className="h-4 w-4" /></button></div>{editing ? <div className="team-access-drawer-body"><label><span className="mb-1.5 block text-[9px] text-[rgba(255,255,255,0.72)]">Nome completo</span><input value={editName} onChange={(event) => setEditName(event.target.value)} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#000000] px-3 text-[10px] text-white outline-none focus:border-white/25" /></label><RoleSelector value={editRole} onChange={(role) => { setEditRole(role); setEditPermissions([...rolePresets[role === 'collaborator' ? 'custom' : role].permissions]); }} /><ModuleSelector selected={editModules} onToggle={(module) => toggleModule(module, editModules, setEditModules)} />{canManagePermissions && <><PermissionSelector selected={editPermissions} onChange={setEditPermissions} /><ScopeSelector scope={editScope} onChange={setEditScope} clients={clients} accounts={connectedAccounts} /></>}<button onClick={async () => { if (await updateUser(editing.id, { name: editName, role: editRole, modules: editModules, permissions: editPermissions, scope: editScope })) setEditing(null); }} className="team-access-submit mt-6 h-10 w-full rounded-lg bg-white text-[10px] font-semibold text-[#000000]">Salvar alterações</button></div> : <form onSubmit={sendInvite} className="team-access-drawer-body"><div className="grid gap-3"><label><span className="mb-1.5 block text-[9px] text-[rgba(255,255,255,0.72)]">Nome completo</span><input required value={invite.name} onChange={(event) => setInvite((current) => ({ ...current, name: event.target.value }))} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#000000] px-3 text-[10px] text-white outline-none focus:border-white/25" /></label><label><span className="mb-1.5 block text-[9px] text-[rgba(255,255,255,0.72)]">E-mail</span><input required type="email" value={invite.email} onChange={(event) => setInvite((current) => ({ ...current, email: event.target.value }))} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#000000] px-3 text-[10px] text-white outline-none focus:border-white/25" /></label></div><RoleSelector value={invite.role} onChange={(role) => setInvite(current => ({ ...current, role, permissions: [...rolePresets[role === 'collaborator' ? 'custom' : role].permissions] }))} /><ModuleSelector selected={invite.modules} onToggle={(module) => toggleModule(module, invite.modules, (modules) => setInvite((current) => ({ ...current, modules })))} />{canManagePermissions && <><PermissionSelector selected={invite.permissions} onChange={(permissions) => setInvite(current => ({ ...current, permissions }))} /><ScopeSelector scope={invite.scope} onChange={(scope) => setInvite(current => ({ ...current, scope }))} clients={clients} accounts={connectedAccounts} /></>}<label className="mt-4 flex items-center gap-2 text-[9px] text-[#808080]"><input type="checkbox" checked={invite.reserveSeat} onChange={event => setInvite(current => ({ ...current, reserveSeat: event.target.checked }))} />Reservar uma licença agora</label><div className="team-access-note mt-5 flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.025] p-3 text-[9px] text-[#808080]"><Clock3 className="h-4 w-4 shrink-0" />Sem reserva, a licença será atribuída somente no aceite. O convite expira em {workspace?.settings.inviteExpiryDays || 7} dias.</div><button className="team-access-submit mt-5 h-10 w-full rounded-lg bg-white text-[10px] font-semibold text-[#000000]">Enviar convite</button></form>}</aside></div>, portalHost)}
    </div>
  );
};

const ModuleSelector: React.FC<{ selected: WorkspaceModule[]; onToggle: (module: WorkspaceModule) => void }> = ({ selected, onToggle }) => (
  <div className="team-access-modules mt-6"><div className="mb-3 text-[9px] font-medium uppercase tracking-[0.13em] text-[#808080]">Módulos liberados</div><div className="team-access-module-grid grid gap-2 sm:grid-cols-2">{workspaceModules.map((module) => { const checked = selected.includes(module.id); return <button key={module.id} type="button" onClick={() => onToggle(module.id)} className={`team-access-module flex items-start gap-3 rounded-lg border p-3 text-left transition ${checked ? 'border-white/20 bg-white/[0.06]' : 'border-white/[0.055] bg-[#000000]'}`}><span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border ${checked ? 'border-white bg-white text-black' : 'border-white/15'}`}>{checked && <Check className="h-3 w-3" />}</span><span><span className={`block text-[9px] font-medium ${checked ? 'text-white' : 'text-[rgba(255,255,255,0.72)]'}`}>{module.label}</span><span className="mt-0.5 block text-[8px] leading-relaxed text-[#808080]">{module.description}</span></span></button>; })}</div></div>
);

function defaultScope(): AccessScope {
  return { allClients: true, clientIds: [], allSocialAccounts: true, socialAccountIds: [], allProjects: true, projectIds: [], resourceIds: [] };
}

const permissionLabels: Record<OrganizationPermission, string> = {
  'organization.manage': 'Administrar organização', 'subscription.read': 'Ver assinatura', 'subscription.manage': 'Alterar assinatura', 'billing.read': 'Ver cobrança',
  'licenses.read': 'Ver licenças', 'licenses.manage': 'Gerenciar licenças', 'members.read': 'Ver equipe', 'members.manage': 'Gerenciar equipe',
  'permissions.manage': 'Gerenciar permissões', 'clients.read': 'Ver clientes', 'clients.manage': 'Gerenciar clientes', 'connections.read': 'Ver conexões',
  'connections.manage': 'Gerenciar conexões', 'content.create': 'Criar conteúdo', 'content.edit': 'Editar conteúdo', 'content.approve': 'Aprovar conteúdo',
  'content.publish': 'Publicar conteúdo', 'analytics.read': 'Ver Analytics', 'automations.manage': 'Gerenciar automações', 'audit.read': 'Ver auditoria',
  'usage.read.own': 'Ver consumo próprio', 'usage.read.organization': 'Ver consumo da organização', 'usage.manage': 'Definir limites de consumo',
};

const PermissionSelector: React.FC<{ selected: OrganizationPermission[]; onChange: (value: OrganizationPermission[]) => void }> = ({ selected, onChange }) => (
  <details className="mt-5 rounded-lg border border-white/[0.06] bg-white/[0.025] p-3"><summary className="cursor-pointer text-[9px] font-medium text-[rgba(255,255,255,0.78)]">Permissões granulares · {selected.length}</summary><div className="mt-3 grid gap-2 sm:grid-cols-2">{(Object.keys(permissionLabels) as OrganizationPermission[]).map((permission) => <label key={permission} className="flex items-start gap-2 text-[8px] leading-4 text-[#808080]"><input type="checkbox" checked={selected.includes(permission)} onChange={() => onChange(selected.includes(permission) ? selected.filter(item => item !== permission) : [...selected, permission])} /><span>{permissionLabels[permission]}</span></label>)}</div></details>
);

const ScopeSelector: React.FC<{ scope: AccessScope; onChange: (value: AccessScope) => void; clients: Array<{ id: string; name: string }>; accounts: Array<{ id: string; name?: string; handle: string }> }> = ({ scope, onChange, clients, accounts }) => {
  const toggleId = (field: 'clientIds' | 'socialAccountIds', id: string) => onChange({ ...scope, [field]: scope[field].includes(id) ? scope[field].filter(item => item !== id) : [...scope[field], id] });
  return <details className="mt-3 rounded-lg border border-white/[0.06] bg-white/[0.025] p-3"><summary className="cursor-pointer text-[9px] font-medium text-[rgba(255,255,255,0.78)]">Escopos de acesso</summary><div className="mt-3 space-y-4"><div><label className="flex items-center gap-2 text-[9px] text-[rgba(255,255,255,0.72)]"><input type="checkbox" checked={scope.allClients} onChange={event => onChange({ ...scope, allClients: event.target.checked, clientIds: event.target.checked ? [] : scope.clientIds })} />Todos os clientes</label>{!scope.allClients && <div className="mt-2 grid gap-1.5">{clients.length ? clients.map(client => <label key={client.id} className="flex items-center gap-2 text-[8px] text-[#808080]"><input type="checkbox" checked={scope.clientIds.includes(client.id)} onChange={() => toggleId('clientIds', client.id)} />{client.name}</label>) : <span className="text-[8px] text-[#808080]">Nenhum cliente disponível.</span>}</div>}</div><div><label className="flex items-center gap-2 text-[9px] text-[rgba(255,255,255,0.72)]"><input type="checkbox" checked={scope.allSocialAccounts} onChange={event => onChange({ ...scope, allSocialAccounts: event.target.checked, socialAccountIds: event.target.checked ? [] : scope.socialAccountIds })} />Todas as contas sociais</label>{!scope.allSocialAccounts && <div className="mt-2 grid gap-1.5">{accounts.length ? accounts.map(account => <label key={account.id} className="flex items-center gap-2 text-[8px] text-[#808080]"><input type="checkbox" checked={scope.socialAccountIds.includes(account.id)} onChange={() => toggleId('socialAccountIds', account.id)} />{account.name || account.handle}</label>) : <span className="text-[8px] text-[#808080]">Nenhuma conta conectada disponível.</span>}</div>}</div></div></details>;
};

const RoleSelector: React.FC<{ value: UserRole; onChange: (role: UserRole) => void }> = ({ value, onChange }) => (
  <label className="mt-4 block"><span className="mb-1.5 block text-[9px] text-[rgba(255,255,255,0.72)]">Papel de acesso</span><select value={value === 'collaborator' ? 'custom' : value} onChange={event => onChange(event.target.value as UserRole)} className="h-10 w-full rounded-lg border border-white/[0.08] bg-[#000000] px-3 text-[10px] text-white outline-none">{Object.entries(rolePresets).filter(([id]) => id !== 'master').map(([id, preset]) => <option key={id} value={id}>{preset.label}</option>)}</select></label>
);
