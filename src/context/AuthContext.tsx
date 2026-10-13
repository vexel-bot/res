import React from 'react';
import type { UserAccount, WorkspaceMember } from '../types';

type AuthPayload = { account: UserAccount; accounts: UserAccount[]; user: WorkspaceMember };
type AuthResponse = AuthPayload & { verificationRequired?: false };
type SignupResponse = Partial<AuthPayload> & { verificationRequired: boolean; deliveryConfigured?: boolean; developmentToken?: string };
type RecoveryResponse = { message: string; deliveryConfigured?: boolean; developmentToken?: string };

type AuthContextValue = {
  loading: boolean;
  authenticated: boolean;
  account?: UserAccount;
  accounts: UserAccount[];
  user?: WorkspaceMember;
  refresh: () => Promise<boolean>;
  uploadAvatar: (file: File, workspaceId: string, signal?: AbortSignal) => Promise<string>;
  login: (email: string, password: string, remember: boolean) => Promise<void>;
  signup: (name: string, email: string, password: string, confirmation: string, termsAccepted: boolean, privacyAccepted: boolean, remember: boolean) => Promise<SignupResponse>;
  forgotPassword: (email: string) => Promise<RecoveryResponse>;
  resetPassword: (token: string, password: string) => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  switchAccount: (workspaceId: string) => Promise<void>;
  removeAccount: (workspaceId: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = React.createContext<AuthContextValue | null>(null);

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/governance/auth${path}`, {
    ...init,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: 'Não foi possível concluir a solicitação.' }));
    const error = new Error(body.error || 'Não foi possível concluir a solicitação.') as Error & { status?: number; details?: unknown };
    error.status = response.status;
    error.details = body;
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [loading, setLoading] = React.useState(true);
  const [payload, setPayload] = React.useState<AuthPayload>();

  const accept = React.useCallback((value: AuthPayload) => {
    setPayload(previous => {
      // A focus/session check must not recreate an unchanged account and
      // unmount its forms when the native file picker returns focus.
      const accounts = value.accounts.map(account => {
        const old = previous?.accounts.find(item => item.id === account.id);
        return old && JSON.stringify(old) === JSON.stringify(account) ? old : account;
      });
      const account = accounts.find(item => item.id === value.account.id)!;
      return { ...value, account, accounts };
    });
    // These keys contain display metadata only. They are never accepted by the
    // server as proof of identity; the session lives in an HTTP-only cookie.
    try {
      localStorage.setItem('clicko-studio:user-accounts', JSON.stringify(value.accounts));
      localStorage.setItem('clicko-studio:active-account-id', value.account.id);
      localStorage.setItem('clicko-studio:environment', value.account.type);
    } catch { /* A full storage quota must not invalidate an authenticated session. */ }
  }, []);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    try { accept(await authRequest<AuthPayload>('/session')); return true; }
    catch { setPayload(undefined); return false; }
    finally { setLoading(false); }
  }, [accept]);

  React.useEffect(() => { void refresh(); }, [refresh]);
  const activeWorkspace = React.useRef(payload?.account.workspaceId);
  activeWorkspace.current = payload?.account.workspaceId;
  const uploadAvatar = React.useCallback(async (file: File, workspaceId: string, signal?: AbortSignal) => {
    const response = await fetch('/api/governance/profile/avatar', {
      method: 'PUT', credentials: 'same-origin', signal,
      headers: { 'Content-Type': file.type, 'x-workspace-id': workspaceId }, body: file,
    });
    const result = await response.json().catch(() => null);
    if (!response.ok) throw new Error(result?.error || 'Não foi possível salvar a foto. Tente novamente.');
    if (activeWorkspace.current !== workspaceId) throw new Error('O perfil ativo mudou.');
    if (!result?.user?.avatar || !result.account || !Array.isArray(result.accounts)) throw new Error('O servidor não confirmou o salvamento da foto.');
    accept(result as AuthPayload);
    return result.user.avatar as string;
  }, [accept]);
  React.useEffect(() => {
    const verify = async () => { try { accept(await authRequest<AuthPayload>('/session')); } catch { setPayload(undefined); } };
    const interval = window.setInterval(() => { void verify(); }, 5 * 60_000);
    const onFocus = () => { if (document.visibilityState === 'visible') void verify(); };
    window.addEventListener('focus', onFocus);
    return () => { window.clearInterval(interval); window.removeEventListener('focus', onFocus); };
  }, [accept]);

  const login = React.useCallback(async (email: string, password: string, remember: boolean) => {
    const invitation = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    accept(await authRequest<AuthResponse>('/login', { method: 'POST', body: JSON.stringify({ email, password, remember, clientInviteId: invitation.get('clientInvite'), clientInviteToken: invitation.get('token') }) }));
  }, [accept]);

  const signup = React.useCallback(async (name: string, email: string, password: string, confirmation: string, termsAccepted: boolean, privacyAccepted: boolean, remember: boolean) => {
    const invitation = new URLSearchParams(window.location.hash.replace(/^#/, ''));
    const response = await authRequest<SignupResponse>('/signup', { method: 'POST', body: JSON.stringify({ name, email, password, confirmation, termsAccepted, privacyAccepted, remember, clientInviteId: invitation.get('clientInvite'), clientInviteToken: invitation.get('token') }) });
    if (!response.verificationRequired && response.account && response.accounts && response.user) accept(response as AuthPayload);
    return response;
  }, [accept]);

  const forgotPassword = React.useCallback((email: string) => authRequest<RecoveryResponse>('/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }), []);
  const resetPassword = React.useCallback(async (token: string, password: string) => { accept(await authRequest<AuthPayload>('/reset-password', { method: 'POST', body: JSON.stringify({ token, password }) })); }, [accept]);
  const verifyEmail = React.useCallback(async (token: string) => { accept(await authRequest<AuthPayload>('/verify-email', { method: 'POST', body: JSON.stringify({ token }) })); }, [accept]);
  const switchAccount = React.useCallback(async (workspaceId: string) => { accept(await authRequest<AuthPayload>('/session/workspace', { method: 'POST', body: JSON.stringify({ workspaceId }) })); }, [accept]);
  const removeAccount = React.useCallback(async (workspaceId: string) => { accept(await authRequest<AuthPayload>(`/accounts/${encodeURIComponent(workspaceId)}`, { method: 'DELETE' })); }, [accept]);
  const logout = React.useCallback(async () => {
    try { await authRequest<void>('/logout', { method: 'POST' }); } finally {
      setPayload(undefined);
      try { localStorage.removeItem('clicko-studio:user-accounts'); localStorage.removeItem('clicko-studio:active-account-id'); } catch { /* ignore */ }
      window.history.replaceState({}, '', '/login');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }
  }, []);

  return <AuthContext.Provider value={{ loading, authenticated: Boolean(payload), account: payload?.account, accounts: payload?.accounts || [], user: payload?.user, refresh, uploadAvatar, login, signup, forgotPassword, resetPassword, verifyEmail, switchAccount, removeAccount, logout }}>{children}</AuthContext.Provider>;
};

export function useAuth() {
  const value = React.useContext(AuthContext);
  if (!value) throw new Error('useAuth precisa estar dentro de AuthProvider.');
  return value;
}
