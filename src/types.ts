export type NavigationTab =
  | 'dashboard'
  | 'create-image'
  | 'create-video'
  | 'create-copy'
  | 'ai-chat'
  | 'connected-accounts'
  | 'workspace'
  | 'strategy'
  | 'library'
  | 'calendar'
  | 'analytics'
  | 'automations'
  | 'approvals'
  | 'team'
  | 'subscription'
  | 'settings';

export type UserRole =
  | 'master'
  | 'administrator'
  | 'manager'
  | 'social_media'
  | 'creative'
  | 'analyst'
  | 'approver'
  | 'custom'
  /** @deprecated Kept only while persisted v1/v2 workspaces are migrated. */
  | 'collaborator';

export type WorkspaceModule =
  | 'dashboard'
  | 'create-image'
  | 'create-video'
  | 'create-copy'
  | 'ai-chat'
  | 'connected-accounts'
  | 'workspace'
  | 'strategy'
  | 'library'
  | 'calendar'
  | 'automations'
  | 'analytics';

export type MemberStatus = 'active' | 'invited' | 'disabled';

export type OrganizationPermission =
  | 'organization.manage'
  | 'subscription.read'
  | 'subscription.manage'
  | 'billing.read'
  | 'licenses.read'
  | 'licenses.manage'
  | 'members.read'
  | 'members.manage'
  | 'permissions.manage'
  | 'clients.read'
  | 'clients.manage'
  | 'connections.read'
  | 'connections.manage'
  | 'content.create'
  | 'content.edit'
  | 'content.approve'
  | 'content.publish'
  | 'analytics.read'
  | 'automations.manage'
  | 'audit.read'
  | 'usage.read.own'
  | 'usage.read.organization'
  | 'usage.manage';

export interface AccessScope {
  allClients: boolean;
  clientIds: string[];
  allSocialAccounts: boolean;
  socialAccountIds: string[];
  allProjects: boolean;
  projectIds: string[];
  resourceIds: string[];
}

export type UsageResource =
  | 'image_generations'
  | 'video_minutes'
  | 'klic_credits'
  | 'storage_bytes'
  | 'social_accounts'
  | 'clients'
  | 'automations';

export interface UsageAllowance {
  limit: number | null;
  used: number;
}

export interface UsagePool {
  workspaceId: string;
  periodStartedAt: string;
  periodEndsAt: string;
  resources: Record<UsageResource, UsageAllowance>;
  memberLimits: Record<string, Partial<Record<UsageResource, number | null>>>;
  memberUsage: Record<string, Partial<Record<UsageResource, number>>>;
  allocationMode: 'shared' | 'member_limits';
}

export type LicenseStatus = 'available' | 'reserved' | 'in_use' | 'suspended';

export interface OrganizationLicense {
  id: string;
  workspaceId: string;
  status: LicenseStatus;
  memberId?: string;
  reservedEmail?: string;
  createdAt: string;
  updatedAt: string;
}

export interface SubscriptionAddOn {
  id: string;
  resource: UsageResource | 'licenses';
  quantity: number;
  status: 'active' | 'canceled';
  createdAt: string;
}

export interface UserAccount {
  id: string;
  workspaceId: string;
  userId: string;
  name: string;
  type: 'personal' | 'company';
  role?: string;
  planName?: string;
  subscriptionStatus?: SubscriptionStatus;
  subscriptionAccessAllowed?: boolean;
  capabilities?: Partial<Record<PlanCapability, boolean>>;
  membersCount?: number;
  email?: string;
  avatar?: string;
  createdAt?: string;
}

export interface WorkspaceMember {
  id: string;
  workspaceId: string;
  name: string;
  email: string;
  avatar: string;
  role: UserRole;
  status: MemberStatus;
  modules: WorkspaceModule[];
  permissions?: OrganizationPermission[];
  scope?: AccessScope;
  licenseId?: string;
  lastAccess: string;
  createdAt: string;
  invitedAt?: string;
  inviteExpiresAt?: string;
}

export interface SaaSPlan {
  id: 'solo' | 'team' | 'business' | 'enterprise';
  name: string;
  maxUsers: number | null;
  monthlyPrice: number | null;
  description: string;
  features: string[];
  audience?: 'personal' | 'organization' | 'both';
  includedLicenses?: number;
  entitlements?: Partial<Record<UsageResource, number | null>>;
  capabilities?: Partial<Record<PlanCapability, boolean>>;
  catalogVersion?: string;
}

export type SubscriptionStatus =
  | 'no_plan'
  | 'pending_checkout'
  | 'pending_payment'
  | 'active'
  | 'trialing'
  | 'past_due'
  | 'payment_failed'
  | 'canceled'
  | 'suspended'
  | 'ended';

export type PlanCapability =
  | 'dashboard'
  | 'image_generation'
  | 'image_editing'
  | 'video_generation'
  | 'video_editing'
  | 'copy_creation'
  | 'klic'
  | 'library'
  | 'calendar'
  | 'analytics'
  | 'radar'
  | 'automations'
  | 'connected_accounts'
  | 'clients'
  | 'approvals'
  | 'team';

export interface SubscriptionEntitlementSnapshot {
  planId: SaaSPlan['id'];
  catalogVersion: string;
  capabilities: Partial<Record<PlanCapability, boolean>>;
  quotas: Partial<Record<UsageResource, number | null>>;
  includedLicenses: number;
  capturedAt: string;
}

export interface SubscriptionHistoryEntry {
  id: string;
  event: 'created' | 'checkout_started' | 'activated' | 'payment_failed' | 'renewed' | 'plan_changed' | 'cancel_scheduled' | 'canceled' | 'reactivated' | 'suspended' | 'ended';
  fromStatus?: SubscriptionStatus;
  toStatus: SubscriptionStatus;
  planId: SaaSPlan['id'];
  occurredAt: string;
  providerEventId?: string;
}

export type OfferContextType =
  | 'first_subscription'
  | 'upgrade'
  | 'seat_increase'
  | 'premium_feature'
  | 'limit_reached'
  | 'renewal'
  | 'promotion';

export type OfferEventName =
  | 'OFFER_VIEWED'
  | 'OFFER_CLICKED'
  | 'UPGRADE_STARTED'
  | 'CHECKOUT_STARTED'
  | 'CHECKOUT_COMPLETED'
  | 'OFFER_DISMISSED';

export interface OfferPromotion {
  originalMonthlyPrice: number;
  promotionalMonthlyPrice: number;
  startsAt: string;
  endsAt: string;
  terms: string;
}

export interface OfferConfiguration {
  id: string;
  enabled: boolean;
  contexts: OfferContextType[];
  environment: 'personal' | 'company' | 'both';
  eligibleCurrentPlans: SaaSPlan['id'][];
  targetPlanId: SaaSPlan['id'];
  headline: string;
  description: string;
  ctaLabel: string;
  benefits: string[];
  badge?: string;
  bonus?: string;
  promotion?: OfferPromotion;
  experimentKey?: string;
  variantId?: string;
}

export interface OfferRequest {
  context: OfferContextType;
  reason: string;
  featureLabel?: string;
  targetPlanId?: SaaSPlan['id'];
  source: string;
  automatic?: boolean;
}

export interface OfferEventPayload {
  event: OfferEventName;
  offerId: string;
  context: OfferContextType;
  source: string;
  currentPlanId?: SaaSPlan['id'];
  targetPlanId?: SaaSPlan['id'];
  occurredAt: string;
  experimentKey?: string;
  variantId?: string;
}

export interface WorkspaceSubscription {
  id: string;
  workspaceId: string;
  planId: SaaSPlan['id'];
  status: SubscriptionStatus;
  startedAt: string;
  renewsAt: string;
  billingEmail: string;
  paymentMethod: string;
  ownerType?: 'personal_account' | 'organization' | 'managed_operation';
  addOns?: SubscriptionAddOn[];
  billingCycle?: 'monthly' | 'annual';
  cancelAtPeriodEnd?: boolean;
  canceledAt?: string;
  endsAt?: string;
  provider?: 'stripe' | 'custom' | 'none';
  providerCustomerId?: string;
  providerSubscriptionId?: string;
  checkoutSessionId?: string;
  pendingPlanId?: SaaSPlan['id'];
  pendingBillingCycle?: 'monthly' | 'annual';
  entitlementSnapshot?: SubscriptionEntitlementSnapshot;
  capabilityOverrides?: Partial<Record<PlanCapability, boolean>>;
  quotaOverrides?: Partial<Record<UsageResource, number | null>>;
  history?: SubscriptionHistoryEntry[];
  accessOverride?: { enabled: boolean; reason: string };
}

export interface GovernanceWorkspace {
  id: string;
  name: string;
  logo: string;
  parentWorkspaceId?: string;
  managedClientId?: string;
  planId: SaaSPlan['id'];
  maxUsers: number | null;
  activeUsers: number;
  subscriptionDate: string;
  subscriptionStatus: WorkspaceSubscription['status'];
  kind?: 'personal' | 'organization';
  ownerUserId?: string;
  settings: {
    inviteExpiryDays: number;
    requireApproval: boolean;
    timezone: string;
  };
}

export type ApprovalStage =
  | 'draft'
  | 'in_review'
  | 'pending_approval'
  | 'approved'
  | 'changes_requested'
  | 'rejected'
  | 'published';

export interface ApprovalComment {
  id: string;
  authorId: string;
  authorName: string;
  message: string;
  createdAt: string;
}

export interface ApprovalHistoryEntry {
  id: string;
  actorId: string;
  actorName: string;
  action: string;
  detail: string;
  createdAt: string;
}

export interface ContentApprovalItem {
  id: string;
  workspaceId: string;
  contentId: string;
  title: string;
  copy: string;
  previewUrl?: string;
  platform: SocialPlatform;
  format: PostFormat;
  authorId: string;
  authorName: string;
  createdAt: string;
  scheduledAt?: string;
  stage: ApprovalStage;
  approvedBy?: string;
  approvedAt?: string;
  publishedBy?: string;
  publishedAt?: string;
  comments: ApprovalComment[];
  history: ApprovalHistoryEntry[];
  strategyId?: string;
  campaignId?: string;
  versions?: ContentVersion[];
}

export interface AuditLogEntry {
  id: string;
  workspaceId: string;
  actorId: string;
  actorName: string;
  action: string;
  resource: string;
  detail: string;
  createdAt: string;
}

export interface GovernanceSession {
  currentUser: WorkspaceMember;
  workspace: GovernanceWorkspace;
}

export type SocialPlatform =
  | 'instagram'
  | 'linkedin'
  | 'tiktok'
  | 'youtube'
  | 'pinterest'
  | 'threads'
  | 'x'
  | 'facebook';

export interface ConnectedResource {
  id: string;
  name: string;
  type: 'profile' | 'page' | 'channel' | 'board' | 'organization';
  handle?: string;
  avatar?: string;
}

export type PostFormat =
  | 'post'
  | 'story'
  | 'carousel'
  | 'reels'
  | 'tiktok'
  | 'youtube-short'
  | 'youtube-long'
  | 'linkedin-article'
  | 'pin'
  | 'thread'
  | 'newsletter'
  | 'blog'
  | 'vsl'
  | 'ad'
  | 'presentation'
  | 'script';

export type PostStatus = 'draft' | 'in_production' | 'in_review' | 'pending_approval' | 'approved' | 'changes_requested' | 'rejected' | 'scheduled' | 'processing' | 'published' | 'error' | 'cancelled';

export interface BrandProfile {
  name: string;
  industry: string;
  tone: string;
  targetAudience: string;
  keywords: string[];
  doAndDonts: string;
  primaryColor: string;
}

export interface AIContextSnapshot {
  workspaceId: string;
  revision: number;
  company: string;
  products: string;
  services: string;
  visualIdentity: string;
  toneOfVoice: string;
  audience: string;
  personas: string;
  objectives: string;
  differentiators: string;
  competitors: string;
  objections: string;
  pains: string;
  desires: string;
  faq: string;
  requiredWords: string;
  forbiddenWords: string;
  history: string;
}

export interface ClientIntelligenceProfile {
  id: string;
  workspaceId: string;
  name: string;
  logoUrl?: string;
  status?: 'active' | 'approval' | 'paused';
  responsibleId?: string;
  responsibleName?: string;
  lastActivityAt?: string;
  segment: string;
  products: string;
  audience: string;
  positioning: string;
  toneOfVoice: string;
  visualIdentity: string;
  brandColors?: string[];
  typography?: string;
  visualReferences?: string;
  differentiators: string;
  competitors?: string;
  keywords?: string;
  avoidTopics?: string;
  notes?: string;
  featuredOffer: string;
  currentObjective: string;
  highlightedContentIds: string[];
  activeCampaignIds: string[];
  recommendedActions: string[];
  access?: {
    view: boolean;
    create: boolean;
    edit: boolean;
    approve: boolean;
    publish: boolean;
  };
  updatedAt: string;
}

export interface CampaignContentItem {
  id: string;
  format: PostFormat;
  funnelStage: 'descoberta' | 'consideracao' | 'conversao' | 'retencao';
  purpose: string;
  hook: string;
  status: 'planned' | 'in_production' | 'ready';
}

export interface CreativeIdea {
  id: string;
  clientId: string;
  campaignId?: string;
  title: string;
  angle: string;
  hook: string;
  format: PostFormat;
  funnelStage: CampaignContentItem['funnelStage'];
  cta: string;
  rationale: string;
}

export interface StudioHandoff {
  id: string;
  source: 'client' | 'campaign' | 'matrix' | 'analytics' | 'repurpose' | 'ai';
  clientId?: string;
  campaignId?: string;
  contentId?: string;
  objective: string;
  title: string;
  angle: string;
  hook: string;
  cta: string;
  format: PostFormat;
  funnelStage: string;
  createdAt: string;
}

export interface ClickScoreBreakdown {
  total: number;
  hook: number;
  clarity: number;
  differentiation: number;
  audienceFit: number;
  objectiveFit: number;
  cta: number;
  retention: number;
  brandConsistency: number;
  strengths: string[];
  improvements: string[];
}

export interface LearningSignal {
  id: string;
  clientId?: string;
  campaignId?: string;
  label: string;
  evidence: string;
  recommendation: string;
  confidence: 'hypothesis' | 'validated';
  source: 'content-metadata' | 'connected-analytics';
  createdAt: string;
}

export type StrategyStatus = 'draft' | 'planned' | 'active' | 'completed';

export interface StrategyCampaign {
  id: string;
  workspaceId: string;
  name: string;
  objective: string;
  startDate: string;
  endDate: string;
  budget: string;
  kpis: string[];
  products: string;
  audience: string;
  offer: string;
  channels: SocialPlatform[];
  importantDates: string;
  funnel: string;
  ctas: string[];
  executionPlan: string[];
  centralMessage?: string;
  angle?: string;
  contentPlan?: CampaignContentItem[];
  clientId?: string;
  status: StrategyStatus;
  contextRevision: number;
  createdAt: string;
  updatedAt: string;
}

export interface LibraryAsset {
  id: string;
  workspaceId: string;
  title: string;
  type: 'content' | 'upload' | 'campaign' | 'version' | 'prompt' | 'image' | 'video' | 'template' | 'document';
  tags: string[];
  campaignId?: string;
  clientId?: string;
  contentId?: string;
  url?: string;
  description?: string;
  mimeType?: string;
  size?: number;
  createdAt: string;
  updatedAt: string;
}

export interface ContentVersion {
  id: string;
  number: number;
  label: string;
  author: string;
  createdAt: string;
  copy?: string;
}

export interface Workspace {
  id: string;
  name: string;
  avatar: string;
  plan: 'Enterprise' | 'Pro' | 'Growth' | 'Solo Creator' | string;
  membersCount: number;
  brandProfile: BrandProfile;
}

export interface CarouselSlide {
  slideNumber: number;
  headline: string;
  text: string;
  bgStyle?: string;
  imagePrompt?: string;
}

export interface ApprovalStatus {
  reviewerName: string;
  reviewerRole: string;
  status: 'approved' | 'rejected' | 'pending';
  comment?: string;
  timestamp: string;
}

export interface Post {
  id: string;
  workspaceId: string;
  title: string;
  platform: SocialPlatform;
  channels?: SocialPlatform[];
  platformAdaptations?: Array<{
    platform: SocialPlatform;
    format?: PostFormat;
    copy?: string;
    caption?: string;
  }>;
  format: PostFormat;
  copy: string;
  hashtags: string[];
  imageUrl?: string;
  videoUrl?: string;
  slides?: CarouselSlide[];
  scheduledAt?: string;
  status: PostStatus;
  likes?: number;
  comments?: number;
  shares?: number;
  reach?: number;
  impressions?: number;
  saves?: number;
  clicks?: number;
  views?: number;
  replies?: number;
  conversions?: number;
  spend?: number;
  revenue?: number;
  paid?: boolean;
  author: string;
  createdAt: string;
  approvals?: ApprovalStatus[];
  aiScore?: number;
  strategyId?: string;
  campaignId?: string;
  responsibleId?: string;
  responsibleName?: string;
  assetIds?: string[];
  socialAccountIds?: string[];
  scheduledPublicationId?: string;
  externalPostId?: string;
  tiktokConsentConfirmed?: boolean;
  publicationError?: string;
  history?: Array<{
    id: string;
    action: string;
    detail: string;
    actorName: string;
    createdAt: string;
  }>;
  contextRevision?: number;
  objective?: string;
  origin?: 'manual' | 'context' | 'strategy' | 'automation' | 'analytics' | 'ai';
  versions?: ContentVersion[];
  clientId?: string;
  creativeIdeaId?: string;
  clickScoreBreakdown?: ClickScoreBreakdown;
}

export interface AutomationNode {
  id: string;
  type: 'trigger' | 'ai_generate' | 'image_studio' | 'schedule' | 'publish' | 'notify';
  label: string;
  details: string;
}

export interface AutomationFlow {
  id: string;
  title: string;
  trigger: string;
  nodes: AutomationNode[];
  isActive: boolean;
  executionsCount: number;
  lastRun?: string;
}

export interface ConnectedAnalyticsPoint {
  date: string;
  followers?: number | null;
  gained?: number | null;
  lost?: number | null;
  reach?: number | null;
  impressions?: number | null;
  engagements?: number | null;
  likes?: number | null;
  comments?: number | null;
  shares?: number | null;
  saves?: number | null;
  replies?: number | null;
  clicks?: number | null;
  views?: number | null;
  conversions?: number | null;
  spend?: number | null;
  revenue?: number | null;
  retention?: number | null;
  posts?: number;
}

export interface ConnectedAnalyticsContent {
  id: string;
  title: string;
  date: string;
  format: PostFormat;
  thumbnail?: string;
  caption?: string;
  campaignId?: string;
  status?: PostStatus;
  paid?: boolean | null;
  reach?: number | null;
  impressions?: number | null;
  likes?: number | null;
  comments?: number | null;
  shares?: number | null;
  saves?: number | null;
  replies?: number | null;
  clicks?: number | null;
  views?: number | null;
  conversions?: number | null;
  spend?: number | null;
  revenue?: number | null;
}

export interface ConnectedAnalyticsSnapshot {
  source: 'provider-api';
  dataStatus: 'available' | 'partial' | 'unavailable';
  updatedAt: string;
  refreshIntervalMinutes?: number;
  points: ConnectedAnalyticsPoint[];
  contents?: ConnectedAnalyticsContent[];
  unavailableMetrics?: string[];
}

export interface ConnectedAccount {
    id: string;
    workspaceId?: string;
    clientId?: string;
  platform: SocialPlatform;
  handle: string;
  connected: boolean;
  followers: string;
  bestTime: string;
  engagement: string;
  name?: string;
  avatar?: string;
  lastSync?: string;
  permissions?: string[];
  availableResources?: ConnectedResource[];
  selectedResourceIds?: string[];
  syncPreferences?: Array<'profile' | 'publishing' | 'analytics'>;
  isDefault?: boolean;
  company?: string;
  connectionStatus?: 'not_configured' | 'authorization_required' | 'connecting' | 'connected' | 'syncing' | 'synced' | 'sync_error' | 'expired' | 'permission_insufficient' | 'authorization_revoked' | 'error';
  lastError?: string;
  analytics?: ConnectedAnalyticsSnapshot;
  providerAccountId?: string;
  providerConnectionIds?: string[];
  accountType?: string;
  connectedAt?: string;
  tokenExpiring?: boolean;
  capabilities?: {
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
}

export interface AIChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  module?: NavigationTab;
  favorite?: boolean;
  brandScore?: number;
  researchedExternally?: boolean;
  actions?: Array<{
    label: string;
    tab: NavigationTab;
    kind: 'campaign' | 'studio' | 'calendar' | 'variants';
    actionId?: string;
    risk?: 'read' | 'reversible' | 'external' | 'critical';
    requiresConfirmation?: boolean;
  }>;
}

export type AIMemoryCategory = 'identity' | 'communication' | 'content' | 'visual' | 'preference';
export type AIMemoryScope = 'task' | 'temporary' | 'recurring' | 'permanent';

export interface AIMemoryEntry {
  id: string;
  workspaceId: string;
  /** Optional client boundary. Workspace memories never override a selected client's identity. */
  clientId?: string;
  category: AIMemoryCategory;
  label: string;
  value: string;
  scope: AIMemoryScope;
  confidence: number;
  source: 'conversation' | 'user' | 'approval' | 'analytics' | 'manual';
  occurrences: number;
  createdAt: string;
  updatedAt: string;
  evolution?: Array<{ value: string; changedAt: string; source: AIMemoryEntry['source'] }>;
}

export interface SearchResultItem {
  id: string;
  title: string;
  subtitle: string;
  type: 'post' | 'campaign' | 'action' | 'workspace' | 'automation' | 'client' | 'asset';
  tabToNavigate: NavigationTab;
}
