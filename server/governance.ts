import { Router, raw, type NextFunction, type Request, type Response } from 'express';
import { AVATAR_TYPES, MAX_AVATAR_BYTES, normalizeProfileAvatar, profileAvatarUrl, type StoredProfileAvatar } from './profileAvatar';
import path from 'node:path';
import { createHash, createHmac, randomBytes, randomUUID, scryptSync, timingSafeEqual } from 'node:crypto';
import { AtomicJsonStore } from './atomicJsonStore';
import { devConfiguration, isLocalDevRequest, issueDevSession, resolveDevSession, revokeDevSession } from './devMode';
import { DEV_WORKSPACE_ID, DEV_USER_ID, DEV_CLIENT_ID } from '../src/development/contracts';
import { CLIENT_OPERATION_REQUIRED, type ClientOperationRecord } from '../src/clients/clientOperations';
import { effectivePermissions, hasPermission, isPrivilegedRole, rolePresets } from '../src/security/accessControl';
import {
  CURRENT_PRIVACY_VERSION,
  CURRENT_TERMS_VERSION,
  firstError,
  isValidEmail,
  isValidPassword,
  normalizeEmail,
  normalizeFullName,
  validateLogin,
  validateSignup,
} from '../src/security/authValidation';
import type {
  AccessScope,
  AuditLogEntry,
  ContentApprovalItem,
  GovernanceWorkspace,
  OrganizationLicense,
  OrganizationPermission,
  OfferEventPayload,
  PlanCapability,
  SaaSPlan,
  SubscriptionEntitlementSnapshot,
  SubscriptionStatus,
  UsagePool,
  UsageResource,
  UserRole,
  UserAccount,
  WorkspaceMember,
  WorkspaceModule,
  WorkspaceSubscription,
} from '../src/types';

export type AuthContext = { workspaceId: string; user: WorkspaceMember };
type AuthenticatedRequest = Request & { auth?: AuthContext };

type AuthCredential = {
  id: string;
  email: string;
  passwordHash: string;
  memberships: Array<{ userId: string; workspaceId: string }>;
  verifiedAt?: string;
  legalConsent?: {
    termsAcceptedAt: string;
    termsVersion: string;
    privacyAcceptedAt: string;
    privacyVersion: string;
  };
  createdAt: string;
};
type AuthSessionRecord = {
  id: string;
  tokenHash: string;
  credentialId: string;
  workspaceId: string;
  createdAt: string;
  expiresAt: string;
};
type AuthActionToken = {
  tokenHash: string;
  credentialId: string;
  kind: 'verify' | 'reset';
  expiresAt: string;
};

const moduleIds: WorkspaceModule[] = [
  'dashboard', 'create-image', 'create-video', 'create-copy', 'ai-chat',
  'connected-accounts', 'workspace', 'strategy',
  'library', 'calendar', 'automations', 'analytics',
];

const allScope = (): AccessScope => ({ allClients: true, clientIds: [], allSocialAccounts: true, socialAccountIds: [], allProjects: true, projectIds: [], resourceIds: [] });
const personalEntitlements: Partial<Record<UsageResource, number | null>> = { image_generations: 80, video_minutes: 0, klic_credits: 500, storage_bytes: 5_000_000_000, social_accounts: 3, clients: null, automations: 3 };
const teamEntitlements: Partial<Record<UsageResource, number | null>> = { image_generations: 500, video_minutes: 12, klic_credits: 5_000, storage_bytes: 100_000_000_000, social_accounts: 16, clients: null, automations: 50 };
const businessEntitlements: Partial<Record<UsageResource, number | null>> = { image_generations: 1_500, video_minutes: 20, klic_credits: 20_000, storage_bytes: 500_000_000_000, social_accounts: 50, clients: null, automations: 250 };
const unlimitedEntitlements: Partial<Record<UsageResource, number | null>> = { image_generations: null, video_minutes: null, klic_credits: null, storage_bytes: null, social_accounts: null, clients: null, automations: null };

const CATALOG_VERSION = '2026-09';
const baseCapabilities: Record<PlanCapability, boolean> = {
  dashboard: true, image_generation: true, image_editing: true, video_generation: true, video_editing: true,
  copy_creation: true, klic: true, library: true, calendar: true, analytics: true, radar: true,
  automations: true, connected_accounts: true, clients: true, approvals: true, team: true,
};
const personalCapabilities: Record<PlanCapability, boolean> = {
  ...baseCapabilities,
  video_generation: false,
  video_editing: false,
  team: false,
  approvals: false,
};

const plans: SaaSPlan[] = [
  { id: 'solo', name: 'Solo', maxUsers: 1, monthlyPrice: 79, description: 'Para operações individuais.', features: ['1 usuário administrador', 'Criação com a KLIC', 'Calendário editorial'], audience: 'personal', includedLicenses: 1, entitlements: personalEntitlements, capabilities: personalCapabilities, catalogVersion: CATALOG_VERSION },
  { id: 'team', name: 'Equipe', maxUsers: 6, monthlyPrice: 249, description: 'Para equipes enxutas e colaborativas.', features: ['1 administrador + 5 colaboradores', 'Fluxo de aprovação', 'Automações'], audience: 'organization', includedLicenses: 6, entitlements: teamEntitlements, capabilities: baseCapabilities, catalogVersion: CATALOG_VERSION },
  { id: 'business', name: 'Negócios', maxUsers: 16, monthlyPrice: 599, description: 'Para operações de conteúdo em escala.', features: ['1 administrador + 15 colaboradores', 'Análises avançadas', 'Auditoria completa'], audience: 'organization', includedLicenses: 16, entitlements: businessEntitlements, capabilities: baseCapabilities, catalogVersion: CATALOG_VERSION },
  { id: 'enterprise', name: 'Corporativo', maxUsers: null, monthlyPrice: null, description: 'Capacidade, suporte e governança personalizados.', features: ['Usuários personalizados', 'SLA dedicado', 'Governança avançada'], audience: 'organization', includedLicenses: 1, entitlements: unlimitedEntitlements, capabilities: baseCapabilities, catalogVersion: CATALOG_VERSION },
];

const developmentPlan: SaaSPlan = { id: 'development', name: 'Desenvolvimento', maxUsers: 100,
  monthlyPrice: 0, description: 'Ambiente local isolado. Não é uma assinatura comercial.',
  features: ['Ferramentas locais', 'Administração de teste', 'Gastos externos bloqueados'],
  audience: 'organization', includedLicenses: 1, entitlements: unlimitedEntitlements,
  capabilities: baseCapabilities, catalogVersion: 'local-dev-v1' };

const workspaces: GovernanceWorkspace[] = [{
  id: 'ws-1',
  name: 'Clicko Studio',
  logo: '/clicko-ai-studios-logo-stacked.png',
  planId: 'team',
  maxUsers: 6,
  activeUsers: 1,
  subscriptionDate: '2026-05-18T12:00:00.000Z',
  subscriptionStatus: 'active',
  kind: 'organization',
  ownerUserId: 'usr-master',
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
  kind: 'personal',
  ownerUserId: 'usr-master-personal',
  settings: { inviteExpiryDays: 7, requireApproval: false, timezone: 'America/Sao_Paulo' },
}];

const users: WorkspaceMember[] = [
  { id: 'usr-master', workspaceId: 'ws-1', name: 'Pedro Henrique', email: 'pedro@clickostudio.com', avatar: '', role: 'master', status: 'active', modules: [...moduleIds], permissions: [...rolePresets.master.permissions], scope: allScope(), licenseId: 'license-ws-1-1', lastAccess: new Date().toISOString(), createdAt: '2026-05-18T12:00:00.000Z' },
  { id: 'usr-master-personal', workspaceId: 'ws-personal', name: 'Pedro Henrique', email: 'pedro.henrique@gmail.com', avatar: '', role: 'master', status: 'active', modules: [...moduleIds], permissions: [...rolePresets.master.permissions], scope: allScope(), lastAccess: new Date().toISOString(), createdAt: '2026-06-01T12:00:00.000Z' },
];

const subscriptions: WorkspaceSubscription[] = [{
  id: 'sub-1', workspaceId: 'ws-1', planId: 'team', status: 'active',
  startedAt: '2026-05-18T12:00:00.000Z', renewsAt: '2026-08-18T12:00:00.000Z',
  billingEmail: 'financeiro@clickostudio.com', paymentMethod: 'Gerenciado pelo provedor seguro', ownerType: 'organization', addOns: [],
}, {
  id: 'sub-personal', workspaceId: 'ws-personal', planId: 'solo', status: 'active',
  startedAt: '2026-06-01T12:00:00.000Z', renewsAt: '2026-09-01T12:00:00.000Z',
  billingEmail: 'pedro.henrique@gmail.com', paymentMethod: 'Gerenciado pelo provedor seguro', ownerType: 'personal_account', addOns: [],
}];

const licenses: OrganizationLicense[] = Array.from({ length: 6 }, (_, index) => ({
  id: `license-ws-1-${index + 1}`, workspaceId: 'ws-1', status: index === 0 ? 'in_use' : 'available',
  ...(index === 0 ? { memberId: 'usr-master' } : {}), createdAt: '2026-05-18T12:00:00.000Z', updatedAt: '2026-05-18T12:00:00.000Z',
}));
const usagePools: UsagePool[] = [];

// Image jobs reserve quota before crossing the async service boundary. The receipt
// and counter share the existing atomic governance snapshot, including on restart.
type StudioImageUsageReceipt = {
  id: string;
  workspaceId: string;
  memberId: string;
  periodStartedAt: string;
  fingerprint: string;
  status: 'reserved' | 'accepted';
  createdAt: string;
  jobId?: string;
};
const studioImageUsageReceipts: StudioImageUsageReceipt[] = [];
type StudioVideoUsageReceipt = Omit<StudioImageUsageReceipt, 'status'> & {
  status: 'reserved' | 'accepted' | 'settled' | 'released'; seconds: number; chargedMinutes: number;
};
const studioVideoUsageReceipts: StudioVideoUsageReceipt[] = [];

const approvals: ContentApprovalItem[] = [];

const auditLogs: AuditLogEntry[] = [];

const inviteTokens = new Map<string, string>();
const authCredentials: AuthCredential[] = [];
const authSessions: AuthSessionRecord[] = [];
const authActionTokens: AuthActionToken[] = [];
const profileAvatars: StoredProfileAvatar[] = [];
type RegisteredClient = Omit<ClientOperationRecord, 'portalDocuments'> & {
  providerCheckoutSessionId?: string;
  providerSubscriptionId?: string;
  portalTokenHash?: string;
  portalExpiresAt?: string;
  independentTokenHash?: string;
  independentExpiresAt?: string;
  portalDocuments?: Array<{ id: string; name: string; mime: string; uploadedAt: string; data: string }>;
  managedInitiatorUserId?: string;
};
const registeredClients: RegisteredClient[] = [];
type BillingCheckoutSession = {
  id: string;
  workspaceId: string;
  planId: SaaSPlan['id'];
  billingCycle: NonNullable<WorkspaceSubscription['billingCycle']>;
  seats: number;
  status: 'created' | 'completed' | 'expired';
  provider: 'stripe';
  providerSessionId?: string;
  createdAt: string;
  completedAt?: string;
  previousStatus: SubscriptionStatus;
};
type ProcessedBillingEvent = { eventId: string; provider: 'stripe'; type: string; workspaceId?: string; processedAt: string };
const billingCheckoutSessions: BillingCheckoutSession[] = [];
const processedBillingEvents: ProcessedBillingEvent[] = [];

export function workspaceOwnsClient(workspaceId: string, clientId: string) {
  return registeredClients.some(client => client.workspaceId === workspaceId && client.id === clientId);
}

function publicClient(client: RegisteredClient): ClientOperationRecord {
  return {
    id: client.id, workspaceId: client.workspaceId, name: client.name, updatedAt: client.updatedAt,
    operationState: client.operationState || 'registered', invitationEmail: client.invitationEmail,
    invitationKind: client.invitationKind, billingStatus: client.billingStatus || 'none',
    linkedWorkspaceId: client.linkedWorkspaceId, sharedSummary: client.sharedSummary,
    portalRequests: client.portalRequests || [], portalComments: client.portalComments || [],
    portalDocuments: (client.portalDocuments || []).map(({ data: _data, ...metadata }) => metadata),
    operationSignals: client.operationSignals || [],
  };
}

function portalClient(req: Request) {
  const token = String(req.header('x-client-portal-token') || '');
  if (!/^[A-Za-z0-9_-]{40,100}$/.test(token)) return undefined;
  const tokenHash = sha256(token);
  return registeredClients.find(item => item.operationState === 'invited' && item.invitationKind === 'portal' && item.portalTokenHash === tokenHash && Date.parse(item.portalExpiresAt || '') > Date.now() && subscriptionAccessAllowed(subscriptionForWorkspace(item.workspaceId)));
}

export function assertClientOperation(auth: AuthContext, clientId: string) {
  assertGovernanceAccess(auth, { clientId });
  const client = registeredClients.find(item => item.id === clientId && item.workspaceId === auth.workspaceId);
  if (!client || !['managed', 'independent'].includes(client.operationState) || client.billingStatus !== 'active') {
    throw Object.assign(new Error(CLIENT_OPERATION_REQUIRED), { status: 402, code: 'CLIENT_OPERATION_REQUIRED' });
  }
  return client;
}

export function publicationApprovalStage(workspaceId: string, contentId: string) {
  const item = approvals.find(approval => approval.workspaceId === workspaceId && approval.contentId === contentId);
  return item ? { id: item.id, stage: item.stage } : null;
}

const usageResources: UsageResource[] = ['image_generations', 'video_minutes', 'klic_credits', 'storage_bytes', 'social_accounts', 'clients', 'automations'];
const roleIds: UserRole[] = ['master', 'administrator', 'manager', 'social_media', 'creative', 'analyst', 'approver', 'custom', 'collaborator'];

function captureEntitlements(plan: SaaSPlan): SubscriptionEntitlementSnapshot {
  return {
    planId: plan.id,
    catalogVersion: plan.catalogVersion || CATALOG_VERSION,
    capabilities: { ...plan.capabilities },
    quotas: { ...plan.entitlements },
    includedLicenses: plan.includedLicenses ?? plan.maxUsers ?? 1,
    capturedAt: nowIso(),
  };
}

function subscriptionForWorkspace(workspaceId: string) {
  return subscriptions.find(item => item.workspaceId === workspaceId);
}

function claimIndependentClientInvite(clientId: string, token: string, email: string, workspaceId: string) {
  if (!/^[A-Za-z0-9_-]{40,100}$/.test(token)) return false;
  const invite = registeredClients.find(item => item.id === clientId && item.invitationKind === 'independent' && item.invitationEmail === email && item.operationState === 'invited' && item.independentTokenHash === sha256(token) && Date.parse(item.independentExpiresAt || '') > Date.now() && (!item.linkedWorkspaceId || item.linkedWorkspaceId === workspaceId));
  if (!invite || registeredClients.some(item => item.id !== invite.id && item.linkedWorkspaceId === workspaceId && item.invitationKind === 'independent')) return false;
  invite.linkedWorkspaceId = workspaceId;
  invite.independentTokenHash = undefined; invite.independentExpiresAt = undefined;
  const active = subscriptionAccessAllowed(subscriptionForWorkspace(workspaceId));
  invite.operationState = active ? 'independent' : 'invited';
  invite.billingStatus = active ? 'active' : 'none';
  invite.updatedAt = nowIso();
  return true;
}

function activateManagedWorkspace(client: RegisteredClient, providerSubscriptionId: string, providerCustomerId: string, providerEventId: string) {
  if (client.linkedWorkspaceId) throw new Error('CLIENT_WORKSPACE_ALREADY_LINKED');
  const parent = workspaces.find(item => item.id === client.workspaceId);
  const payer = users.find(item => item.id === client.managedInitiatorUserId && item.workspaceId === client.workspaceId && item.status === 'active');
  if (!parent || parent.parentWorkspaceId || !payer) throw new Error('MANAGED_OPERATION_OWNER_INVALID');
  const credential = authCredentials.find(item => item.email === normalizeEmail(payer.email) && item.memberships.some(membership => membership.userId === payer.id && membership.workspaceId === parent.id));
  if (!credential && process.env.NODE_ENV === 'production') throw new Error('MANAGED_OPERATION_CREDENTIAL_REQUIRED');
  const createdAt = nowIso();
  const workspaceId = id('ws-managed');
  const userId = id('usr-managed');
  const licenseId = id('license');
  workspaces.push({ id: workspaceId, name: client.name, logo: '', planId: 'solo', maxUsers: 1, activeUsers: 1, subscriptionDate: createdAt, subscriptionStatus: 'active', kind: 'organization', parentWorkspaceId: parent.id, managedClientId: client.id, ownerUserId: userId, settings: { inviteExpiryDays: 7, requireApproval: false, timezone: parent.settings.timezone } });
  users.push({ id: userId, workspaceId, name: payer.name, email: payer.email, avatar: payer.avatar, role: 'master', status: 'active', modules: [...moduleIds], permissions: [...rolePresets.master.permissions], scope: allScope(), licenseId, lastAccess: createdAt, createdAt });
  licenses.push({ id: licenseId, workspaceId, memberId: userId, status: 'in_use', createdAt, updatedAt: createdAt });
  subscriptions.push({ id: id('sub-managed'), workspaceId, planId: 'solo', status: 'active', startedAt: createdAt, renewsAt: '', billingEmail: payer.email, paymentMethod: 'Gerenciado pelo provedor seguro', ownerType: 'managed_operation', addOns: [], provider: 'stripe', providerCustomerId, providerSubscriptionId, entitlementSnapshot: captureEntitlements(plans.find(plan => plan.id === 'solo')!), billingCycle: 'monthly', history: [{ id: id('sub-history'), event: 'activated', toStatus: 'active', planId: 'solo', occurredAt: createdAt, providerEventId }] });
  usagePools.push(newUsagePool(workspaceId));
  if (credential) credential.memberships.push({ userId, workspaceId });
  client.linkedWorkspaceId = workspaceId;
  client.providerSubscriptionId = providerSubscriptionId;
  client.operationState = 'managed'; client.billingStatus = 'active'; client.invitationKind = undefined;
  client.portalTokenHash = undefined; client.portalExpiresAt = undefined; client.updatedAt = createdAt;
  return workspaceId;
}

function subscriptionAccessAllowed(subscription?: WorkspaceSubscription) {
  if (!subscription) return false;
  const workspace = workspaces.find(item => item.id === subscription.workspaceId);
  if (workspace?.parentWorkspaceId && !subscriptionAccessAllowed(subscriptionForWorkspace(workspace.parentWorkspaceId))) return false;
  if (subscription.accessOverride?.enabled) return true;
  const serverAllowList = new Set(String(process.env.CLICKO_INTERNAL_ACCESS_WORKSPACE_IDS || '').split(',').map(value => value.trim()).filter(Boolean));
  if (serverAllowList.has(subscription.workspaceId)) return true;
  if (subscription.status === 'active' || subscription.status === 'trialing') return true;
  if (subscription.status === 'canceled' && subscription.cancelAtPeriodEnd && Date.parse(subscription.endsAt || subscription.renewsAt) > Date.now()) return true;
  return false;
}

function capabilityForModule(module?: WorkspaceModule): PlanCapability | undefined {
  if (!module) return undefined;
  return ({
    dashboard: 'dashboard', 'create-image': 'image_generation', 'create-video': 'video_generation', 'create-copy': 'copy_creation',
    'ai-chat': 'klic', 'connected-accounts': 'connected_accounts', workspace: 'clients', strategy: 'radar',
    library: 'library', calendar: 'calendar', automations: 'automations', analytics: 'analytics',
  } satisfies Partial<Record<WorkspaceModule, PlanCapability>>)[module];
}

function capabilityForPermission(permission?: OrganizationPermission): PlanCapability | undefined {
  if (!permission) return undefined;
  if (permission.startsWith('members.') || permission.startsWith('licenses.')) return 'team';
  if (permission === 'content.approve') return 'approvals';
  if (permission.startsWith('connections.')) return 'connected_accounts';
  if (permission.startsWith('analytics.')) return 'analytics';
  if (permission.startsWith('clients.')) return 'clients';
  return undefined;
}

function resourceCapability(resource: UsageResource): PlanCapability | undefined {
  return ({ image_generations: 'image_generation', video_minutes: 'video_generation', klic_credits: 'klic', social_accounts: 'connected_accounts', clients: 'clients', automations: 'automations' } satisfies Partial<Record<UsageResource, PlanCapability>>)[resource];
}

function subscriptionCapability(subscription: WorkspaceSubscription, capability: PlanCapability) {
  if (subscription.capabilityOverrides?.[capability] !== undefined) return subscription.capabilityOverrides[capability] === true;
  return subscription.entitlementSnapshot?.capabilities?.[capability] === true;
}

function entitlementLimit(workspaceId: string, resource: UsageResource) {
  if (resource === 'clients') return null;
  const subscription = subscriptionForWorkspace(workspaceId);
  const plan = plans.find(item => item.id === subscription?.planId);
  const base = subscription?.quotaOverrides?.[resource] !== undefined
    ? subscription.quotaOverrides[resource]
    : subscription?.entitlementSnapshot?.quotas?.[resource] ?? plan?.entitlements?.[resource];
  const extra = (subscription?.addOns || []).filter(item => item.status === 'active' && item.resource === resource).reduce((sum, item) => sum + item.quantity, 0);
  return base === null ? null : Math.max(0, Number(base || 0) + extra);
}

function newUsagePool(workspaceId: string): UsagePool {
  const started = new Date();
  const end = new Date(Date.UTC(started.getUTCFullYear(), started.getUTCMonth() + 1, 1));
  return {
    workspaceId, periodStartedAt: started.toISOString(), periodEndsAt: end.toISOString(), allocationMode: 'shared', memberLimits: {}, memberUsage: {},
    resources: Object.fromEntries(usageResources.map(resource => [resource, { limit: entitlementLimit(workspaceId, resource), used: 0 }])) as UsagePool['resources'],
  };
}

function ensureGovernanceModel() {
  // A CRM registration is never a billable operation; migrate legacy client quotas.
  for (const subscription of subscriptions) {
    if (subscription.entitlementSnapshot) subscription.entitlementSnapshot.quotas.clients = null;
  }
  for (const pool of usagePools) {
    if (pool.resources?.clients) pool.resources.clients.limit = null;
  }
  for (const workspace of workspaces) {
    workspace.kind ||= workspace.planId === 'solo' ? 'personal' : 'organization';
    const master = users.find(user => user.workspaceId === workspace.id && user.role === 'master');
    workspace.ownerUserId ||= master?.id;
    const subscription = subscriptions.find(item => item.workspaceId === workspace.id);
    if (subscription) {
      subscription.ownerType ||= workspace.kind === 'personal' ? 'personal_account' : 'organization';
      subscription.addOns ||= [];
      const plan = plans.find(item => item.id === subscription.planId);
      if (plan && !subscription.entitlementSnapshot) subscription.entitlementSnapshot = captureEntitlements(plan);
      subscription.provider ||= 'none';
      subscription.billingCycle ||= 'monthly';
      subscription.history ||= [];
      workspace.subscriptionStatus = subscription.status;
    }
    if (!usagePools.some(pool => pool.workspaceId === workspace.id)) usagePools.push(newUsagePool(workspace.id));
    if (workspace.kind === 'organization') {
      const included = plans.find(plan => plan.id === workspace.planId)?.includedLicenses ?? workspace.maxUsers ?? 1;
      while (licenses.filter(license => license.workspaceId === workspace.id).length < included) {
        licenses.push({ id: id('license'), workspaceId: workspace.id, status: 'available', createdAt: nowIso(), updatedAt: nowIso() });
      }
    }
  }
  for (const user of users) {
    if (user.role === 'collaborator') user.role = 'custom';
    user.permissions ||= [...rolePresets[user.role as Exclude<UserRole, 'collaborator'>].permissions];
    user.scope ||= user.role === 'master' ? allScope() : { allClients: false, clientIds: [], allSocialAccounts: false, socialAccountIds: [], allProjects: false, projectIds: [], resourceIds: [] };
    const workspace = workspaces.find(item => item.id === user.workspaceId);
    if (workspace?.kind === 'organization' && user.status === 'active' && !user.licenseId) {
      const license = licenses.find(item => item.workspaceId === user.workspaceId && item.status === 'available');
      if (license) { license.status = 'in_use'; license.memberId = user.id; license.updatedAt = nowIso(); user.licenseId = license.id; }
    }
  }
}

type GovernanceSnapshot = {
  studioVideoUsageReceipts?: StudioVideoUsageReceipt[];
  studioImageUsageReceipts?: StudioImageUsageReceipt[];
  profileAvatars?: StoredProfileAvatar[];
  registeredClients?: RegisteredClient[];
  version: 4;
  workspaces: GovernanceWorkspace[];
  users: WorkspaceMember[];
  subscriptions: WorkspaceSubscription[];
  approvals: ContentApprovalItem[];
  auditLogs: AuditLogEntry[];
  inviteTokens: Array<[string, string]>;
  authCredentials: AuthCredential[];
  authSessions: AuthSessionRecord[];
  authActionTokens: AuthActionToken[];
  licenses: OrganizationLicense[];
  usagePools: UsagePool[];
  billingCheckoutSessions: BillingCheckoutSession[];
  processedBillingEvents: ProcessedBillingEvent[];
};
type LegacyGovernanceSnapshot = Omit<GovernanceSnapshot, 'version' | 'authCredentials' | 'authSessions' | 'authActionTokens' | 'licenses' | 'usagePools' | 'billingCheckoutSessions' | 'processedBillingEvents'> & { version: 1 };
type GovernanceSnapshotV2 = Omit<GovernanceSnapshot, 'version' | 'licenses' | 'usagePools' | 'billingCheckoutSessions' | 'processedBillingEvents'> & { version: 2 };
type GovernanceSnapshotV3 = Omit<GovernanceSnapshot, 'version' | 'billingCheckoutSessions' | 'processedBillingEvents'> & { version: 3 };
type StoredGovernanceSnapshot = GovernanceSnapshot | GovernanceSnapshotV3 | GovernanceSnapshotV2 | LegacyGovernanceSnapshot;
const snapshot = (): GovernanceSnapshot => structuredClone({ version: 4, workspaces, users, subscriptions, approvals, auditLogs, inviteTokens: [...inviteTokens], authCredentials, authSessions, authActionTokens, profileAvatars, registeredClients, licenses, usagePools, studioImageUsageReceipts, studioVideoUsageReceipts, billingCheckoutSessions, processedBillingEvents });
function restore(value: StoredGovernanceSnapshot) {
  studioVideoUsageReceipts.splice(0, studioVideoUsageReceipts.length, ...(value.studioVideoUsageReceipts || []));
  studioImageUsageReceipts.splice(0, studioImageUsageReceipts.length, ...(value.studioImageUsageReceipts || []));
  profileAvatars.splice(0, profileAvatars.length, ...(value.profileAvatars || []));
  registeredClients.splice(0, registeredClients.length, ...(value.registeredClients || []));
  workspaces.splice(0, workspaces.length, ...value.workspaces);
  users.splice(0, users.length, ...value.users);
  subscriptions.splice(0, subscriptions.length, ...value.subscriptions);
  approvals.splice(0, approvals.length, ...value.approvals);
  auditLogs.splice(0, auditLogs.length, ...value.auditLogs);
  inviteTokens.clear(); value.inviteTokens.forEach(([token, userId]) => inviteTokens.set(token, userId));
  authCredentials.splice(0, authCredentials.length, ...('authCredentials' in value ? value.authCredentials : []));
  authSessions.splice(0, authSessions.length, ...('authSessions' in value ? value.authSessions : []));
  authActionTokens.splice(0, authActionTokens.length, ...('authActionTokens' in value ? value.authActionTokens : []));
  licenses.splice(0, licenses.length, ...('licenses' in value ? value.licenses : []));
  usagePools.splice(0, usagePools.length, ...('usagePools' in value ? value.usagePools : []));
  billingCheckoutSessions.splice(0, billingCheckoutSessions.length, ...('billingCheckoutSessions' in value ? value.billingCheckoutSessions : []));
  processedBillingEvents.splice(0, processedBillingEvents.length, ...('processedBillingEvents' in value ? value.processedBillingEvents : []));
  ensureGovernanceModel();
}
function validSnapshot(value: unknown): value is StoredGovernanceSnapshot {
  if (!value || typeof value !== 'object') return false;
  const state = value as StoredGovernanceSnapshot;
  if (state.studioVideoUsageReceipts !== undefined && (!Array.isArray(state.studioVideoUsageReceipts) || !state.studioVideoUsageReceipts.every(item => item && /^[a-f0-9]{64}$/.test(item.id) && /^[a-f0-9]{64}$/.test(item.fingerprint) && typeof item.workspaceId === 'string' && typeof item.memberId === 'string' && typeof item.periodStartedAt === 'string' && Number.isFinite(item.seconds) && item.seconds > 0 && Number.isFinite(item.chargedMinutes) && item.chargedMinutes >= 0 && ['reserved', 'accepted', 'settled', 'released'].includes(item.status)))) return false;
  if (state.studioImageUsageReceipts !== undefined && (!Array.isArray(state.studioImageUsageReceipts) || !state.studioImageUsageReceipts.every(item => item && /^[a-f0-9]{64}$/.test(item.id) && /^[a-f0-9]{64}$/.test(item.fingerprint) && typeof item.workspaceId === 'string' && typeof item.memberId === 'string' && typeof item.periodStartedAt === 'string' && typeof item.createdAt === 'string' && ['reserved', 'accepted'].includes(item.status) && (item.jobId === undefined || typeof item.jobId === 'string')))) return false;
  if (state.profileAvatars !== undefined && (!Array.isArray(state.profileAvatars) || !state.profileAvatars.every(item => item && typeof item.userId === 'string' && typeof item.workspaceId === 'string' && typeof item.data === 'string' && typeof item.version === 'string'))) return false;
  if (state.registeredClients !== undefined && (!Array.isArray(state.registeredClients) || !state.registeredClients.every(item => item && typeof item.id === 'string' && typeof item.name === 'string' && typeof item.workspaceId === 'string' && typeof item.updatedAt === 'string' && (!item.operationState || ['registered', 'invited', 'managed', 'independent'].includes(item.operationState))))) return false;
  if (![1, 2, 3, 4].includes(state.version) || !['workspaces', 'users', 'subscriptions', 'approvals', 'auditLogs', 'inviteTokens'].every(key => Array.isArray((state as any)[key]))) return false;
  if (state.version >= 2 && !['authCredentials', 'authSessions', 'authActionTokens'].every(key => Array.isArray((state as any)[key]))) return false;
  if (state.version >= 3 && (!Array.isArray((state as any).licenses) || !Array.isArray((state as any).usagePools))) return false;
  if (state.version === 4 && (!Array.isArray(state.billingCheckoutSessions) || !Array.isArray(state.processedBillingEvents))) return false;
  const ids = new Set<string>();
  if (!state.workspaces.every(ws => ws && typeof ws.id === 'string' && !ids.has(ws.id) && ids.add(ws.id) && typeof ws.name === 'string' && ws.settings && Number.isFinite(ws.settings.inviteExpiryDays))) return false;
  const scoped = (items: Array<{ id: string; workspaceId: string }>) => {
    const seen = new Set<string>();
    return items.every(item => item && typeof item.id === 'string' && !seen.has(item.id) && seen.add(item.id) && ids.has(item.workspaceId));
  };
  return scoped(state.users) && scoped(state.subscriptions) && scoped(state.approvals) && scoped(state.auditLogs)
    && (state.registeredClients === undefined || scoped(state.registeredClients))
    && state.users.every(user => roleIds.includes(user.role) && ['active', 'disabled', 'invited'].includes(user.status) && Array.isArray(user.modules))
    && state.approvals.every(item => typeof item.contentId === 'string' && Array.isArray(item.history) && Array.isArray(item.comments))
    && state.inviteTokens.every(pair => Array.isArray(pair) && pair.length === 2 && pair.every(part => typeof part === 'string') && state.users.some(user => user.id === pair[1]))
    && (state.version === 1 || (
      state.authCredentials.every(item => item && typeof item.id === 'string' && typeof item.email === 'string' && typeof item.passwordHash === 'string' && Array.isArray(item.memberships) && item.memberships.length > 0 && item.memberships.every(membership => state.users.some(user => user.id === membership.userId && user.workspaceId === membership.workspaceId)))
      && state.authSessions.every(item => item && typeof item.tokenHash === 'string' && typeof item.expiresAt === 'string' && state.authCredentials.some(credential => credential.id === item.credentialId))
      && state.authActionTokens.every(item => item && ['verify', 'reset'].includes(item.kind) && typeof item.tokenHash === 'string' && state.authCredentials.some(credential => credential.id === item.credentialId))
    ))
    && (state.version < 3 || (scoped((state as GovernanceSnapshotV3 | GovernanceSnapshot).licenses) && (state as GovernanceSnapshotV3 | GovernanceSnapshot).usagePools.every(pool => ids.has(pool.workspaceId) && usageResources.every(resource => pool.resources?.[resource]))))
    && (state.version !== 4 || (state.billingCheckoutSessions.every(item => ids.has(item.workspaceId) && plans.some(plan => plan.id === item.planId)) && state.processedBillingEvents.every(item => typeof item.eventId === 'string')));
}
let repository: AtomicJsonStore<StoredGovernanceSnapshot> | undefined;
let repositoryFile: string | null | undefined;

function configurePersistence(filename: string | null) {
  const resolved = filename === null ? null : path.resolve(filename);
  if (repositoryFile !== undefined) {
    if (repositoryFile !== resolved) throw new Error('A governança já foi inicializada com outro armazenamento neste processo.');
    return;
  }
  if (resolved) {
    for (const root of [path.resolve('public'), path.resolve('dist')]) {
      const relative = path.relative(root, resolved);
      if (!relative || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
        throw new Error('O armazenamento de governança deve ficar fora de public/ e dist/.');
      }
    }
    const store = new AtomicJsonStore(resolved, validSnapshot);
    restore(store.load(snapshot()));
    repository = store;
  }
  repositoryFile = resolved;
}

/** First-boot seed only. An existing store is loaded without replacing its projects or test members. */
function prepareDevGovernance() {
  if (!devConfiguration()) return;
  if (!plans.some(plan => plan.id === 'development')) plans.push(developmentPlan);
  if (repositoryFile !== undefined) return;
  const created = new Date().toISOString();
  workspaces.splice(0, workspaces.length, {
    id: DEV_WORKSPACE_ID, name: 'Clicko DEV', logo: '', planId: 'development', maxUsers: 100, activeUsers: 1,
    subscriptionDate: created, subscriptionStatus: 'active', kind: 'organization', ownerUserId: DEV_USER_ID,
    settings: { inviteExpiryDays: 7, requireApproval: false, timezone: 'America/Sao_Paulo' },
  });
  users.splice(0, users.length, { id: DEV_USER_ID, workspaceId: DEV_WORKSPACE_ID, name: 'Clicko Developer',
    email: 'developer@clicko.local', avatar: '', role: 'master', status: 'active', modules: [...moduleIds],
    permissions: [...rolePresets.master.permissions], scope: allScope(), createdAt: created, lastAccess: created });
  subscriptions.splice(0, subscriptions.length, { id: 'sub-dev-clicko', workspaceId: DEV_WORKSPACE_ID,
    planId: 'development', status: 'active', startedAt: created, renewsAt: '', billingEmail: 'developer@clicko.local',
    paymentMethod: 'Sem cobrança · somente desenvolvimento', provider: 'none', ownerType: 'organization',
    addOns: [], entitlementSnapshot: captureEntitlements(developmentPlan) });
  registeredClients.splice(0, registeredClients.length, { id: DEV_CLIENT_ID, workspaceId: DEV_WORKSPACE_ID,
    name: 'Cliente DEV', operationState: 'managed', billingStatus: 'active', updatedAt: created });
  licenses.splice(0); usagePools.splice(0); approvals.splice(0); auditLogs.splice(0); inviteTokens.clear();
  authCredentials.splice(0); authSessions.splice(0); authActionTokens.splice(0); profileAvatars.splice(0);
  billingCheckoutSessions.splice(0); processedBillingEvents.splice(0);
  studioImageUsageReceipts.splice(0); studioVideoUsageReceipts.splice(0);
  ensureGovernanceModel();
}

function devAuthPayload(expiresAt: string) {
  const account = accountFromMembership({ userId: DEV_USER_ID, workspaceId: DEV_WORKSPACE_ID });
  const user = users.find(item => item.id === DEV_USER_ID && item.workspaceId === DEV_WORKSPACE_ID && item.status === 'active');
  if (!account || !user) throw new Error('DEV_IDENTITY_UNAVAILABLE');
  return { account: { ...account, role: 'Administrador de desenvolvimento' }, accounts: [{ ...account, role: 'Administrador de desenvolvimento' }],
    user, development: { enabled: true, workspaceId: DEV_WORKSPACE_ID, clientId: DEV_CLIENT_ID, expiresAt } };
}

export function developmentAuth(): AuthContext | undefined {
  if (!devConfiguration()) return undefined;
  const user = users.find(item => item.id === DEV_USER_ID && item.workspaceId === DEV_WORKSPACE_ID && item.status === 'active');
  return user ? { user, workspaceId: DEV_WORKSPACE_ID } : undefined;
}

// All governance mutation handlers are synchronous. Commit before acknowledging
// HTTP success, including 204 DELETE; on storage failure restore the previous state.
function persistMutation(req: Request, res: Response, next: NextFunction) {
  if (!repository || !['POST', 'PATCH', 'PUT', 'DELETE'].includes(req.method)) return next();
  const before = snapshot();
  const originalJson = res.json.bind(res);
  const originalEnd = res.end.bind(res);
  let committed = false;
  const commit = () => {
    if (committed) return true;
    committed = true;
    try { repository!.save(snapshot()); return true; }
    catch {
      restore(before);
      res.statusCode = 503;
      res.removeHeader('Content-Length');
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      originalEnd(JSON.stringify({ error: 'Não foi possível salvar a alteração. O estado anterior foi preservado. Verifique o armazenamento do servidor.' }));
      return false;
    }
  };
  res.json = ((body: unknown) => commit() ? originalJson(body) : res) as Response['json'];
  res.end = ((...args: any[]) => commit() ? originalEnd(...args) : res) as Response['end'];
  next();
}

const nowIso = () => new Date().toISOString();
const id = (prefix: string) => `${prefix}-${randomUUID()}`;

function refreshWorkspaceSeats(workspaceId: string) {
  const workspace = workspaces.find((item) => item.id === workspaceId);
  if (workspace) workspace.activeUsers = users.filter((user) => user.workspaceId === workspaceId && user.status === 'active').length;
}

function addAudit(auth: AuthContext, action: string, resource: string, detail: string) {
  auditLogs.unshift({ id: id('audit'), workspaceId: auth.workspaceId, actorId: auth.user.id, actorName: auth.user.name, action, resource, detail, createdAt: nowIso() });
}

const SESSION_COOKIE = 'clicko_session';
const DEVELOPMENT_PROFILE_COOKIE = 'clicko_dev_profile';
const sha256 = (value: string) => createHash('sha256').update(value).digest('hex');
const hashPassword = (password: string) => {
  const salt = randomBytes(16).toString('base64url');
  return `scrypt$${salt}$${scryptSync(password, salt, 64).toString('base64url')}`;
};
const passwordMatches = (password: string, encoded: string) => {
  const [algorithm, salt, hash] = encoded.split('$');
  if (algorithm !== 'scrypt' || !salt || !hash) return false;
  try {
    const stored = Buffer.from(hash, 'base64url');
    const candidate = scryptSync(password, salt, stored.length);
    return stored.length === candidate.length && timingSafeEqual(stored, candidate);
  } catch { return false; }
};

const cookieValue = (req: Request, name: string) => String(req.headers.cookie || '').split(';').map(part => part.trim()).find(part => part.startsWith(`${name}=`))?.slice(name.length + 1) || '';
const sessionCookie = (value: string, maxAgeSeconds: number) => `${SESSION_COOKIE}=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAgeSeconds}${process.env.NODE_ENV === 'production' ? '; Secure' : ''}`;
const clearSessionCookie = () => `${SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0${process.env.NODE_ENV === 'production' ? '; Secure' : ''}`;
const accountFromMembership = (membership: { userId: string; workspaceId: string }): UserAccount | null => {
  if (membership.workspaceId === DEV_WORKSPACE_ID && !devConfiguration()) return null;
  const user = users.find(item => item.id === membership.userId && item.workspaceId === membership.workspaceId && item.status === 'active');
  const workspace = workspaces.find(item => item.id === membership.workspaceId);
  if (!user || !workspace) return null;
  const subscription = subscriptionForWorkspace(workspace.id);
  return {
    id: `account-${workspace.id}`,
    workspaceId: workspace.id,
    userId: user.id,
    name: workspace.kind === 'personal' ? user.name : workspace.name,
    type: workspace.kind === 'personal' ? 'personal' : 'company',
    role: user.role === 'master' ? (workspace.kind === 'personal' ? 'Solo Creator' : 'Master') : rolePresets[user.role === 'collaborator' ? 'custom' : user.role].label,
    planName: plans.find(plan => plan.id === workspace.planId)?.name,
    subscriptionStatus: subscription?.status || workspace.subscriptionStatus,
    subscriptionAccessAllowed: subscriptionAccessAllowed(subscription),
    capabilities: { ...subscription?.entitlementSnapshot?.capabilities, ...subscription?.capabilityOverrides },
    membersCount: users.filter(item => item.workspaceId === workspace.id && item.status === 'active').length,
    email: user.email,
    avatar: user.avatar,
    createdAt: user.createdAt,
  };
};
function resolveDevelopmentBypass(req: Request) {
  if (process.env.CLICKO_DEV_MODE === 'true') return null;
  if (process.env.NODE_ENV !== 'development' || process.env.CLICKO_DEV_AUTH_BYPASS !== 'true') return null;
  const baseAccounts = (['personal', 'company'] as const).map(type => {
    const workspace = workspaces.find(item => !item.parentWorkspaceId && (item.planId === 'solo' ? 'personal' : 'company') === type);
    const user = workspace && users.find(item => item.workspaceId === workspace.id && item.role === 'master' && item.status === 'active');
    const account = user && accountFromMembership({ userId: user.id, workspaceId: user.workspaceId });
    return workspace && user && account ? { workspace, user, account } : null;
  }).filter((item): item is NonNullable<typeof item> => Boolean(item));
  const companyWorkspaceId = baseAccounts.find(item => item.account.type === 'company')?.workspace.id;
  const managedAccounts = workspaces.filter(item => item.parentWorkspaceId === companyWorkspaceId).map(workspace => {
    const user = users.find(item => item.workspaceId === workspace.id && item.role === 'master' && item.status === 'active');
    const account = user && accountFromMembership({ userId: user.id, workspaceId: workspace.id });
    return user && account ? { workspace, user, account } : null;
  }).filter((item): item is NonNullable<typeof item> => Boolean(item));
  const accounts = [...baseAccounts, ...managedAccounts];
  if (!accounts.length) return null;
  const cookieProfile = cookieValue(req, DEVELOPMENT_PROFILE_COOKIE);
  const configuredType = process.env.CLICKO_DEV_AUTH_BYPASS_PROFILE === 'personal' ? 'personal' : 'company';
  const requestedType = cookieProfile === 'personal' || cookieProfile === 'company' ? cookieProfile : configuredType;
  const active = accounts.find(item => item.workspace.id === cookieProfile) || accounts.find(item => !item.workspace.parentWorkspaceId && item.account.type === requestedType) || accounts[0];
  return { ...active, accounts: accounts.map(item => item.account) };
}
const developmentProfileCookie = (workspaceId: string) => `${DEVELOPMENT_PROFILE_COOKIE}=${workspaceId}; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800`;
function resolveBrowserSession(req: Request) {
  // With the explicit server-side development flag enabled, use the same
  // preview context for session discovery, profile switching and API access.
  // A leftover real-login cookie must not hide the two development profiles.
  // Production and flag-disabled sessions keep their original membership rules.
  if (resolveDevelopmentBypass(req)) return null;
  const token = cookieValue(req, SESSION_COOKIE);
  if (!token) return null;
  const record = authSessions.find(item => item.tokenHash === sha256(token) && Date.parse(item.expiresAt) > Date.now());
  if (!record) return null;
  const credential = authCredentials.find(item => item.id === record.credentialId && item.verifiedAt);
  const membership = credential?.memberships.find(item => item.workspaceId === record.workspaceId);
  const account = membership ? accountFromMembership(membership) : null;
  if (!credential || !account) return null;
  const user = users.find(item => item.id === account.userId && item.workspaceId === account.workspaceId)!;
  return { token, record, credential, account, user };
}
function createBrowserSession(credential: AuthCredential, workspaceId: string, remember: boolean) {
  const membership = credential.memberships.find(item => item.workspaceId === workspaceId) || credential.memberships[0];
  if (!membership) throw new Error('AUTH_MEMBERSHIP_REQUIRED');
  const token = randomBytes(32).toString('base64url');
  const maxAgeSeconds = remember ? 30 * 86_400 : 12 * 3_600;
  const record: AuthSessionRecord = { id: id('session'), tokenHash: sha256(token), credentialId: credential.id, workspaceId: membership.workspaceId, createdAt: nowIso(), expiresAt: new Date(Date.now() + maxAgeSeconds * 1000).toISOString() };
  authSessions.push(record);
  return { token, record, maxAgeSeconds };
}
function authPayload(credential: AuthCredential, activeWorkspaceId: string) {
  const accounts = credential.memberships.map(accountFromMembership).filter((item): item is UserAccount => Boolean(item));
  const account = accounts.find(item => item.workspaceId === activeWorkspaceId) || accounts[0];
  if (!account) throw new Error('AUTH_ACCOUNT_REQUIRED');
  return { account, accounts, user: users.find(item => item.id === account.userId && item.workspaceId === account.workspaceId)! };
}
const loginAttempts = new Map<string, { count: number; resetAt: number }>();
function checkLoginThrottle(key: string) {
  const current = loginAttempts.get(key);
  if (!current || current.resetAt <= Date.now()) { loginAttempts.set(key, { count: 1, resetAt: Date.now() + 15 * 60_000 }); return true; }
  current.count += 1;
  return current.count <= 8;
}

function requireSameOrigin(req: Request, res: Response, next: NextFunction) {
  const origin = req.header('origin');
  if (origin) {
    try { if (new URL(origin).host !== req.header('host')) return res.status(403).json({ error: 'Origem da solicitação não autorizada.' }); }
    catch { return res.status(403).json({ error: 'Origem da solicitação inválida.' }); }
  }
  next();
}

export function authenticate(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  if (devConfiguration()) {
    const expiresAt = resolveDevSession(req);
    if (!expiresAt) return res.status(401).json({ code: 'DEV_SESSION_REQUIRED', error: 'Atualize a página para iniciar a sessão local DEV.' });
    const payload = devAuthPayload(expiresAt);
    req.auth = { workspaceId: DEV_WORKSPACE_ID, user: payload.user };
    return next();
  }
  const browserSession = resolveBrowserSession(req);
  if (browserSession) {
    req.auth = { workspaceId: browserSession.account.workspaceId, user: browserSession.user };
    return next();
  }
  const developmentBypass = resolveDevelopmentBypass(req);
  if (developmentBypass) {
    req.auth = { workspaceId: developmentBypass.workspace.id, user: developmentBypass.user };
    return next();
  }
  // Header identities exist only for isolated test processes. Runtime clients
  // must prove possession of an opaque HTTP-only session cookie.
  if (process.env.NODE_ENV !== 'test') return res.status(401).json({ error: 'Sua sessão expirou. Entre novamente para continuar.' });
  const workspaceId = String(req.header('x-workspace-id') || '').trim();
  const userId = String(req.header('x-user-id') || '').trim();
  if (!workspaceId || !userId) return res.status(401).json({ error: 'Identifique o usuário e o ambiente antes de continuar.' });
  const user = users.find((item) => item.id === userId && item.workspaceId === workspaceId);
  if (!user || user.status !== 'active') return res.status(401).json({ error: 'Sessão inválida ou usuário inativo.' });
  if (!workspaces.some((item) => item.id === workspaceId)) return res.status(404).json({ error: 'Ambiente de trabalho não encontrado.' });
  req.auth = { workspaceId, user };
  next();
}

export function masterOnly(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  if (!isPrivilegedRole(req.auth?.user.role)) return res.status(403).json({ error: 'Apenas um administrador autorizado pode realizar esta ação.' });
  next();
}

export function permissionOnly(permission: OrganizationPermission, options: { requireSubscription?: boolean } = {}) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction) => {
    try { assertGovernanceAccess(req.auth!, { permission }, options); }
    catch (error) {
      const failure = error as Error & { status?: number; code?: string };
      return res.status(failure.status || 403).json({ error: failure.message, code: failure.code || 'PERMISSION_DENIED', permission });
    }
    next();
  };
}

export function memberHasScope(user: WorkspaceMember, kind: 'client' | 'socialAccount' | 'project' | 'resource', resourceId: string) {
  if (isPrivilegedRole(user.role)) return true;
  const scope = user.scope;
  if (!scope) return false;
  if (kind === 'client') return scope.allClients || scope.clientIds.includes(resourceId);
  if (kind === 'socialAccount') return scope.allSocialAccounts || scope.socialAccountIds.includes(resourceId);
  if (kind === 'project') return scope.allProjects || scope.projectIds.includes(resourceId);
  return scope.resourceIds.includes(resourceId);
}

export function assertGovernanceAccess(auth: AuthContext, input: { permission?: OrganizationPermission; module?: WorkspaceModule; capability?: PlanCapability; clientId?: string | null; socialAccountId?: string | null }, options: { requireSubscription?: boolean } = {}) {
  const user = users.find(item => item.id === auth.user.id && item.workspaceId === auth.workspaceId && item.status === 'active');
  const workspace = workspaces.find(item => item.id === auth.workspaceId);
  if (!user || !workspace) throw Object.assign(new Error('Sessão ou vínculo inativo.'), { status: 403, code: 'MEMBERSHIP_INACTIVE' });
  const subscription = subscriptionForWorkspace(workspace.id);
  if (options.requireSubscription !== false && !subscriptionAccessAllowed(subscription)) {
    throw Object.assign(new Error('Regularize a assinatura para acessar os recursos da Clicko.'), { status: 402, code: 'SUBSCRIPTION_REQUIRED', subscriptionStatus: subscription?.status || 'no_plan' });
  }
  const capability = input.capability || capabilityForModule(input.module) || capabilityForPermission(input.permission);
  if (capability && subscription && !subscriptionCapability(subscription, capability)) {
    throw Object.assign(new Error('Este recurso não está incluído no plano contratado.'), { status: 403, code: 'PLAN_CAPABILITY_REQUIRED', capability });
  }
  if (workspace.kind === 'organization' && !isPrivilegedRole(user.role)) {
    const license = licenses.find(item => item.id === user.licenseId && item.workspaceId === workspace.id && item.memberId === user.id && item.status === 'in_use');
    if (!license) throw Object.assign(new Error('Este membro não possui uma licença ativa.'), { status: 403, code: 'LICENSE_REQUIRED' });
  }
  if (input.permission && !hasPermission(user, input.permission)) throw Object.assign(new Error('Ação não permitida para este papel.'), { status: 403, code: 'PERMISSION_DENIED' });
  if (input.module && !isPrivilegedRole(user.role) && !user.modules.includes(input.module)) throw Object.assign(new Error('Módulo não liberado para este membro.'), { status: 403, code: 'MODULE_DENIED' });
  if (input.clientId && !memberHasScope(user, 'client', input.clientId)) throw Object.assign(new Error('Cliente fora do escopo deste membro.'), { status: 403, code: 'CLIENT_SCOPE_DENIED' });
  if (input.socialAccountId && !memberHasScope(user, 'socialAccount', input.socialAccountId)) throw Object.assign(new Error('Conta social fora do escopo deste membro.'), { status: 403, code: 'SOCIAL_SCOPE_DENIED' });
  return user;
}

function applyGovernanceUsage(auth: AuthContext, resource: UsageResource, amount = 1) {
  if (!Number.isFinite(amount) || amount <= 0) throw Object.assign(new Error('Consumo inválido.'), { status: 400, code: 'USAGE_AMOUNT_INVALID' });
  const user = assertGovernanceAccess(auth, {});
  const subscription = subscriptionForWorkspace(auth.workspaceId)!;
  const capability = resourceCapability(resource);
  if (capability && !subscriptionCapability(subscription, capability)) throw Object.assign(new Error('Este recurso não está incluído no plano contratado.'), { status: 403, code: 'PLAN_CAPABILITY_REQUIRED', capability });
  const pool = usagePools.find(item => item.workspaceId === auth.workspaceId) || (() => { const created = newUsagePool(auth.workspaceId); usagePools.push(created); return created; })();
  const allowance = pool.resources[resource];
  const memberUsed = pool.memberUsage[user.id]?.[resource] || 0;
  const memberLimit = pool.memberLimits[user.id]?.[resource];
  if (allowance.limit !== null && allowance.used + amount > allowance.limit) throw Object.assign(new Error('O limite contratado para este recurso foi atingido.'), { status: 409, code: 'USAGE_POOL_EXHAUSTED' });
  if (pool.allocationMode === 'member_limits' && memberLimit !== undefined && memberLimit !== null && memberUsed + amount > memberLimit) throw Object.assign(new Error('Seu limite individual para este recurso foi atingido.'), { status: 409, code: 'MEMBER_USAGE_EXHAUSTED' });
  allowance.used += amount;
  pool.memberUsage[user.id] ||= {};
  pool.memberUsage[user.id][resource] = memberUsed + amount;
  return { resource, amount, allowance: structuredClone(allowance), memberUsed: memberUsed + amount };
}

function persistUsageChange<T>(change: () => T): T {
  const before = snapshot();
  try {
    const result = change();
    repository?.save(snapshot());
    return result;
  } catch (error) {
    restore(before);
    const failure = error as { status?: number; code?: string };
    if (failure.status >= 400 && failure.status < 600 && failure.code) throw error;
    throw Object.assign(new Error('Não foi possível registrar o consumo. O saldo anterior foi preservado.'), { status: 503, code: 'USAGE_PERSISTENCE_UNAVAILABLE' });
  }
}

export function consumeGovernanceUsage(auth: AuthContext, resource: UsageResource, amount = 1) {
  return persistUsageChange(() => applyGovernanceUsage(auth, resource, amount));
}

/** Same workspace/client/key is one job, independently of browser retries or actor. */
export function reserveStudioImageUsage(auth: AuthContext, receiptId: string, fingerprint: string) {
  assertGovernanceAccess(auth, { module: 'create-image', capability: 'image_generation' });
  if (!/^[a-f0-9]{64}$/.test(receiptId) || !/^[a-f0-9]{64}$/.test(fingerprint))
    throw Object.assign(new Error('Identidade do pedido inválida.'), { status: 400, code: 'IMAGE_USAGE_ID_INVALID' });
  const existing = studioImageUsageReceipts.find(item => item.workspaceId === auth.workspaceId && item.id === receiptId);
  if (existing) {
    if (existing.fingerprint !== fingerprint)
      throw Object.assign(new Error('Esta chave já identifica outro pedido de imagem. Confira o pedido original.'), { status: 409, code: 'IMAGE_IDEMPOTENCY_CONFLICT' });
    return existing.id;
  }
  return persistUsageChange(() => {
    applyGovernanceUsage(auth, 'image_generations', 1);
    const pool = usagePools.find(item => item.workspaceId === auth.workspaceId)!;
    studioImageUsageReceipts.push({ id: receiptId, workspaceId: auth.workspaceId, memberId: auth.user.id, periodStartedAt: pool.periodStartedAt, fingerprint, status: 'reserved', createdAt: nowIso() });
    return receiptId;
  });
}

/** Only a confirmed pre-admission rejection releases quota. Job failures never do. */
export function settleStudioImageUsage(auth: AuthContext, receiptId: string, jobId?: string) {
  const receipt = studioImageUsageReceipts.find(item => item.workspaceId === auth.workspaceId && item.id === receiptId);
  if (!receipt || receipt.status === 'accepted') return;
  persistUsageChange(() => {
    if (jobId) {
      receipt.status = 'accepted';
      receipt.jobId = jobId;
      addAudit(auth, 'usage.image.accepted', 'image_generations', `Uma solicitação de imagem aceita: ${jobId}`);
    } else {
      const pool = usagePools.find(item => item.workspaceId === receipt.workspaceId && item.periodStartedAt === receipt.periodStartedAt);
      if (pool) {
        pool.resources.image_generations.used = Math.max(0, pool.resources.image_generations.used - 1);
        const member = pool.memberUsage[receipt.memberId];
        if (member) member.image_generations = Math.max(0, (member.image_generations || 0) - 1);
      }
      studioImageUsageReceipts.splice(studioImageUsageReceipts.indexOf(receipt), 1);
    }
  });
}

/** Only generated scenes consume minutes. Editor exports/previews never call this. */
export function reserveStudioVideoUsage(auth: AuthContext, id: string, fingerprint: string, seconds: number) {
  assertGovernanceAccess(auth, { module: 'create-video', capability: 'video_generation' });
  if (!/^[a-f0-9]{64}$/.test(id) || !/^[a-f0-9]{64}$/.test(fingerprint) || !Number.isFinite(seconds) || seconds <= 0 || seconds > 3600)
    throw Object.assign(new Error('Solicitação de vídeo inválida.'), { status: 422, code: 'VIDEO_REQUEST_INVALID' });
  const existing = studioVideoUsageReceipts.find(row => row.workspaceId === auth.workspaceId && row.id === id);
  if (existing) {
    if (existing.fingerprint !== fingerprint) throw Object.assign(new Error('Chave já utilizada para outro vídeo.'), { status: 409, code: 'VIDEO_IDEMPOTENCY_CONFLICT' });
    if (existing.status !== 'released') return;
  }
  persistUsageChange(() => {
    // Covers the existing technical duration tolerance without exceeding a pre-authorized hold.
    const minutes = (seconds + .15) / 60;
    applyGovernanceUsage(auth, 'video_minutes', minutes);
    const pool = usagePools.find(row => row.workspaceId === auth.workspaceId)!;
    if (existing) studioVideoUsageReceipts.splice(studioVideoUsageReceipts.indexOf(existing), 1);
    studioVideoUsageReceipts.push({ id, fingerprint, workspaceId: auth.workspaceId, memberId: auth.user.id,
      periodStartedAt: pool.periodStartedAt, status: 'reserved', seconds, chargedMinutes: minutes, createdAt: nowIso() });
  });
}

export function settleStudioVideoUsage(auth: AuthContext, id: string, outcome: { jobId?: string; seconds?: number; release?: boolean }) {
  const receipt = studioVideoUsageReceipts.find(row => row.workspaceId === auth.workspaceId && row.id === id);
  if (!receipt || receipt.status === 'settled' || receipt.status === 'released') return;
  if (outcome.seconds !== undefined && (!Number.isFinite(outcome.seconds) || outcome.seconds < 0 || outcome.seconds > receipt.seconds + .15 + 1e-6))
    throw Object.assign(new Error('Duração gerada fora da reserva autorizada.'), { status: 502, code: 'VIDEO_DURATION_UNCONFIRMED' });
  persistUsageChange(() => {
    if (outcome.jobId) { receipt.jobId = outcome.jobId; receipt.status = 'accepted'; }
    if (!outcome.release && outcome.seconds === undefined) return;
    const charged = outcome.release ? 0 : outcome.seconds! / 60;
    const refund = Math.max(0, receipt.chargedMinutes - charged);
    const pool = usagePools.find(row => row.workspaceId === receipt.workspaceId && row.periodStartedAt === receipt.periodStartedAt);
    if (pool) {
      pool.resources.video_minutes.used = Math.max(0, pool.resources.video_minutes.used - refund);
      const member = pool.memberUsage[receipt.memberId];
      if (member) member.video_minutes = Math.max(0, (member.video_minutes || 0) - refund);
    }
    receipt.chargedMinutes = charged;
    receipt.status = outcome.release ? 'released' : 'settled';
    addAudit(auth, 'usage.video.' + receipt.status, 'video_minutes', `Cenas geradas: ${outcome.seconds || 0} segundos. Editor não tarifado.`);
  });
}

export function reconcileStudioVideoJob(auth: AuthContext, job: Record<string, any>) {
  const receipt = studioVideoUsageReceipts.find(row => row.workspaceId === auth.workspaceId && row.jobId === job.id);
  if (!receipt) return;
  if (job.status === 'succeeded' && typeof job.result?.generatedVideoSeconds === 'number' && job.result?.assetId && job.result?.checksumSha256)
    settleStudioVideoUsage(auth, receipt.id, { seconds: job.result.generatedVideoSeconds });
  else if (['failed', 'cancelled'].includes(job.status) && (!job.result?.submissionStarted || job.result?.submissionOutcome === 'rejected' || job.result?.responseKey))
    settleStudioVideoUsage(auth, receipt.id, { release: true });
}

/** Read-only adapter for internal orchestration; caller must hold a resolved session. */
export function readGovernanceAccountType(auth: AuthContext) {
  assertGovernanceAccess(auth, {});
  const workspace = workspaces.find(item => item.id === auth.workspaceId);
  if (!workspace) throw Object.assign(new Error('Ambiente de trabalho não encontrado.'), { status: 404, code: 'WORKSPACE_NOT_FOUND' });
  return workspace.kind === 'personal' ? 'personal' as const : 'company' as const;
}

export function readStudioWorkspace(auth: AuthContext, clientId: string | null) {
  assertGovernanceAccess(auth, { clientId });
  const workspace = workspaces.find(item => item.id === auth.workspaceId)!;
  const client = clientId ? registeredClients.find(item => item.id === clientId && item.workspaceId === workspace.id) : undefined;
  if (clientId && !client) throw Object.assign(new Error('Cliente não encontrado neste ambiente.'), { status: 404, code: 'CLIENT_NOT_FOUND' });
  return { name: client?.name || workspace.name };
}

/** Read-only KLIC adapter; unlike generic workspace readers, this requires the AI module. */
export function readKlicGovernance(auth: AuthContext) {
  const user = assertGovernanceAccess(auth, { module: 'ai-chat' });
  const workspace = workspaces.find(item => item.id === auth.workspaceId);
  if (!workspace) throw new Error('KLIC_SESSION_REVOKED');
  return {
    accountType: workspace.kind === 'personal' ? 'personal' as const : 'company' as const,
    user: structuredClone(user),
    approvals: hasPermission(user, 'content.approve') ? structuredClone(approvals.filter(item => item.workspaceId === workspace.id).slice(0, 80).map(({ id, workspaceId, contentId, title, stage, scheduledAt }) => ({ id, workspaceId, contentId, title, stage, scheduledAt }))) : [],
    team: hasPermission(user, 'members.read') ? users.filter(item => item.workspaceId === workspace.id).slice(0, 80).map(({ id, workspaceId, name, role, status }) => ({ id, workspaceId, name, role, status })) : [],
    history: auditLogs.filter(item => item.workspaceId === workspace.id && item.actorId === user.id).slice(0, 20).map(({ id, workspaceId, action, createdAt }) => ({ id, workspaceId, action, createdAt })),
  };
}

function moduleOnly(req: AuthenticatedRequest, res: Response, next: NextFunction) {
  const requestedModule = String(req.params.moduleId || '') as WorkspaceModule;
  if (!moduleIds.includes(requestedModule)) return res.status(404).json({ error: 'Módulo desconhecido.' });
  try { assertGovernanceAccess(req.auth!, { module: requestedModule }); }
  catch (error) { const failure = error as Error & { status?: number; code?: string }; return res.status(failure.status || 403).json({ error: failure.message, code: failure.code }); }
  next();
}

function validModules(value: unknown): WorkspaceModule[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is WorkspaceModule => moduleIds.includes(item as WorkspaceModule));
}

function normalizeScope(value: unknown): AccessScope {
  const scope = value && typeof value === 'object' ? value as Partial<AccessScope> : {};
  const ids = (candidate: unknown) => Array.isArray(candidate) ? [...new Set(candidate.filter((item): item is string => typeof item === 'string' && item.length > 0 && item.length <= 160))] : [];
  return {
    allClients: scope.allClients === true,
    clientIds: ids(scope.clientIds),
    allSocialAccounts: scope.allSocialAccounts === true,
    socialAccountIds: ids(scope.socialAccountIds),
    allProjects: scope.allProjects === true,
    projectIds: ids(scope.projectIds),
    resourceIds: ids(scope.resourceIds),
  };
}

function publishingConfigured(platform: ContentApprovalItem['platform']) {
  if (platform === 'instagram' || platform === 'facebook') return Boolean((process.env.META_APP_ID || process.env.META_CLIENT_ID) && (process.env.META_APP_SECRET || process.env.META_CLIENT_SECRET));
  if (platform === 'threads') return Boolean(process.env.THREADS_APP_ID && process.env.THREADS_APP_SECRET);
  if (platform === 'linkedin') return Boolean(process.env.LINKEDIN_CLIENT_ID && process.env.LINKEDIN_CLIENT_SECRET);
  if (platform === 'youtube') return Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
  if (platform === 'tiktok') return Boolean(process.env.TIKTOK_CLIENT_KEY && process.env.TIKTOK_CLIENT_SECRET);
  return false;
}

const statusEvent = (status: SubscriptionStatus): 'activated' | 'payment_failed' | 'renewed' | 'canceled' | 'suspended' | 'ended' => {
  if (status === 'active' || status === 'trialing') return 'activated';
  if (status === 'payment_failed' || status === 'past_due') return 'payment_failed';
  if (status === 'canceled') return 'canceled';
  if (status === 'suspended') return 'suspended';
  if (status === 'ended') return 'ended';
  return 'renewed';
};

function transitionSubscription(workspaceId: string, status: SubscriptionStatus, providerEventId?: string, detail?: { planId?: SaaSPlan['id']; billingCycle?: NonNullable<WorkspaceSubscription['billingCycle']>; providerCustomerId?: string; providerSubscriptionId?: string; renewsAt?: string; paymentMethod?: string }) {
  const subscription = subscriptionForWorkspace(workspaceId);
  const workspace = workspaces.find(item => item.id === workspaceId);
  if (!subscription || !workspace) throw new Error('BILLING_WORKSPACE_NOT_FOUND');
  const previousStatus = subscription.status;
  const previousPlanId = subscription.planId;
  const plan = plans.find(item => item.id === (detail?.planId || subscription.pendingPlanId || subscription.planId));
  if (!plan) throw new Error('BILLING_PLAN_NOT_FOUND');
  if (status === 'active' || status === 'trialing') {
    subscription.planId = plan.id;
    subscription.pendingPlanId = undefined;
    subscription.billingCycle = detail?.billingCycle || subscription.pendingBillingCycle || subscription.billingCycle || 'monthly';
    subscription.pendingBillingCycle = undefined;
    subscription.entitlementSnapshot = captureEntitlements(plan);
    subscription.provider = 'stripe';
    if (['no_plan', 'pending_checkout', 'pending_payment'].includes(previousStatus)) subscription.startedAt = nowIso();
    subscription.renewsAt = detail?.renewsAt || new Date(Date.now() + (subscription.billingCycle === 'annual' ? 365 : 30) * 86_400_000).toISOString();
    subscription.canceledAt = undefined;
    subscription.endsAt = undefined;
    subscription.cancelAtPeriodEnd = false;
    workspace.planId = plan.id;
    workspace.maxUsers = plan.maxUsers;
    workspace.kind = plan.audience === 'personal' ? 'personal' : 'organization';
    const pool = usagePools.find(item => item.workspaceId === workspaceId) || (() => { const created = newUsagePool(workspaceId); usagePools.push(created); return created; })();
    for (const resource of usageResources) pool.resources[resource].limit = entitlementLimit(workspaceId, resource);
    if (workspace.kind === 'organization') {
      const checkout = billingCheckoutSessions.find(item => item.workspaceId === workspaceId && item.status === 'completed');
      const targetSeats = Math.max(plan.includedLicenses || 1, checkout?.seats || 1);
      while (licenses.filter(item => item.workspaceId === workspaceId).length < targetSeats) licenses.push({ id: id('license'), workspaceId, status: 'available', createdAt: nowIso(), updatedAt: nowIso() });
      const owner = users.find(item => item.workspaceId === workspaceId && item.id === workspace.ownerUserId);
      if (owner && !owner.licenseId) {
        const license = licenses.find(item => item.workspaceId === workspaceId && item.status === 'available');
        if (license) { license.status = 'in_use'; license.memberId = owner.id; license.updatedAt = nowIso(); owner.licenseId = license.id; }
      }
    }
  }
  subscription.status = status;
  subscription.providerCustomerId = detail?.providerCustomerId || subscription.providerCustomerId;
  subscription.providerSubscriptionId = detail?.providerSubscriptionId || subscription.providerSubscriptionId;
  if (detail?.paymentMethod) subscription.paymentMethod = detail.paymentMethod;
  subscription.history ||= [];
  const event = (status === 'active' || status === 'trialing')
    ? (previousPlanId !== plan.id ? 'plan_changed' : previousStatus === 'active' ? 'renewed' : ['past_due', 'payment_failed', 'suspended'].includes(previousStatus) ? 'reactivated' : 'activated')
    : statusEvent(status);
  subscription.history.push({ id: id('sub-history'), event, fromStatus: previousStatus, toStatus: status, planId: plan.id, occurredAt: nowIso(), providerEventId });
  workspace.subscriptionStatus = status;
  return subscription;
}

function stripeSignatureValid(req: Request, secret: string) {
  const signatureHeader = String(req.header('stripe-signature') || '');
  const parts = Object.fromEntries(signatureHeader.split(',').map(item => item.split('=', 2)).filter(pair => pair.length === 2));
  const timestamp = Number(parts.t);
  const signature = parts.v1;
  const rawBody = (req as Request & { rawBody?: Buffer }).rawBody;
  if (!rawBody || !Number.isFinite(timestamp) || !signature || Math.abs(Date.now() / 1000 - timestamp) > 300) return false;
  const expected = createHmac('sha256', secret).update(`${timestamp}.${rawBody.toString('utf8')}`).digest('hex');
  const actualBuffer = Buffer.from(signature, 'hex');
  const expectedBuffer = Buffer.from(expected, 'hex');
  return actualBuffer.length === expectedBuffer.length && timingSafeEqual(actualBuffer, expectedBuffer);
}

function stripePriceId(planId: SaaSPlan['id']) {
  return ({ solo: process.env.STRIPE_PRICE_SOLO, team: process.env.STRIPE_PRICE_TEAM, business: process.env.STRIPE_PRICE_BUSINESS, enterprise: process.env.STRIPE_PRICE_ENTERPRISE, development: undefined })[planId];
}

function stripeAnnualPriceId(planId: SaaSPlan['id']) {
  return ({ solo: process.env.STRIPE_PRICE_SOLO_ANNUAL, team: process.env.STRIPE_PRICE_TEAM_ANNUAL, business: process.env.STRIPE_PRICE_BUSINESS_ANNUAL, enterprise: process.env.STRIPE_PRICE_ENTERPRISE_ANNUAL, development: undefined })[planId];
}

async function createStripeCheckout(req: Request, checkout: BillingCheckoutSession, billingEmail: string) {
  if (process.env.CLICKO_DEV_MODE === 'true') throw Object.assign(new Error('DEV_EXTERNAL_PAYMENT_DISABLED'), { status: 403 });
  if (process.env.NODE_ENV === 'test' && process.env.STRIPE_TEST_CHECKOUT === 'true') {
    checkout.providerSessionId = `cs_test_${randomUUID()}`;
    return { id: checkout.providerSessionId, url: `https://checkout.stripe.test/${checkout.providerSessionId}` };
  }
  const secret = process.env.STRIPE_SECRET_KEY;
  const plan = plans.find(item => item.id === checkout.planId);
  const price = checkout.billingCycle === 'annual' ? stripeAnnualPriceId(checkout.planId) : stripePriceId(checkout.planId);
  if (!secret || !plan || plan.monthlyPrice === null || (checkout.billingCycle === 'monthly' && !price)) throw Object.assign(new Error('A cobrança ainda não está configurada neste ambiente.'), { status: 503, code: 'BILLING_NOT_CONFIGURED' });
  const origin = `${req.protocol}://${req.get('host')}`;
  const body = new URLSearchParams({
    mode: 'subscription',
    success_url: `${origin}/subscription?checkout=return`,
    cancel_url: `${origin}/subscription?checkout=canceled`,
    customer_email: billingEmail,
    ...(price ? { 'line_items[0][price]': price, 'line_items[0][quantity]': String(checkout.seats) } : {
      'line_items[0][price_data][currency]': 'brl',
      'line_items[0][price_data][unit_amount]': String(Math.round(plan.monthlyPrice * 12 * 100)),
      'line_items[0][price_data][recurring][interval]': 'year',
      'line_items[0][price_data][product_data][name]': `Clicko ${plan.name} — anual`,
      'line_items[0][quantity]': '1',
    }),
    'metadata[checkoutId]': checkout.id,
    'metadata[workspaceId]': checkout.workspaceId,
    'metadata[planId]': checkout.planId,
    'metadata[billingCycle]': checkout.billingCycle,
    'subscription_data[metadata][workspaceId]': checkout.workspaceId,
    'subscription_data[metadata][planId]': checkout.planId,
    'subscription_data[metadata][billingCycle]': checkout.billingCycle,
  });
  const response = await fetch('https://api.stripe.com/v1/checkout/sessions', { method: 'POST', headers: { Authorization: `Bearer ${secret}`, 'Content-Type': 'application/x-www-form-urlencoded' }, body });
  const payload = await response.json() as { id?: string; url?: string; error?: { message?: string; code?: string } };
  if (!response.ok || !payload.id || !payload.url) throw Object.assign(new Error('Não foi possível iniciar o checkout seguro.'), { status: 502, code: payload.error?.code || 'BILLING_PROVIDER_ERROR' });
  checkout.providerSessionId = payload.id;
  return payload;
}

export function createGovernanceRouter(options: { dataFile?: string | null } = {}) {
  const dev = devConfiguration();
  if (dev && options.dataFile !== undefined && path.resolve(options.dataFile || '') !== path.join(dev.root, 'governance.json'))
    throw new Error('DEV_GOVERNANCE_STORE_MUST_BE_ISOLATED');
  prepareDevGovernance();
  configurePersistence(options.dataFile === undefined ? process.env.CLICKO_GOVERNANCE_DATA_FILE || path.resolve('.clicko-data', 'governance.json') : options.dataFile);
  if (dev && (workspaces.some(item => item.id !== DEV_WORKSPACE_ID)
      || !workspaces.some(item => item.id === DEV_WORKSPACE_ID && item.planId === 'development')
      || !registeredClients.some(item => item.id === DEV_CLIENT_ID && item.workspaceId === DEV_WORKSPACE_ID)))
    throw new Error('DEV_STORE_CONTAINS_UNEXPECTED_IDENTITIES');
  ensureGovernanceModel();
  if (dev) repository?.save(snapshot());
  const router = Router();
  // Decode before taking the mutation snapshot: the existing commit/rollback
  // boundary remains synchronous even when multiple uploads are in flight.
  router.put('/profile/avatar', authenticate, requireSameOrigin,
    raw({ type: AVATAR_TYPES, limit: MAX_AVATAR_BYTES }),
    async (req: AuthenticatedRequest, res, next) => {
      if (req.header('x-workspace-id') !== req.auth!.workspaceId) return res.status(409).json({ error: 'O perfil ativo mudou. Selecione a foto novamente.' });
      if (!AVATAR_TYPES.includes(req.header('content-type')?.split(';')[0] || '')) return res.status(415).json({ error: 'Selecione uma imagem JPG, PNG ou WebP.' });
      if (!Buffer.isBuffer(req.body) || !req.body.length) return res.status(400).json({ error: 'Selecione uma imagem válida.' });
      try { res.locals.avatar = await normalizeProfileAvatar(req.body); next(); }
      catch { res.status(422).json({ error: 'Não foi possível abrir a imagem. Use um JPG, PNG ou WebP válido, sem animação.' }); }
    });
  router.use((error: { type?: string }, _req: Request, res: Response, next: NextFunction) => {
    if (error.type === 'entity.too.large') return res.status(413).json({ error: 'A imagem deve possuir no máximo 5 MB.' });
    next(error);
  });
  router.use(persistMutation);

  router.post('/billing/webhook', (req, res) => {
    const secret = process.env.STRIPE_WEBHOOK_SECRET;
    if (!secret || !stripeSignatureValid(req, secret)) return res.status(400).json({ error: 'Assinatura do webhook inválida.', code: 'BILLING_WEBHOOK_SIGNATURE_INVALID' });
    const event = req.body as { id?: string; type?: string; data?: { object?: any } };
    if (!event.id || !event.type || !event.data?.object) return res.status(400).json({ error: 'Evento de cobrança inválido.', code: 'BILLING_EVENT_INVALID' });
    if (processedBillingEvents.some(item => item.eventId === event.id)) return res.json({ received: true, duplicate: true });
    const object = event.data.object;
    const managedClient = registeredClients.find(item =>
      (item.providerCheckoutSessionId && item.providerCheckoutSessionId === object.id)
      || (item.providerSubscriptionId && [object.id, object.subscription].includes(item.providerSubscriptionId)));
    if (managedClient) {
      try {
        if (event.type === 'checkout.session.completed') {
          if (object.payment_status !== 'paid' || Number(object.amount_total) <= 0 || !object.subscription) return res.status(409).json({ error: 'O pagamento ainda não foi confirmado.', code: 'PAYMENT_NOT_CONFIRMED' });
          if (managedClient.billingStatus !== 'checkout_pending') return res.status(409).json({ error: 'Checkout não está pendente.', code: 'BILLING_CHECKOUT_NOT_PENDING' });
          activateManagedWorkspace(managedClient, String(object.subscription), String(object.customer || ''), event.id);
        } else if (event.type === 'checkout.session.expired') {
          managedClient.billingStatus = 'none'; managedClient.providerCheckoutSessionId = undefined;
        } else if (event.type === 'invoice.paid') {
          managedClient.billingStatus = 'active';
          if (managedClient.linkedWorkspaceId) transitionSubscription(managedClient.linkedWorkspaceId, 'active', event.id);
        } else if (event.type === 'invoice.payment_failed') {
          managedClient.billingStatus = 'past_due';
          if (managedClient.linkedWorkspaceId) transitionSubscription(managedClient.linkedWorkspaceId, 'payment_failed', event.id);
        } else if (event.type === 'customer.subscription.updated') {
          const active = ['active', 'trialing'].includes(String(object.status));
          managedClient.billingStatus = active ? 'active' : 'past_due';
          if (managedClient.linkedWorkspaceId) transitionSubscription(managedClient.linkedWorkspaceId, active ? 'active' : 'past_due', event.id);
        } else if (event.type === 'customer.subscription.deleted') {
          managedClient.billingStatus = 'ended';
          if (managedClient.linkedWorkspaceId) transitionSubscription(managedClient.linkedWorkspaceId, 'ended', event.id);
        }
        managedClient.updatedAt = nowIso();
        processedBillingEvents.push({ eventId: event.id, provider: 'stripe', type: event.type, workspaceId: managedClient.workspaceId, processedAt: nowIso() });
        auditLogs.unshift({ id: id('audit'), workspaceId: managedClient.workspaceId, actorId: 'billing-provider', actorName: 'Stripe', action: `client-operation.${event.type}`, resource: `client:${managedClient.id}`, detail: 'Estado da operação atualizado por evento autenticado do provedor.', createdAt: nowIso() });
        return res.json({ received: true, duplicate: false });
      } catch { return res.status(422).json({ error: 'O evento não corresponde a uma operação gerenciada válida.', code: 'MANAGED_BILLING_EVENT_INVALID' }); }
    }
    let workspaceId = String(object.metadata?.workspaceId || object.subscription_details?.metadata?.workspaceId || '');
    if (!workspaceId && object.subscription) workspaceId = subscriptions.find(item => item.providerSubscriptionId === object.subscription)?.workspaceId || '';
    if (!workspaceId && object.id) workspaceId = subscriptions.find(item => item.providerSubscriptionId === object.id)?.workspaceId || '';
    try {
      if (event.type === 'checkout.session.completed') {
        const checkoutId = String(object.metadata?.checkoutId || '');
        const checkout = billingCheckoutSessions.find(item => item.id === checkoutId && item.providerSessionId === object.id && item.status === 'created');
        if (!checkout || !['paid', 'no_payment_required'].includes(String(object.payment_status))) return res.status(409).json({ error: 'O pagamento ainda não foi confirmado.', code: 'PAYMENT_NOT_CONFIRMED' });
        checkout.status = 'completed'; checkout.completedAt = nowIso(); workspaceId = checkout.workspaceId;
        transitionSubscription(workspaceId, 'active', event.id, { planId: checkout.planId, billingCycle: checkout.billingCycle, providerCustomerId: String(object.customer || ''), providerSubscriptionId: String(object.subscription || ''), paymentMethod: 'Gerenciado pelo provedor seguro' });
      } else if (event.type === 'checkout.session.expired') {
        const checkout = billingCheckoutSessions.find(item => item.providerSessionId === object.id && item.status === 'created');
        if (!checkout) throw new Error('BILLING_CHECKOUT_NOT_FOUND');
        checkout.status = 'expired'; workspaceId = checkout.workspaceId;
        const subscription = subscriptionForWorkspace(workspaceId)!;
        subscription.status = checkout.previousStatus || 'no_plan'; subscription.pendingPlanId = undefined; subscription.pendingBillingCycle = undefined; subscription.checkoutSessionId = undefined;
        workspaces.find(item => item.id === workspaceId)!.subscriptionStatus = subscription.status;
      } else if (event.type === 'invoice.paid') {
        if (!workspaceId) throw new Error('BILLING_WORKSPACE_NOT_FOUND');
        const renewsAt = object.lines?.data?.[0]?.period?.end ? new Date(Number(object.lines.data[0].period.end) * 1000).toISOString() : undefined;
        transitionSubscription(workspaceId, 'active', event.id, { providerCustomerId: String(object.customer || ''), providerSubscriptionId: String(object.subscription || ''), renewsAt });
      } else if (event.type === 'invoice.payment_failed') {
        if (!workspaceId) throw new Error('BILLING_WORKSPACE_NOT_FOUND');
        transitionSubscription(workspaceId, 'payment_failed', event.id, { providerCustomerId: String(object.customer || ''), providerSubscriptionId: String(object.subscription || '') });
      } else if (event.type === 'customer.subscription.updated') {
        if (!workspaceId) throw new Error('BILLING_WORKSPACE_NOT_FOUND');
        const mapped: SubscriptionStatus = object.status === 'active' ? 'active' : object.status === 'trialing' ? 'trialing' : object.status === 'past_due' ? 'past_due' : object.status === 'canceled' ? 'canceled' : object.status === 'unpaid' ? 'suspended' : 'pending_payment';
        const subscription = transitionSubscription(workspaceId, mapped, event.id, { providerCustomerId: String(object.customer || ''), providerSubscriptionId: String(object.id || ''), renewsAt: object.current_period_end ? new Date(Number(object.current_period_end) * 1000).toISOString() : undefined });
        subscription.cancelAtPeriodEnd = object.cancel_at_period_end === true;
        subscription.endsAt = object.cancel_at ? new Date(Number(object.cancel_at) * 1000).toISOString() : subscription.cancelAtPeriodEnd ? subscription.renewsAt : undefined;
      } else if (event.type === 'customer.subscription.deleted') {
        if (!workspaceId) throw new Error('BILLING_WORKSPACE_NOT_FOUND');
        const subscription = transitionSubscription(workspaceId, 'ended', event.id, { providerCustomerId: String(object.customer || ''), providerSubscriptionId: String(object.id || '') });
        subscription.endsAt = nowIso();
      }
      for (const client of registeredClients.filter(item => item.linkedWorkspaceId === workspaceId && item.invitationKind === 'independent')) {
        const active = subscriptionAccessAllowed(subscriptionForWorkspace(workspaceId));
        client.operationState = active ? 'independent' : 'invited';
        client.billingStatus = active ? 'active' : 'none';
        client.updatedAt = nowIso();
      }
      processedBillingEvents.push({ eventId: event.id, provider: 'stripe', type: event.type, ...(workspaceId ? { workspaceId } : {}), processedAt: nowIso() });
      if (workspaceId) auditLogs.unshift({ id: id('audit'), workspaceId, actorId: 'billing-provider', actorName: 'Stripe', action: `billing.${event.type}`, resource: `subscription:${subscriptionForWorkspace(workspaceId)?.id || 'unknown'}`, detail: `Evento confirmado pelo provedor (${event.id})`, createdAt: nowIso() });
      return res.json({ received: true, duplicate: false });
    } catch (error) {
      const code = error instanceof Error ? error.message : 'BILLING_EVENT_FAILED';
      return res.status(code === 'BILLING_WORKSPACE_NOT_FOUND' || code === 'BILLING_PLAN_NOT_FOUND' ? 404 : 422).json({ error: 'O evento não corresponde a uma assinatura conhecida.', code });
    }
  });

  router.get('/client-portal', (req, res) => {
    const client = portalClient(req);
    if (!client) return res.status(401).json({ error: 'Convite inválido ou expirado.', code: 'PORTAL_INVITE_INVALID' });
    res.setHeader('Cache-Control', 'private, no-store');
    return res.json({ client: { name: client.name, sharedSummary: client.sharedSummary || '', portalRequests: client.portalRequests || [], portalComments: client.portalComments || [], portalDocuments: (client.portalDocuments || []).map(({ data: _data, ...metadata }) => metadata) } });
  });
  router.post('/client-portal/comments', requireSameOrigin, (req, res) => {
    const client = portalClient(req);
    if (!client) return res.status(401).json({ error: 'Convite inválido ou expirado.', code: 'PORTAL_INVITE_INVALID' });
    const message = String(req.body?.message || '').trim();
    if (!message || message.length > 2000) return res.status(400).json({ error: 'Escreva um comentário de até 2.000 caracteres.' });
    client.portalComments ||= [];
    if (client.portalComments.length >= 100) return res.status(409).json({ error: 'O limite de comentários deste convite foi atingido.' });
    client.portalComments.push({ id: id('portal-comment'), message, createdAt: nowIso() }); client.updatedAt = nowIso();
    return res.status(201).json({ saved: true });
  });
  router.post('/client-portal/requests/:requestId/approve', requireSameOrigin, (req, res) => {
    const client = portalClient(req);
    if (!client) return res.status(401).json({ error: 'Convite inválido ou expirado.', code: 'PORTAL_INVITE_INVALID' });
    const request = client.portalRequests?.find(item => item.id === req.params.requestId);
    if (!request) return res.status(404).json({ error: 'Solicitação não encontrada.' });
    if (request.status !== 'pending') return res.status(409).json({ error: 'Esta solicitação já foi respondida.' });
    request.status = 'approved'; request.decidedAt = nowIso(); client.updatedAt = nowIso();
    return res.json({ approved: true });
  });
  router.post('/client-portal/documents', requireSameOrigin, (req, res) => {
    const client = portalClient(req);
    if (!client) return res.status(401).json({ error: 'Convite inválido ou expirado.', code: 'PORTAL_INVITE_INVALID' });
    const name = String(req.body?.name || '').trim().slice(0, 120);
    const mime = String(req.body?.mime || '');
    const data = String(req.body?.data || '');
    if (!name || !['application/pdf', 'image/jpeg', 'image/png', 'image/webp'].includes(mime) || !/^[A-Za-z0-9+/]+={0,2}$/.test(data)) return res.status(400).json({ error: 'Envie um PDF, JPG, PNG ou WebP válido.' });
    const bytes = Buffer.from(data, 'base64');
    if (!bytes.length || bytes.length > 2_000_000) return res.status(413).json({ error: 'O documento deve possuir no máximo 2 MB.' });
    client.portalDocuments ||= [];
    if (client.portalDocuments.length >= 10) return res.status(409).json({ error: 'O limite de documentos deste convite foi atingido.' });
    client.portalDocuments.push({ id: id('portal-doc'), name, mime, data, uploadedAt: nowIso() }); client.updatedAt = nowIso();
    return res.status(201).json({ saved: true });
  });

  router.put('/profile/avatar', authenticate, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const normalized = res.locals.avatar as { data: string; version: string };
    const current = resolveBrowserSession(req);
    // Memberships belonging to the same authenticated person share their photo;
    // development preview identities and unrelated users remain independent.
    const memberships = current?.credential.memberships || [{ userId: auth.user.id, workspaceId: auth.workspaceId }];
    for (const membership of memberships) {
      const member = users.find(item => item.id === membership.userId && item.workspaceId === membership.workspaceId);
      if (!member) continue;
      const record = { ...membership, ...normalized };
      const index = profileAvatars.findIndex(item => item.userId === member.id && item.workspaceId === member.workspaceId);
      if (index < 0) profileAvatars.push(record); else profileAvatars[index] = record;
      member.avatar = profileAvatarUrl(member.id, normalized.version);
    }
    addAudit(auth, 'profile.avatar.updated', `user:${auth.user.id}`, 'Foto de perfil atualizada');
    res.setHeader('Cache-Control', 'no-store');
    const development = resolveDevelopmentBypass(req);
    res.json(devConfiguration() ? devAuthPayload(resolveDevSession(req)!) : current ? authPayload(current.credential, auth.workspaceId) : { account: development?.account, accounts: development?.accounts, user: auth.user });
  });

  router.get('/users/:userId/avatar', authenticate, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const owned = resolveBrowserSession(req)?.credential.memberships || [];
    const preview = resolveDevelopmentBypass(req)?.accounts || [];
    const record = profileAvatars.find(item => item.userId === req.params.userId && (
      item.workspaceId === auth.workspaceId || owned.some(member => member.userId === item.userId && member.workspaceId === item.workspaceId)
      || preview.some(account => account.userId === item.userId && account.workspaceId === item.workspaceId)
    ));
    res.setHeader('Cache-Control', 'private, no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    if (!record) return res.status(404).end();
    res.type('image/webp').send(Buffer.from(record.data, 'base64'));
  });

  router.get('/auth/session', (req, res) => {
    if (devConfiguration()) {
      if (!isLocalDevRequest(req)) return res.status(403).json({ code: 'DEV_LOCAL_REQUEST_REQUIRED' });
      try { return res.json(devAuthPayload(issueDevSession(req, res))); }
      catch { return res.status(503).json({ code: 'DEV_SESSION_UNAVAILABLE', error: 'A sessão DEV não está disponível.' }); }
    }
    const current = resolveBrowserSession(req);
    if (!current) {
      const developmentBypass = resolveDevelopmentBypass(req);
      if (!developmentBypass) return res.status(401).json({ error: 'Nenhuma sessão válida foi encontrada.' });
      res.setHeader('Cache-Control', 'no-store');
      return res.json({ account: developmentBypass.account, accounts: developmentBypass.accounts, user: developmentBypass.user });
    }
    return res.json(authPayload(current.credential, current.record.workspaceId));
  });

  router.post('/auth/signup', requireSameOrigin, (req, res) => {
    const name = normalizeFullName(req.body?.name);
    const email = normalizeEmail(req.body?.email);
    const password = String(req.body?.password || '');
    const confirmation = String(req.body?.confirmation || '');
    const validation = validateSignup({ name, email, password, confirmation, termsAccepted: req.body?.termsAccepted === true, privacyAccepted: req.body?.privacyAccepted === true });
    if (Object.keys(validation).length) return res.status(400).json({ error: firstError(validation) || 'Revise os dados informados.', code: 'VALIDATION_ERROR', fieldErrors: validation });
    if (name.length > 100) return res.status(400).json({ error: 'Informe seu nome completo.', code: 'VALIDATION_ERROR', fieldErrors: { name: 'Informe seu nome completo.' } });
    if (authCredentials.some(item => item.email === email) || users.some(item => normalizeEmail(item.email) === email)) return res.status(409).json({ error: 'Já existe uma conta utilizando este e-mail.', code: 'EMAIL_ALREADY_REGISTERED', fieldErrors: { email: 'Já existe uma conta utilizando este e-mail.' } });
    if (!checkLoginThrottle(`signup:${req.ip}`)) return res.status(429).json({ error: 'Muitas tentativas de cadastro. Aguarde alguns minutos.' });
    const createdAt = nowIso();
    const workspaceId = id('ws-personal');
    const userId = id('usr');
    const workspace: GovernanceWorkspace = { id: workspaceId, name: `${name} — Plano Pessoal`, logo: '', planId: 'solo', maxUsers: 1, activeUsers: 1, subscriptionDate: createdAt, subscriptionStatus: 'no_plan', kind: 'personal', ownerUserId: userId, settings: { inviteExpiryDays: 7, requireApproval: false, timezone: 'America/Sao_Paulo' } };
    const user: WorkspaceMember = { id: userId, workspaceId, name, email, avatar: '', role: 'master', status: 'active', modules: [...moduleIds], permissions: [...rolePresets.master.permissions], scope: allScope(), lastAccess: createdAt, createdAt };
    workspaces.push(workspace);
    users.push(user);
    subscriptions.push({ id: id('sub'), workspaceId, planId: 'solo', status: 'no_plan', startedAt: createdAt, renewsAt: '', billingEmail: email, paymentMethod: 'Não configurado', ownerType: 'personal_account', addOns: [], provider: 'none', billingCycle: 'monthly', history: [{ id: id('sub-history'), event: 'created', toStatus: 'no_plan', planId: 'solo', occurredAt: createdAt }] });
    usagePools.push(newUsagePool(workspaceId));
    const verificationRequired = process.env.AUTH_EMAIL_VERIFICATION_REQUIRED === 'true';
    const credential: AuthCredential = {
      id: id('credential'), email, passwordHash: hashPassword(password), memberships: [{ userId, workspaceId }],
      ...(verificationRequired ? {} : { verifiedAt: createdAt }), createdAt,
      legalConsent: { termsAcceptedAt: createdAt, termsVersion: CURRENT_TERMS_VERSION, privacyAcceptedAt: createdAt, privacyVersion: CURRENT_PRIVACY_VERSION },
    };
    authCredentials.push(credential);
    const clientInviteId = String(req.body?.clientInviteId || '');
    claimIndependentClientInvite(clientInviteId, String(req.body?.clientInviteToken || ''), email, workspaceId);
    let developmentToken: string | undefined;
    if (verificationRequired) {
      const token = randomBytes(32).toString('base64url');
      authActionTokens.push({ tokenHash: sha256(token), credentialId: credential.id, kind: 'verify', expiresAt: new Date(Date.now() + 24 * 3_600_000).toISOString() });
      if (process.env.NODE_ENV !== 'production' && process.env.AUTH_DEV_EXPOSE_TOKENS === 'true') developmentToken = token;
      return res.status(201).json({ verificationRequired: true, deliveryConfigured: false, ...(developmentToken ? { developmentToken } : {}) });
    }
    const session = createBrowserSession(credential, workspaceId, Boolean(req.body?.remember));
    res.setHeader('Set-Cookie', sessionCookie(session.token, session.maxAgeSeconds));
    return res.status(201).json({ verificationRequired: false, ...authPayload(credential, workspaceId) });
  });

  router.post('/auth/login', requireSameOrigin, (req, res) => {
    const email = normalizeEmail(req.body?.email);
    const password = String(req.body?.password || '');
    const throttleKey = `${req.ip}:${email}`;
    if (!checkLoginThrottle(throttleKey)) return res.status(429).json({ error: 'Muitas tentativas. Aguarde alguns minutos antes de tentar novamente.' });
    const validation = validateLogin({ email, password });
    if (Object.keys(validation).length) return res.status(400).json({ error: 'E-mail ou senha incorretos.', code: 'INVALID_CREDENTIALS' });
    const credential = authCredentials.find(item => item.email === email);
    if (!credential || !passwordMatches(password, credential.passwordHash)) return res.status(401).json({ error: 'E-mail ou senha incorretos.', code: 'INVALID_CREDENTIALS' });
    if (!credential.verifiedAt) return res.status(403).json({ error: 'Confirme seu e-mail antes de entrar.', verificationRequired: true });
    loginAttempts.delete(throttleKey);
    const preferredWorkspace = String(req.body?.workspaceId || '');
    const workspaceId = credential.memberships.some(item => item.workspaceId === preferredWorkspace) ? preferredWorkspace : credential.memberships[0]?.workspaceId;
    if (!workspaceId) return res.status(403).json({ error: 'Esta conta não possui um ambiente ativo.' });
    claimIndependentClientInvite(String(req.body?.clientInviteId || ''), String(req.body?.clientInviteToken || ''), credential.email, workspaceId);
    const session = createBrowserSession(credential, workspaceId, Boolean(req.body?.remember));
    const user = users.find(item => credential.memberships.some(membership => membership.userId === item.id && membership.workspaceId === item.workspaceId));
    if (user) user.lastAccess = nowIso();
    res.setHeader('Set-Cookie', sessionCookie(session.token, session.maxAgeSeconds));
    return res.json(authPayload(credential, workspaceId));
  });

  router.post('/auth/logout', requireSameOrigin, (req, res) => {
    if (devConfiguration()) { revokeDevSession(req, res); return res.status(204).end(); }
    const token = cookieValue(req, SESSION_COOKIE);
    if (token) {
      const index = authSessions.findIndex(item => item.tokenHash === sha256(token));
      if (index >= 0) authSessions.splice(index, 1);
    }
    res.setHeader('Set-Cookie', clearSessionCookie());
    return res.status(204).end();
  });

  router.post('/auth/forgot-password', requireSameOrigin, (req, res) => {
    const email = normalizeEmail(req.body?.email);
    const generic = { message: 'Se o e-mail estiver cadastrado, as instruções de recuperação serão enviadas.', deliveryConfigured: false };
    if (!checkLoginThrottle(`recovery:${req.ip}:${email}`)) return res.status(202).json(generic);
    let credential = isValidEmail(email) ? authCredentials.find(item => item.email === email) : undefined;
    // Legacy workspaces predate credentials. Recovery is the only claim path:
    // ownership must still be proven by the expiring token sent to that email.
    if (!credential && isValidEmail(email)) {
      const legacyMemberships = users.filter(item => normalizeEmail(item.email) === email && item.status === 'active').map(item => ({ userId: item.id, workspaceId: item.workspaceId }));
      if (legacyMemberships.length) {
        credential = { id: id('credential'), email, passwordHash: hashPassword(randomBytes(32).toString('base64url')), memberships: legacyMemberships, createdAt: nowIso() };
        authCredentials.push(credential);
      }
    }
    let developmentToken: string | undefined;
    if (credential) {
      for (let index = authActionTokens.length - 1; index >= 0; index -= 1) if (authActionTokens[index].credentialId === credential.id && authActionTokens[index].kind === 'reset') authActionTokens.splice(index, 1);
      const token = randomBytes(32).toString('base64url');
      authActionTokens.push({ tokenHash: sha256(token), credentialId: credential.id, kind: 'reset', expiresAt: new Date(Date.now() + 30 * 60_000).toISOString() });
      if (process.env.NODE_ENV !== 'production' && process.env.AUTH_DEV_EXPOSE_TOKENS === 'true') developmentToken = token;
    }
    return res.status(202).json({ ...generic, ...(developmentToken ? { developmentToken } : {}) });
  });

  router.post('/auth/reset-password', requireSameOrigin, (req, res) => {
    const tokenHash = sha256(String(req.body?.token || ''));
    const password = String(req.body?.password || '');
    if (!isValidPassword(password)) return res.status(400).json({ error: 'Use ao menos 8 caracteres, com letra maiúscula, minúscula e número.' });
    const actionToken = authActionTokens.find(item => item.tokenHash === tokenHash && item.kind === 'reset' && Date.parse(item.expiresAt) > Date.now());
    const credential = actionToken ? authCredentials.find(item => item.id === actionToken.credentialId) : undefined;
    if (!actionToken || !credential) return res.status(400).json({ error: 'Este link de recuperação é inválido ou expirou.' });
    credential.passwordHash = hashPassword(password);
    credential.verifiedAt = nowIso();
    for (let index = authSessions.length - 1; index >= 0; index -= 1) if (authSessions[index].credentialId === credential.id) authSessions.splice(index, 1);
    authActionTokens.splice(authActionTokens.indexOf(actionToken), 1);
    const session = createBrowserSession(credential, credential.memberships[0].workspaceId, true);
    res.setHeader('Set-Cookie', sessionCookie(session.token, session.maxAgeSeconds));
    return res.json(authPayload(credential, session.record.workspaceId));
  });

  router.post('/auth/verify-email', requireSameOrigin, (req, res) => {
    const tokenHash = sha256(String(req.body?.token || ''));
    const actionToken = authActionTokens.find(item => item.tokenHash === tokenHash && item.kind === 'verify' && Date.parse(item.expiresAt) > Date.now());
    const credential = actionToken ? authCredentials.find(item => item.id === actionToken.credentialId) : undefined;
    if (!actionToken || !credential) return res.status(400).json({ error: 'Este link de verificação é inválido ou expirou.' });
    credential.verifiedAt = nowIso();
    authActionTokens.splice(authActionTokens.indexOf(actionToken), 1);
    const session = createBrowserSession(credential, credential.memberships[0].workspaceId, true);
    res.setHeader('Set-Cookie', sessionCookie(session.token, session.maxAgeSeconds));
    return res.json(authPayload(credential, session.record.workspaceId));
  });

  router.post('/workspaces/register', (req, res) => {
    const browserSession = resolveBrowserSession(req);
    if (!browserSession) return res.status(401).json({ error: 'Entre na Clicko antes de adicionar outro perfil.' });
    const workspaceId = String(req.body?.workspaceId || '').trim();
    const userId = String(req.body?.userId || '').trim();
    const name = String(req.body?.name || '').trim();
    const type = req.body?.type === 'personal' ? 'personal' : 'company';
    const email = browserSession.credential.email;
    if (!/^ws-[a-z0-9-]+$/i.test(workspaceId) || !/^usr-[a-z0-9-]+$/i.test(userId) || !name) return res.status(400).json({ error: 'Identificação do ambiente inválida.' });
    let workspace = workspaces.find((item) => item.id === workspaceId);
    let user = users.find((item) => item.id === userId && item.workspaceId === workspaceId);
    if (workspace && !user) return res.status(409).json({ error: 'Este ambiente já existe. Utilize uma conta autorizada ou um convite do administrador.' });
    if (!workspace) {
      const planId: SaaSPlan['id'] = type === 'personal' ? 'solo' : /enterprise/i.test(String(req.body?.planName)) ? 'enterprise' : /business/i.test(String(req.body?.planName)) ? 'business' : 'team';
      const plan = plans.find((item) => item.id === planId)!;
      const createdAt = nowIso();
      workspace = { id: workspaceId, name, logo: '', planId, maxUsers: plan.maxUsers, activeUsers: 1, subscriptionDate: createdAt, subscriptionStatus: 'no_plan', kind: type === 'personal' ? 'personal' : 'organization', ownerUserId: userId, settings: { inviteExpiryDays: 7, requireApproval: type === 'company', timezone: 'America/Sao_Paulo' } };
      workspaces.push(workspace);
      subscriptions.push({ id: id('sub'), workspaceId, planId, status: 'no_plan', startedAt: createdAt, renewsAt: '', billingEmail: email, paymentMethod: 'Não configurado', ownerType: type === 'personal' ? 'personal_account' : 'organization', addOns: [], provider: 'none', billingCycle: 'monthly', history: [{ id: id('sub-history'), event: 'created', toStatus: 'no_plan', planId, occurredAt: createdAt }] });
      usagePools.push(newUsagePool(workspaceId));
      if (type === 'company') for (let index = 0; index < (plan.includedLicenses ?? plan.maxUsers ?? 1); index += 1) licenses.push({ id: id('license'), workspaceId, status: 'available', createdAt, updatedAt: createdAt });
    }
    if (!user) {
      const license = type === 'company' ? licenses.find(item => item.workspaceId === workspaceId && item.status === 'available') : undefined;
      user = { id: userId, workspaceId, name: type === 'personal' ? name : 'Administrador', email, avatar: '', role: 'master', status: 'active', modules: [...moduleIds], permissions: [...rolePresets.master.permissions], scope: allScope(), ...(license ? { licenseId: license.id } : {}), lastAccess: nowIso(), createdAt: nowIso() };
      users.push(user);
      if (license) { license.status = 'in_use'; license.memberId = user.id; license.updatedAt = nowIso(); }
    }
    if (!browserSession.credential.memberships.some(item => item.workspaceId === workspaceId)) browserSession.credential.memberships.push({ userId: user.id, workspaceId });
    browserSession.record.workspaceId = workspaceId;
    res.status(201).json({ workspace, user });
  });

  router.post('/invites/accept', (req, res) => {
    const token = String(req.body?.token || '');
    const password = String(req.body?.password || '');
    const userId = inviteTokens.get(token);
    const member = users.find((item) => item.id === userId && item.status === 'invited');
    if (!member) return res.status(404).json({ error: 'Convite inválido ou já utilizado.' });
    if (member.inviteExpiresAt && new Date(member.inviteExpiresAt).getTime() < Date.now()) return res.status(410).json({ error: 'Este convite expirou. Solicite um novo convite ao administrador.' });
    if (password.length < 8) return res.status(400).json({ error: 'A senha deve possuir ao menos 8 caracteres.' });
    const memberWorkspace = workspaces.find(item => item.id === member.workspaceId)!;
    if (!subscriptionAccessAllowed(subscriptionForWorkspace(member.workspaceId))) return res.status(402).json({ error: 'A assinatura deste ambiente precisa estar ativa antes do aceite do convite.', code: 'SUBSCRIPTION_REQUIRED' });
    if (memberWorkspace.kind === 'organization') {
      let license = licenses.find(item => item.workspaceId === member.workspaceId && item.status === 'reserved' && item.reservedEmail === member.email);
      license ||= licenses.find(item => item.workspaceId === member.workspaceId && item.status === 'available');
      if (!license) return res.status(409).json({ error: 'Não há licença disponível para aceitar este convite.', code: 'LICENSE_REQUIRED' });
      license.status = 'in_use'; license.memberId = member.id; license.reservedEmail = undefined; license.updatedAt = nowIso(); member.licenseId = license.id;
    }
    member.status = 'active';
    member.lastAccess = nowIso();
    inviteTokens.delete(token);
    const email = normalizeEmail(member.email);
    const existingCredential = authCredentials.find(item => item.email === email);
    if (existingCredential) {
      if (!existingCredential.memberships.some(item => item.workspaceId === member.workspaceId)) existingCredential.memberships.push({ userId: member.id, workspaceId: member.workspaceId });
    } else {
      authCredentials.push({ id: id('credential'), email, passwordHash: hashPassword(password), memberships: [{ userId: member.id, workspaceId: member.workspaceId }], verifiedAt: nowIso(), createdAt: nowIso() });
    }
    refreshWorkspaceSeats(member.workspaceId);
    auditLogs.unshift({ id: id('audit'), workspaceId: member.workspaceId, actorId: member.id, actorName: member.name, action: 'invite.accepted', resource: 'user:' + member.id, detail: 'Convite aceito e acesso ao ambiente de trabalho ativado', createdAt: nowIso() });
    res.json({ user: member, workspace: workspaces.find((item) => item.id === member.workspaceId) });
  });

  router.use(authenticate);

  router.get('/billing/catalog', (_req, res) => res.json({ version: CATALOG_VERSION, plans }));
  router.get('/billing/status', (req: AuthenticatedRequest, res) => {
    const subscription = subscriptionForWorkspace(req.auth!.workspaceId);
    const workspace = workspaces.find(item => item.id === req.auth!.workspaceId);
    if (!subscription || !workspace) return res.status(404).json({ error: 'Assinatura não encontrada.' });
    res.setHeader('Cache-Control', 'no-store');
    res.json({ subscription, workspace, accessAllowed: subscriptionAccessAllowed(subscription) });
  });
  router.post('/billing/checkout', requireSameOrigin, async (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    try { assertGovernanceAccess(auth, { permission: 'subscription.manage' }, { requireSubscription: false }); }
    catch (error) { const failure = error as Error & { status?: number; code?: string }; return res.status(failure.status || 403).json({ error: failure.message, code: failure.code }); }
    const workspace = workspaces.find(item => item.id === auth.workspaceId)!;
    if (workspaces.find(item => item.id === auth.workspaceId)?.parentWorkspaceId) return res.status(409).json({ error: 'Esta operação é cobrada pelo ambiente gestor. Gerencie a licença no cadastro do cliente.', code: 'MANAGED_BILLING_PARENT_REQUIRED' });
    const plan = plans.find(item => item.id === req.body?.planId);
    if (!plan) return res.status(400).json({ error: 'Plano inválido.' });
    const billingCycle = req.body?.billingCycle ?? 'monthly';
    if (billingCycle !== 'monthly' && billingCycle !== 'annual') return res.status(400).json({ error: 'Periodicidade de cobrança inválida.', code: 'BILLING_CYCLE_INVALID' });
    const currentSubscription = subscriptionForWorkspace(workspace.id)!;
    const expectedAudience = workspace.kind === 'personal' ? 'personal' : 'organization';
    if (currentSubscription.status !== 'no_plan' && plan.audience !== 'both' && plan.audience !== expectedAudience) return res.status(409).json({ error: 'Este plano não corresponde ao tipo deste perfil.', code: 'PLAN_AUDIENCE_MISMATCH' });
    if (plan.monthlyPrice === null) return res.status(409).json({ error: 'O plano Corporativo exige uma proposta comercial personalizada.', code: 'CONTACT_SALES_REQUIRED' });
    const occupied = licenses.filter(item => item.workspaceId === workspace.id && ['in_use', 'reserved'].includes(item.status)).length;
    const seats = plan.audience === 'personal' ? 1 : Math.max(1, Math.trunc(Number(req.body?.seats || plan.includedLicenses || 1)));
    if (seats < occupied) return res.status(409).json({ error: `Existem ${occupied} licenças ocupadas. Selecione ao menos essa quantidade.`, code: 'SEATS_BELOW_OCCUPIED' });
    if (plan.maxUsers !== null && seats > plan.maxUsers) return res.status(409).json({ error: `O plano ${plan.name} permite até ${plan.maxUsers} usuários.`, code: 'SEATS_ABOVE_PLAN' });
    const checkout: BillingCheckoutSession = { id: id('checkout'), workspaceId: workspace.id, planId: plan.id, billingCycle, seats, status: 'created', provider: 'stripe', previousStatus: currentSubscription.status, createdAt: nowIso() };
    try {
      const provider = await createStripeCheckout(req, checkout, auth.user.email);
      billingCheckoutSessions.push(checkout);
      const subscription = subscriptionForWorkspace(workspace.id)!;
      const previousStatus = subscription.status;
      if (!subscriptionAccessAllowed(subscription)) subscription.status = 'pending_checkout';
      subscription.pendingPlanId = plan.id; subscription.pendingBillingCycle = billingCycle; subscription.checkoutSessionId = checkout.id; subscription.provider = 'stripe';
      subscription.history ||= []; subscription.history.push({ id: id('sub-history'), event: 'checkout_started', fromStatus: previousStatus, toStatus: subscription.status, planId: plan.id, occurredAt: nowIso() });
      workspace.subscriptionStatus = subscription.status;
      addAudit(auth, 'billing.checkout_started', `subscription:${subscription.id}`, `Checkout iniciado para o plano ${plan.name}`);
      return res.status(201).json({ checkoutUrl: provider.url, checkoutSessionId: checkout.id, status: subscription.status });
    } catch (error) {
      const failure = error as Error & { status?: number; code?: string };
      return res.status(failure.status || 502).json({ error: failure.message, code: failure.code || 'BILLING_PROVIDER_ERROR' });
    }
  });
  router.post('/billing/cancel', requireSameOrigin, async (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    try { assertGovernanceAccess(auth, { permission: 'subscription.manage' }); }
    catch (error) { const failure = error as Error & { status?: number; code?: string }; return res.status(failure.status || 403).json({ error: failure.message, code: failure.code }); }
    const subscription = subscriptionForWorkspace(auth.workspaceId)!;
    const secret = process.env.STRIPE_SECRET_KEY;
    if (!secret || !subscription.providerSubscriptionId) return res.status(503).json({ error: 'O gerenciamento da cobrança não está configurado neste ambiente.', code: 'BILLING_NOT_CONFIGURED' });
    const atPeriodEnd = req.body?.atPeriodEnd !== false;
    const response = await fetch(`https://api.stripe.com/v1/subscriptions/${encodeURIComponent(subscription.providerSubscriptionId)}`, {
      method: atPeriodEnd ? 'POST' : 'DELETE',
      headers: { Authorization: `Bearer ${secret}`, 'Content-Type': 'application/x-www-form-urlencoded' },
      ...(atPeriodEnd ? { body: new URLSearchParams({ cancel_at_period_end: 'true' }) } : {}),
    });
    if (!response.ok) return res.status(502).json({ error: 'O provedor não confirmou o cancelamento.', code: 'BILLING_PROVIDER_ERROR' });
    const previousStatus = subscription.status;
    subscription.cancelAtPeriodEnd = atPeriodEnd;
    subscription.canceledAt = nowIso();
    subscription.endsAt = atPeriodEnd ? subscription.renewsAt : nowIso();
    if (!atPeriodEnd) { subscription.status = 'ended'; workspaces.find(item => item.id === auth.workspaceId)!.subscriptionStatus = 'ended'; }
    subscription.history ||= []; subscription.history.push({ id: id('sub-history'), event: atPeriodEnd ? 'cancel_scheduled' : 'ended', fromStatus: previousStatus, toStatus: subscription.status, planId: subscription.planId, occurredAt: nowIso() });
    addAudit(auth, atPeriodEnd ? 'subscription.cancel_scheduled' : 'subscription.ended', `subscription:${subscription.id}`, atPeriodEnd ? 'Cancelamento agendado para o fim do período' : 'Assinatura encerrada');
    res.json(subscription);
  });

  router.post('/auth/session/workspace', requireSameOrigin, (req, res) => {
    if (devConfiguration()) {
      const expiresAt = resolveDevSession(req);
      if (!expiresAt || req.body?.workspaceId !== DEV_WORKSPACE_ID) return res.status(403).json({ code: 'DEV_WORKSPACE_SCOPE_REQUIRED' });
      return res.json(devAuthPayload(expiresAt));
    }
    const current = resolveBrowserSession(req);
    const workspaceId = String(req.body?.workspaceId || '');
    if (!current) {
      const developmentBypass = resolveDevelopmentBypass(req);
      const account = developmentBypass?.accounts.find(item => item.workspaceId === workspaceId);
      if (!developmentBypass || !account) return res.status(403).json({ error: 'Este perfil não pertence à sua conta.' });
      const user = users.find(item => item.id === account.userId && item.workspaceId === account.workspaceId && item.status === 'active');
      if (!user) return res.status(403).json({ error: 'Este perfil não está disponível.' });
      res.setHeader('Set-Cookie', developmentProfileCookie(account.workspaceId));
      res.setHeader('Cache-Control', 'no-store');
      return res.json({ account, accounts: developmentBypass.accounts, user });
    }
    if (!current.credential.memberships.some(item => item.workspaceId === workspaceId)) return res.status(403).json({ error: 'Este perfil não pertence à sua conta.' });
    current.record.workspaceId = workspaceId;
    return res.json(authPayload(current.credential, workspaceId));
  });

  router.delete('/auth/accounts/:workspaceId', requireSameOrigin, (req, res) => {
    const current = resolveBrowserSession(req);
    if (!current) return res.status(401).json({ error: 'Sua sessão expirou. Entre novamente.' });
    if (current.credential.memberships.length <= 1) return res.status(409).json({ error: 'Mantenha ao menos um perfil vinculado à sua conta.' });
    const index = current.credential.memberships.findIndex(item => item.workspaceId === req.params.workspaceId);
    if (index < 0) return res.status(404).json({ error: 'Este perfil não pertence à sua conta.' });
    current.credential.memberships.splice(index, 1);
    if (current.record.workspaceId === req.params.workspaceId) current.record.workspaceId = current.credential.memberships[0].workspaceId;
    return res.json(authPayload(current.credential, current.record.workspaceId));
  });

  router.get('/session', (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    res.json({ currentUser: auth.user, workspace: workspaces.find((item) => item.id === auth.workspaceId) });
  });

  router.get('/workspace', (req: AuthenticatedRequest, res) => res.json(workspaces.find((item) => item.id === req.auth!.workspaceId)));
  router.get('/clients', permissionOnly('clients.read'), (req: AuthenticatedRequest, res) => {
    res.setHeader('Cache-Control', 'private, no-store');
    res.json(registeredClients.filter(client => client.workspaceId === req.auth!.workspaceId && memberHasScope(req.auth!.user, 'client', client.id)).map(publicClient));
  });
  router.post('/clients/register', permissionOnly('clients.manage'), requireSameOrigin, (req: AuthenticatedRequest, res) => {
    const clientId = String(req.body?.id || '').trim();
    const name = String(req.body?.name || '').trim();
    if (!/^client-[A-Za-z0-9_-]{1,100}$/.test(clientId) || !name || name.length > 160) return res.status(400).json({ error: 'Cliente inválido.' });
    const existing = registeredClients.find(client => client.id === clientId);
    if (existing && existing.workspaceId !== req.auth!.workspaceId) return res.status(409).json({ error: 'Este identificador de cliente pertence a outro ambiente.' });
    const record: RegisteredClient = { id: clientId, workspaceId: req.auth!.workspaceId, name, operationState: 'registered', billingStatus: 'none', updatedAt: nowIso() };
    if (existing) { existing.name = name; existing.updatedAt = record.updatedAt; }
    else registeredClients.push(record);
    addAudit(req.auth!, 'client.registered', `client:${clientId}`, 'Cliente disponível para vinculação a contas sociais');
    return res.status(existing ? 200 : 201).json(publicClient(existing || record));
  });
  router.post('/clients/:clientId/invite', permissionOnly('clients.manage'), requireSameOrigin, (req: AuthenticatedRequest, res) => {
    const client = registeredClients.find(item => item.id === req.params.clientId && item.workspaceId === req.auth!.workspaceId);
    if (!client || !memberHasScope(req.auth!.user, 'client', client.id)) return res.status(404).json({ error: 'Cliente não encontrado.' });
    if (client.billingStatus === 'active') return res.status(409).json({ error: 'Este cliente já possui uma operação ativa.', code: 'CLIENT_OPERATION_ACTIVE' });
    const email = normalizeEmail(req.body?.email);
    const kind = req.body?.kind;
    if (!isValidEmail(email) || !['portal', 'independent'].includes(kind)) return res.status(400).json({ error: 'Informe um e-mail e um tipo de convite válidos.' });
    client.operationState = 'invited'; client.invitationEmail = email; client.invitationKind = kind; client.updatedAt = nowIso();
    addAudit(req.auth!, 'client.invited', `client:${client.id}`, `Convite ${kind} preparado para ${email}`);
    const origin = `${req.protocol}://${req.get('host')}`;
    const invitationToken = randomBytes(32).toString('base64url');
    client.portalTokenHash = kind === 'portal' ? sha256(invitationToken) : undefined;
    client.portalExpiresAt = kind === 'portal' ? new Date(Date.now() + 14 * 86_400_000).toISOString() : undefined;
    client.independentTokenHash = kind === 'independent' ? sha256(invitationToken) : undefined;
    client.independentExpiresAt = kind === 'independent' ? new Date(Date.now() + 14 * 86_400_000).toISOString() : undefined;
    return res.json({ client: publicClient(client), deliveryConfigured: false, inviteUrl: kind === 'independent' ? `${origin}/signup#clientInvite=${encodeURIComponent(client.id)}&token=${encodeURIComponent(invitationToken)}` : `${origin}/client-portal#token=${encodeURIComponent(invitationToken)}` });
  });
  router.post('/clients/:clientId/portal-request', permissionOnly('clients.manage'), requireSameOrigin, (req: AuthenticatedRequest, res) => {
    const client = registeredClients.find(item => item.id === req.params.clientId && item.workspaceId === req.auth!.workspaceId);
    if (!client || !memberHasScope(req.auth!.user, 'client', client.id)) return res.status(404).json({ error: 'Cliente não encontrado.' });
    const title = String(req.body?.title || '').trim();
    const detail = String(req.body?.detail || '').trim();
    if (!title || title.length > 120 || detail.length > 2000) return res.status(400).json({ error: 'Informe um título válido e uma descrição de até 2.000 caracteres.' });
    client.portalRequests ||= [];
    if (client.portalRequests.length >= 100) return res.status(409).json({ error: 'O limite de solicitações deste cliente foi atingido.' });
    const request = { id: id('portal-request'), title, detail, status: 'pending' as const, createdAt: nowIso() };
    client.portalRequests.push(request); client.updatedAt = nowIso();
    addAudit(req.auth!, 'client.portal_request_created', `client:${client.id}`, `Solicitação criada: ${title}`);
    return res.status(201).json({ request });
  });
  router.patch('/clients/:clientId/shared-summary', permissionOnly('clients.manage'), requireSameOrigin, (req: AuthenticatedRequest, res) => {
    const client = registeredClients.find(item => item.id === req.params.clientId && item.workspaceId === req.auth!.workspaceId);
    if (!client || !memberHasScope(req.auth!.user, 'client', client.id)) return res.status(404).json({ error: 'Cliente não encontrado.' });
    const summary = String(req.body?.summary || '').trim();
    if (summary.length > 2000) return res.status(400).json({ error: 'O resumo deve ter no máximo 2.000 caracteres.' });
    client.sharedSummary = summary; client.updatedAt = nowIso();
    return res.json({ client: publicClient(client) });
  });
  router.get('/clients/:clientId/portal-documents/:documentId', permissionOnly('clients.read'), (req: AuthenticatedRequest, res) => {
    const client = registeredClients.find(item => item.id === req.params.clientId && item.workspaceId === req.auth!.workspaceId);
    if (!client || !memberHasScope(req.auth!.user, 'client', client.id)) return res.status(404).json({ error: 'Cliente não encontrado.' });
    const document = client.portalDocuments?.find(item => item.id === req.params.documentId);
    if (!document) return res.status(404).json({ error: 'Documento não encontrado.' });
    res.setHeader('Cache-Control', 'private, no-store'); res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Content-Disposition', `attachment; filename="${document.id}.${document.mime === 'application/pdf' ? 'pdf' : document.mime.split('/')[1]}"`);
    return res.type(document.mime).send(Buffer.from(document.data, 'base64'));
  });
  router.get('/clients/:clientId/operation-access', permissionOnly('clients.read'), (req: AuthenticatedRequest, res) => {
    try { const client = assertClientOperation(req.auth!, req.params.clientId); return res.json({ allowed: true, client: publicClient(client) }); }
    catch (error) { const failure = error as Error & { status?: number; code?: string }; return res.status(failure.status || 402).json({ allowed: false, code: failure.code || 'CLIENT_OPERATION_REQUIRED', error: failure.message }); }
  });
  router.post('/clients/:clientId/operation-intents', permissionOnly('clients.manage'), requireSameOrigin, (req: AuthenticatedRequest, res) => {
    const client = registeredClients.find(item => item.id === req.params.clientId && item.workspaceId === req.auth!.workspaceId);
    if (!client || !memberHasScope(req.auth!.user, 'client', client.id)) return res.status(404).json({ error: 'Cliente não encontrado.' });
    const kind = String(req.body?.kind || '') as NonNullable<RegisteredClient['operationSignals']>[number]['kind'];
    if (!['costs', 'reports', 'automations', 'integrations', 'team', 'settings'].includes(kind)) return res.status(400).json({ error: 'Sinal operacional inválido.' });
    client.operationSignals ||= [];
    if (!client.operationSignals.some(item => item.kind === kind)) client.operationSignals.push({ kind, at: nowIso() });
    client.updatedAt = nowIso();
    return res.json({ suggested: !['managed', 'independent'].includes(client.operationState), signals: client.operationSignals });
  });
  router.post('/clients/:clientId/managed-checkout', permissionOnly('clients.manage'), requireSameOrigin, async (req: AuthenticatedRequest, res) => {
    const client = registeredClients.find(item => item.id === req.params.clientId && item.workspaceId === req.auth!.workspaceId);
    if (!client || !memberHasScope(req.auth!.user, 'client', client.id)) return res.status(404).json({ error: 'Cliente não encontrado.' });
    if (workspaces.find(item => item.id === req.auth!.workspaceId)?.parentWorkspaceId) return res.status(409).json({ error: 'Uma operação gerenciada não pode criar subcontas adicionais.', code: 'MANAGED_NESTING_DENIED' });
    if (client.billingStatus === 'active') return res.status(409).json({ error: 'Este cliente já possui uma operação ativa.', code: 'CLIENT_OPERATION_ACTIVE' });
    if (client.billingStatus === 'checkout_pending') return res.status(409).json({ error: 'Já existe um pagamento iniciado para este cliente.', code: 'CLIENT_CHECKOUT_PENDING' });
    if (client.linkedWorkspaceId) return res.status(409).json({ error: 'Este cliente já está vinculado a uma conta independente.', code: 'CLIENT_WORKSPACE_ALREADY_LINKED' });
    if (process.env.NODE_ENV === 'production' && !resolveBrowserSession(req)) return res.status(403).json({ error: 'Entre com sua conta antes de contratar uma operação gerenciada.', code: 'MANAGED_OPERATION_CREDENTIAL_REQUIRED' });
    const secret = process.env.STRIPE_SECRET_KEY;
    const price = process.env.STRIPE_MANAGED_OPERATION_PRICE_ID;
    const testCheckout = process.env.NODE_ENV === 'test' && process.env.STRIPE_TEST_CHECKOUT === 'true';
    if ((!secret && !testCheckout) || !price) return res.status(503).json({ error: 'A cobrança por operação gerenciada ainda não está configurada.', code: 'MANAGED_BILLING_NOT_CONFIGURED' });
    const origin = `${req.protocol}://${req.get('host')}`;
    const body = new URLSearchParams({ mode: 'subscription', success_url: `${origin}/clients?managed=return`, cancel_url: `${origin}/clients?managed=canceled`, customer_email: req.auth!.user.email, 'line_items[0][price]': price, 'line_items[0][quantity]': '1', 'metadata[managedClientId]': client.id, 'metadata[workspaceId]': client.workspaceId, 'subscription_data[metadata][managedClientId]': client.id, 'subscription_data[metadata][workspaceId]': client.workspaceId });
    try {
      let payload: { id?: string; url?: string };
      if (testCheckout) { const testId = `cs_test_managed_${randomUUID()}`; payload = { id: testId, url: `https://checkout.stripe.test/${testId}` }; }
      else {
        const response = await fetch('https://api.stripe.com/v1/checkout/sessions', { method: 'POST', headers: { Authorization: `Bearer ${secret}`, 'Content-Type': 'application/x-www-form-urlencoded' }, body });
        payload = await response.json() as { id?: string; url?: string };
        if (!response.ok || !payload.id || !payload.url) return res.status(502).json({ error: 'O provedor não iniciou o pagamento.', code: 'BILLING_PROVIDER_ERROR' });
      }
      client.providerCheckoutSessionId = payload.id; client.managedInitiatorUserId = req.auth!.user.id; client.billingStatus = 'checkout_pending'; client.updatedAt = nowIso();
      addAudit(req.auth!, 'client.managed_checkout_started', `client:${client.id}`, 'Checkout da operação gerenciada iniciado; aguardando confirmação do provedor.');
      return res.status(201).json({ checkoutUrl: payload.url, client: publicClient(client) });
    } catch { return res.status(502).json({ error: 'Não foi possível iniciar o pagamento.', code: 'BILLING_PROVIDER_ERROR' }); }
  });
  router.get('/plans', permissionOnly('subscription.read', { requireSubscription: false }), (_req, res) => res.json(plans));
  router.get('/access/effective', (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const workspace = workspaces.find(item => item.id === auth.workspaceId)!;
    const license = auth.user.licenseId ? licenses.find(item => item.id === auth.user.licenseId && item.workspaceId === auth.workspaceId) : undefined;
    res.json({ workspaceId: auth.workspaceId, kind: workspace.kind, role: auth.user.role, modules: auth.user.modules, permissions: effectivePermissions(auth.user), scope: auth.user.scope || allScope(), license: license ? { id: license.id, status: license.status } : null });
  });
  router.get('/access/modules/:moduleId', moduleOnly, (req: AuthenticatedRequest, res) => res.json({ allowed: true, moduleId: req.params.moduleId, workspaceId: req.auth!.workspaceId }));

  router.get('/users', permissionOnly('members.read'), (req: AuthenticatedRequest, res) => {
    res.json(users.filter((item) => item.workspaceId === req.auth!.workspaceId));
  });

  router.post('/invites', permissionOnly('members.manage'), (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const workspace = workspaces.find((item) => item.id === auth.workspaceId)!;
    if (workspace.kind !== 'organization') return res.status(409).json({ error: 'Contas pessoais não possuem equipe ou licenças.', code: 'PERSONAL_ACCOUNT_NO_TEAM' });
    const reserveSeat = req.body?.reserveSeat === true;
    const availableLicense = licenses.find(item => item.workspaceId === auth.workspaceId && item.status === 'available');
    if (reserveSeat && !availableLicense) {
      addAudit(auth, 'invite.blocked', 'workspace:' + workspace.id, 'Convite bloqueado por limite do plano');
      return res.status(409).json({ error: 'Não há licença disponível para reservar este convite.', code: 'LICENSE_REQUIRED' });
    }
    const email = String(req.body?.email || '').trim().toLowerCase();
    const name = String(req.body?.name || '').trim();
    if (!name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return res.status(400).json({ error: 'Informe nome e e-mail válidos.' });
    if (users.some((item) => item.workspaceId === auth.workspaceId && item.email.toLowerCase() === email)) return res.status(409).json({ error: 'Já existe um usuário ou convite com este e-mail.' });
    const invitedAt = nowIso();
    const inviteExpiresAt = new Date(Date.now() + workspace.settings.inviteExpiryDays * 86_400_000).toISOString();
    const requestedRole = String(req.body?.role || 'custom') as UserRole;
    const role: Exclude<UserRole, 'master' | 'collaborator'> = ['administrator', 'manager', 'social_media', 'creative', 'analyst', 'approver', 'custom'].includes(requestedRole) ? requestedRole as Exclude<UserRole, 'master' | 'collaborator'> : 'custom';
    const permissions = Array.isArray(req.body?.permissions) ? req.body.permissions.filter((item: unknown): item is OrganizationPermission => rolePresets.master.permissions.includes(item as OrganizationPermission)) : [...rolePresets[role].permissions];
    const member: WorkspaceMember = { id: id('usr'), workspaceId: auth.workspaceId, name, email, avatar: '', role, status: 'invited', modules: validModules(req.body?.modules), permissions, scope: normalizeScope(req.body?.scope), ...(reserveSeat && availableLicense ? { licenseId: availableLicense.id } : {}), lastAccess: 'Convite pendente', createdAt: invitedAt, invitedAt, inviteExpiresAt };
    users.push(member);
    if (reserveSeat && availableLicense) { availableLicense.status = 'reserved'; availableLicense.reservedEmail = email; availableLicense.updatedAt = nowIso(); }
    const inviteToken = id('invite');
    inviteTokens.set(inviteToken, member.id);
    addAudit(auth, 'invite.created', 'user:' + member.id, `Convite registrado para ${email}; entrega externa pendente`);
    res.status(201).json({ ...member, ...(process.env.NODE_ENV === 'test' ? { developmentInviteToken: inviteToken } : {}) });
  });

  router.patch('/users/:userId', permissionOnly('members.manage'), (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const member = users.find((item) => item.id === req.params.userId && item.workspaceId === auth.workspaceId);
    if (!member) return res.status(404).json({ error: 'Usuário não encontrado neste ambiente de trabalho.' });
    if (isPrivilegedRole(member.role)) return res.status(400).json({ error: 'Este usuário administrativo não pode ser alterado por esta ação.' });
    if (req.body?.status === 'active' && member.status !== 'active') {
      if (member.status === 'invited') return res.status(409).json({ error: 'O usuário precisa aceitar o convite antes de ser ativado.' });
      const license = member.licenseId ? licenses.find(item => item.id === member.licenseId && item.status !== 'suspended') : licenses.find(item => item.workspaceId === auth.workspaceId && item.status === 'available');
      if (!license) return res.status(409).json({ error: 'Não há licença disponível para reativar este usuário.', code: 'LICENSE_REQUIRED' });
      member.licenseId = license.id; license.status = 'in_use'; license.memberId = member.id; license.updatedAt = nowIso();
    }
    if (typeof req.body?.name === 'string' && req.body.name.trim()) member.name = req.body.name.trim();
    if (req.body?.status === 'active' || req.body?.status === 'disabled') member.status = req.body.status;
    if (req.body?.modules) member.modules = validModules(req.body.modules);
    if (typeof req.body?.role === 'string' && req.body.role !== 'master' && roleIds.includes(req.body.role)) member.role = req.body.role === 'collaborator' ? 'custom' : req.body.role;
    if (req.body?.permissions && hasPermission(auth.user, 'permissions.manage')) member.permissions = req.body.permissions.filter((item: unknown): item is OrganizationPermission => rolePresets.master.permissions.includes(item as OrganizationPermission));
    if (req.body?.scope && hasPermission(auth.user, 'permissions.manage')) member.scope = normalizeScope(req.body.scope);
    if (member.status === 'disabled' && member.licenseId) {
      const license = licenses.find(item => item.id === member.licenseId);
      if (license) { license.status = 'available'; license.memberId = undefined; license.reservedEmail = undefined; license.updatedAt = nowIso(); }
      member.licenseId = undefined;
    }
    refreshWorkspaceSeats(auth.workspaceId);
    addAudit(auth, 'user.updated', 'user:' + member.id, `Permissões ou status de ${member.name} atualizados`);
    res.json(member);
  });

  router.post('/users/:userId/resend-invite', permissionOnly('members.manage'), (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const member = users.find((item) => item.id === req.params.userId && item.workspaceId === auth.workspaceId && item.status === 'invited');
    if (!member) return res.status(404).json({ error: 'Convite pendente não encontrado.' });
    const days = workspaces.find((item) => item.id === auth.workspaceId)!.settings.inviteExpiryDays;
    member.invitedAt = nowIso();
    member.inviteExpiresAt = new Date(Date.now() + days * 86_400_000).toISOString();
    addAudit(auth, 'invite.resent', 'user:' + member.id, `Prazo do convite renovado para ${member.email}; entrega externa pendente`);
    res.json(member);
  });

  router.delete('/users/:userId', permissionOnly('members.manage'), (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const index = users.findIndex((item) => item.id === req.params.userId && item.workspaceId === auth.workspaceId);
    if (index < 0) return res.status(404).json({ error: 'Usuário não encontrado neste ambiente de trabalho.' });
    if (isPrivilegedRole(users[index].role)) return res.status(400).json({ error: 'Este usuário administrativo não pode ser removido.' });
    const [removed] = users.splice(index, 1);
    if (removed.licenseId) {
      const license = licenses.find(item => item.id === removed.licenseId && item.workspaceId === auth.workspaceId);
      if (license) { license.status = 'available'; license.memberId = undefined; license.reservedEmail = undefined; license.updatedAt = nowIso(); }
    }
    for (const [token, userId] of inviteTokens) if (userId === removed.id) inviteTokens.delete(token);
    for (let credentialIndex = authCredentials.length - 1; credentialIndex >= 0; credentialIndex -= 1) {
      const credential = authCredentials[credentialIndex];
      credential.memberships = credential.memberships.filter(item => !(item.userId === removed.id && item.workspaceId === removed.workspaceId));
      if (!credential.memberships.length) {
        authCredentials.splice(credentialIndex, 1);
        for (let sessionIndex = authSessions.length - 1; sessionIndex >= 0; sessionIndex -= 1) if (authSessions[sessionIndex].credentialId === credential.id) authSessions.splice(sessionIndex, 1);
        for (let tokenIndex = authActionTokens.length - 1; tokenIndex >= 0; tokenIndex -= 1) if (authActionTokens[tokenIndex].credentialId === credential.id) authActionTokens.splice(tokenIndex, 1);
      }
    }
    refreshWorkspaceSeats(auth.workspaceId);
    addAudit(auth, 'user.removed', 'user:' + removed.id, `${removed.name} removido do ambiente de trabalho`);
    res.status(204).end();
  });

  router.get('/licenses', permissionOnly('licenses.read'), (req: AuthenticatedRequest, res) => {
    const workspace = workspaces.find(item => item.id === req.auth!.workspaceId)!;
    if (workspace.kind !== 'organization') return res.json([]);
    res.json(licenses.filter(item => item.workspaceId === workspace.id));
  });

  router.post('/licenses', permissionOnly('licenses.manage'), requireSameOrigin, (req: AuthenticatedRequest, res) => {
    const workspace = workspaces.find(item => item.id === req.auth!.workspaceId)!;
    if (workspace.kind !== 'organization') return res.status(409).json({ error: 'Contas pessoais não utilizam licenças.' });
    const quantity = Number(req.body?.quantity);
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 100) return res.status(400).json({ error: 'Informe uma quantidade de licenças entre 1 e 100.' });
    const createdAt = nowIso();
    const created = Array.from({ length: quantity }, () => ({ id: id('license'), workspaceId: workspace.id, status: 'available' as const, createdAt, updatedAt: createdAt }));
    licenses.push(...created);
    workspace.maxUsers = (workspace.maxUsers ?? licenses.length - quantity) + quantity;
    subscriptions.find(item => item.workspaceId === workspace.id)!.addOns!.push({ id: id('addon'), resource: 'licenses', quantity, status: 'active', createdAt });
    addAudit(req.auth!, 'licenses.added', `workspace:${workspace.id}`, `${quantity} licença(s) adicional(is) provisionada(s)`);
    res.status(201).json(created);
  });

  router.patch('/licenses/:licenseId', permissionOnly('licenses.manage'), (req: AuthenticatedRequest, res) => {
    const license = licenses.find(item => item.id === req.params.licenseId && item.workspaceId === req.auth!.workspaceId);
    if (!license) return res.status(404).json({ error: 'Licença não encontrada.' });
    if (license.memberId && users.some(item => item.id === license.memberId && item.role === 'master')) return res.status(409).json({ error: 'A licença da Conta Master não pode ser suspensa.' });
    if (req.body?.status !== 'available' && req.body?.status !== 'suspended') return res.status(400).json({ error: 'Estado de licença inválido.' });
    const member = license.memberId ? users.find(item => item.id === license.memberId && item.workspaceId === license.workspaceId) : undefined;
    license.status = req.body.status;
    license.updatedAt = nowIso();
    if (member && license.status === 'suspended') { member.status = 'disabled'; member.licenseId = undefined; }
    license.memberId = undefined; license.reservedEmail = undefined;
    addAudit(req.auth!, 'license.updated', `license:${license.id}`, `Licença alterada para ${license.status}`);
    res.json(license);
  });

  router.get('/usage', permissionOnly('usage.read.own'), (req: AuthenticatedRequest, res) => {
    const pool = usagePools.find(item => item.workspaceId === req.auth!.workspaceId) || newUsagePool(req.auth!.workspaceId);
    if (hasPermission(req.auth!.user, 'usage.read.organization')) return res.json(pool);
    const memberId = req.auth!.user.id;
    const memberLimits = pool.memberLimits[memberId] || {};
    const memberUsage = pool.memberUsage[memberId] || {};
    const ownResources = Object.fromEntries(usageResources.map(resource => [resource, {
      used: memberUsage[resource] || 0,
      limit: memberLimits[resource] ?? null,
    }])) as UsagePool['resources'];
    res.json({ workspaceId: pool.workspaceId, periodStartedAt: pool.periodStartedAt, periodEndsAt: pool.periodEndsAt, allocationMode: pool.allocationMode, resources: ownResources, memberLimits: { [memberId]: memberLimits }, memberUsage: { [memberId]: memberUsage } });
  });

  router.patch('/usage/policy', permissionOnly('usage.manage'), (req: AuthenticatedRequest, res) => {
    const pool = usagePools.find(item => item.workspaceId === req.auth!.workspaceId)!;
    if (req.body?.allocationMode === 'shared' || req.body?.allocationMode === 'member_limits') pool.allocationMode = req.body.allocationMode;
    const memberId = String(req.body?.memberId || '');
    if (memberId) {
      if (!users.some(item => item.id === memberId && item.workspaceId === req.auth!.workspaceId)) return res.status(404).json({ error: 'Membro não encontrado.' });
      const incoming = req.body?.limits && typeof req.body.limits === 'object' ? req.body.limits : {};
      const limits: Partial<Record<UsageResource, number | null>> = {};
      for (const resource of usageResources) if (resource in incoming) {
        const value = incoming[resource];
        if (value !== null && (!Number.isFinite(value) || value < 0)) return res.status(400).json({ error: `Limite inválido para ${resource}.` });
        limits[resource] = value;
      }
      pool.memberLimits[memberId] = limits;
    }
    addAudit(req.auth!, 'usage.policy_updated', `usage:${pool.workspaceId}`, 'Política de consumo atualizada');
    res.json(pool);
  });

  router.post('/usage/consume', (req: AuthenticatedRequest, res) => {
    const resource = String(req.body?.resource || '') as UsageResource;
    if (!usageResources.includes(resource)) return res.status(400).json({ error: 'Recurso de consumo inválido.' });
    const moduleByResource: Partial<Record<UsageResource, WorkspaceModule>> = { image_generations: 'create-image', video_minutes: 'create-video', klic_credits: 'ai-chat', automations: 'automations' };
    try {
      if (moduleByResource[resource]) assertGovernanceAccess(req.auth!, { module: moduleByResource[resource] });
      res.json(consumeGovernanceUsage(req.auth!, resource, Number(req.body?.amount ?? 1)));
    } catch (error) {
      const failure = error as Error & { status?: number; code?: string };
      res.status(failure.status || 409).json({ error: failure.message, code: failure.code });
    }
  });

  router.post('/subscription/add-ons', permissionOnly('subscription.manage'), (req: AuthenticatedRequest, res) => {
    const resource = String(req.body?.resource || '') as UsageResource;
    const quantity = Number(req.body?.quantity);
    if (!usageResources.includes(resource) || !Number.isFinite(quantity) || quantity <= 0) return res.status(400).json({ error: 'Complemento inválido.' });
    if (resource === 'clients') return res.status(409).json({ error: 'Clientes cadastrados não possuem cobrança por quantidade. Para uma operação separada, contrate uma licença gerenciada ou convide o cliente a assinar.', code: 'CLIENT_REGISTRATION_FREE' });
    const subscription = subscriptions.find(item => item.workspaceId === req.auth!.workspaceId)!;
    const addOn = { id: id('addon'), resource, quantity, status: 'active' as const, createdAt: nowIso() };
    subscription.addOns ||= []; subscription.addOns.push(addOn);
    const pool = usagePools.find(item => item.workspaceId === req.auth!.workspaceId)!;
    pool.resources[resource].limit = entitlementLimit(req.auth!.workspaceId, resource);
    addAudit(req.auth!, 'subscription.addon_added', `subscription:${subscription.id}`, `Complemento de ${resource} adicionado`);
    res.status(201).json({ addOn, allowance: pool.resources[resource] });
  });

  router.post('/ownership/transfer', masterOnly, requireSameOrigin, (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const workspace = workspaces.find(item => item.id === auth.workspaceId)!;
    const target = users.find(item => item.id === req.body?.targetUserId && item.workspaceId === auth.workspaceId && item.status === 'active');
    if (workspace.kind !== 'organization' || workspace.ownerUserId !== auth.user.id) return res.status(403).json({ error: 'Somente a Conta Master atual pode transferir a propriedade.' });
    if (!target || target.id === auth.user.id || !target.licenseId) return res.status(400).json({ error: 'Escolha um membro ativo e licenciado.' });
    const previous = users.find(item => item.id === workspace.ownerUserId && item.workspaceId === workspace.id)!;
    previous.role = 'administrator'; previous.permissions = [...rolePresets.administrator.permissions];
    target.role = 'master'; target.permissions = [...rolePresets.master.permissions]; target.scope = allScope();
    workspace.ownerUserId = target.id;
    addAudit(auth, 'ownership.transferred', `workspace:${workspace.id}`, `Conta Master transferida para ${target.name}`);
    res.json({ workspace, previousOwner: previous, owner: target });
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

  router.get('/subscription', permissionOnly('subscription.read', { requireSubscription: false }), (req: AuthenticatedRequest, res) => {
    const subscription = subscriptions.find((item) => item.workspaceId === req.auth!.workspaceId);
    if (!subscription) return res.status(404).json({ error: 'Assinatura não encontrada.' });
    if (!hasPermission(req.auth!.user, 'billing.read')) return res.json({ ...subscription, billingEmail: '', paymentMethod: '' });
    res.json(subscription);
  });
  router.patch('/subscription', permissionOnly('subscription.manage', { requireSubscription: false }), (_req: AuthenticatedRequest, res) => {
    res.status(409).json({ error: 'Alterações de plano devem ser confirmadas pelo checkout seguro.', code: 'CHECKOUT_REQUIRED' });
  });

  router.post('/approvals', (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    try { assertGovernanceAccess(auth, { module: 'calendar', capability: 'approvals', permission: 'content.create', clientId: req.body?.clientId ? String(req.body.clientId) : null }); }
    catch (error) { const failure = error as Error & { status?: number; code?: string }; return res.status(failure.status || 403).json({ error: failure.message, code: failure.code }); }
    const title = String(req.body?.title || '').trim();
    const contentId = String(req.body?.contentId || '').trim();
    const copy = String(req.body?.copy || '').trim();
    const platform = String(req.body?.platform || '') as ContentApprovalItem['platform'];
    const format = String(req.body?.format || '') as ContentApprovalItem['format'];
    if (!title || !contentId || !platform || !format) return res.status(400).json({ error: 'Título, conteúdo, plataforma e formato são obrigatórios.' });
    if (req.body?.scheduledAt && !Number.isFinite(Date.parse(req.body.scheduledAt))) return res.status(400).json({ error: 'Informe uma data e horário válidos.' });
    const existing = approvals.find((item) => item.workspaceId === auth.workspaceId && item.contentId === contentId);
    if (existing) return res.status(409).json({ error: 'Este conteúdo já possui um fluxo de aprovação.' });
    const createdAt = nowIso();
    const approval: ContentApprovalItem = {
      id: id('approval'), workspaceId: auth.workspaceId, contentId, title, copy, platform, format,
      authorId: auth.user.id, authorName: auth.user.name, createdAt,
      scheduledAt: req.body?.scheduledAt ? String(req.body.scheduledAt) : undefined,
      stage: 'pending_approval', comments: [],
      history: [{ id: id('history'), actorId: auth.user.id, actorName: auth.user.name, action: 'submitted', detail: 'Conteúdo enviado para aprovação pelo Calendário', createdAt }],
      campaignId: req.body?.campaignId ? String(req.body.campaignId) : undefined,
      strategyId: req.body?.strategyId ? String(req.body.strategyId) : undefined,
    };
    approvals.unshift(approval);
    addAudit(auth, 'content.submitted', 'content:' + contentId, 'Conteúdo enviado para aprovação pelo Calendário');
    return res.status(201).json(approval);
  });

  router.get('/approvals', permissionOnly('content.approve'), (req: AuthenticatedRequest, res) => res.json(approvals.filter((item) => item.workspaceId === req.auth!.workspaceId)));
  router.post('/approvals/:approvalId/actions', permissionOnly('content.approve'), (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const approval = approvals.find((item) => item.id === req.params.approvalId && item.workspaceId === auth.workspaceId);
    if (!approval) return res.status(404).json({ error: 'Conteúdo não encontrado nesta fila.' });
    const action = String(req.body?.action || '');
    const comment = String(req.body?.comment || '').trim();
    const allowed = ['approve', 'request_changes', 'reject', 'publish', 'schedule', 'reschedule', 'comment'];
    if (!allowed.includes(action)) return res.status(400).json({ error: 'Ação de aprovação inválida.' });
    if (['comment', 'request_changes', 'reject'].includes(action) && !comment) return res.status(400).json({ error: 'Escreva um comentário para registrar esta ação.' });
    if (approval.stage === 'published' && action !== 'comment') return res.status(409).json({ error: 'Um conteúdo publicado não pode retornar à revisão por esta ação.' });
    if (['schedule', 'reschedule'].includes(action) && (!Number.isFinite(Date.parse(req.body?.scheduledAt)) || Date.parse(req.body.scheduledAt) <= Date.now())) return res.status(400).json({ error: 'Escolha uma data e horário futuros válidos.' });
    if ((action === 'publish' || action === 'schedule') && approval.stage !== 'approved') {
      addAudit(auth, 'publication.blocked', 'content:' + approval.contentId, 'Publicação bloqueada: conteúdo sem aprovação');
      return res.status(409).json({ error: 'Este conteúdo precisa ser aprovado pelo administrador antes da publicação.' });
    }
    if (action === 'publish') {
      const reason = publishingConfigured(approval.platform)
        ? `O envio direto para ${approval.platform} ainda não possui um publicador ativo neste servidor. O conteúdo permaneceu aprovado.`
        : `A publicação no ${approval.platform} exige credenciais oficiais configuradas. O conteúdo permaneceu aprovado.`;
      addAudit(auth, 'publication.blocked', 'content:' + approval.contentId, reason);
      return res.status(501).json({ error: reason });
    }
    if (comment) approval.comments.push({ id: id('comment'), authorId: auth.user.id, authorName: auth.user.name, message: comment, createdAt: nowIso() });
    const actionMap: Record<string, { stage?: ContentApprovalItem['stage']; detail: string }> = {
      approve: { stage: 'approved', detail: 'Conteúdo aprovado pelo administrador' },
      request_changes: { stage: 'changes_requested', detail: 'Ajustes solicitados ao colaborador' },
      reject: { stage: 'rejected', detail: 'Conteúdo reprovado pelo administrador' },
      publish: { stage: 'published', detail: 'Conteúdo publicado oficialmente' },
      schedule: { detail: 'Publicação aprovada e agendada' },
      reschedule: { detail: 'Data de planejamento alterada pelo Calendário, mantendo a etapa de aprovação' },
      comment: { detail: 'Comentário adicionado à revisão' },
    };
    const transition = actionMap[action];
    if (transition.stage) approval.stage = transition.stage;
    if (action === 'approve') { approval.approvedBy = auth.user.id; approval.approvedAt = nowIso(); }
    if (action === 'publish') { approval.publishedBy = auth.user.id; approval.publishedAt = nowIso(); }
    if (['schedule', 'reschedule'].includes(action) && req.body?.scheduledAt) approval.scheduledAt = String(req.body.scheduledAt);
    approval.history.unshift({ id: id('history'), actorId: auth.user.id, actorName: auth.user.name, action, detail: transition.detail, createdAt: nowIso() });
    addAudit(auth, `approval.${action}`, 'content:' + approval.contentId, transition.detail);
    res.json(approval);
  });

  router.post('/approvals/:approvalId/automatic-publish', permissionOnly('content.publish'), (req: AuthenticatedRequest, res) => {
    const auth = req.auth!;
    const approval = approvals.find((item) => item.id === req.params.approvalId && item.workspaceId === auth.workspaceId);
    if (!approval) return res.status(404).json({ error: 'Conteúdo não encontrado.' });
    if (approval.stage !== 'approved') {
      addAudit(auth, 'automation.publication_blocked', 'content:' + approval.contentId, 'Agendamento cancelado por ausência de aprovação');
      return res.status(409).json({ error: 'Publicação automática cancelada: aprovação do administrador pendente.' });
    }
    const reason = publishingConfigured(approval.platform)
      ? `A publicação automática no ${approval.platform} ainda não possui um publicador ativo neste servidor.`
      : `A publicação automática no ${approval.platform} não está configurada.`;
    addAudit(auth, 'automation.publication_blocked', 'content:' + approval.contentId, reason);
    return res.status(501).json({ error: reason });
  });

  router.get('/audit-logs', permissionOnly('audit.read'), (req: AuthenticatedRequest, res) => res.json(auditLogs.filter((item) => item.workspaceId === req.auth!.workspaceId).slice(0, 100)));

  return router;
}
