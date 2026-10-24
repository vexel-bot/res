import type { NavigationTab, WorkspaceMember } from '../types';
import type { KlicPageDetails } from './pageContext';

export type KlicDomain = 'brand' | 'clients' | 'strategy' | 'calendar' | 'library' | 'analytics' | 'connections' | 'approvals' | 'team' | 'history' | 'automations' | 'radar';
export type KlicScope = { workspaceId: string; userId: string; clientId: string | null };
export type KlicActor = KlicScope & { user: WorkspaceMember; accountType: 'personal' | 'company' };
export type KlicRecord = { workspaceId: string; clientId?: string | null; id?: string; [key: string]: unknown };
export type KlicEnvelope = {
  workspaceId: string;
  userId: string;
  clientId: string | null;
  source: 'browser-local';
  records: Partial<Record<KlicDomain, KlicRecord[]>>;
};
export type KlicPageContext = {
  module: NavigationTab;
  workspaceId: string;
  clientId: string | null;
  details: KlicPageDetails;
};
export type KlicRequest = {
  workspaceId: string;
  clientId: string | null;
  source: NavigationTab;
  pageContext?: KlicPageContext;
  context?: KlicEnvelope;
  message?: string;
  region?: 'BR' | 'GLOBAL';
  forceRefresh?: boolean;
  conversationContext?: Array<{ role: 'user' | 'assistant'; content: string }>;
};
export type KlicStage = 'understand' | 'analyze' | 'create' | 'organize' | 'execute' | 'measure' | 'learn';
export type KlicIntent = 'question' | 'analysis' | 'creation' | 'organization' | 'execution' | 'measurement' | 'learning';
export type KlicActionRisk = 'read' | 'reversible' | 'external' | 'critical';
export type KlicStageStatus = 'completed' | 'ready' | 'awaiting_confirmation' | 'blocked' | 'skipped';
export type KlicPlanStage = {
  stage: KlicStage;
  status: KlicStageStatus;
  summary: string;
  toolIds: string[];
};
export type KlicActionSuggestion = {
  actionId: string;
  label: string;
  destination: NavigationTab;
  risk: KlicActionRisk;
  requiresConfirmation: boolean;
  reason?: string;
};
export type KlicGoal = KlicScope & {
  id: string;
  title: string;
  metric?: string;
  target?: string;
  period?: string;
  status: 'active' | 'completed' | 'archived';
  source: 'user';
  createdAt: string;
  updatedAt: string;
};
export type KlicOrchestration = {
  traceId: string;
  intent: KlicIntent;
  source: NavigationTab;
  scopeMode: 'client' | 'workspace';
  page: KlicPageContext | null;
  status: 'planned' | 'awaiting_confirmation' | 'blocked' | 'completed';
  stages: KlicPlanStage[];
  actions: KlicActionSuggestion[];
  goals: Array<Pick<KlicGoal, 'id' | 'title' | 'metric' | 'target' | 'period' | 'status'>>;
  evidence: Array<Omit<KlicSource, 'records'>>;
};
export type KlicSource = { domain: KlicDomain; provenance: 'service' | 'browser-local' | 'mixed'; status: 'available' | 'empty' | 'unavailable' | 'denied'; records: KlicRecord[]; reason?: string };
export type KlicRecommendation = { id: string; text: string; evidence: string[]; kind: 'observation' | 'recommendation'; destination?: NavigationTab };
export type KlicAnalysis = { traceId: string; recommendations: KlicRecommendation[]; sources: Array<Omit<KlicSource, 'records'>>; insight: string };
export const KLIC_DOMAINS: KlicDomain[] = ['brand', 'clients', 'strategy', 'calendar', 'library', 'analytics', 'connections', 'approvals', 'team', 'history', 'automations', 'radar'];
export const KLIC_MODULES: NavigationTab[] = ['dashboard', 'ai-chat', 'workspace', 'strategy', 'calendar', 'library', 'analytics', 'connected-accounts', 'approvals', 'team', 'automations', 'settings', 'subscription', 'create-copy'];
export const domainModule: Record<KlicDomain, NavigationTab> = {
  brand: 'workspace', clients: 'workspace', strategy: 'strategy', calendar: 'calendar', library: 'library', analytics: 'analytics', connections: 'connected-accounts',
  approvals: 'approvals', team: 'team', history: 'ai-chat', automations: 'automations', radar: 'ai-chat',
};
export const scopeKey = (scope: KlicScope) => JSON.stringify([scope.workspaceId, scope.userId, scope.clientId]);
