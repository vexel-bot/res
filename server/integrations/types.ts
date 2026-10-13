export const socialProviderIds = ['instagram', 'facebook', 'tiktok', 'youtube', 'linkedin', 'threads', 'pinterest', 'x'] as const;
export type SocialProviderId = typeof socialProviderIds[number];
export type SocialOwnerType = 'personal' | 'workspace';
export type SocialConnectionStatus = 'connected' | 'expired' | 'permission_insufficient' | 'authorization_revoked' | 'error';

export type SocialCapabilities = {
  canReadProfile: boolean;
  canReadAnalytics: boolean;
  canPublishText: boolean;
  canPublishImage: boolean;
  canPublishCarousel: boolean;
  canPublishVideo: boolean;
  canPublishShortVideo: boolean;
  canPublishStory: boolean;
  canPublishDocument: boolean;
  canSchedule: boolean;
  canReadPosts: boolean;
  canReadComments: boolean;
  canReplyComments: boolean;
};

export type StoredSocialConnection = {
  id: string;
  ownerType: SocialOwnerType;
  ownerId: string;
  actorId?: string;
  clientId?: string;
  provider: SocialProviderId;
  providerAccountId: string;
  accountType?: string;
  username?: string;
  displayName: string;
  avatarUrl?: string;
  accessTokenEncrypted: string;
  refreshTokenEncrypted?: string;
  tokenExpiresAt?: string;
  refreshTokenExpiresAt?: string;
  scopes: string[];
  status: SocialConnectionStatus;
  capabilities: SocialCapabilities;
  lastSyncedAt?: string;
  lastError?: string;
  providerMetadata: Record<string, string | number | boolean | string[]>;
  createdAt: string;
  updatedAt: string;
};

export type StoredOAuthState = {
  stateHash: string;
  browserBindingHash: string;
  provider: SocialProviderId;
  ownerType: SocialOwnerType;
  ownerId: string;
  actorId: string;
  redirectUri: string;
  returnTo: string;
  codeVerifier?: string;
  expiresAt: string;
  createdAt: string;
};

export type StoredOAuthSelectionAccount = {
  providerAccountId: string;
  accountType?: string;
  username?: string;
  displayName: string;
  avatarUrl?: string;
  accessTokenEncrypted: string;
  refreshTokenEncrypted?: string;
  tokenExpiresAt?: string;
  refreshTokenExpiresAt?: string;
  scopes: string[];
  capabilities: SocialCapabilities;
  providerMetadata: Record<string, string | number | boolean | string[]>;
};

export type StoredOAuthSelection = {
  tokenHash: string;
  provider: SocialProviderId;
  ownerType: SocialOwnerType;
  ownerId: string;
  actorId: string;
  accounts: StoredOAuthSelectionAccount[];
  expiresAt: string;
  createdAt: string;
};

export type StoredSocialAuditEvent = {
  id: string;
  ownerType: SocialOwnerType;
  ownerId: string;
  actorId: string;
  provider: SocialProviderId;
  action: 'oauth_started' | 'oauth_cancelled' | 'oauth_failed' | 'resources_discovered' | 'connected' | 'refreshed' | 'reconnected' | 'disconnected' | 'client_bound';
  connectionIds?: string[];
  outcome: 'success' | 'failure';
  code?: string;
  createdAt: string;
};

export type SocialIntegrationSnapshot = {
  version: 1;
  connections: StoredSocialConnection[];
  oauthStates: StoredOAuthState[];
  oauthSelections?: StoredOAuthSelection[];
  auditEvents?: StoredSocialAuditEvent[];
  publicationOperations?: StoredSocialPublication[];
  analyticsSnapshots?: StoredSocialAnalyticsSnapshot[];
  scheduledPublications?: StoredScheduledPublication[];
};

export type StoredScheduledPublication = {
  id: string;
  ownerType: SocialOwnerType;
  ownerId: string;
  clientId?: string;
  connectionId: string;
  contentId: string;
  title?: string;
  provider?: SocialProviderId;
  approvalId?: string;
  request: SocialPublishRequest;
  scheduledAt: string;
  status: 'scheduled' | 'publishing' | 'published' | 'processing' | 'failed' | 'indeterminate' | 'cancelled';
  providerPostId?: string;
  errorCode?: string;
  createdAt: string;
  updatedAt: string;
};

export type StoredSocialAnalyticsSnapshot = {
  ownerType: SocialOwnerType;
  ownerId: string;
  connectionId: string;
  provider: SocialProviderId;
  from: string;
  to: string;
  metrics: SocialMetrics;
  updatedAt: string;
};

export type StoredSocialPublication = {
  id: string;
  ownerType: SocialOwnerType;
  ownerId: string;
  connectionId: string;
  idempotencyKey: string;
  requestHash: string;
  status: 'processing' | 'published' | 'indeterminate' | 'failed';
  providerPostId?: string;
  errorCode?: string;
  createdAt: string;
  updatedAt: string;
};

export type ProviderCredentials = {
  clientId: string;
  clientSecret: string;
  redirectUri: string;
};

export type ProviderTokenSet = {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: string;
  refreshTokenExpiresAt?: string;
  scopes: string[];
};

export type ProviderAccount = {
  id: string;
  username?: string;
  displayName: string;
  avatarUrl?: string;
  accountType?: string;
  accessToken?: string;
  metadata?: Record<string, string | number | boolean | string[]>;
};

export type ProviderResource = {
  id: string;
  name: string;
  type: 'profile' | 'page' | 'channel' | 'board' | 'organization';
  handle?: string;
  avatarUrl?: string;
  metadata?: Record<string, string | number | boolean | string[]>;
};

export type SocialPublishKind = 'text' | 'image' | 'carousel' | 'video' | 'short_video' | 'story' | 'document';

export type SocialPublishRequest = {
  kind: SocialPublishKind;
  text?: string;
  title?: string;
  description?: string;
  mediaUrls?: string[];
  providerAssetIds?: string[];
  destinationId?: string;
  scheduledAt?: string;
  userConsentConfirmed?: boolean;
  privacyLevel?: string;
  disableDuet?: boolean;
  disableComment?: boolean;
  disableStitch?: boolean;
};

export type SocialPublishResult = {
  providerPostId: string;
  status: 'published' | 'processing';
  providerMetadata?: Record<string, string | number | boolean | string[]>;
};

export type SocialMetrics = {
  followers?: number;
  reach?: number;
  impressions?: number;
  views?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  saves?: number;
  clicks?: number;
  engagements?: number;
};

export type SocialAnalytics = {
  from: string;
  to: string;
  metrics: SocialMetrics;
  providerMetrics: Record<string, number>;
  rawMetadata?: Record<string, string | number | boolean | string[]>;
  nextCursor?: string;
};

export type FetchLike = typeof fetch;

export type ProviderRequestContext = {
  credentials: ProviderCredentials;
  fetch: FetchLike;
  signal: AbortSignal;
};

export type SocialProvider = {
  id: SocialProviderId;
  label: string;
  requiredEnvironment: string[];
  credentials: () => ProviderCredentials | null;
  usesPkce: boolean;
  authorizationUrl: (input: { credentials: ProviderCredentials; redirectUri: string; state: string; codeChallenge?: string }) => string;
  exchangeCode: (context: ProviderRequestContext, input: { code: string; redirectUri: string; codeVerifier?: string }) => Promise<ProviderTokenSet>;
  grantedScopes?: (context: ProviderRequestContext, token: ProviderTokenSet) => Promise<string[]>;
  accounts: (context: ProviderRequestContext, token: ProviderTokenSet) => Promise<ProviderAccount[]>;
  account?: (context: ProviderRequestContext, token: ProviderTokenSet, providerAccountId: string) => Promise<ProviderAccount | null>;
  resources?: (context: ProviderRequestContext, token: ProviderTokenSet, account: StoredSocialConnection) => Promise<ProviderResource[]>;
  refresh?: (context: ProviderRequestContext, refreshToken: string) => Promise<ProviderTokenSet>;
  revoke?: (context: ProviderRequestContext, accessToken: string) => Promise<void>;
  publish?: (context: ProviderRequestContext, token: ProviderTokenSet, account: StoredSocialConnection, request: SocialPublishRequest) => Promise<SocialPublishResult>;
  analytics?: (context: ProviderRequestContext, token: ProviderTokenSet, account: StoredSocialConnection, range: { from: string; to: string; cursor?: string }) => Promise<SocialAnalytics>;
  capabilities: (scopes: string[]) => SocialCapabilities;
};

export type PublicSocialConnection = Omit<StoredSocialConnection,
  'accessTokenEncrypted' | 'refreshTokenEncrypted' | 'providerMetadata' | 'ownerId' | 'actorId'> & { tokenExpiring?: boolean };

export const emptyCapabilities = (): SocialCapabilities => ({
  canReadProfile: false,
  canReadAnalytics: false,
  canPublishText: false,
  canPublishImage: false,
  canPublishCarousel: false,
  canPublishVideo: false,
  canPublishShortVideo: false,
  canPublishStory: false,
  canPublishDocument: false,
  canSchedule: false,
  canReadPosts: false,
  canReadComments: false,
  canReplyComments: false,
});
