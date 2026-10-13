import type { ConnectedAccount, SocialPlatform } from '../types';

/** Public metadata returned by the authenticated social API. No tokens enter this layer. */
export type SocialConnectionSummary = {
  id: string;
  clientId?: string;
  provider: SocialPlatform;
  providerAccountId: string;
  username?: string;
  displayName: string;
  avatarUrl?: string;
  createdAt?: string;
  scopes: string[];
  status: NonNullable<ConnectedAccount['connectionStatus']>;
  capabilities: NonNullable<ConnectedAccount['capabilities']>;
  lastSyncedAt?: string;
  lastError?: string;
  tokenExpiring?: boolean;
  accountType?: string;
};

export function connectedAccountsFromServer(workspaceId: string, records: SocialConnectionSummary[], previous: ConnectedAccount[]): ConnectedAccount[] {
  return records.map(record => {
    const existing = previous.find(item => item.id === record.id);
    return {
      ...existing,
      id: record.id,
      clientId: record.clientId,
      workspaceId,
      platform: record.provider,
      providerAccountId: record.providerAccountId,
      providerConnectionIds: [record.id],
      handle: record.username ? `@${record.username.replace(/^@/, '')}` : record.displayName,
      name: record.displayName,
      avatar: record.avatarUrl,
      connected: record.status === 'connected',
      connectionStatus: record.status,
      permissions: record.scopes,
      capabilities: record.capabilities,
      lastSync: record.lastSyncedAt || existing?.lastSync || 'Nunca',
      lastError: record.lastError,
      tokenExpiring: record.tokenExpiring,
      accountType: record.accountType,
      connectedAt: record.createdAt,
      followers: existing?.followers || '—',
      engagement: existing?.engagement || '—',
      bestTime: existing?.bestTime || 'Sem dados',
    };
  });
}
