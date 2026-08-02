export type NavigationTab =
  | 'dashboard'
  | 'workspace'
  | 'brain'
  | 'strategy'
  | 'studio'
  | 'library'
  | 'calendar'
  | 'publisher'
  | 'analytics'
  | 'automations'
  | 'approvals'
  | 'team'
  | 'subscription'
  | 'audit-logs'
  | 'settings';

export type UserRole = 'master' | 'collaborator';

export type WorkspaceModule =
  | 'dashboard'
  | 'workspace'
  | 'brain'
  | 'strategy'
  | 'studio'
  | 'library'
  | 'calendar'
  | 'automations'
  | 'analytics';

export type MemberStatus = 'active' | 'invited' | 'disabled';

export interface WorkspaceMember {
  id: string;
  workspaceId: string;
  name: string;
  email: string;
  avatar: string;
  role: UserRole;
  status: MemberStatus;
  modules: WorkspaceModule[];
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
}

export interface WorkspaceSubscription {
  id: string;
  workspaceId: string;
  planId: SaaSPlan['id'];
  status: 'active' | 'trialing' | 'past_due' | 'canceled';
  startedAt: string;
  renewsAt: string;
  billingEmail: string;
  paymentMethod: string;
}

export interface GovernanceWorkspace {
  id: string;
  name: string;
  logo: string;
  planId: SaaSPlan['id'];
  maxUsers: number | null;
  activeUsers: number;
  subscriptionDate: string;
  subscriptionStatus: WorkspaceSubscription['status'];
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

export type PostStatus = 'draft' | 'in_review' | 'pending_approval' | 'approved' | 'changes_requested' | 'rejected' | 'scheduled' | 'published';

export interface BrandProfile {
  name: string;
  industry: string;
  tone: string;
  targetAudience: string;
  keywords: string[];
  doAndDonts: string;
  primaryColor: string;
}

export interface BrandBrain {
  workspaceId: string;
  revision: number;
  updatedAt: string;
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
  sourceLinks: string[];
  sourceFiles: BrainSource[];
}

export interface BrainSource {
  id: string;
  name: string;
  type: 'document' | 'image' | 'video' | 'logo' | 'link' | 'social';
  url?: string;
  addedAt: string;
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
  status: StrategyStatus;
  brainRevision: number;
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
  contentId?: string;
  url?: string;
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
  plan: 'Enterprise' | 'Pro' | 'Growth';
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
  author: string;
  createdAt: string;
  approvals?: ApprovalStatus[];
  aiScore?: number;
  strategyId?: string;
  campaignId?: string;
  brainRevision?: number;
  objective?: string;
  origin?: 'manual' | 'brain' | 'strategy' | 'automation' | 'analytics';
  versions?: ContentVersion[];
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

export interface ConnectedAccount {
  id: string;
  platform: SocialPlatform;
  handle: string;
  connected: boolean;
  followers: string;
  bestTime: string;
  engagement: string;
}

export interface AIActionSuggestion {
  id: string;
  title: string;
  description: string;
  type: 'campaign' | 'schedule' | 'repurpose' | 'optimize';
  badge: string;
  impact: string;
}

export interface SearchResultItem {
  id: string;
  title: string;
  subtitle: string;
  type: 'post' | 'campaign' | 'action' | 'workspace' | 'automation';
  tabToNavigate: NavigationTab;
}
