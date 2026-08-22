import React from 'react';
import { apiFetch, authToken } from '../api';
import type { Post } from '../types';

type ServerUser = { id: string; email: string; name: string };
type ServerWorkspace = {
  id: string;
  name: string;
  avatar: string;
  plan: string;
  membersCount: number;
  role: string;
  brandProfile: Record<string, unknown>;
};

type ServerBootstrap = {
  user: ServerUser;
  workspaces: ServerWorkspace[];
  posts: Post[];
  suggestions: Array<Record<string, unknown>>;
};

type ServerStatus = 'guest' | 'loading' | 'connected' | 'error';

type ServerStateValue = {
  status: ServerStatus;
  bootstrap?: ServerBootstrap;
  error?: string;
  refresh: () => Promise<void>;
  createCampaign: (payload: Record<string, unknown>) => Promise<{ id: string; name: string }>;
  createPost: (payload: Record<string, unknown>) => Promise<Post>;
  approvalAction: (postId: string, action: 'approve' | 'request_changes' | 'reject' | 'publish' | 'schedule' | 'comment', options?: { comment?: string; scheduledAt?: string }) => Promise<Post>;
};

const ServerStateContext = React.createContext<ServerStateValue | null>(null);

export function ServerStateProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<ServerStatus>(() => authToken.get() ? 'loading' : 'guest');
  const [bootstrap, setBootstrap] = React.useState<ServerBootstrap>();
  const [error, setError] = React.useState<string>();

  const refresh = React.useCallback(async () => {
    if (!authToken.get()) {
      setStatus('guest');
      setBootstrap(undefined);
      return;
    }
    setStatus('loading');
    try {
      const result = await apiFetch<ServerBootstrap>('/api/v1/bootstrap');
      setBootstrap(result);
      setError(undefined);
      setStatus('connected');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao sincronizar o workspace.');
      setStatus('error');
    }
  }, []);

  React.useEffect(() => { void refresh(); }, [refresh]);

  React.useEffect(() => {
    const unauthorized = () => {
      authToken.clear();
      setBootstrap(undefined);
      setStatus('guest');
    };
    window.addEventListener('nexus:unauthorized', unauthorized);
    return () => window.removeEventListener('nexus:unauthorized', unauthorized);
  }, []);

  const activeWorkspaceId = bootstrap?.workspaces[0]?.id;

  const createCampaign = React.useCallback(async (payload: Record<string, unknown>) => {
    if (!activeWorkspaceId) throw new Error('Entre com uma conta funcional para criar a campanha no servidor.');
    const campaign = await apiFetch<{ id: string; name: string }>('/api/v1/campaigns', {
      method: 'POST',
      body: JSON.stringify({ ...payload, workspaceId: activeWorkspaceId }),
    });
    await refresh();
    return campaign;
  }, [activeWorkspaceId, refresh]);

  const createPost = React.useCallback(async (payload: Record<string, unknown>) => {
    if (!activeWorkspaceId) throw new Error('Entre com uma conta funcional para salvar o conteúdo no servidor.');
    const post = await apiFetch<Post>('/api/v1/posts', {
      method: 'POST',
      body: JSON.stringify({ ...payload, workspaceId: activeWorkspaceId }),
    });
    await refresh();
    return post;
  }, [activeWorkspaceId, refresh]);

  const approvalAction = React.useCallback(async (postId: string, action: 'approve' | 'request_changes' | 'reject' | 'publish' | 'schedule' | 'comment', options: { comment?: string; scheduledAt?: string } = {}) => {
    const result = await apiFetch<{ post: Post }>(`/api/v1/posts/${postId}/approval-actions`, {
      method: 'POST',
      body: JSON.stringify({ action, comment: options.comment, scheduledAt: options.scheduledAt }),
    });
    await refresh();
    return result.post;
  }, [refresh]);

  return <ServerStateContext.Provider value={{ status, bootstrap, error, refresh, createCampaign, createPost, approvalAction }}>{children}</ServerStateContext.Provider>;
}

export function useServerState() {
  const value = React.useContext(ServerStateContext);
  if (!value) throw new Error('useServerState deve ser usado dentro de ServerStateProvider.');
  return value;
}

