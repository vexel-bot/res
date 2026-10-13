import React from 'react';
import type {
  AuditLogEntry,
  ContentApprovalItem,
  GovernanceSession,
  GovernanceWorkspace,
  OrganizationLicense,
  NavigationTab,
  OfferEventPayload,
  AccessScope,
  OrganizationPermission,
  SaaSPlan,
  UserAccount,
  WorkspaceMember,
  WorkspaceModule,
  WorkspaceSubscription,
  UsagePool,
  UserRole,
} from '../types';
import { canAccessNavigation, hasPermission, isPrivilegedRole } from '../security/accessControl';
import { createRequestGuard } from '../utils/requestGuard';
import { useAuth } from './AuthContext';

export type EnvironmentMode = 'company' | 'personal';

type Feedback = { type: 'success' | 'error'; message: string } | null;

type GovernanceContextValue = {
  environmentMode: EnvironmentMode;
  setEnvironmentMode: (mode: EnvironmentMode) => void;
  accounts: UserAccount[];
  activeAccountId: string;
  activeAccount: UserAccount;
  switchAccount: (accountId: string) => void;
  addAccount: (account: Omit<UserAccount, 'id' | 'workspaceId' | 'userId'>) => Promise<string | null>;
  removeAccount: (accountId: string) => void;
  loading: boolean;
  feedback: Feedback;
  currentUser?: WorkspaceMember;
  workspace?: GovernanceWorkspace;
  users: WorkspaceMember[];
  plans: SaaSPlan[];
  subscription?: WorkspaceSubscription;
  licenses: OrganizationLicense[];
  usage?: UsagePool;
  approvals: ContentApprovalItem[];
  auditLogs: AuditLogEntry[];
  isMaster: boolean;
  canAccess: (tab: NavigationTab) => boolean;
  clearFeedback: () => void;
  inviteUser: (payload: { name: string; email: string; modules: WorkspaceModule[]; role?: UserRole; permissions?: OrganizationPermission[]; scope?: AccessScope; reserveSeat?: boolean }) => Promise<boolean>;
  updateUser: (userId: string, payload: { name?: string; status?: 'active' | 'disabled'; modules?: WorkspaceModule[]; role?: UserRole; permissions?: OrganizationPermission[]; scope?: AccessScope }) => Promise<boolean>;
  deleteUser: (userId: string) => Promise<boolean>;
  resendInvite: (userId: string) => Promise<boolean>;
  changePlan: (planId: SaaSPlan['id'], billingCycle?: NonNullable<WorkspaceSubscription['billingCycle']>) => Promise<boolean>;
  recordOfferEvent: (payload: OfferEventPayload) => Promise<void>;
  createApproval: (payload: Pick<ContentApprovalItem, 'contentId' | 'title' | 'copy' | 'platform' | 'format' | 'scheduledAt' | 'campaignId' | 'strategyId'>) => Promise<ContentApprovalItem | null>;
  approvalAction: (approvalId: string, action: 'approve' | 'request_changes' | 'reject' | 'publish' | 'schedule' | 'reschedule' | 'comment', comment?: string, scheduledAt?: string) => Promise<ContentApprovalItem | null>;
  refresh: () => Promise<void>;
};

const GovernanceContext = React.createContext<GovernanceContextValue | null>(null);

const ANONYMOUS_ACCOUNT: UserAccount = { id: 'anonymous', workspaceId: 'anonymous', userId: 'anonymous', name: 'Clicko', type: 'personal' };
const navigationCapability: Partial<Record<NavigationTab, keyof NonNullable<UserAccount['capabilities']>>> = {
  dashboard: 'dashboard', 'create-image': 'image_generation', 'create-video': 'video_generation', 'create-copy': 'copy_creation', 'ai-chat': 'klic',
  'connected-accounts': 'connected_accounts', workspace: 'clients', strategy: 'radar', library: 'library', calendar: 'calendar', analytics: 'analytics', automations: 'automations', approvals: 'approvals', team: 'team',
};

async function request<T>(path: string, account: UserAccount, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/governance${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'x-workspace-id': account.workspaceId,
      'x-user-id': account.userId,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: 'Não foi possível concluir a operação.' }));
    throw new Error(body.error || 'Não foi possível concluir a operação.');
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const GovernanceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const auth = useAuth();
  const accounts = auth.accounts;
  const activeAccountId = auth.account?.id || '';
  const activeAccount = auth.account || ANONYMOUS_ACCOUNT;

  const [loading, setLoading] = React.useState(true);
  const [feedback, setFeedback] = React.useState<Feedback>(null);
  const [session, setSession] = React.useState<GovernanceSession>();
  const [workspace, setWorkspace] = React.useState<GovernanceWorkspace>();
  const [users, setUsers] = React.useState<WorkspaceMember[]>([]);
  const [plans, setPlans] = React.useState<SaaSPlan[]>([]);
  const [subscription, setSubscription] = React.useState<WorkspaceSubscription>();
  const [licenses, setLicenses] = React.useState<OrganizationLicense[]>([]);
  const [usage, setUsage] = React.useState<UsagePool>();
  const [approvals, setApprovals] = React.useState<ContentApprovalItem[]>([]);
  const [auditLogs, setAuditLogs] = React.useState<AuditLogEntry[]>([]);

  const accountRef = React.useRef(activeAccount.id);
  accountRef.current = activeAccount.id;
  const refreshGuard = React.useRef(createRequestGuard());
  React.useEffect(() => () => refreshGuard.current.invalidate(), []);

  const setEnvironmentMode = React.useCallback((mode: EnvironmentMode) => {
    window.localStorage.setItem('clicko-studio:environment', mode);
    window.dispatchEvent(new CustomEvent('clicko:environment-change', { detail: { mode } }));
  }, []);

  React.useEffect(() => { setEnvironmentMode(activeAccount.type); }, [activeAccount.type, setEnvironmentMode]);

  const switchAccount = React.useCallback((accountId: string) => {
    const target = accounts.find((a) => a.id === accountId);
    if (!target) return;
    void auth.switchAccount(target.workspaceId).then(() => setEnvironmentMode(target.type)).catch(error => setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Não foi possível trocar de perfil.' }));
  }, [accounts, auth, setEnvironmentMode]);

  const addAccount = React.useCallback(async (newAccData: Omit<UserAccount, 'id' | 'workspaceId' | 'userId'>) => {
    const id = `acc-${newAccData.type}-${Date.now()}`;
    const workspaceId = `ws-${newAccData.type}-${Date.now()}`;
    const userId = `usr-master-${workspaceId}`;
    const newAcc: UserAccount = {
      id,
      workspaceId,
      userId,
      ...newAccData,
      createdAt: new Date().toISOString(),
    };
    try {
      const response = await fetch('/api/governance/workspaces/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspaceId, userId, name: newAcc.name, type: newAcc.type, email: newAcc.email, planName: newAcc.planName }),
      });
      if (!response.ok) throw new Error('Não foi possível criar o ambiente isolado.');
    } catch (error) {
      setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Não foi possível criar o ambiente.' });
      return null;
    }
    await auth.refresh();
    setEnvironmentMode(newAcc.type);
    return id;
  }, [auth, setEnvironmentMode]);

  const removeAccount = React.useCallback((accountId: string) => {
    const target = accounts.find(item => item.id === accountId);
    if (!target) return;
    void auth.removeAccount(target.workspaceId).catch(error => setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Não foi possível remover o perfil.' }));
  }, [accounts, auth]);

  const refresh = React.useCallback(async () => {
    if (!auth.authenticated || !auth.account) {
      refreshGuard.current.invalidate();
      setSession(undefined); setWorkspace(undefined); setUsers([]); setPlans([]); setSubscription(undefined); setLicenses([]); setUsage(undefined); setApprovals([]); setAuditLogs([]);
      setLoading(auth.loading);
      return;
    }
    const isCurrent = refreshGuard.current.begin(activeAccount.id, () => accountRef.current);
    setLoading(true);
    setSession(undefined);
    setWorkspace(undefined);
    setUsers([]); setPlans([]); setSubscription(undefined); setLicenses([]); setUsage(undefined); setApprovals([]); setAuditLogs([]);
    try {
      const nextSession = await request<GovernanceSession>('/session', activeAccount);
      const nextWorkspace = await request<GovernanceWorkspace>('/workspace', activeAccount);
      const nextPlans = hasPermission(nextSession.currentUser, 'subscription.read') ? await request<SaaSPlan[]>('/plans', activeAccount) : [];
      const nextSubscription = hasPermission(nextSession.currentUser, 'subscription.read') ? await request<WorkspaceSubscription>('/subscription', activeAccount) : undefined;
      if (!activeAccount.subscriptionAccessAllowed) {
        if (!isCurrent()) return;
        setPlans(nextPlans); setSubscription(nextSubscription); setSession(nextSession); setWorkspace(nextWorkspace);
        return;
      }
      const [nextUsers, nextLicenses, nextUsage, nextApprovals, nextAuditLogs] = await Promise.all([
        activeAccount.type === 'company' && hasPermission(nextSession.currentUser, 'members.read') ? request<WorkspaceMember[]>('/users', activeAccount) : Promise.resolve([nextSession.currentUser]),
        activeAccount.type === 'company' && hasPermission(nextSession.currentUser, 'licenses.read') ? request<OrganizationLicense[]>('/licenses', activeAccount) : Promise.resolve([]),
        hasPermission(nextSession.currentUser, 'usage.read.own') ? request<UsagePool>('/usage', activeAccount) : Promise.resolve(undefined),
        activeAccount.type === 'company' && hasPermission(nextSession.currentUser, 'content.approve') ? request<ContentApprovalItem[]>('/approvals', activeAccount) : Promise.resolve([]),
        hasPermission(nextSession.currentUser, 'audit.read') ? request<AuditLogEntry[]>('/audit-logs', activeAccount) : Promise.resolve([]),
      ]);
      if (!isCurrent()) return;
      setUsers(nextUsers);
      setPlans(nextPlans);
      setSubscription(nextSubscription);
      setLicenses(nextLicenses);
      setUsage(nextUsage);
      setApprovals(nextApprovals);
      setAuditLogs(nextAuditLogs);
      setSession(nextSession);
      setWorkspace(nextWorkspace);
    } catch (error) {
      if (isCurrent()) setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Falha ao carregar a governança.' });
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, [activeAccount, auth.account, auth.authenticated, auth.loading]);

  React.useEffect(() => { void refresh(); }, [refresh]);

  const run = async <T,>(operation: () => Promise<T>, message: string, onSuccess?: (value: T) => void) => {
    const accountId = activeAccount.id;
    try {
      const value = await operation();
      if (accountId !== accountRef.current) return null;
      onSuccess?.(value);
      setFeedback({ type: 'success', message });
      return value;
    } catch (error) {
      if (accountId !== accountRef.current) return null;
      setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Não foi possível concluir a ação.' });
      return null;
    }
  };

  const inviteUser: GovernanceContextValue['inviteUser'] = async (payload) => Boolean(await run(
    () => request<WorkspaceMember>('/invites', activeAccount, { method: 'POST', body: JSON.stringify(payload) }),
    'Convite registrado. O envio de e-mail ainda depende da integração de entrega.',
    (member) => setUsers((current) => [...current, member]),
  ));

  const updateUser: GovernanceContextValue['updateUser'] = async (userId, payload) => Boolean(await run(
    () => request<WorkspaceMember>(`/users/${userId}`, activeAccount, { method: 'PATCH', body: JSON.stringify(payload) }),
    'Usuário atualizado.',
    (member) => setUsers((current) => current.map((item) => item.id === member.id ? member : item)),
  ));

  const deleteUser: GovernanceContextValue['deleteUser'] = async (userId) => {
    const result = await run(() => request<void>(`/users/${userId}`, activeAccount, { method: 'DELETE' }), 'Usuário removido.', () => setUsers((current) => current.filter((item) => item.id !== userId)));
    return result !== null;
  };

  const resendInvite: GovernanceContextValue['resendInvite'] = async (userId) => Boolean(await run(
    () => request<WorkspaceMember>(`/users/${userId}/resend-invite`, activeAccount, { method: 'POST' }),
    'Prazo do convite renovado. O envio de e-mail ainda depende da integração de entrega.',
    (member) => setUsers((current) => current.map((item) => item.id === member.id ? member : item)),
  ));

  const changePlan: GovernanceContextValue['changePlan'] = async (planId, billingCycle = 'monthly') => Boolean(await run(
    () => request<{ checkoutUrl: string }>('/billing/checkout', activeAccount, { method: 'POST', body: JSON.stringify({ planId, billingCycle }) }),
    'Checkout seguro iniciado.',
    (result) => window.location.assign(result.checkoutUrl),
  ));

  const recordOfferEvent: GovernanceContextValue['recordOfferEvent'] = async (payload) => {
    try {
      await request<void>('/offers/events', activeAccount, { method: 'POST', body: JSON.stringify(payload) });
    } catch {
      const key = 'clicko:offer-events:pending';
      try {
        const pending = JSON.parse(window.localStorage.getItem(key) || '[]');
        window.localStorage.setItem(key, JSON.stringify([...pending, payload].slice(-50)));
      } catch {
        // Tracking must never interrupt the subscription flow.
      }
    }
  };

  const approvalAction: GovernanceContextValue['approvalAction'] = async (approvalId, action, comment, scheduledAt) => run(
    () => request<ContentApprovalItem>(`/approvals/${approvalId}/actions`, activeAccount, { method: 'POST', body: JSON.stringify({ action, comment, scheduledAt }) }),
    action === 'comment' ? 'Comentário adicionado.' : 'Fluxo de aprovação atualizado.',
    (approval) => setApprovals((current) => current.map((item) => item.id === approval.id ? approval : item)),
  );

  const createApproval: GovernanceContextValue['createApproval'] = async (payload) => run(
    () => request<ContentApprovalItem>('/approvals', activeAccount, { method: 'POST', body: JSON.stringify(payload) }),
    'Conteúdo enviado para aprovação.',
    (approval) => setApprovals((current) => [approval, ...current.filter((item) => item.id !== approval.id)]),
  );

  const currentUser = session?.currentUser.workspaceId === activeAccount.workspaceId && session.currentUser.id === activeAccount.userId ? session.currentUser : undefined;
  const value: GovernanceContextValue = {
    environmentMode: activeAccount.type,
    setEnvironmentMode,
    accounts,
    activeAccountId,
    activeAccount,
    switchAccount,
    addAccount,
    removeAccount,
    loading,
    feedback,
    currentUser,
    workspace: workspace?.id === activeAccount.workspaceId ? workspace : undefined,
    users: users.filter(item => item.workspaceId === activeAccount.workspaceId),
    plans,
    subscription: subscription?.workspaceId === activeAccount.workspaceId ? subscription : undefined,
    licenses: licenses.filter(item => item.workspaceId === activeAccount.workspaceId),
    usage: usage?.workspaceId === activeAccount.workspaceId ? usage : undefined,
    approvals: approvals.filter(item => item.workspaceId === activeAccount.workspaceId),
    auditLogs: auditLogs.filter(item => item.workspaceId === activeAccount.workspaceId),
    isMaster: isPrivilegedRole(currentUser?.role),
    canAccess: (tab) => canAccessNavigation(currentUser, tab, activeAccount.type) && (navigationCapability[tab] ? activeAccount.capabilities?.[navigationCapability[tab]!] === true : true),
    clearFeedback: () => setFeedback(null),
    inviteUser,
    updateUser,
    deleteUser,
    resendInvite,
    changePlan,
    recordOfferEvent,
    createApproval,
    approvalAction,
    refresh,
  };

  return <GovernanceContext.Provider value={value}>{children}</GovernanceContext.Provider>;
};

export function useGovernance() {
  const context = React.useContext(GovernanceContext);
  if (!context) throw new Error('useGovernance precisa estar dentro de GovernanceProvider.');
  return context;
}
