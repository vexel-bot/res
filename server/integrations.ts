import { createHash, randomBytes, randomUUID } from 'node:crypto';
import path from 'node:path';
import { Router, type Request, type Response } from 'express';
import { assertGovernanceAccess, authenticate, permissionOnly, publicationApprovalStage, readGovernanceAccountType, workspaceOwnsClient, type AuthContext } from './governance';
import { createTokenCipherFromEnvironment, type TokenCipher } from './integrations/crypto';
import { callbackReason, publicIntegrationError, SocialIntegrationError } from './integrations/errors';
import { validatePublishRequest } from './integrations/publishing';
import { supportsClickoScheduling, validateScheduledProviderRequest } from './integrations/scheduling';
import { socialProviderRegistry } from './integrations/providers/registry';
import { SocialIntegrationRepository, type SocialIntegrationRepositoryPort, type SocialOwner } from './integrations/repository';
import { PostgresSocialIntegrationRepository } from './integrations/postgresRepository';
import { socialProviderIds, type FetchLike, type PublicSocialConnection, type SocialProvider, type SocialProviderId, type SocialPublishRequest, type StoredOAuthSelectionAccount, type StoredSocialConnection, type StoredScheduledPublication } from './integrations/types';

type AuthenticatedRequest = Request & { auth?: AuthContext };
type RouterOptions = { dataFile?: string | null; fetch?: FetchLike; now?: () => number; repository?: SocialIntegrationRepositoryPort; schedulerIntervalMs?: number };

let readableRepository: SocialIntegrationRepositoryPort | undefined;
let scheduledRunner: (() => Promise<void>) | undefined;
let scheduledTimer: NodeJS.Timeout | undefined;

export async function runDueScheduledPublications() { await scheduledRunner?.(); }

export async function socialIntegrationReadiness() {
  if (!readableRepository) throw new Error('SOCIAL_REPOSITORY_NOT_INITIALIZED');
  return readableRepository.health();
}

export async function closeSocialIntegrationRepository() {
  if (scheduledTimer) clearInterval(scheduledTimer);
  scheduledTimer = undefined;
  scheduledRunner = undefined;
  await readableRepository?.close?.();
  readableRepository = undefined;
}

const sha256 = (value: string) => createHash('sha256').update(value).digest('base64url');
const OAUTH_BINDING_COOKIE = 'clicko_social_oauth';
const cookieValue = (req: Request, name: string) => String(req.headers.cookie || '').split(';').map(part => part.trim()).find(part => part.startsWith(`${name}=`))?.slice(name.length + 1) || '';
const oauthBindingCookie = (value: string, maxAgeSeconds: number) => `${OAUTH_BINDING_COOKIE}=${value}; Path=/api/integrations/oauth/callback; HttpOnly; SameSite=Lax; Max-Age=${maxAgeSeconds}${process.env.NODE_ENV === 'production' ? '; Secure' : ''}`;
const clearOauthBindingCookie = () => oauthBindingCookie('', 0);
const effectiveCapabilities = (connection: StoredSocialConnection) => ({ ...connection.capabilities,
  canSchedule: Boolean(socialProviderRegistry().get(connection.provider)?.publish && supportsClickoScheduling(connection)) });
const publicConnection = (connection: StoredSocialConnection, now = Date.now()): PublicSocialConnection => {
  const { accessTokenEncrypted: _accessToken, refreshTokenEncrypted: _refreshToken, providerMetadata: _metadata, ownerId: _ownerId, actorId: _actorId, ...safe } = connection;
  return { ...safe, capabilities: effectiveCapabilities(connection), tokenExpiring: connection.status === 'connected' && Boolean(connection.tokenExpiresAt && Date.parse(connection.tokenExpiresAt) <= now + 24 * 60 * 60_000) };
};

function validateDataFile(filename: string | null) {
  if (!filename) return null;
  const resolved = path.resolve(filename);
  for (const root of [path.resolve('public'), path.resolve('dist')]) {
    const relative = path.relative(root, resolved);
    if (!relative || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) throw new Error('SOCIAL_STORE_PUBLIC_PATH');
  }
  return resolved;
}

function providerId(req: Request): SocialProviderId {
  const value = String(req.params.provider || '').toLowerCase();
  if (!socialProviderIds.includes(value as SocialProviderId)) throw new SocialIntegrationError('SOCIAL_PROVIDER_UNKNOWN', 404, 'Plataforma não suportada.');
  return value as SocialProviderId;
}

function ownerFor(req: AuthenticatedRequest): SocialOwner {
  const auth = req.auth;
  if (!auth) throw new SocialIntegrationError('SOCIAL_SESSION_REQUIRED', 401, 'Sua sessão expirou. Entre novamente.');
  return { ownerType: readGovernanceAccountType(auth) === 'personal' ? 'personal' : 'workspace', ownerId: auth.workspaceId };
}

function assertSocialScope(req: AuthenticatedRequest, input: { clientId?: string | null; connectionId?: string | null }) {
  try { assertGovernanceAccess(req.auth!, { clientId: input.clientId, socialAccountId: input.connectionId }); }
  catch (error) {
    const failure = error as Error & { status?: number; code?: string };
    throw new SocialIntegrationError(failure.code || 'SOCIAL_SCOPE_DENIED', failure.status || 403, failure.message || 'Recurso fora do seu escopo.');
  }
}

function applicationOrigin(req: Request) {
  return String(process.env.PUBLIC_APP_URL || process.env.APP_URL || `${req.protocol}://${req.get('host')}`).replace(/\/$/, '');
}

function trustedMutationOrigin(req: Request, origin: string) {
  if (origin === applicationOrigin(req)) return true;
  if (process.env.NODE_ENV === 'production') return false;
  try {
    const actual = new URL(`${req.protocol}://${req.get('host')}`);
    const supplied = new URL(origin);
    if (supplied.origin === actual.origin) return true;
    const localHosts = new Set(['localhost', '127.0.0.1', '::1']);
    return localHosts.has(supplied.hostname) && localHosts.has(actual.hostname) && supplied.port === actual.port && supplied.protocol === actual.protocol;
  } catch { return false; }
}

function safeReturnTo(value: unknown) {
  const candidate = String(value || '/connected-accounts');
  return candidate.startsWith('/') && !candidate.startsWith('//') ? candidate : '/connected-accounts';
}

function isoDateTimestamp(value: string, endOfDay = false) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return Number.NaN;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const timestamp = Date.UTC(year, month - 1, day, endOfDay ? 23 : 0, endOfDay ? 59 : 0, endOfDay ? 59 : 0, endOfDay ? 999 : 0);
  const parsed = new Date(timestamp);
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day ? timestamp : Number.NaN;
}

function redirectUri(provider: SocialProvider, req: Request) {
  return provider.credentials()?.redirectUri || `${applicationOrigin(req)}/api/integrations/oauth/callback`;
}

function providerContext(provider: SocialProvider, fetcher: FetchLike) {
  const credentials = provider.credentials();
  if (!credentials || !validRedirectUri(credentials.redirectUri)) throw new SocialIntegrationError('SOCIAL_CONFIGURATION_REQUIRED', 503, 'A integração precisa ser configurada pelo administrador.');
  return { credentials, fetch: fetcher, signal: AbortSignal.timeout(20_000) };
}

function validRedirectUri(value: string) {
  try {
    const url = new URL(value);
    if (url.pathname !== '/api/integrations/oauth/callback') return false;
    if (process.env.NODE_ENV === 'production') return url.protocol === 'https:';
    return url.protocol === 'https:' || (url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname));
  } catch { return false; }
}

function statusFor(error: unknown): StoredSocialConnection['status'] {
  const failure = publicIntegrationError(error);
  if (failure.code === 'SOCIAL_AUTHORIZATION_REVOKED') return 'authorization_revoked';
  if (failure.code === 'SOCIAL_PERMISSION_INSUFFICIENT') return 'permission_insufficient';
  return 'error';
}

function providerSummary(provider: SocialProvider, cipher: TokenCipher | null) {
  const credentials = provider.credentials();
  const missingConfiguration = [
    ...(!credentials ? provider.requiredEnvironment.filter(key => !process.env[key]?.trim()) : []),
    ...(!cipher ? ['SOCIAL_TOKEN_ENCRYPTION_KEY'] : []),
  ];
  if (credentials && !validRedirectUri(credentials.redirectUri)) missingConfiguration.push('HTTPS_REDIRECT_URI');
  const configured = Boolean(credentials && validRedirectUri(credentials.redirectUri) && cipher);
  return { id: provider.id, name: provider.label, configured, status: configured ? 'ready' : 'configuration_required', missingConfiguration };
}

export async function readKlicConnections(workspaceId: string, accountType: 'personal' | 'company', clientId: string | null = null) {
  const providers = socialProviderRegistry();
  const owner = { ownerType: accountType === 'personal' ? 'personal' as const : 'workspace' as const, ownerId: workspaceId };
  const connections = readableRepository ? await readableRepository.list(owner) : [];
  let cipher: TokenCipher | null = null;
  try { cipher = createTokenCipherFromEnvironment(); } catch { cipher = null; }
  return socialProviderIds.flatMap(provider => {
    const accounts = connections.filter(connection => connection.provider === provider && (!clientId || connection.clientId === clientId));
    const configured = providerSummary(providers.get(provider)!, cipher).configured;
    if (!accounts.length) return clientId ? [] : [{ workspaceId, clientId: null, platform: provider, connected: false, configured }];
    return accounts.slice(0, 12).map(connection => ({
      workspaceId, clientId, id: connection.id, socialAccountId: connection.id, platform: provider,
      accountName: connection.displayName, accountHandle: connection.username || null,
      assignedClientId: connection.clientId || null, status: connection.status,
      connected: connection.status === 'connected' && (!connection.tokenExpiresAt || Date.parse(connection.tokenExpiresAt) > Date.now()),
      tokenExpiring: Boolean(connection.tokenExpiresAt && Date.parse(connection.tokenExpiresAt) <= Date.now() + 24 * 60 * 60_000), configured,
    }));
  });
}

export async function readKlicAnalytics(workspaceId: string, accountType: 'personal' | 'company', clientId: string | null = null) {
  if (!readableRepository) return [];
  const owner = { ownerType: accountType === 'personal' ? 'personal' as const : 'workspace' as const, ownerId: workspaceId };
  const snapshots = await readableRepository.listAnalyticsSnapshots(owner);
  const connections = await readableRepository.list(owner);
  const assigned = new Map(connections.map(connection => [connection.id, connection.clientId]));
  const latest = new Map<string, typeof snapshots[number]>();
  for (const snapshot of snapshots.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))) {
    if ((!clientId || assigned.get(snapshot.connectionId) === clientId) && !latest.has(snapshot.connectionId)) latest.set(snapshot.connectionId, snapshot);
  }
  return [...latest.values()].slice(0, 12).flatMap(snapshot => Object.entries(snapshot.metrics).map(([metric, current]) => ({
    workspaceId, clientId, id: `${snapshot.connectionId}:${metric}`, socialAccountId: snapshot.connectionId,
    platform: snapshot.provider, metric, current, start: snapshot.from, end: snapshot.to, dataStatus: 'available',
    updatedAt: snapshot.updatedAt,
  })));
}

export async function readKlicScheduledPublications(workspaceId: string, accountType: 'personal' | 'company', clientId: string | null = null) {
  if (!readableRepository) return [];
  const owner = { ownerType: accountType === 'personal' ? 'personal' as const : 'workspace' as const, ownerId: workspaceId };
  const jobs = await readableRepository.listScheduled(owner);
  return jobs.filter(job => !clientId || job.clientId === clientId).slice(0, 80).map(job => ({
    workspaceId, clientId, assignedClientId: job.clientId || null, id: job.contentId, publicationId: job.id,
    socialAccountId: job.connectionId, platform: job.provider || null, title: job.title || 'Conteúdo agendado',
    copy: (job.request.text || '').slice(0, 500), status: job.status, scheduledAt: job.scheduledAt,
    providerPostId: job.providerPostId || null,
  }));
}

export function createIntegrationsRouter(options: RouterOptions = {}) {
  const providers = socialProviderRegistry();
  const dataFile = options.dataFile === undefined
    ? process.env.NODE_ENV === 'test' ? null : process.env.CLICKO_SOCIAL_DATA_FILE || path.resolve('.clicko-data', 'social-integrations.json')
    : options.dataFile;
  const storageDriver = String(process.env.SOCIAL_STORAGE_DRIVER || (process.env.NODE_ENV === 'production' ? 'postgres' : 'json')).toLowerCase();
  if (process.env.NODE_ENV === 'production' && !options.repository && storageDriver !== 'postgres' && process.env.SOCIAL_ALLOW_SINGLE_INSTANCE_STORE !== 'true') {
    throw new Error('SOCIAL_PRODUCTION_REPOSITORY_REQUIRED');
  }
  const repository: SocialIntegrationRepositoryPort = options.repository || (storageDriver === 'postgres'
    ? new PostgresSocialIntegrationRepository(String(process.env.SOCIAL_DATABASE_URL || ''), process.env.SOCIAL_DATABASE_SSL !== 'disable')
    : new SocialIntegrationRepository(validateDataFile(dataFile)));
  readableRepository = repository;
  const fetcher = options.fetch || fetch;
  const now = options.now || Date.now;
  let cipher: TokenCipher | null = null;
  try { cipher = createTokenCipherFromEnvironment(); } catch { cipher = null; }
  const router = Router();

  const requireCipher = () => {
    if (!cipher) throw new SocialIntegrationError('SOCIAL_CONFIGURATION_REQUIRED', 503, 'A criptografia das integrações sociais precisa ser configurada pelo administrador.');
    return cipher;
  };
  const getProvider = (req: Request) => providers.get(providerId(req))!;
  const respondError = (res: Response, error: unknown, requestId = randomUUID()) => {
    const failure = publicIntegrationError(error);
    console.warn('SOCIAL_INTEGRATION_EVENT', { requestId, code: failure.code, status: failure.status });
    return res.status(failure.status).json({ error: failure.publicMessage, code: failure.code, requestId });
  };

  async function refreshConnection(owner: SocialOwner, provider: SocialProvider, connection: StoredSocialConnection, force = false) {
    const expiresSoon = connection.tokenExpiresAt && Date.parse(connection.tokenExpiresAt) <= now() + 60_000;
    if (!force && !expiresSoon) return connection;
    if (!connection.refreshTokenEncrypted || !provider.refresh) {
      await repository.update(connection.id, owner, { status: 'expired', lastError: 'Reconexão necessária.' });
      throw new SocialIntegrationError('SOCIAL_AUTHORIZATION_EXPIRED', 401, 'O token expirou. Reconecte a conta.');
    }
    try {
      const encrypted = requireCipher();
      const currentRefreshToken = encrypted.decrypt(connection.refreshTokenEncrypted);
      const token = await provider.refresh(providerContext(provider, fetcher), currentRefreshToken);
      const scopes = token.scopes.length ? token.scopes : connection.scopes;
      return (await repository.update(connection.id, owner, {
        accessTokenEncrypted: encrypted.encrypt(token.accessToken),
        refreshTokenEncrypted: encrypted.encrypt(token.refreshToken || currentRefreshToken),
        tokenExpiresAt: token.expiresAt,
        refreshTokenExpiresAt: token.refreshTokenExpiresAt || connection.refreshTokenExpiresAt,
        scopes,
        capabilities: provider.capabilities(scopes),
        status: 'connected',
        lastError: undefined,
      }))!;
    } catch (error) {
      await repository.update(connection.id, owner, { status: statusFor(error), lastError: publicIntegrationError(error).publicMessage });
      throw error;
    }
  }

  async function validateDestination(provider: SocialProvider, connection: StoredSocialConnection, request: SocialPublishRequest) {
    if (!request.destinationId) return;
    if (provider.resources) {
      const token = { accessToken: requireCipher().decrypt(connection.accessTokenEncrypted), scopes: connection.scopes };
      const resources = await provider.resources(providerContext(provider, fetcher), token, connection);
      if (resources.some(resource => resource.id === request.destinationId)) return;
    } else if (request.destinationId === connection.providerAccountId) return;
    throw new SocialIntegrationError('SOCIAL_RESOURCE_INVALID', 403, 'O destino selecionado não pertence a esta conexão.');
  }

  let schedulerBusy = false;
  scheduledRunner = async () => {
    if (schedulerBusy) return;
    schedulerBusy = true;
    try {
      const stale = await repository.recoverStalePublishing(new Date(now() - 10 * 60_000).toISOString(), new Date(now()).toISOString());
      for (const job of stale) console.warn('SOCIAL_SCHEDULE_EVENT', {
        publicationId: job.id, socialAccountId: job.connectionId, workspaceId: job.ownerId,
        status: 'indeterminate', code: 'SOCIAL_PUBLICATION_INDETERMINATE',
      });
      const jobs = await repository.claimDue(new Date(now()).toISOString(), 10);
      for (const job of jobs) {
        const owner = { ownerType: job.ownerType, ownerId: job.ownerId };
        let claimed = false;
        try {
          const connection = (await repository.list(owner)).find(item => item.id === job.connectionId);
          if (!connection || connection.status !== 'connected') throw new SocialIntegrationError('ACCOUNT_DISCONNECTED', 409, 'A conta social não está conectada.');
          if (job.clientId && (connection.clientId !== job.clientId || !workspaceOwnsClient(job.ownerId, job.clientId))) {
            throw new SocialIntegrationError('SOCIAL_CLIENT_MISMATCH', 409, 'A conta social não pertence ao cliente selecionado.');
          }
          const approval = publicationApprovalStage(job.ownerId, job.contentId);
          if ((job.approvalId && approval?.id !== job.approvalId) || (approval && approval.stage !== 'approved')) {
            throw new SocialIntegrationError('APPROVAL_REQUIRED', 409, 'A publicação ainda não foi aprovada.');
          }
          const provider = providers.get(connection.provider)!;
          if (!provider.publish) throw new SocialIntegrationError('SOCIAL_PUBLISHING_NOT_IMPLEMENTED', 409, 'Esta rede não oferece publicação nesta configuração.');
          const active = await refreshConnection(owner, provider, connection);
          validatePublishRequest(job.request, active.capabilities, now());
          validateScheduledProviderRequest(active.provider, job.request);
          await validateDestination(provider, active, job.request);
          const key = job.id;
          const requestHash = sha256(JSON.stringify(job.request));
          const existing = await repository.publication(owner, key);
          if (existing) {
            if (existing.providerPostId) {
              await repository.updateScheduled(owner, job.id, { status: existing.status === 'published' ? 'published' : 'processing', providerPostId: existing.providerPostId }, new Date(now()).toISOString());
              continue;
            }
            throw new SocialIntegrationError('SOCIAL_PUBLICATION_INDETERMINATE', 409, 'O resultado anterior desta publicação é incerto.');
          }
          await repository.claimPublication(owner, { connectionId: active.id, idempotencyKey: key, requestHash }, new Date(now()).toISOString());
          claimed = true;
          const token = { accessToken: requireCipher().decrypt(active.accessTokenEncrypted), scopes: active.scopes };
          const result = await provider.publish(providerContext(provider, fetcher), token, active, job.request);
          await repository.updatePublication(owner, (await repository.publication(owner, key))!.id, { status: result.status, providerPostId: result.providerPostId }, new Date(now()).toISOString());
          await repository.updateScheduled(owner, job.id, { status: result.status, providerPostId: result.providerPostId }, new Date(now()).toISOString());
          console.info('SOCIAL_SCHEDULE_EVENT', { publicationId: job.id, socialAccountId: job.connectionId, workspaceId: job.ownerId, provider: connection.provider, status: result.status });
        } catch (error) {
          const failure = publicIntegrationError(error);
          const operation = claimed ? await repository.publication(owner, job.id) : undefined;
          if (operation?.providerPostId) {
            await repository.updateScheduled(owner, job.id, { status: operation.status === 'published' ? 'published' : 'processing', providerPostId: operation.providerPostId }, new Date(now()).toISOString());
            console.warn('SOCIAL_SCHEDULE_EVENT', { publicationId: job.id, socialAccountId: job.connectionId, workspaceId: job.ownerId, status: 'provider_confirmed_store_recovered' });
            continue;
          }
          await repository.updateScheduled(owner, job.id, { status: claimed ? 'indeterminate' : 'failed', errorCode: failure.code }, new Date(now()).toISOString());
          if (claimed) {
            if (operation) await repository.updatePublication(owner, operation.id, { status: 'indeterminate', errorCode: failure.code }, new Date(now()).toISOString());
          }
          console.warn('SOCIAL_SCHEDULE_EVENT', { publicationId: job.id, socialAccountId: job.connectionId, workspaceId: job.ownerId, status: claimed ? 'indeterminate' : 'failed', code: failure.code });
        }
      }
    } catch (error) {
      console.warn('SOCIAL_SCHEDULE_LOOP', { code: publicIntegrationError(error).code });
    } finally { schedulerBusy = false; }
  };
  const intervalMs = options.schedulerIntervalMs ?? (process.env.NODE_ENV === 'test' ? 0 : 15_000);
  if (intervalMs > 0) {
    if (scheduledTimer) clearInterval(scheduledTimer);
    scheduledTimer = setInterval(() => { void scheduledRunner?.(); }, intervalMs);
    scheduledTimer.unref();
  }

  async function storeAccount(input: StoredOAuthSelectionAccount, state: { ownerType: SocialOwner['ownerType']; ownerId: string; actorId: string; provider: SocialProviderId }, timestamp: string) {
    return repository.upsert({
      ownerType: state.ownerType, ownerId: state.ownerId, actorId: state.actorId, provider: state.provider,
      providerAccountId: input.providerAccountId, accountType: input.accountType, username: input.username,
      displayName: input.displayName, avatarUrl: input.avatarUrl, accessTokenEncrypted: input.accessTokenEncrypted,
      refreshTokenEncrypted: input.refreshTokenEncrypted, tokenExpiresAt: input.tokenExpiresAt,
      refreshTokenExpiresAt: input.refreshTokenExpiresAt, scopes: input.scopes, status: 'connected',
      capabilities: input.capabilities, lastSyncedAt: timestamp, lastError: undefined,
      providerMetadata: input.providerMetadata,
    }, timestamp);
  }

  router.get('/oauth/callback', async (req, res) => {
    const requestId = randomUUID();
    const stateValue = String(req.query.state || '');
    if (!/^[A-Za-z0-9_-]{32,256}$/.test(stateValue)) return res.status(400).send('Autorização expirada ou inválida. Volte à Clicko e tente novamente.');
    const stateHash = sha256(stateValue);
    const pendingState = await repository.findState(stateHash, now());
    const browserBinding = cookieValue(req, OAUTH_BINDING_COOKIE);
    if (!pendingState || !browserBinding || sha256(browserBinding) !== pendingState.browserBindingHash) {
      return res.status(400).send('Autorização expirada ou inválida. Volte à Clicko e tente novamente.');
    }
    const state = await repository.consumeState(stateHash, now());
    if (!state) return res.status(400).send('Autorização expirada ou inválida. Volte à Clicko e tente novamente.');
    res.setHeader('Set-Cookie', clearOauthBindingCookie());
    const destination = new URL(state.returnTo, applicationOrigin(req));
    destination.searchParams.set('integration', state.provider);
    if (req.query.error) {
      await repository.audit({ ownerType: state.ownerType, ownerId: state.ownerId, actorId: state.actorId, provider: state.provider, action: 'oauth_cancelled', outcome: 'failure', code: String(req.query.error).slice(0, 80) }, new Date(now()).toISOString());
      destination.searchParams.set('status', 'error');
      destination.searchParams.set('reason', 'authorization_denied');
      return res.redirect(destination.toString());
    }
    try {
      const provider = providers.get(state.provider)!;
      const encrypted = requireCipher();
      const code = String(req.query.code || '');
      if (!code || code.length > 4096) throw new SocialIntegrationError('SOCIAL_CALLBACK_INCOMPLETE', 400, 'A resposta de autorização está incompleta.');
      const context = providerContext(provider, fetcher);
      const exchanged = await provider.exchangeCode(context, { code, redirectUri: state.redirectUri, codeVerifier: state.codeVerifier });
      const scopes = provider.grantedScopes ? await provider.grantedScopes(context, exchanged) : exchanged.scopes;
      const token = { ...exchanged, scopes };
      const accounts = await provider.accounts(context, token);
      if (!accounts.length) throw new SocialIntegrationError('SOCIAL_PERMISSION_INSUFFICIENT', 403, 'Nenhuma conta compatível foi disponibilizada pela plataforma.');
      const timestamp = new Date(now()).toISOString();
      const pendingAccounts: StoredOAuthSelectionAccount[] = accounts.map(account => ({
        providerAccountId: account.id, accountType: account.accountType, username: account.username,
        displayName: account.displayName, avatarUrl: account.avatarUrl,
        accessTokenEncrypted: encrypted.encrypt(account.accessToken || token.accessToken),
        refreshTokenEncrypted: token.refreshToken ? encrypted.encrypt(token.refreshToken) : undefined,
        tokenExpiresAt: token.expiresAt, refreshTokenExpiresAt: token.refreshTokenExpiresAt,
        scopes, capabilities: provider.capabilities(scopes), providerMetadata: account.metadata || {},
      }));
      if (pendingAccounts.length > 1) {
        const selectionToken = randomBytes(32).toString('base64url');
        await repository.addSelection({
          tokenHash: sha256(selectionToken), provider: state.provider, ownerType: state.ownerType,
          ownerId: state.ownerId, actorId: state.actorId, accounts: pendingAccounts,
          expiresAt: new Date(now() + 10 * 60_000).toISOString(), createdAt: timestamp,
        }, now());
        await repository.audit({ ownerType: state.ownerType, ownerId: state.ownerId, actorId: state.actorId, provider: state.provider, action: 'resources_discovered', outcome: 'success' }, timestamp);
        destination.searchParams.set('status', 'selection_required');
        destination.searchParams.set('selection', selectionToken);
        destination.searchParams.set('count', String(pendingAccounts.length));
        return res.redirect(destination.toString());
      }
      const connection = await storeAccount(pendingAccounts[0], state, timestamp);
      await repository.audit({ ownerType: state.ownerType, ownerId: state.ownerId, actorId: state.actorId, provider: state.provider, action: 'connected', outcome: 'success', connectionIds: [connection.id] }, timestamp);
      destination.searchParams.set('status', 'connected');
      destination.searchParams.set('count', String(accounts.length));
      return res.redirect(destination.toString());
    } catch (error) {
      const failure = publicIntegrationError(error);
      await repository.audit({ ownerType: state.ownerType, ownerId: state.ownerId, actorId: state.actorId, provider: state.provider, action: 'oauth_failed', outcome: 'failure', code: failure.code }, new Date(now()).toISOString());
      console.warn('SOCIAL_INTEGRATION_EVENT', { requestId, provider: state.provider, code: failure.code, status: failure.status });
      destination.searchParams.set('status', 'error');
      destination.searchParams.set('reason', callbackReason(error));
      return res.redirect(destination.toString());
    }
  });

  router.use(authenticate);

  router.use((req: AuthenticatedRequest, res, next) => {
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) return next();
    const origin = req.header('origin');
    const fetchSite = req.header('sec-fetch-site');
    if ((origin && !trustedMutationOrigin(req, origin)) || fetchSite === 'cross-site') {
      return respondError(res, new SocialIntegrationError('SOCIAL_ORIGIN_REJECTED', 403, 'A origem da solicitação não é confiável.'));
    }
    return next();
  });

  router.get('/oauth/selections/:selectionToken', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const token = String(req.params.selectionToken || '');
      if (!/^[A-Za-z0-9_-]{32,256}$/.test(token)) throw new SocialIntegrationError('SOCIAL_SELECTION_INVALID', 400, 'A seleção de contas expirou ou é inválida.');
      const selection = await repository.selection(sha256(token), ownerFor(req), req.auth!.user.id, now());
      if (!selection) throw new SocialIntegrationError('SOCIAL_SELECTION_INVALID', 404, 'A seleção de contas expirou ou é inválida.');
      res.setHeader('Cache-Control', 'private, no-store');
      return res.json({ provider: selection.provider, accounts: selection.accounts.map(({ accessTokenEncrypted: _access, refreshTokenEncrypted: _refresh, providerMetadata: _metadata, ...account }) => account), expiresAt: selection.expiresAt });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/oauth/selections/:selectionToken', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const token = String(req.params.selectionToken || '');
      if (!/^[A-Za-z0-9_-]{32,256}$/.test(token)) throw new SocialIntegrationError('SOCIAL_SELECTION_INVALID', 400, 'A seleção de contas expirou ou é inválida.');
      const owner = ownerFor(req);
      const pending = await repository.selection(sha256(token), owner, req.auth!.user.id, now());
      if (!pending) throw new SocialIntegrationError('SOCIAL_SELECTION_INVALID', 404, 'A seleção de contas expirou ou é inválida.');
      const selectedIds = Array.isArray(req.body?.providerAccountIds) ? [...new Set(req.body.providerAccountIds.filter((id: unknown): id is string => typeof id === 'string'))] : [];
      if (!selectedIds.length || selectedIds.some(id => !pending.accounts.some(account => account.providerAccountId === id))) {
        throw new SocialIntegrationError('SOCIAL_SELECTION_INVALID', 400, 'Escolha ao menos uma conta disponibilizada pelo provedor.');
      }
      const selection = await repository.consumeSelection(sha256(token), owner, req.auth!.user.id, now());
      if (!selection) throw new SocialIntegrationError('SOCIAL_SELECTION_INVALID', 409, 'Esta seleção já foi concluída.');
      const timestamp = new Date(now()).toISOString();
      const connections = await Promise.all(selection.accounts.filter(account => selectedIds.includes(account.providerAccountId)).map(account => storeAccount(account, selection, timestamp)));
      await repository.audit({ ...owner, actorId: req.auth!.user.id, provider: selection.provider, action: 'connected', outcome: 'success', connectionIds: connections.map(connection => connection.id) }, timestamp);
      return res.status(201).json({ provider: selection.provider, connections: connections.map(connection => publicConnection(connection, now())) });
    } catch (error) { return respondError(res, error); }
  });

  router.get('/providers', permissionOnly('connections.read'), (_req, res) => {
    res.setHeader('Cache-Control', 'private, no-store');
    return res.json({ providers: [...providers.values()].map(provider => providerSummary(provider, cipher)) });
  });

  router.get('/connections', permissionOnly('connections.read'), async (req: AuthenticatedRequest, res) => {
    res.setHeader('Cache-Control', 'private, no-store');
    const owner = ownerFor(req);
    const connections = (await repository.list(owner)).filter(connection => {
      try { assertSocialScope(req, { clientId: connection.clientId, connectionId: connection.id }); return true; } catch { return false; }
    });
    return res.json({ connections: connections.map(connection => publicConnection(connection, now())), providers: [...providers.values()].map(provider => providerSummary(provider, cipher)) });
  });

  router.get('/publications/scheduled', permissionOnly('connections.read'), async (req: AuthenticatedRequest, res) => {
    try {
      res.setHeader('Cache-Control', 'private, no-store');
      const publications = (await repository.listScheduled(ownerFor(req))).filter(job => {
        try { assertSocialScope(req, { clientId: job.clientId, connectionId: job.connectionId }); return true; } catch { return false; }
      });
      return res.json({ publications });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/publications/schedule', permissionOnly('content.publish'), async (req: AuthenticatedRequest, res) => {
    try {
      const owner = ownerFor(req);
      const contentId = String(req.body?.contentId || '').trim();
      const connectionId = String(req.body?.connectionId || '').trim();
      const clientId = req.body?.clientId == null ? undefined : String(req.body.clientId);
      const scheduledAt = String(req.body?.scheduledAt || '');
      const scheduleTime = Date.parse(scheduledAt);
      if (!/^[A-Za-z0-9_-]{3,120}$/.test(contentId) || !connectionId) throw new SocialIntegrationError('SOCIAL_SCHEDULE_INVALID', 400, 'Informe o conteúdo e a conta social.');
      if (!Number.isFinite(scheduleTime) || scheduleTime <= now() || scheduleTime > now() + 366 * 24 * 60 * 60_000) {
        throw new SocialIntegrationError('SOCIAL_SCHEDULE_INVALID', 400, 'Escolha uma data futura de até um ano.');
      }
      const connection = (await repository.list(owner)).find(item => item.id === connectionId);
      if (!connection || connection.status !== 'connected') throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 409, 'A conta social não está conectada neste ambiente.');
      assertSocialScope(req, { clientId: clientId || connection.clientId, connectionId });
      if ((connection.clientId || clientId) && (!clientId || !workspaceOwnsClient(req.auth!.workspaceId, clientId) || connection.clientId !== clientId)) {
        throw new SocialIntegrationError('SOCIAL_CLIENT_MISMATCH', 409, 'A conta social não pertence ao cliente selecionado.');
      }
      const provider = providers.get(connection.provider)!;
      if (!provider.publish || !effectiveCapabilities(connection).canSchedule) throw new SocialIntegrationError('SOCIAL_SCHEDULE_UNAVAILABLE', 409, 'Esta conta não oferece publicação automática com as permissões atuais.');
      if (req.body?.request?.scheduledAt) throw new SocialIntegrationError('SOCIAL_SCHEDULE_INVALID', 400, 'Informe o horário somente no campo de agendamento da Clicko.');
      const request = validatePublishRequest(req.body?.request, connection.capabilities, now());
      validateScheduledProviderRequest(connection.provider, request);
      await validateDestination(provider, connection, request);
      if (!request.text?.trim() && !request.mediaUrls?.length && !request.providerAssetIds?.length) {
        throw new SocialIntegrationError('SOCIAL_CONTENT_INVALID', 422, 'Informe texto ou mídia válida para a publicação.');
      }
      const approval = publicationApprovalStage(req.auth!.workspaceId, contentId);
      if (approval && approval.stage !== 'approved') throw new SocialIntegrationError('APPROVAL_REQUIRED', 409, 'Aprove o conteúdo antes de confirmar a publicação automática.');
      const input: Omit<StoredScheduledPublication, 'id' | 'ownerType' | 'ownerId' | 'status' | 'createdAt' | 'updatedAt'> = {
        clientId, contentId, connectionId, approvalId: approval?.id, request, scheduledAt: new Date(scheduleTime).toISOString(),
        provider: connection.provider, title: String(req.body?.title || '').trim().slice(0, 160) || undefined,
      };
      const existing = (await repository.listScheduled(owner)).find(item => item.contentId === contentId && item.connectionId === connectionId);
      if (existing && existing.status !== 'scheduled') {
        throw new SocialIntegrationError('SOCIAL_SCHEDULE_CONFLICT', 409, 'Este conteúdo já possui um histórico de publicação nesta conta. Crie um novo conteúdo para agendar novamente.');
      }
      if (existing && (existing.scheduledAt !== input.scheduledAt || JSON.stringify(existing.request) !== JSON.stringify(request))) {
        throw new SocialIntegrationError('SOCIAL_SCHEDULE_CONFLICT', 409, 'Este conteúdo já possui um agendamento diferente para esta conta.');
      }
      const job = await repository.schedule(owner, input, new Date(now()).toISOString());
      if (!job) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 409, 'A conta social não está mais disponível.');
      if (job.status !== 'scheduled' || job.scheduledAt !== input.scheduledAt || JSON.stringify(job.request) !== JSON.stringify(request)) {
        throw new SocialIntegrationError('SOCIAL_SCHEDULE_CONFLICT', 409, 'Este conteúdo já possui um agendamento diferente para esta conta.');
      }
      console.info('SOCIAL_SCHEDULE_EVENT', { publicationId: job.id, socialAccountId: connection.id, workspaceId: owner.ownerId, provider: connection.provider, status: job.status });
      return res.status(existing ? 200 : 201).json({ publication: job, replayed: Boolean(existing) });
    } catch (error) { return respondError(res, error); }
  });

  router.patch('/publications/scheduled/:id', permissionOnly('content.publish'), async (req: AuthenticatedRequest, res) => {
    try {
      const owner = ownerFor(req);
      const job = (await repository.listScheduled(owner)).find(item => item.id === req.params.id);
      if (!job) throw new SocialIntegrationError('SOCIAL_SCHEDULE_CONFLICT', 404, 'Agendamento não encontrado neste ambiente.');
      assertSocialScope(req, { clientId: job.clientId, connectionId: job.connectionId });
      const scheduledAt = String(req.body?.scheduledAt || '');
      const scheduleTime = Date.parse(scheduledAt);
      if (!Number.isFinite(scheduleTime) || scheduleTime <= now() || scheduleTime > now() + 366 * 24 * 60 * 60_000) {
        throw new SocialIntegrationError('SOCIAL_SCHEDULE_INVALID', 400, 'Escolha uma data futura de até um ano.');
      }
      const updated = await repository.rescheduleScheduled(owner, job.id, new Date(scheduleTime).toISOString(), new Date(now()).toISOString());
      if (!updated) throw new SocialIntegrationError('SOCIAL_SCHEDULE_CONFLICT', 409, 'A publicação já começou ou foi concluída. O agendamento não foi alterado.');
      return res.json({ publication: updated });
    } catch (error) { return respondError(res, error); }
  });

  router.delete('/publications/scheduled/:id', permissionOnly('content.publish'), async (req: AuthenticatedRequest, res) => {
    try {
      const owner = ownerFor(req);
      const job = (await repository.listScheduled(owner)).find(item => item.id === req.params.id);
      if (!job) throw new SocialIntegrationError('SOCIAL_SCHEDULE_CONFLICT', 404, 'Agendamento não encontrado neste ambiente.');
      assertSocialScope(req, { clientId: job.clientId, connectionId: job.connectionId });
      const cancelled = await repository.cancelScheduled(owner, req.params.id, new Date(now()).toISOString());
      if (!cancelled) throw new SocialIntegrationError('SOCIAL_SCHEDULE_CONFLICT', 409, 'Este agendamento não pode mais ser cancelado.');
      return res.json({ publication: cancelled });
    } catch (error) { return respondError(res, error); }
  });

  router.patch('/connections/:connectionId/client', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const owner = ownerFor(req);
      const clientId = req.body?.clientId;
      if (clientId !== null && (typeof clientId !== 'string' || !workspaceOwnsClient(req.auth!.workspaceId, clientId))) {
        throw new SocialIntegrationError('SOCIAL_CLIENT_INVALID', 400, 'Selecione um cliente deste ambiente.');
      }
      const current = (await repository.list(owner)).find(item => item.id === req.params.connectionId);
      if (!current) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 404, 'A conta social não foi encontrada neste ambiente.');
      assertSocialScope(req, { clientId: clientId || current.clientId, connectionId: current.id });
      const connection = await repository.update(req.params.connectionId, owner, { clientId: clientId || undefined });
      if (!connection) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 404, 'A conta social não foi encontrada neste ambiente.');
      await repository.audit({ ...owner, actorId: req.auth!.user.id, provider: connection.provider, action: 'client_bound', outcome: 'success', connectionIds: [connection.id] }, new Date(now()).toISOString());
      return res.json({ connection: publicConnection(connection, now()) });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/connections/validate', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const owner = ownerFor(req);
      const clientId = req.body?.clientId;
      const ids = req.body?.connectionIds;
      if (!Array.isArray(ids) || !ids.length || ids.length > 8 || ids.some((id: unknown) => typeof id !== 'string')) {
        throw new SocialIntegrationError('SOCIAL_SELECTION_INVALID', 400, 'Selecione as contas sociais da publicação.');
      }
      if (clientId != null && (typeof clientId !== 'string' || !workspaceOwnsClient(req.auth!.workspaceId, clientId))) {
        throw new SocialIntegrationError('SOCIAL_CLIENT_INVALID', 400, 'Selecione um cliente deste ambiente.');
      }
      const connections = await repository.list(owner);
      const selected = ids.map((id: string) => connections.find(connection => connection.id === id));
      if (selected.some((connection: StoredSocialConnection | undefined) => !connection || connection.status !== 'connected')) {
        throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 409, 'Uma conta social está desconectada ou não pertence a este ambiente.');
      }
      if (selected.some((connection: StoredSocialConnection | undefined) => (connection?.clientId || clientId) && connection?.clientId !== clientId)) {
        throw new SocialIntegrationError('SOCIAL_CLIENT_MISMATCH', 409, 'Esta conta social está vinculada a outro cliente.');
      }
      selected.forEach(connection => assertSocialScope(req, { clientId: clientId || connection?.clientId, connectionId: connection?.id }));
      if (req.body?.requireScheduling === true && selected.some((connection: StoredSocialConnection | undefined) => !effectiveCapabilities(connection!).canSchedule)) {
        throw new SocialIntegrationError('SOCIAL_SCHEDULE_UNAVAILABLE', 409, 'Uma das contas não oferece publicação automática com as permissões atuais.');
      }
      return res.json({ valid: true, connectionIds: ids });
    } catch (error) { return respondError(res, error); }
  });

  router.get('/analytics/snapshots', permissionOnly('analytics.read'), async (req: AuthenticatedRequest, res) => {
    try {
      res.setHeader('Cache-Control', 'private, no-store');
      const owner = ownerFor(req);
      const connections = await repository.list(owner);
      const byId = new Map(connections.map(connection => [connection.id, connection]));
      const snapshots = (await repository.listAnalyticsSnapshots(owner)).filter(snapshot => {
        const connection = byId.get(snapshot.connectionId);
        try { if (!connection) return false; assertSocialScope(req, { clientId: connection.clientId, connectionId: connection.id }); return true; } catch { return false; }
      });
      return res.json({ snapshots });
    } catch (error) { return respondError(res, error); }
  });

  router.get('/connections/:connectionId/analytics', permissionOnly('analytics.read'), async (req: AuthenticatedRequest, res) => {
    try {
      const owner = ownerFor(req);
      const stored = (await repository.list(owner)).find(item => item.id === req.params.connectionId);
      if (!stored) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 404, 'A conta social não foi encontrada neste ambiente.');
      assertSocialScope(req, { clientId: stored.clientId, connectionId: stored.id });
      const provider = providers.get(stored.provider)!;
      if (!stored.capabilities.canReadAnalytics) throw new SocialIntegrationError('SOCIAL_PERMISSION_INSUFFICIENT', 403, 'As permissões concedidas não liberam Analytics para esta conexão.');
      if (!provider.analytics) throw new SocialIntegrationError('SOCIAL_ANALYTICS_UNAVAILABLE', 409, 'O coletor oficial desta rede ainda não está disponível nesta configuração.');
      const to = typeof req.query.to === 'string' ? req.query.to : new Date(now()).toISOString().slice(0, 10);
      const from = typeof req.query.from === 'string' ? req.query.from : new Date(now() - 30 * 24 * 60 * 60_000).toISOString().slice(0, 10);
      const fromTime = isoDateTimestamp(from);
      const toTime = isoDateTimestamp(to, true);
      if (!Number.isFinite(fromTime) || !Number.isFinite(toTime) || fromTime > toTime || toTime - fromTime > 366 * 24 * 60 * 60_000) {
        throw new SocialIntegrationError('SOCIAL_ANALYTICS_RANGE_INVALID', 400, 'Informe um período válido de até 366 dias.');
      }
      const connection = await refreshConnection(owner, provider, stored);
      const token = { accessToken: requireCipher().decrypt(connection.accessTokenEncrypted), scopes: connection.scopes };
      const analytics = await provider.analytics(providerContext(provider, fetcher), token, connection, {
        from, to, cursor: typeof req.query.cursor === 'string' ? req.query.cursor : undefined,
      });
      await repository.upsertAnalyticsSnapshot(owner, { connectionId: connection.id, provider: connection.provider,
        from, to, metrics: analytics.metrics, updatedAt: new Date(now()).toISOString() });
      await repository.update(connection.id, owner, { lastSyncedAt: new Date(now()).toISOString(), status: 'connected', lastError: undefined });
      res.setHeader('Cache-Control', 'private, no-store');
      return res.json({ source: 'provider-api', dataStatus: 'available', connectionId: connection.id, provider: connection.provider, analytics });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/connections/:connectionId/publish', permissionOnly('content.publish'), async (req: AuthenticatedRequest, res) => {
    const requestId = randomUUID();
    let claimedId: string | undefined;
    try {
      const owner = ownerFor(req);
      const idempotencyKey = String(req.get('Idempotency-Key') || '');
      if (!/^[A-Za-z0-9._:-]{16,128}$/.test(idempotencyKey)) throw new SocialIntegrationError('SOCIAL_IDEMPOTENCY_KEY_REQUIRED', 400, 'Informe uma chave de idempotência válida para publicar.');
      const stored = (await repository.list(owner)).find(item => item.id === req.params.connectionId);
      if (!stored) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 404, 'A conta social não foi encontrada neste ambiente.');
      assertSocialScope(req, { clientId: stored.clientId || req.body?.clientId, connectionId: stored.id });
      if ((stored.clientId || req.body?.clientId != null) && (typeof req.body?.clientId !== 'string' || stored.clientId !== req.body.clientId || !workspaceOwnsClient(req.auth!.workspaceId, req.body.clientId))) {
        throw new SocialIntegrationError('SOCIAL_CLIENT_MISMATCH', 409, 'A conta social não pertence ao cliente selecionado.');
      }
      const provider = providers.get(stored.provider)!;
      if (!provider.publish) throw new SocialIntegrationError('SOCIAL_PUBLISHING_NOT_IMPLEMENTED', 409, 'A publicação por esta rede ainda depende da configuração do fluxo oficial de mídia.');
      const input = req.body && typeof req.body === 'object' ? req.body : {};
      if (input.scheduledAt) throw new SocialIntegrationError('SOCIAL_SCHEDULE_INVALID', 400, 'Use o agendamento da Clicko para publicar no futuro.');
      const connection = await refreshConnection(owner, provider, stored);
      const request = validatePublishRequest(input, connection.capabilities, now());
      const token = { accessToken: requireCipher().decrypt(connection.accessTokenEncrypted), scopes: connection.scopes };
      await validateDestination(provider, connection, request);
      const requestHash = sha256(JSON.stringify(request));
      const existing = await repository.publication(owner, idempotencyKey);
      if (existing) {
        if (existing.requestHash !== requestHash) throw new SocialIntegrationError('SOCIAL_IDEMPOTENCY_CONFLICT', 409, 'Esta chave de publicação já foi usada com outro conteúdo.');
        if (existing.providerPostId && (existing.status === 'published' || existing.status === 'processing')) {
          return res.json({ status: existing.status, providerPostId: existing.providerPostId, replayed: true });
        }
        throw new SocialIntegrationError('SOCIAL_PUBLICATION_IN_PROGRESS', 409, 'Esta publicação já foi recebida e não será duplicada.');
      }
      const claimed = await repository.claimPublication(owner, { connectionId: connection.id, idempotencyKey, requestHash }, new Date(now()).toISOString());
      claimedId = claimed.id;
      const result = await provider.publish(providerContext(provider, fetcher), token, connection, request);
      await repository.updatePublication(owner, claimed.id, { status: result.status, providerPostId: result.providerPostId, errorCode: undefined }, new Date(now()).toISOString());
      return res.status(201).json({ ...result, replayed: false });
    } catch (error) {
      if (claimedId) {
        const owner = ownerFor(req);
        await repository.updatePublication(owner, claimedId, { status: 'indeterminate', errorCode: publicIntegrationError(error).code }, new Date(now()).toISOString());
      }
      return respondError(res, error, requestId);
    }
  });

  router.post('/:provider/authorize', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const provider = getProvider(req);
      requireCipher();
      const credentials = provider.credentials();
      if (!credentials) throw new SocialIntegrationError('SOCIAL_CONFIGURATION_REQUIRED', 503, 'A integração precisa ser configurada pelo administrador.');
      const owner = ownerFor(req);
      const state = randomBytes(32).toString('base64url');
      const browserBinding = randomBytes(32).toString('base64url');
      const codeVerifier = provider.usesPkce ? randomBytes(64).toString('base64url') : undefined;
      const callback = redirectUri(provider, req);
      await repository.addState({
        stateHash: sha256(state), browserBindingHash: sha256(browserBinding), provider: provider.id, ...owner, actorId: req.auth!.user.id,
        redirectUri: callback, returnTo: safeReturnTo(req.body?.returnTo), codeVerifier,
        expiresAt: new Date(now() + 10 * 60_000).toISOString(), createdAt: new Date(now()).toISOString(),
      });
      await repository.audit({ ...owner, actorId: req.auth!.user.id, provider: provider.id, action: 'oauth_started', outcome: 'success' }, new Date(now()).toISOString());
      res.setHeader('Set-Cookie', oauthBindingCookie(browserBinding, 10 * 60));
      return res.json({ authorizationUrl: provider.authorizationUrl({ credentials, redirectUri: callback, state, codeChallenge: codeVerifier ? sha256(codeVerifier) : undefined }) });
    } catch (error) { return respondError(res, error); }
  });

  router.get('/:provider/status', permissionOnly('connections.read'), async (req: AuthenticatedRequest, res) => {
    try {
      const provider = getProvider(req);
      const owner = ownerFor(req);
      const state = providerSummary(provider, cipher);
      const connections = await repository.list(owner, provider.id);
      const refreshed: StoredSocialConnection[] = [];
      for (const connection of connections) {
        try { refreshed.push(await refreshConnection(owner, provider, connection)); }
        catch { refreshed.push((await repository.list(owner, provider.id)).find(item => item.id === connection.id) || connection); }
      }
      return res.json({ ...state, connected: refreshed.some(item => item.status === 'connected'), expired: refreshed.some(item => item.status === 'expired'), connections: refreshed.map(connection => publicConnection(connection, now())) });
    } catch (error) { return respondError(res, error); }
  });

  router.get('/:provider/resources', permissionOnly('connections.read'), async (req: AuthenticatedRequest, res) => {
    try {
      const provider = getProvider(req);
      const owner = ownerFor(req);
      const connections = await repository.list(owner, provider.id);
      if (!connections.length) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 401, 'Esta plataforma precisa ser autorizada.');
      const active: StoredSocialConnection[] = [];
      for (const connection of connections) active.push(await refreshConnection(owner, provider, connection));
      const resources = [];
      for (const item of active) {
        if (provider.resources) {
          const token = { accessToken: requireCipher().decrypt(item.accessTokenEncrypted), scopes: item.scopes };
          const available = await provider.resources(providerContext(provider, fetcher), token, item);
          resources.push(...available.map(resource => ({ ...resource, avatar: resource.avatarUrl, connectionId: item.id, capabilities: item.capabilities })));
        } else {
          resources.push({ id: item.providerAccountId, connectionId: item.id, name: item.displayName, handle: item.username ? `@${item.username.replace(/^@/, '')}` : undefined, avatar: item.avatarUrl, type: provider.id === 'facebook' ? 'page' : provider.id === 'youtube' ? 'channel' : provider.id === 'linkedin' && item.accountType === 'organization' ? 'organization' : 'profile', capabilities: item.capabilities });
        }
      }
      return res.json({
        resources,
        permissions: [...new Set(active.flatMap(item => item.scopes))],
      });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/:provider/test', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const provider = getProvider(req);
      const owner = ownerFor(req);
      const connections = await repository.list(owner, provider.id);
      if (!connections.length) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 401, 'Esta plataforma precisa ser autorizada.');
      const results: Array<{ id: string; status: StoredSocialConnection['status']; code?: string }> = [];
      for (const stored of connections) {
        try {
          const connection = await refreshConnection(owner, provider, stored);
          const token = { accessToken: requireCipher().decrypt(connection.accessTokenEncrypted), scopes: connection.scopes };
          const context = providerContext(provider, fetcher);
          const account = provider.account
            ? await provider.account(context, token, connection.providerAccountId)
            : (await provider.accounts(context, token)).find(item => item.id === connection.providerAccountId) || null;
          if (!account) throw new SocialIntegrationError('SOCIAL_AUTHORIZATION_REVOKED', 401, 'A conta não está mais disponível nesta autorização.');
          await repository.update(connection.id, owner, { displayName: account.displayName, username: account.username, avatarUrl: account.avatarUrl, status: 'connected', lastError: undefined });
          results.push({ id: connection.id, status: 'connected' });
        } catch (error) {
          const failure = publicIntegrationError(error);
          const status = statusFor(error);
          await repository.update(stored.id, owner, { status, lastError: failure.publicMessage });
          results.push({ id: stored.id, status, code: failure.code });
        }
      }
      return res.json({ healthy: results.every(item => item.status === 'connected'), results });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/:provider/refresh', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const provider = getProvider(req);
      const owner = ownerFor(req);
      const connections = await repository.list(owner, provider.id);
      if (!connections.length) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 401, 'Esta plataforma precisa ser autorizada.');
      const refreshed = [];
      for (const connection of connections) refreshed.push(publicConnection(await refreshConnection(owner, provider, connection, true), now()));
      await repository.audit({ ...owner, actorId: req.auth!.user.id, provider: provider.id, action: 'refreshed', outcome: 'success', connectionIds: connections.map(connection => connection.id) }, new Date(now()).toISOString());
      return res.json({ connections: refreshed });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/:provider/sync', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const provider = getProvider(req);
      const owner = ownerFor(req);
      let connections = await repository.list(owner, provider.id);
      const requestedConnection = typeof req.body?.connectionId === 'string' ? req.body.connectionId : undefined;
      if (requestedConnection) connections = connections.filter(item => item.id === requestedConnection);
      if (!connections.length) throw new SocialIntegrationError('SOCIAL_CONNECTION_REQUIRED', 401, 'Esta plataforma precisa ser autorizada.');
      const refreshed: StoredSocialConnection[] = [];
      for (const connection of connections) refreshed.push(await refreshConnection(owner, provider, connection));
      connections = refreshed;
      const selected = Array.isArray(req.body?.selectedResourceIds) ? req.body.selectedResourceIds.filter((id: unknown): id is string => typeof id === 'string') : [];
      if (selected.length) {
        const allowed = new Set(connections.flatMap(item => [item.id, item.providerAccountId]));
        if (provider.resources) {
          for (const connection of connections) {
            const token = { accessToken: requireCipher().decrypt(connection.accessTokenEncrypted), scopes: connection.scopes };
            const resources = await provider.resources(providerContext(provider, fetcher), token, connection);
            resources.forEach(resource => allowed.add(resource.id));
          }
        }
        if (selected.some(id => !allowed.has(id))) throw new SocialIntegrationError('SOCIAL_RESOURCE_INVALID', 400, 'Uma das contas selecionadas não pertence a este ambiente.');
        if (!provider.resources) connections = connections.filter(item => selected.includes(item.id) || selected.includes(item.providerAccountId));
      }
      const wantsAnalytics = Array.isArray(req.body?.syncPreferences) && req.body.syncPreferences.includes('analytics');
      if (wantsAnalytics && !connections.some(item => item.capabilities.canReadAnalytics)) {
        throw new SocialIntegrationError('SOCIAL_PERMISSION_INSUFFICIENT', 403, 'As permissões concedidas não liberam Analytics para esta conexão.');
      }
      const active = connections;
      const syncedAt = new Date(now()).toISOString();
      await Promise.all(active.map(connection => repository.update(connection.id, owner, { lastSyncedAt: syncedAt, status: 'connected', lastError: undefined })));
      return res.json({
        status: 'synced', syncedAt, selectedResources: active.length,
        capabilities: active.map(item => ({ connectionId: item.id, providerAccountId: item.providerAccountId, ...item.capabilities })),
        analytics: wantsAnalytics ? { source: 'provider-api', dataStatus: 'unavailable', updatedAt: syncedAt, refreshIntervalMinutes: 60, points: [], contents: [], unavailableMetrics: ['followers_history', 'reach', 'impressions', 'engagements', 'views', 'clicks', 'conversions', 'retention'] } : undefined,
        analyticsMessage: wantsAnalytics ? 'A conexão é real, mas este adaptador ainda não coleta métricas. Nenhum dado foi simulado.' : undefined,
      });
    } catch (error) { return respondError(res, error); }
  });

  router.post('/:provider/disconnect', permissionOnly('connections.manage'), async (req: AuthenticatedRequest, res) => {
    try {
      const provider = getProvider(req);
      const owner = ownerFor(req);
      const requestedId = typeof req.body?.connectionId === 'string' ? req.body.connectionId : undefined;
      const connections = (await repository.list(owner, provider.id)).filter(item => !requestedId || item.id === requestedId);
      if (!connections.length) return res.json({ disconnected: true, count: 0 });
      if (provider.revoke && provider.credentials() && cipher) {
        for (const connection of connections) await provider.revoke(providerContext(provider, fetcher), cipher.decrypt(connection.accessTokenEncrypted));
      }
      await repository.remove(owner, provider.id, connections.map(item => item.id));
      await repository.audit({ ...owner, actorId: req.auth!.user.id, provider: provider.id, action: 'disconnected', outcome: 'success', connectionIds: connections.map(connection => connection.id) }, new Date(now()).toISOString());
      return res.json({ disconnected: true, count: connections.length });
    } catch (error) { return respondError(res, error); }
  });

  return router;
}
