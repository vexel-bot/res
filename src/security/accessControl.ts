import type { NavigationTab, OrganizationPermission, UserRole, WorkspaceMember, WorkspaceModule } from '../types';

export const workspaceModules: Array<{ id: WorkspaceModule; label: string; description: string }> = [
  { id: 'dashboard', label: 'Painel', description: 'Resumo inteligente da operação' },
  { id: 'create-image', label: 'Criar Imagem', description: 'Geração e edição visual com a KLIC' },
  { id: 'create-video', label: 'Criar Vídeo', description: 'Produção e exportação de vídeos' },
  { id: 'create-copy', label: 'Criar Texto', description: 'Textos, roteiros, SEO e campanhas' },
  { id: 'calendar', label: 'Calendário', description: 'Planejamento e agendamento editorial' },
  { id: 'analytics', label: 'Análises', description: 'Métricas, relatórios e recomendações' },
  { id: 'ai-chat', label: 'KLIC', description: 'IA da Clicko Studios com memória contextual' },
  { id: 'automations', label: 'Automações', description: 'Fluxos, gatilhos e execuções' },
  { id: 'connected-accounts', label: 'Conexões', description: 'Canais e integrações sociais' },
  { id: 'workspace', label: 'Ambiente de Trabalho', description: 'Empresas, clientes e projetos' },
  { id: 'strategy', label: 'Estratégia', description: 'Campanhas e planos de comunicação' },
  { id: 'library', label: 'Biblioteca', description: 'Ativos, versões e materiais' },
];

export const isPrivilegedRole = (role: UserRole | undefined) => role === 'master';

export const rolePresets: Record<Exclude<UserRole, 'collaborator'>, { label: string; permissions: OrganizationPermission[] }> = {
  master: { label: 'Master', permissions: ['organization.manage', 'subscription.read', 'subscription.manage', 'billing.read', 'licenses.read', 'licenses.manage', 'members.read', 'members.manage', 'permissions.manage', 'clients.read', 'clients.manage', 'connections.read', 'connections.manage', 'content.create', 'content.edit', 'content.approve', 'content.publish', 'analytics.read', 'automations.manage', 'audit.read', 'usage.read.own', 'usage.read.organization', 'usage.manage'] },
  administrator: { label: 'Administrador', permissions: ['organization.manage', 'subscription.read', 'licenses.read', 'licenses.manage', 'members.read', 'members.manage', 'permissions.manage', 'clients.read', 'clients.manage', 'connections.read', 'connections.manage', 'content.create', 'content.edit', 'content.approve', 'content.publish', 'analytics.read', 'automations.manage', 'audit.read', 'usage.read.own', 'usage.read.organization', 'usage.manage'] },
  manager: { label: 'Gestor', permissions: ['members.read', 'clients.read', 'clients.manage', 'connections.read', 'content.create', 'content.edit', 'content.approve', 'content.publish', 'analytics.read', 'automations.manage', 'usage.read.own', 'usage.read.organization'] },
  social_media: { label: 'Social Media', permissions: ['clients.read', 'connections.read', 'content.create', 'content.edit', 'content.publish', 'analytics.read', 'usage.read.own'] },
  creative: { label: 'Designer / Criativo', permissions: ['clients.read', 'content.create', 'content.edit', 'usage.read.own'] },
  analyst: { label: 'Analista', permissions: ['clients.read', 'connections.read', 'analytics.read', 'usage.read.own'] },
  approver: { label: 'Aprovador', permissions: ['clients.read', 'content.approve', 'analytics.read', 'usage.read.own'] },
  custom: { label: 'Personalizado', permissions: ['usage.read.own'] },
};

export const effectivePermissions = (user: Pick<WorkspaceMember, 'role' | 'permissions'> | undefined): OrganizationPermission[] => {
  if (!user) return [];
  if (user.permissions) return user.permissions;
  if (user.role === 'collaborator') return rolePresets.custom.permissions;
  return rolePresets[user.role].permissions;
};

export const hasPermission = (user: Pick<WorkspaceMember, 'role' | 'permissions'> | undefined, permission: OrganizationPermission) =>
  Boolean(user && (user.role === 'master' || effectivePermissions(user).includes(permission)));

const tabPermissions: Partial<Record<NavigationTab, OrganizationPermission>> = {
  approvals: 'content.approve',
  'connected-accounts': 'connections.read',
  workspace: 'clients.read',
  analytics: 'analytics.read',
  automations: 'automations.manage',
  team: 'members.read',
  subscription: 'subscription.read',
};

const tabModules: Partial<Record<NavigationTab, WorkspaceModule>> = {
  dashboard: 'dashboard',
  'create-image': 'create-image',
  'create-video': 'create-video',
  'create-copy': 'create-copy',
  calendar: 'calendar',
  analytics: 'analytics',
  'ai-chat': 'ai-chat',
  automations: 'automations',
  'connected-accounts': 'connected-accounts',
  workspace: 'workspace', strategy: 'strategy', library: 'library',
};

const corporateOnlyTabs = new Set<NavigationTab>(['approvals', 'team', 'automations', 'workspace']);

export function canAccessNavigation(
  user: Pick<WorkspaceMember, 'role' | 'modules' | 'permissions'> | undefined,
  tab: NavigationTab,
  environmentMode: 'company' | 'personal' = 'company'
) {
  if (!user) return false;
  if (environmentMode === 'personal' && corporateOnlyTabs.has(tab)) {
    return false;
  }
  if (isPrivilegedRole(user.role)) return true;
  const requiredPermission = tabPermissions[tab];
  if (requiredPermission && !hasPermission(user, requiredPermission)) return false;
  const requiredModule = tabModules[tab];
  return requiredModule ? user.modules.includes(requiredModule) : true;
}

export function roleLabel(role: UserRole) {
  if (role === 'collaborator') return 'Colaborador';
  return rolePresets[role].label;
}
