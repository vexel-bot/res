import type { ApprovalStage, NavigationTab, PostStatus, StrategyStatus } from '../types';

export const navigationLabel: Record<NavigationTab, string> = {
  dashboard: 'Painel',
  'create-image': 'Criar imagem',
  'create-video': 'Criar vídeo',
  'create-copy': 'Criar texto',
  'ai-chat': 'KLIC',
  'connected-accounts': 'Conexões',
  workspace: 'Ambiente de trabalho',
  strategy: 'Estratégia',
  library: 'Biblioteca',
  calendar: 'Calendário',
  analytics: 'Análises',
  automations: 'Automações',
  approvals: 'Aprovações',
  team: 'Equipe',
  subscription: 'Assinatura',
  settings: 'Configurações',
};

export const postStatusLabel: Record<PostStatus, string> = {
  draft: 'Rascunho',
  in_production: 'Em produção',
  in_review: 'Em revisão',
  pending_approval: 'Aguardando aprovação',
  approved: 'Aprovado',
  changes_requested: 'Ajustes solicitados',
  rejected: 'Reprovado',
  scheduled: 'Agendado',
  published: 'Publicado',
  error: 'Erro',
};

export const approvalStageLabel: Record<ApprovalStage, string> = {
  draft: 'Rascunho',
  in_review: 'Em revisão',
  pending_approval: 'Aguardando aprovação',
  approved: 'Aprovado',
  changes_requested: 'Ajustes solicitados',
  rejected: 'Reprovado',
  published: 'Publicado',
};

export const strategyStatusLabel: Record<StrategyStatus, string> = {
  draft: 'Rascunho',
  planned: 'Planejada',
  active: 'Ativa',
  completed: 'Concluída',
};

const auditTerms: Record<string, string> = {
  user: 'usuário',
  content: 'conteúdo',
  subscription: 'assinatura',
  workspace: 'ambiente',
  automation: 'automação',
  invite: 'convite',
  viewed: 'visualizada',
  submitted: 'enviado',
  accepted: 'aceito',
  created: 'criado',
  blocked: 'bloqueado',
  updated: 'atualizado',
  resent: 'reenviado',
  removed: 'removido',
  plan_changed: 'plano alterado',
  published: 'publicado',
};

export function localizeAuditToken(value: string) {
  return value
    .split('.')
    .map((part) => auditTerms[part] || part)
    .join(' · ');
}

export function localizeResource(value: string) {
  const [type, id] = value.split(':');
  return `${auditTerms[type] || type}${id ? `: ${id}` : ''}`;
}
