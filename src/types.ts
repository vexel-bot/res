export type NavigationTab =
  | 'dashboard'
  | 'ai-central'
  | 'creation'
  | 'images'
  | 'video'
  | 'calendar'
  | 'publisher'
  | 'analytics'
  | 'automations'
  | 'collaboration'
  | 'settings';

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

export type PostStatus = 'draft' | 'pending_approval' | 'scheduled' | 'published';

export interface BrandProfile {
  name: string;
  industry: string;
  tone: string;
  targetAudience: string;
  keywords: string[];
  doAndDonts: string;
  primaryColor: string;
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

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'Owner' | 'Admin' | 'Creator' | 'Reviewer' | 'Client';
  avatar: string;
  status: 'active' | 'invited';
  lastActive: string;
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
