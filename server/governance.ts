import { Router, type NextFunction, type Request, type Response } from 'express';
import type {
  AuditLogEntry,
  ContentApprovalItem,
  GovernanceWorkspace,
  OfferEventPayload,
  SaaSPlan,
  WorkspaceMember,
  WorkspaceModule,
  WorkspaceSubscription,
} from '../src/types';

type AuthContext = { workspaceId: string; user: WorkspaceMember };
type AuthenticatedRequest = Request & { auth?: AuthContext };

const moduleIds: WorkspaceModule[] = [
  'dashboard', 'create-image', 'create-video', 'create-copy', 'ai-chat',
  'templates', 'connected-accounts', 'workspace', 'brain', 'strategy',
  'studio', 'library', 'calendar', 'automations', 'analytics',
];

const plans: SaaSPlan[] = [
  { id: 'solo', name: 'Solo', maxUsers: 1, monthlyPrice: 79, description: 'Para operações individuais.', features: ['1 usuário administrador', 'Criação com IA', 'Calendário editorial'] },
  { id: 'team', name: 'Equipe', maxUsers: 6, monthlyPrice: 249, description: 'Para equipes enxutas e colaborativas.', features: ['1 administrador + 5 colaboradores', 'Fluxo de aprovação', 'Automações'] },
  { id: 'business', name: 'Negócios', maxUsers: 16, monthlyPrice: 599, description: 'Para operações de conteúdo em escala.', features: ['1 administrador + 15 colaboradores', 'Análises avançadas', 'Auditoria completa'] },
  { id: 'enterprise', name: 'Corporativo', maxUsers: null, monthlyPrice: null, description: 'Capacidade, suporte e governança personalizados.', features: ['Usuários personalizados', 'SLA dedicado', 'Governança avançada'] },
];

const workspaces: GovernanceWorkspace[] = [{
  id: 'ws-1',
  name: 'Clicko Studio',
  logo: '/clicko-ai-studios-logo-stacked.png',
  planId: 'team',
  maxUsers: 6,
  activeUsers: 3,
  subscriptionDate: '2026-05-18T12:00:00.000Z',
  subscriptionStatus: 'active',
  settings: { inviteExpiryDays: 7, requireApproval: true, timezone: 'America/Sao_Paulo' },
}, {
  id: 'ws-personal',
  name: 'Pedro Henrique — Plano Pessoal',
  logo: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=120&q=80',
  planId: 'solo',
  maxUsers: 1,
  activeUsers: 1,
  subscriptionDate: '2026-06-01T12:00:00.000Z',
  subscriptionStatus: 'active',
  settings: { inviteExpiryDays: 7, requireApproval: false, timezone: 'America/Sao_Paulo' },
}];

const users: WorkspaceMember[] = [
  { id: 'usr-master', workspaceId: 'ws-1', name: 'Pedro Henrique', email: 'pedro@clickostudio.com', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=120&q=80', role: 'master', status: 'active', modules: [...moduleIds], lastAccess: new Date().toISOString(), createdAt: '2026-05-18T12:00:00.000Z' },
  { id: 'usr-lucas', workspaceId: 'ws-1', name: 'Lucas Silva', email: 'lucas@clickostudio.com', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=120&q=80', role: 'collaborator', status: 'active', modules: ['dashboard', 'create-image', 'create-video', 'create-copy', 'ai-chat', 'templates', 'workspace', 'brain', 'strategy', 'studio', 'library', 'calendar'], lastAccess: '2026-08-02T14:42:00.000Z', createdAt: '2026-06-03T13:00:00.000Z' },
  { id: 'usr-ana', workspaceId: 'ws-1', name: 'Ana Martins', email: 'ana@clickostudio.com', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80', role: 'collaborator', status: 'active', modules: ['dashboard', 'create-image', 'create-copy', 'ai-chat', 'templates', 'workspace', 'studio', 'library', 'calendar', 'analytics'], lastAccess: '2026-08-02T12:18:00.000Z', createdAt: '2026-06-21T16:30:00.000Z' },
  { id: 'usr-caio', workspaceId: 'ws-1', name: 'Caio Rocha', email: 'caio@clickostudio.com', avatar: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=120&q=80', role: 'collaborator', status: 'disabled', modules: ['dashboard', 'create-copy', 'ai-chat', 'studio'], lastAccess: '2026-07-28T19:05:00.000Z', createdAt: '2026-07-02T10:10:00.000Z' },
  { id: 'usr-invite', workspaceId: 'ws-1', name: 'Marina Costa', email: 'marina@clickostudio.com', avatar: '', role: 'collaborator', status: 'invited', modules: ['dashboard', 'create-image', 'create-copy', 'ai-chat', 'templates', 'studio', 'library', 'calendar'], lastAccess: 'Convite pendente', createdAt: '2026-08-01T09:00:00.000Z', invitedAt: '2026-08-01T09:00:00.000Z', inviteExpiresAt: '2026-08-08T09:00:00.000Z' },
  { id: 'usr-master-personal', workspaceId: 'ws-personal', name: 'Pedro Henrique (Pessoal)', email: 'pedro.henrique@gmail.com', avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=120&q=80', role: 'master', status: 'active', modules: [...moduleIds], lastAccess: new Date().toISOString(), createdAt: '2026-06-01T12:00:00.000Z' },
];

const subscriptions: WorkspaceSubscription[] = [{
  id: 'sub-1', workspaceId: 'ws-1', planId: 'team', status: 'active',
  startedAt: '2026-05-18T12:00:00.000Z', renewsAt: '2026-08-18T12:00:00.000Z',
  billingEmail: 'financeiro@clickostudio.com', paymentMethod: 'Visa final 4821',
}, {
  id: 'sub-personal', workspaceId: 'ws-personal', planId: 'solo', status: 'active',
  startedAt: '2026-06-01T12:00:00.000Z', renewsAt: '2026-09-01T12:00:00.000Z',
  billingEmail: 'pedro.henrique@gmail.com', paymentMethod: 'Mastercard final 9012',
}];

const approvals: ContentApprovalItem[] = [{
  id: 'approval-103', workspaceId: 'ws-1', contentId: 'post-103',
  title: 'O erro que quebra a retenção nos primeiros 3 segundos',
  copy: 'Pare de postar vídeos sem essa legenda dinâmica! Veja os três ajustes que aumentaram nossa retenção em 42%.',
  previewUrl: 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=900&q=80',
  platform: 'tiktok', format: 'reels', authorId: 'usr-lucas', authorName: 'Lucas Silva',
  createdAt: '2026-08-02T11:00:00.000Z', scheduledAt: '2026-08-03T22:00:00.000Z', stage: 'pending_approval',
  campaignId: 'strategy-q3', strategyId: 'strategy-q3',
  versions: [
    { id: 'version-103-1', number: 1, label: 'Roteiro inicial', author: 'Lucas Silva', createdAt: '2026-08-02T11:00:00.000Z' },
    { id: 'version-103-2', number: 2, label: 'Gancho revisado', author: 'Lucas Silva', createdAt: '2026-08-02T11:38:00.000Z' },
  ],
  comments: [{ id: 'comment-1', authorId: 'usr-master', authorName: 'Pedro Henrique', message: 'O gancho pode ficar mais direto sem perder o tom da marca?', createdAt: '2026-08-02T12:15:00.000Z' }],
  history: [
    { id: 'history-1', actorId: 'usr-lucas', actorName: 'Lucas Silva', action: 'created', detail: 'Conteúdo criado como rascunho', createdAt: '2026-08-02T11:00:00.000Z' },
    { id: 'history-2', actorId: 'usr-lucas', actorName: 'Lucas Silva', action: 'submitted', detail: 'Enviado para aprovação do administrador', createdAt: '2026-08-02T11:42:00.000Z' },
  ],
}, {
  id: 'approval-105', workspaceId: 'ws-1', contentId: 'post-105', title: 'Checklist de campanha para lançamentos B2B',
  copy: 'Um checklist prático para alinhar estratégia, criação, mídia e mensuração antes de colocar a campanha no ar.',
  previewUrl: 'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=900&q=80',
  platform: 'linkedin', format: 'carousel', authorId: 'usr-ana', authorName: 'Ana Martins', createdAt: '2026-08-01T15:20:00.000Z', stage: 'in_review',
  campaignId: 'strategy-q3', strategyId: 'strategy-q3',
  versions: [{ id: 'version-105-1', number: 1, label: 'Versão inicial', author: 'Ana Martins', createdAt: '2026-08-01T15:20:00.000Z' }],
  comments: [], history: [{ id: 'history-3', actorId: 'usr-ana', actorName: 'Ana Martins', action: 'created', detail: 'Conteúdo enviado para revisão interna', createdAt: '2026-08-01T15:20:00.000Z' }],
}];

const auditLogs: AuditLogEntry[] = [
  { id: 'audit-1', workspaceId: 'ws-1', actorId: 'usr-master', actorName: 'Pedro Henrique', action: 'subscription.viewed', resource: 'subscription:sub-1', detail: 'Assinatura Equipe consultada', createdAt: '2026-08-02T13:10:00.000Z' },
  { id: 'audit-2', workspaceId: 'ws-1', actorId: 'usr-lucas', actorName: 'Lucas Silva', action: 'content.submitted', resource: 'content:post-103', detail: 'Conteúdo enviado para aprovação', createdAt: '2026-08-02T11:42:00.000Z' },
];

const inviteTokens = new Map<string, string>([['invite-marina-demo', 'usr-invite']]);

const nowIso = () => new Date().toISOString();
const id = (prefix: string) => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

function refreshWorkspaceSeats(workspaceId: string) {
  const workspace = workspaces.find((item) => item.id === workspaceId);
  if (workspace) workspace.activeUsers = users.filter((user) => user.workspaceId === workspaceId && user.status === 'active').length;
}

function addAudit(auth: AuthContext, action: string, resource: string, detail: string) {
  auditLogs.unshift({ id: id('audit'), workspaceId: auth.workspaceId, actorId: auth.user.id, actorName: auth.user.name, action, resource, detail, createdAt: nowIso() });
}

function authenticate(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  const workspaceId = String(req.header('x-workspace-id') || 'ws-1');
  const userId = String(req.header('x-user-id') || 'usr-master');
  const user = users.find((item) => item.id === userId && item.workspaceId === workspaceId);
  if (!user || user.status !== 'active') return res.status(401).json({ error: 'Sessão inválida ou usuário inativo.' });
  if (!workspaces.some((item) => item.id === workspaceId)) return res.status(404).json({ error: 'Ambiente de trabalho não encontrado.' });
  req.auth = { workspaceId, user };
  next();
}

function masterOnly(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  if (req.auth?.user.role !== 'master') return res.status(403).json({ error: 'Apenas o usuário administrador pode realizar esta ação.' });
  next();
}

function moduleOnly(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  const requestedModule = String(req.params.moduleId || '') as WorkspaceModule;
  if (!moduleIds.includes(requestedModule)) return res.status(404).json({ error: 'Módulo desconhecido.' });
  const user = req.auth!.user;
  if (user.role !== 'master' && !user.modules.includes(requestedModule)) return res.status(403).json({ error: 'Este módulo não foi liberado pelo administrador.' });
  next();
}

function validModules(value: unknown): WorkspaceModule[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is WorkspaceModule => moduleIds.includes(item as WorkspaceModule));
}

export function createGovernanceRouter() {
  const router = Router();

  router.post('/invites/accept', (req, res) => {
    const token = String(req.body?.token || '');
    const password = String(req.body?.password || '');
    const userId = inviteTokens.get(token);
    const member = users.find((item) => item.id === userId && item.status === 'invited');
    if (!member) return res.status(404).json({ error: 'Convite inválido ou já utilizado.' });
    if (member.inviteExpiresAt && new Date(member.inviteExpiresAt).getTime() < Date.now()) return res.status(410).json({ error: 'Este convite expirou. Solicite um novo convite ao administrador.' });
    if (password.length < 8) return res.status(400).json({ error: 'A senha deve possuir ao menos 8 caracteres.' });
    member.status = 'active';
    member.lastAccess = nowIso();
    inviteTokens.delete(token);
    refreshWorkspaceSeats(member.workspaceId);
    auditLogs.unshift({ id: id('audit'), workspaceId: member.workspaceId, actorId: member.id, actorName: member.name, action: 'invite.accepted', resource: 'user:' + member.id, detail: 'Convite aceito e acesso ao ambiente de trabalho ativado', createdAt: nowIso() });
    res.json({ user: member, workspace: workspaces.find((item) => item.id === member.workspaceId) });
  });

  router.use(authenticate);

  router.get('/session', (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    res.json({ currentUser: auth.user, workspace: workspaces.find((item) => item.id === auth.workspaceId) });
  });

  router.get('/workspace', (req: AuthenticatedRequest, res) => res.json(workspaces.find((item) => item.id === req.auth!.workspaceId)));
  router.get('/plans', masterOnly, (_req, res) => res.json(plans));
  router.get('/access/modules/:moduleId', moduleOnly, (req: AuthenticatedRequest, res) => res.json({ allowed: true, moduleId: req.params.moduleId, workspaceId: req.auth!.workspaceId }));

  router.get('/users', masterOnly, (req: AuthenticatedRequest, res) => {
    res.json(users.filter((item) => item.workspaceId === req.auth!.workspaceId));
  });

  router.post('/invites', masterOnly, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const workspace = workspaces.find((item) => item.id === auth.workspaceId)!;
    const occupiedSeats = users.filter((item) => item.workspaceId === auth.workspaceId && item.status !== 'disabled').length;
    if (workspace.maxUsers !== null && occupiedSeats >= workspace.maxUsers) {
      addAudit(auth, 'invite.blocked', 'workspace:' + workspace.id, 'Convite bloqueado por limite do plano');
      return res.status(409).json({ error: 'Você atingiu o limite de usuários do seu plano. Mude para um plano superior para adicionar novos colaboradores.' });
    }
    const email = String(req.body?.email || '').trim().toLowerCase();
    const name = String(req.body?.name || '').trim();
    if (!email || !name) return res.status(400).json({ error: 'Nome e e-mail são obrigatórios.' });
    if (users.some((item) => item.workspaceId === auth.workspaceId && item.email.toLowerCase() === email)) return res.status(409).json({ error: 'Já existe um usuário ou convite com este e-mail.' });
    const invitedAt = nowIso();
    const inviteExpiresAt = new Date(Date.now() + workspace.settings.inviteExpiryDays * 86_400_000).toISOString();
    const member: WorkspaceMember = { id: id('usr'), workspaceId: auth.workspaceId, name, email, avatar: '', role: 'collaborator', status: 'invited', modules: validModules(req.body?.modules), lastAccess: 'Convite pendente', createdAt: invitedAt, invitedAt, inviteExpiresAt };
    users.push(member);
    inviteTokens.set(id('invite'), member.id);
    addAudit(auth, 'invite.created', 'user:' + member.id, `Convite enviado para ${email}`);
    res.status(201).json(member);
  });

  router.patch('/users/:userId', masterOnly, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const member = users.find((item) => item.id === req.params.userId && item.workspaceId === auth.workspaceId);
    if (!member) return res.status(404).json({ error: 'Usuário não encontrado neste ambiente de trabalho.' });
    if (member.role === 'master') return res.status(400).json({ error: 'O usuário administrador não pode ser alterado por esta ação.' });
    if (typeof req.body?.name === 'string' && req.body.name.trim()) member.name = req.body.name.trim();
    if (req.body?.status === 'active' || req.body?.status === 'disabled') member.status = req.body.status;
    if (req.body?.modules) member.modules = validModules(req.body.modules);
    refreshWorkspaceSeats(auth.workspaceId);
    addAudit(auth, 'user.updated', 'user:' + member.id, `Permissões ou status de ${member.name} atualizados`);
    res.json(member);
  });

  router.post('/users/:userId/resend-invite', masterOnly, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const member = users.find((item) => item.id === req.params.userId && item.workspaceId === auth.workspaceId && item.status === 'invited');
    if (!member) return res.status(404).json({ error: 'Convite pendente não encontrado.' });
    const days = workspaces.find((item) => item.id === auth.workspaceId)!.settings.inviteExpiryDays;
    member.invitedAt = nowIso();
    member.inviteExpiresAt = new Date(Date.now() + days * 86_400_000).toISOString();
    addAudit(auth, 'invite.resent', 'user:' + member.id, `Convite reenviado para ${member.email}`);
    res.json(member);
  });

  router.delete('/users/:userId', masterOnly, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const index = users.findIndex((item) => item.id === req.params.userId && item.workspaceId === auth.workspaceId);
    if (index < 0) return res.status(404).json({ error: 'Usuário não encontrado neste ambiente de trabalho.' });
    if (users[index].role === 'master') return res.status(400).json({ error: 'O usuário administrador não pode ser removido.' });
    const [removed] = users.splice(index, 1);
    refreshWorkspaceSeats(auth.workspaceId);
    addAudit(auth, 'user.removed', 'user:' + removed.id, `${removed.name} removido do ambiente de trabalho`);
    res.status(204).end();
  });

  router.post('/offers/events', (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const allowedEvents: OfferEventPayload['event'][] = [
      'OFFER_VIEWED', 'OFFER_CLICKED', 'UPGRADE_STARTED',
      'CHECKOUT_STARTED', 'CHECKOUT_COMPLETED', 'OFFER_DISMISSED',
    ];
    const event = String(req.body?.event || '') as OfferEventPayload['event'];
    if (!allowedEvents.includes(event)) return res.status(400).json({ error: 'Evento de oferta inválido.' });
    const offerId = String(req.body?.offerId || '').slice(0, 120);
    const context = String(req.body?.context || '').slice(0, 80);
    const targetPlanId = String(req.body?.targetPlanId || '').slice(0, 40);
    addAudit(auth, `offer.${event.toLowerCase()}`, `offer:${offerId || 'contextual'}`, `${context}${targetPlanId ? ` · plano ${targetPlanId}` : ''}`);
    res.status(204).end();
  });

  router.get('/subscription', masterOnly, (req: AuthenticatedRequest, res) => res.json(subscriptions.find((item) => item.workspaceId === req.auth!.workspaceId)));
  router.patch('/subscription', masterOnly, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const plan = plans.find((item) => item.id === req.body?.planId);
    if (!plan) return res.status(400).json({ error: 'Plano inválido.' });
    const occupiedSeats = users.filter((item) => item.workspaceId === auth.workspaceId && item.status !== 'disabled').length;
    if (plan.maxUsers !== null && occupiedSeats > plan.maxUsers) return res.status(409).json({ error: `O plano ${plan.name} permite ${plan.maxUsers} usuário(s), mas o ambiente possui ${occupiedSeats} assentos ocupados.` });
    const subscription = subscriptions.find((item) => item.workspaceId === auth.workspaceId)!;
    const workspace = workspaces.find((item) => item.id === auth.workspaceId)!;
    subscription.planId = plan.id;
    workspace.planId = plan.id;
    workspace.maxUsers = plan.maxUsers;
    addAudit(auth, 'subscription.plan_changed', 'subscription:' + subscription.id, `Plano alterado para ${plan.name}`);
    res.json({ subscription, workspace });
  });

  router.get('/approvals', masterOnly, (req: AuthenticatedRequest, res) => res.json(approvals.filter((item) => item.workspaceId === req.auth!.workspaceId)));
  router.post('/approvals/:approvalId/actions', masterOnly, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const approval = approvals.find((item) => item.id === req.params.approvalId && item.workspaceId === auth.workspaceId);
    if (!approval) return res.status(404).json({ error: 'Conteúdo não encontrado nesta fila.' });
    const action = String(req.body?.action || '');
    const comment = String(req.body?.comment || '').trim();
    const allowed = ['approve', 'request_changes', 'reject', 'publish', 'schedule', 'comment'];
    if (!allowed.includes(action)) return res.status(400).json({ error: 'Ação de aprovação inválida.' });
    if ((action === 'publish' || action === 'schedule') && approval.stage !== 'approved') {
      addAudit(auth, 'publication.blocked', 'content:' + approval.contentId, 'Publicação bloqueada: conteúdo sem aprovação');
      return res.status(409).json({ error: 'Este conteúdo precisa ser aprovado pelo administrador antes da publicação.' });
    }
    if (comment) approval.comments.push({ id: id('comment'), authorId: auth.user.id, authorName: auth.user.name, message: comment, createdAt: nowIso() });
    const actionMap: Record<string, { stage?: ContentApprovalItem['stage']; detail: string }> = {
      approve: { stage: 'approved', detail: 'Conteúdo aprovado pelo administrador' },
      request_changes: { stage: 'changes_requested', detail: 'Ajustes solicitados ao colaborador' },
      reject: { stage: 'rejected', detail: 'Conteúdo reprovado pelo administrador' },
      publish: { stage: 'published', detail: 'Conteúdo publicado oficialmente' },
      schedule: { detail: 'Publicação aprovada e agendada' },
      comment: { detail: 'Comentário adicionado à revisão' },
    };
    const transition = actionMap[action];
    if (transition.stage) approval.stage = transition.stage;
    if (action === 'approve') { approval.approvedBy = auth.user.id; approval.approvedAt = nowIso(); }
    if (action === 'publish') { approval.publishedBy = auth.user.id; approval.publishedAt = nowIso(); }
    if (action === 'schedule' && req.body?.scheduledAt) approval.scheduledAt = String(req.body.scheduledAt);
    approval.history.unshift({ id: id('history'), actorId: auth.user.id, actorName: auth.user.name, action, detail: transition.detail, createdAt: nowIso() });
    addAudit(auth, `approval.${action}`, 'content:' + approval.contentId, transition.detail);
    res.json(approval);
  });

  router.post('/approvals/:approvalId/automatic-publish', masterOnly, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const approval = approvals.find((item) => item.id === req.params.approvalId && item.workspaceId === auth.workspaceId);
    if (!approval) return res.status(404).json({ error: 'Conteúdo não encontrado.' });
    if (approval.stage !== 'approved') {
      addAudit(auth, 'automation.publication_blocked', 'content:' + approval.contentId, 'Agendamento cancelado por ausência de aprovação');
      return res.status(409).json({ error: 'Publicação automática cancelada: aprovação do administrador pendente.' });
    }
    approval.stage = 'published';
    approval.publishedBy = auth.user.id;
    approval.publishedAt = nowIso();
    addAudit(auth, 'automation.published', 'content:' + approval.contentId, 'Conteúdo aprovado publicado automaticamente');
    res.json(approval);
  });

  router.get('/audit-logs', masterOnly, (req: AuthenticatedRequest, res) => res.json(auditLogs.filter((item) => item.workspaceId === req.auth!.workspaceId).slice(0, 100)));

  return router;
}
