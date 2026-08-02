import type { NavigationTab, UserRole, WorkspaceMember, WorkspaceModule } from '../types';

export const workspaceModules: Array<{ id: WorkspaceModule; label: string; description: string }> = [
  { id: 'dashboard', label: 'Dashboard', description: 'Resumo e indicadores do Workspace' },
  { id: 'workspace', label: 'Workspace', description: 'Clientes, projetos e operação central' },
  { id: 'brain', label: 'Brain', description: 'Memória estratégica persistente da marca' },
  { id: 'strategy', label: 'Strategy', description: 'Campanhas, objetivos e planos de comunicação' },
  { id: 'studio', label: 'Studio', description: 'Criação de texto, imagem e vídeo' },
  { id: 'library', label: 'Biblioteca', description: 'Memória de ativos, versões e materiais' },
  { id: 'calendar', label: 'Agenda e Calendário', description: 'Planejamento editorial' },
  { id: 'automations', label: 'Templates e Automações', description: 'Fluxos liberados pelo Master' },
  { id: 'analytics', label: 'Analytics', description: 'Métricas e inteligência de desempenho' },
];

const masterOnlyTabs = new Set<NavigationTab>(['approvals', 'publisher', 'team', 'subscription', 'audit-logs', 'settings']);

const tabModules: Partial<Record<NavigationTab, WorkspaceModule>> = {
  dashboard: 'dashboard',
  workspace: 'workspace',
  brain: 'brain',
  strategy: 'strategy',
  studio: 'studio',
  library: 'library',
  calendar: 'calendar',
  analytics: 'analytics',
  automations: 'automations',
};

export function canAccessNavigation(user: Pick<WorkspaceMember, 'role' | 'modules'> | undefined, tab: NavigationTab) {
  if (!user) return false;
  if (user.role === 'master') return true;
  if (masterOnlyTabs.has(tab)) return false;
  const requiredModule = tabModules[tab];
  return requiredModule ? user.modules.includes(requiredModule) : false;
}

export function roleLabel(role: UserRole) {
  return role === 'master' ? 'Master' : 'Colaborador';
}

export function isCriticalTab(tab: NavigationTab) {
  return masterOnlyTabs.has(tab);
}
