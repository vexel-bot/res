import React from 'react';
import type {
  AuditLogEntry,
  ContentApprovalItem,
  GovernanceSession,
  GovernanceWorkspace,
  NavigationTab,
  SaaSPlan,
  WorkspaceMember,
  WorkspaceModule,
  WorkspaceSubscription,
} from '../types';
import { canAccessNavigation } from '../security/accessControl';

type Feedback = { type: 'success' | 'error'; message: string } | null;

type GovernanceContextValue = {
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
  approvalAction: (approvalId: string, action: 'approve' | 'request_changes' | 'reject' | 'publish' | 'schedule' | 'comment', comment?: string, scheduledAt?: string) => Promise<ContentApprovalItem | null>;
  refresh: () => Promise<void>;
};

const GovernanceContext = React.createContext<GovernanceContextValue | null>(null);

const workspaceId = 'ws-1';

function getUserId() {
  return window.localStorage.getItem('clicko-studio:session-user') || 'usr-master';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/governance${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'x-workspace-id': workspaceId,
      'x-user-id': getUserId(),
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
  const [loading, setLoading] = React.useState(true);
  const [feedback, setFeedback] = React.useState<Feedback>(null);
  const [session, setSession] = React.useState<GovernanceSession>();
  const [workspace, setWorkspace] = React.useState<GovernanceWorkspace>();
  const [users, setUsers] = React.useState<WorkspaceMember[]>([]);
  const [plans, setPlans] = React.useState<SaaSPlan[]>([]);
  const [subscription, setSubscription] = React.useState<WorkspaceSubscription>();
  const [approvals, setApprovals] = React.useState<ContentApprovalItem[]>([]);
  const [auditLogs, setAuditLogs] = React.useState<AuditLogEntry[]>([]);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try {
      const nextSession = await request<GovernanceSession>('/session');
      const nextWorkspace = await request<GovernanceWorkspace>('/workspace');
      setSession(nextSession);
      setWorkspace(nextWorkspace);
      if (nextSession.currentUser.role === 'master') {
        const [nextUsers, nextPlans, nextSubscription, nextApprovals, nextAuditLogs] = await Promise.all([
          request<WorkspaceMember[]>('/users'),
          request<SaaSPlan[]>('/plans'),
          request<WorkspaceSubscription>('/subscription'),
          request<ContentApprovalItem[]>('/approvals'),
          request<AuditLogEntry[]>('/audit-logs'),
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
  }, []);

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
    () => request<WorkspaceMember>('/invites', { method: 'POST', body: JSON.stringify(payload) }),
    'Convite enviado com sucesso.',
    (member) => setUsers((current) => [...current, member]),
  ));

  const updateUser: GovernanceContextValue['updateUser'] = async (userId, payload) => Boolean(await run(
    () => request<WorkspaceMember>(`/users/${userId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    'Usuário atualizado.',
    (member) => setUsers((current) => current.map((item) => item.id === member.id ? member : item)),
  ));

  const deleteUser: GovernanceContextValue['deleteUser'] = async (userId) => {
    const result = await run(() => request<void>(`/users/${userId}`, { method: 'DELETE' }), 'Usuário removido.', () => setUsers((current) => current.filter((item) => item.id !== userId)));
    return result !== null;
  };

  const resendInvite: GovernanceContextValue['resendInvite'] = async (userId) => Boolean(await run(
    () => request<WorkspaceMember>(`/users/${userId}/resend-invite`, { method: 'POST' }),
    'Convite reenviado e prazo renovado.',
    (member) => setUsers((current) => current.map((item) => item.id === member.id ? member : item)),
  ));

  const changePlan: GovernanceContextValue['changePlan'] = async (planId) => Boolean(await run(
    () => request<{ subscription: WorkspaceSubscription; workspace: GovernanceWorkspace }>('/subscription', { method: 'PATCH', body: JSON.stringify({ planId }) }),
    'Plano atualizado com sucesso.',
    (result) => { setSubscription(result.subscription); setWorkspace(result.workspace); },
  ));

  const approvalAction: GovernanceContextValue['approvalAction'] = async (approvalId, action, comment, scheduledAt) => run(
    () => request<ContentApprovalItem>(`/approvals/${approvalId}/actions`, { method: 'POST', body: JSON.stringify({ action, comment, scheduledAt }) }),
    action === 'comment' ? 'Comentário adicionado.' : 'Fluxo de aprovação atualizado.',
    (approval) => setApprovals((current) => current.map((item) => item.id === approval.id ? approval : item)),
  );

  const currentUser = session?.currentUser;
  const value: GovernanceContextValue = {
    loading, feedback, currentUser, workspace, users, plans, subscription, approvals, auditLogs,
    isMaster: currentUser?.role === 'master',
    canAccess: (tab) => canAccessNavigation(currentUser, tab),
    clearFeedback: () => setFeedback(null),
    inviteUser, updateUser, deleteUser, resendInvite, changePlan, approvalAction, refresh,
  };

  return <GovernanceContext.Provider value={value}>{children}</GovernanceContext.Provider>;
};

export function useGovernance() {
  const context = React.useContext(GovernanceContext);
  if (!context) throw new Error('useGovernance precisa estar dentro de GovernanceProvider.');
  return context;
}
