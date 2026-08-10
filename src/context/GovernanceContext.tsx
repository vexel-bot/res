import React from 'react';
import type {
  AuditLogEntry,
  ContentApprovalItem,
  GovernanceSession,
  GovernanceWorkspace,
  NavigationTab,
  OfferEventPayload,
  SaaSPlan,
  UserAccount,
  WorkspaceMember,
  WorkspaceModule,
  WorkspaceSubscription,
} from '../types';
import { canAccessNavigation } from '../security/accessControl';

export type EnvironmentMode = 'company' | 'personal';

type Feedback = { type: 'success' | 'error'; message: string } | null;

type GovernanceContextValue = {
  environmentMode: EnvironmentMode;
  setEnvironmentMode: (mode: EnvironmentMode) => void;
  accounts: UserAccount[];
  activeAccountId: string;
  activeAccount: UserAccount;
  switchAccount: (accountId: string) => void;
  addAccount: (account: Omit<UserAccount, 'id'>) => string;
  removeAccount: (accountId: string) => void;
  loading: boolean;
  feedback: Feedback;
  currentUser?: WorkspaceMember;
  workspace?: GovernanceWorkspace;
  users: WorkspaceMember[];
  plans: SaaSPlan[];
  subscription?: WorkspaceSubscription;
  approvals: ContentApprovalItem[];
  auditLogs: AuditLogEntry[];
  isMaster: boolean;
  canAccess: (tab: NavigationTab) => boolean;
  clearFeedback: () => void;
  inviteUser: (payload: { name: string; email: string; modules: WorkspaceModule[] }) => Promise<boolean>;
  updateUser: (userId: string, payload: { name?: string; status?: 'active' | 'disabled'; modules?: WorkspaceModule[] }) => Promise<boolean>;
  deleteUser: (userId: string) => Promise<boolean>;
  resendInvite: (userId: string) => Promise<boolean>;
  changePlan: (planId: SaaSPlan['id']) => Promise<boolean>;
  recordOfferEvent: (payload: OfferEventPayload) => Promise<void>;
  approvalAction: (approvalId: string, action: 'approve' | 'request_changes' | 'reject' | 'publish' | 'schedule' | 'comment', comment?: string, scheduledAt?: string) => Promise<ContentApprovalItem | null>;
  refresh: () => Promise<void>;
};

const GovernanceContext = React.createContext<GovernanceContextValue | null>(null);

const DEFAULT_ACCOUNTS: UserAccount[] = [
  {
    id: 'acc-personal-1',
    name: 'Conta Pessoal',
    type: 'personal',
    role: 'Solo Creator',
    planName: 'Plano Solo',
    email: 'pedro.henrique@clickostudio.com',
  },
  {
    id: 'acc-ws-1',
    name: 'Conta Workspace',
    type: 'company',
    role: 'Equipe & Governança',
    planName: 'Plano Enterprise',
    membersCount: 12,
    email: 'equipe@clickostudio.com',
  },
];

function getStoredAccounts(): UserAccount[] {
  try {
    const stored = window.localStorage.getItem('clicko-studio:user-accounts');
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const hasPersonal = parsed.some((a: UserAccount) => a.type === 'personal');
        const hasCompany = parsed.some((a: UserAccount) => a.type === 'company');
        let updated = [...parsed];
        if (!hasPersonal) {
          updated.unshift(DEFAULT_ACCOUNTS[0]);
        }
        if (!hasCompany) {
          updated.push(DEFAULT_ACCOUNTS[1]);
        }
        return updated;
      }
    }
  } catch (e) {
    console.error('Error reading stored accounts', e);
  }
  return DEFAULT_ACCOUNTS;
}

function getStoredEnvironment(): EnvironmentMode {
  const stored = window.localStorage.getItem('clicko-studio:environment');
  return stored === 'personal' ? 'personal' : 'company';
}

function getActiveWorkspaceId(envMode: EnvironmentMode) {
  return envMode === 'personal' ? 'ws-personal' : 'ws-1';
}

function getUserId(envMode: EnvironmentMode) {
  const stored = window.localStorage.getItem('clicko-studio:session-user');
  if (stored) return stored;
  return envMode === 'personal' ? 'usr-master-personal' : 'usr-master';
}

async function request<T>(path: string, envMode: EnvironmentMode, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/governance${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'x-workspace-id': getActiveWorkspaceId(envMode),
      'x-user-id': getUserId(envMode),
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
  const [accounts, setAccounts] = React.useState<UserAccount[]>(getStoredAccounts);
  const [activeAccountId, setActiveAccountId] = React.useState<string>(() => {
    const stored = window.localStorage.getItem('clicko-studio:active-account-id');
    const existing = getStoredAccounts();
    if (stored && existing.some((a) => a.id === stored)) return stored;
    return existing[0]?.id || 'acc-personal-1';
  });

  const [environmentMode, setEnvironmentModeState] = React.useState<EnvironmentMode>(() => {
    const activeAcc = getStoredAccounts().find(a => a.id === window.localStorage.getItem('clicko-studio:active-account-id'));
    if (activeAcc) return activeAcc.type;
    return getStoredEnvironment();
  });

  const [loading, setLoading] = React.useState(true);
  const [feedback, setFeedback] = React.useState<Feedback>(null);
  const [session, setSession] = React.useState<GovernanceSession>();
  const [workspace, setWorkspace] = React.useState<GovernanceWorkspace>();
  const [users, setUsers] = React.useState<WorkspaceMember[]>([]);
  const [plans, setPlans] = React.useState<SaaSPlan[]>([]);
  const [subscription, setSubscription] = React.useState<WorkspaceSubscription>();
  const [approvals, setApprovals] = React.useState<ContentApprovalItem[]>([]);
  const [auditLogs, setAuditLogs] = React.useState<AuditLogEntry[]>([]);

  const activeAccount = React.useMemo(() => {
    return accounts.find((a) => a.id === activeAccountId) || accounts[0] || DEFAULT_ACCOUNTS[0];
  }, [accounts, activeAccountId]);

  const setEnvironmentMode = React.useCallback((mode: EnvironmentMode) => {
    window.localStorage.setItem('clicko-studio:environment', mode);
    setEnvironmentModeState(mode);
    window.dispatchEvent(new CustomEvent('clicko:environment-change', { detail: { mode } }));
  }, []);

  const switchAccount = React.useCallback((accountId: string) => {
    const target = accounts.find((a) => a.id === accountId);
    if (!target) return;
    setActiveAccountId(accountId);
    window.localStorage.setItem('clicko-studio:active-account-id', accountId);
    if (target.type !== environmentMode) {
      setEnvironmentMode(target.type);
    }
  }, [accounts, environmentMode, setEnvironmentMode]);

  const addAccount = React.useCallback((newAccData: Omit<UserAccount, 'id'>) => {
    const id = `acc-${newAccData.type}-${Date.now()}`;
    const newAcc: UserAccount = {
      id,
      ...newAccData,
      createdAt: new Date().toISOString(),
    };
    setAccounts((current) => {
      const updated = [...current, newAcc];
      window.localStorage.setItem('clicko-studio:user-accounts', JSON.stringify(updated));
      return updated;
    });
    setActiveAccountId(id);
    window.localStorage.setItem('clicko-studio:active-account-id', id);
    setEnvironmentMode(newAcc.type);
    return id;
  }, [setEnvironmentMode]);

  const removeAccount = React.useCallback((accountId: string) => {
    setAccounts((current) => {
      if (current.length <= 1) return current;
      const updated = current.filter((a) => a.id !== accountId);
      window.localStorage.setItem('clicko-studio:user-accounts', JSON.stringify(updated));
      if (activeAccountId === accountId && updated.length > 0) {
        const fallback = updated[0];
        setActiveAccountId(fallback.id);
        window.localStorage.setItem('clicko-studio:active-account-id', fallback.id);
        setEnvironmentMode(fallback.type);
      }
      return updated;
    });
  }, [activeAccountId, setEnvironmentMode]);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const nextSession = await request<GovernanceSession>('/session', environmentMode);
      const nextWorkspace = await request<GovernanceWorkspace>('/workspace', environmentMode);
      setSession(nextSession);
      setWorkspace(nextWorkspace);
      if (nextSession.currentUser.role === 'master') {
        const [nextUsers, nextPlans, nextSubscription, nextApprovals, nextAuditLogs] = await Promise.all([
          request<WorkspaceMember[]>('/users', environmentMode),
          request<SaaSPlan[]>('/plans', environmentMode),
          request<WorkspaceSubscription>('/subscription', environmentMode),
          request<ContentApprovalItem[]>('/approvals', environmentMode),
          request<AuditLogEntry[]>('/audit-logs', environmentMode),
        ]);
        setUsers(nextUsers);
        setPlans(nextPlans);
        setSubscription(nextSubscription);
        setApprovals(nextApprovals);
        setAuditLogs(nextAuditLogs);
      } else {
        setUsers([nextSession.currentUser]);
        setPlans([]);
        setSubscription(undefined);
        setApprovals([]);
        setAuditLogs([]);
      }
    } catch (error) {
      setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Falha ao carregar a governança.' });
    } finally {
      setLoading(false);
    }
  }, [environmentMode]);

  React.useEffect(() => { void refresh(); }, [refresh]);

  const run = async <T,>(operation: () => Promise<T>, message: string, onSuccess?: (value: T) => void) => {
    try {
      const value = await operation();
      onSuccess?.(value);
      setFeedback({ type: 'success', message });
      return value;
    } catch (error) {
      setFeedback({ type: 'error', message: error instanceof Error ? error.message : 'Não foi possível concluir a ação.' });
      return null;
    }
  };

  const inviteUser: GovernanceContextValue['inviteUser'] = async (payload) => Boolean(await run(
    () => request<WorkspaceMember>('/invites', environmentMode, { method: 'POST', body: JSON.stringify(payload) }),
    'Convite enviado com sucesso.',
    (member) => setUsers((current) => [...current, member]),
  ));

  const updateUser: GovernanceContextValue['updateUser'] = async (userId, payload) => Boolean(await run(
    () => request<WorkspaceMember>(`/users/${userId}`, environmentMode, { method: 'PATCH', body: JSON.stringify(payload) }),
    'Usuário atualizado.',
    (member) => setUsers((current) => current.map((item) => item.id === member.id ? member : item)),
  ));

  const deleteUser: GovernanceContextValue['deleteUser'] = async (userId) => {
    const result = await run(() => request<void>(`/users/${userId}`, environmentMode, { method: 'DELETE' }), 'Usuário removido.', () => setUsers((current) => current.filter((item) => item.id !== userId)));
    return result !== null;
  };

  const resendInvite: GovernanceContextValue['resendInvite'] = async (userId) => Boolean(await run(
    () => request<WorkspaceMember>(`/users/${userId}/resend-invite`, environmentMode, { method: 'POST' }),
    'Convite reenviado e prazo renovado.',
    (member) => setUsers((current) => current.map((item) => item.id === member.id ? member : item)),
  ));

  const changePlan: GovernanceContextValue['changePlan'] = async (planId) => Boolean(await run(
    () => request<{ subscription: WorkspaceSubscription; workspace: GovernanceWorkspace }>('/subscription', environmentMode, { method: 'PATCH', body: JSON.stringify({ planId }) }),
    'Plano atualizado com sucesso.',
    (result) => { setSubscription(result.subscription); setWorkspace(result.workspace); },
  ));

  const recordOfferEvent: GovernanceContextValue['recordOfferEvent'] = async (payload) => {
    try {
      await request<void>('/offers/events', environmentMode, { method: 'POST', body: JSON.stringify(payload) });
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
    () => request<ContentApprovalItem>(`/approvals/${approvalId}/actions`, environmentMode, { method: 'POST', body: JSON.stringify({ action, comment, scheduledAt }) }),
    action === 'comment' ? 'Comentário adicionado.' : 'Fluxo de aprovação atualizado.',
    (approval) => setApprovals((current) => current.map((item) => item.id === approval.id ? approval : item)),
  );

  const currentUser = session?.currentUser;
  const value: GovernanceContextValue = {
    environmentMode,
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
    workspace,
    users,
    plans,
    subscription,
    approvals,
    auditLogs,
    isMaster: currentUser?.role === 'master',
    canAccess: (tab) => canAccessNavigation(currentUser, tab, environmentMode),
    clearFeedback: () => setFeedback(null),
    inviteUser,
    updateUser,
    deleteUser,
    resendInvite,
    changePlan,
    recordOfferEvent,
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
