import type { NavigationTab, UserRole, WorkspaceMember, WorkspaceModule } from '../types';

export const workspaceModules: Array<{ id: WorkspaceModule; label: string; description: string }> = [
  { id: 'dashboard', label: 'Painel', description: 'Resumo inteligente da operação' },
  { id: 'create-image', label: 'Criar Imagem', description: 'Geração e edição visual com IA' },
  { id: 'create-video', label: 'Criar Vídeo', description: 'Produção e exportação de vídeos' },
  { id: 'create-copy', label: 'Criar Texto', description: 'Textos, roteiros, SEO e campanhas' },
  { id: 'calendar', label: 'Calendário', description: 'Planejamento e agendamento editorial' },
  { id: 'analytics', label: 'Análises', description: 'Métricas, relatórios e recomendações' },
  { id: 'ai-chat', label: 'Chat com IA', description: 'Assistente com memória contextual' },
  { id: 'automations', label: 'Automações', description: 'Fluxos, gatilhos e execuções' },
  { id: 'templates', label: 'Modelos', description: 'Biblioteca reutilizável da equipe' },
  { id: 'connected-accounts', label: 'Contas Conectadas', description: 'Canais e integrações sociais' },
  { id: 'workspace', label: 'Ambiente de Trabalho', description: 'Empresas, clientes e projetos' },
  { id: 'brain', label: 'Memória da Marca', description: 'Memória estratégica persistente' },
  { id: 'strategy', label: 'Estratégia', description: 'Campanhas e planos de comunicação' },
  { id: 'studio', label: 'Estúdio', description: 'Produção multimídia integrada' },
  { id: 'library', label: 'Biblioteca', description: 'Ativos, versões e materiais' },
];

const masterOnlyTabs = new Set<NavigationTab>(['approvals', 'connected-accounts', 'publisher', 'team', 'subscription', 'audit-logs', 'settings']);

const tabModules: Partial<Record<NavigationTab, WorkspaceModule>> = {
  dashboard: 'dashboard',
  'create-image': 'create-image',
  'create-video': 'create-video',
  'create-copy': 'create-copy',
  calendar: 'calendar',
  analytics: 'analytics',
  'ai-chat': 'ai-chat',
  automations: 'automations',
  templates: 'templates',
  'connected-accounts': 'connected-accounts',
  workspace: 'workspace', brain: 'brain', strategy: 'strategy', studio: 'studio', library: 'library',
};

export function canAccessNavigation(user: Pick<WorkspaceMember, 'role' | 'modules'> | undefined, tab: NavigationTab) {
  if (!user) return false;
  if (user.role === 'master') return true;
  if (masterOnlyTabs.has(tab)) return false;
  const requiredModule = tabModules[tab];
  return requiredModule ? user.modules.includes(requiredModule) : false;
}

export function roleLabel(role: UserRole) { return role === 'master' ? 'Administrador' : 'Colaborador'; }
export function isCriticalTab(tab: NavigationTab) { return masterOnlyTabs.has(tab); }
