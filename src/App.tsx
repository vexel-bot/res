/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { visualTransition } from './motion/visualTransition';
import { appearance } from './theme/appearance';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { SpotlightModal } from './components/SpotlightModal';
import { ClickoLoader } from './components/ClickoLoader';
import { LoginView } from './components/LoginView';
import { SubscriptionGateView } from './components/SubscriptionGateView';
import { AccessDeniedView } from './components/AccessDeniedView';
import { GovernanceFeedback } from './components/GovernanceFeedback';
import { PublicComplianceView, publicCompliancePage } from './components/PublicComplianceView';
import { ClientPortalView } from './components/ClientPortalView';
import { useGovernance } from './context/GovernanceContext';
import { useAuth } from './context/AuthContext';
import { useOperations } from './context/OperationsContext';
import { useTheme } from './context/ThemeContext';
import { useVisualViewport } from './hooks/useVisualViewport';
import { setKlicActiveModule } from './klic/pageContext';
import type { ApprovalStage } from './types';

import {
  NavigationTab,
  Post,
} from './types';

const DashboardView = React.lazy(() => import('./components/DashboardEditorialView').then(module => ({ default: module.DashboardView })));
const WorkspaceView = React.lazy(() => import('./components/WorkspaceView').then(module => ({ default: module.WorkspaceView })));
const StrategyView = React.lazy(() => import('./components/StrategyView').then(module => ({ default: module.StrategyView })));
const LibraryView = React.lazy(() => import('./components/LibraryView').then(module => ({ default: module.LibraryView })));
const CreationStudioView = React.lazy(() => import('./components/CreationStudioView').then(module => ({ default: module.CreationStudioView })));
const AIChatView = React.lazy(() => import('./components/AIChatView').then(module => ({ default: module.AIChatView })));
const ConnectedAccountsView = React.lazy(() => import('./components/ConnectedAccountsView').then(module => ({ default: module.ConnectedAccountsView })));
const EditorialCalendarView = React.lazy(() => import('./components/EditorialCalendarView').then(module => ({ default: module.EditorialCalendarView })));
const AnalyticsView = React.lazy(() => import('./components/AnalyticsIntelligenceView').then(module => ({ default: module.AnalyticsView })));
const AutomationBuilderView = React.lazy(() => import('./components/AutomationBuilderView').then(module => ({ default: module.AutomationBuilderView })));
const SettingsView = React.lazy(() => import('./components/SettingsView').then(module => ({ default: module.SettingsView })));
const TeamManagementView = React.lazy(() => import('./components/TeamManagementView').then(module => ({ default: module.TeamManagementView })));
const ApprovalsView = React.lazy(() => import('./components/ApprovalsView').then(module => ({ default: module.ApprovalsView })));
const SubscriptionView = React.lazy(() => import('./components/SubscriptionView').then(module => ({ default: module.SubscriptionView })));
const FloatingAIAssistant = React.lazy(() => import('./components/FloatingAIAssistant').then(module => ({ default: module.FloatingAIAssistant })));
const KlicOperationalBridge = React.lazy(() => import('./klic/KlicOperationalBridge').then(module => ({ default: module.KlicOperationalBridge })));
const ClickoStudioView = React.lazy(() => import('./studios/ClickoStudioView').then(module => ({ default: module.ClickoStudioView })));

const TAB_PATHS: Record<NavigationTab, string> = {
  dashboard: '/dashboard',
  'create-image': '/image',
  'create-video': '/video',
  'create-copy': '/create',
  'ai-chat': '/klic',
  'connected-accounts': '/connected-accounts',
  workspace: '/clients',
  strategy: '/strategy',
  library: '/library',
  calendar: '/calendar',
  analytics: '/analytics',
  automations: '/automations',
  approvals: '/approvals',
  team: '/team',
  subscription: '/subscription',
  settings: '/settings',
};

const PATH_TABS = Object.fromEntries(
  Object.entries(TAB_PATHS).map(([tab, path]) => [path, tab as NavigationTab]),
) as Record<string, NavigationTab>;

const initialNavigationTab = (): NavigationTab => {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  return PATH_TABS[path] || 'dashboard';
};

export default function App() {
  useVisualViewport();
  const { theme } = useTheme();
  const auth = useAuth();
  const { currentUser, canAccess, loading: governanceLoading } = useGovernance();
  const { activeWorkspace, posts, addPosts, updatePosts } = useOperations();
  const [currentTab, setCurrentTab] = React.useState<NavigationTab>(initialNavigationTab);

  const [isSpotlightOpen, setIsSpotlightOpen] = React.useState(false);
  const [isCompact, setIsCompact] = React.useState(false);
  const [showSplash, setShowSplash] = React.useState(() => window.location.pathname !== '/login');
  const compliancePage = publicCompliancePage(window.location.pathname);
  const subscriptionAccessAllowed = auth.account?.subscriptionAccessAllowed ?? ['active', 'trialing'].includes(auth.account?.subscriptionStatus || '');

  const navigate = React.useCallback((tab: NavigationTab, replace = false) => {
    setKlicActiveModule(tab);
    visualTransition('content', () => setCurrentTab(tab));
    const nextPath = TAB_PATHS[tab];
    if (window.location.pathname !== nextPath) {
      window.history[replace ? 'replaceState' : 'pushState']({}, '', nextPath);
    }
  }, []);

  React.useEffect(() => {
    const openCommandCenter = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase('pt-BR') === 'k') {
        event.preventDefault();
        setIsSpotlightOpen(true);
      }
    };
    window.addEventListener('keydown', openCommandCenter);
    return () => window.removeEventListener('keydown', openCommandCenter);
  }, []);

  React.useEffect(() => {
    const onPopState = () => {
      const tab = initialNavigationTab();
      setKlicActiveModule(tab);
      visualTransition('content', () => setCurrentTab(tab));
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  React.useEffect(() => {
    if (!showSplash) return;
    const timer = window.setTimeout(() => setShowSplash(false), 780);
    return () => window.clearTimeout(timer);
  }, [showSplash]);

  React.useEffect(() => {
    if (auth.authenticated && ['/login', '/signup', '/forgot-password', '/reset-password', '/verify-email'].includes(window.location.pathname.replace(/\/+$/, '') || '/')) {
      const destination = subscriptionAccessAllowed ? '/dashboard' : '/plans';
      window.history.replaceState({}, '', destination);
      if (destination === '/dashboard') { setKlicActiveModule('dashboard'); setCurrentTab('dashboard'); }
    }
  }, [auth.authenticated, subscriptionAccessAllowed]);

  // Global handler to add new posts generated by AI or created manually
  const handleAddPosts = (newPostsData: Partial<Post>[]) => {
    const created: Post[] = newPostsData.map((p, idx) => ({
      id: `post-${Date.now()}-${idx}`,
      workspaceId: activeWorkspace.id,
      title: p.title || 'Conteúdo Sem Título',
      platform: p.platform || 'instagram',
      format: p.format || 'post',
      copy: p.copy || '',
      hashtags: p.hashtags || [],
      slides: p.slides,
      imageUrl: p.imageUrl,
      videoUrl: p.videoUrl,
      scheduledAt: p.scheduledAt || new Date().toISOString(),
      status: currentUser?.role === 'collaborator' && ['scheduled', 'published'].includes(p.status || 'scheduled') ? 'pending_approval' : (p.status || 'scheduled'),
      author: p.author || currentUser?.name || 'Usuário',
      createdAt: new Date().toISOString(),
      aiScore: p.aiScore || 90,
      clientId: p.clientId,
      campaignId: p.campaignId,
      strategyId: p.strategyId,
      contextRevision: p.contextRevision,
      objective: p.objective,
      origin: p.origin,
      creativeIdeaId: p.creativeIdeaId,
      clickScoreBreakdown: p.clickScoreBreakdown,
    }));

    addPosts(created);
  };

  const handleSaveSinglePost = (postData: Partial<Post>) => {
    handleAddPosts([postData]);
    navigate('calendar');
  };

  const handleApprovalStatusChange = (contentId: string, stage: ApprovalStage) => {
    const statusMap: Record<ApprovalStage, Post['status']> = {
      draft: 'draft',
      in_review: 'in_review',
      pending_approval: 'pending_approval',
      approved: 'approved',
      changes_requested: 'changes_requested',
      rejected: 'rejected',
      published: 'published',
    };
    updatePosts((current) => current.map((post) => post.id === contentId ? { ...post, status: statusMap[stage] } : post));
  };

  // Image/Video retain their existing flow: this audit explicitly excludes them.
  const excludedMediaTab = currentTab === 'create-image' || currentTab === 'create-video';
  const hasAccessToCurrentTab = excludedMediaTab
    ? governanceLoading || !currentUser || canAccess(currentTab)
    : !governanceLoading && Boolean(currentUser) && canAccess(currentTab);

  if (compliancePage) {
    return <PublicComplianceView page={compliancePage} />;
  }

  if (window.location.pathname === '/client-portal') return <ClientPortalView />;

  if (auth.loading) {
    return <main data-theme={theme} className="clicko-session-loading grid min-h-screen place-items-center bg-black text-white"><ClickoLoader size="large" tone={appearance.isAuthPath(location.pathname) ? 'dark' : 'auto'} label="Verificando sessão" /></main>;
  }

  if (!auth.authenticated) {
    return <LoginView />;
  }

  if (!subscriptionAccessAllowed) {
    return <SubscriptionGateView />;
  }

  return (
    <div data-theme={theme} data-current-tab={currentTab} data-atmosphere="solid" className={`clicko-app-shell ${currentTab === 'create-image' || currentTab === 'create-video' ? '' : 'clicko-creative-workspace'} flex min-h-screen font-sans antialiased selection:bg-[rgba(255,255,255,0.72)] selection:text-[#000000]`}>
      {currentTab !== 'create-image' && currentTab !== 'create-video' && <React.Suspense fallback={null}><KlicOperationalBridge module={currentTab} /></React.Suspense>}
      {showSplash && (
        <div className="clicko-splash fixed inset-0 z-[100] grid place-items-center bg-black">
          <ClickoLoader size="large" label="Carregando Clicko" />
        </div>
      )}
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={navigate}
        isCompact={isCompact}
        onToggleCompact={() => setIsCompact(!isCompact)}
        onOpenSpotlight={() => setIsSpotlightOpen(true)}
        onNewPost={() => navigate('create-copy')}
      />

      {/* Main Workspace Stage */}
      <div
        className={`clicko-app-stage flex min-w-0 flex-1 flex-col transition-all duration-300 ease-out ${
          isCompact ? 'pl-[80px]' : 'pl-[232px] max-[900px]:pl-[80px]'
        }`}
      >
        {/* Header Toolbar */}
        <Header
          currentTab={currentTab}
          activeWorkspace={activeWorkspace}
          onOpenSpotlight={() => setIsSpotlightOpen(true)}
          onOpenAICentral={() => navigate('ai-chat')}
          onNewPost={() => navigate('create-copy')}
          isCompact={isCompact}
          onToggleCompact={() => setIsCompact(!isCompact)}
          onNavigate={navigate}
        />

        {/* Dynamic Tab View Area */}
        <main className="clicko-main-stage flex-1 overflow-x-hidden overflow-y-auto">
          <React.Suspense fallback={<ClickoLoader context="section" label="Carregando o módulo" />}>
            {!hasAccessToCurrentTab && (governanceLoading ? <ClickoLoader context="section" label="Carregando o ambiente" /> : <AccessDeniedView onBack={() => navigate('dashboard')} />)}

          {hasAccessToCurrentTab && currentTab === 'dashboard' && (
            <DashboardView
              posts={posts}
              activeWorkspace={activeWorkspace}
              onNavigate={navigate}
              onNewPost={() => navigate('create-copy')}
              onSelectPost={() => navigate('calendar')}
            />
          )}

          {hasAccessToCurrentTab && currentTab === 'workspace' && <WorkspaceView onNavigate={navigate} />}

          {hasAccessToCurrentTab && currentTab === 'strategy' && <StrategyView onOpenStudio={() => navigate('create-image')} />}

          {hasAccessToCurrentTab && currentTab === 'library' && <LibraryView onOpenStudio={() => navigate('create-image')} />}

          {hasAccessToCurrentTab && currentTab === 'create-image' && <ClickoStudioView module="create-image" onNavigate={navigate} />}

          {hasAccessToCurrentTab && currentTab === 'create-video' && <ClickoStudioView module="create-video" onNavigate={navigate} />}

          {hasAccessToCurrentTab && currentTab === 'create-copy' && <CreationStudioView onSavePost={handleSaveSinglePost} />}

          {hasAccessToCurrentTab && currentTab === 'ai-chat' && <AIChatView onNavigate={navigate} />}

          {hasAccessToCurrentTab && currentTab === 'connected-accounts' && <ConnectedAccountsView />}

          {hasAccessToCurrentTab && currentTab === 'calendar' && (
            <EditorialCalendarView
              posts={posts}
              onNewPost={() => navigate('create-copy')}
              onNavigate={navigate}
            />
          )}

          {hasAccessToCurrentTab && currentTab === 'analytics' && <AnalyticsView onOpenStudio={() => navigate('create-image')} onNavigate={navigate} />}

          {hasAccessToCurrentTab && currentTab === 'automations' && <AutomationBuilderView onNavigate={navigate} />}

          {hasAccessToCurrentTab && currentTab === 'approvals' && <ApprovalsView onStatusChange={handleApprovalStatusChange} onNavigate={navigate} />}

          {hasAccessToCurrentTab && currentTab === 'team' && <TeamManagementView />}

          {hasAccessToCurrentTab && currentTab === 'subscription' && <SubscriptionView />}

            {hasAccessToCurrentTab && currentTab === 'settings' && <SettingsView />}
          </React.Suspense>
        </main>
      </div>

      {/* Spotlight Raycast Search Overlay */}
      <SpotlightModal
        isOpen={isSpotlightOpen}
        onClose={() => setIsSpotlightOpen(false)}
        onNavigate={navigate}
      />
      <GovernanceFeedback />
      {currentTab !== 'ai-chat' && currentTab !== 'dashboard' && <React.Suspense fallback={null}><FloatingAIAssistant currentTab={currentTab} onOpenFullChat={() => navigate('ai-chat')} /></React.Suspense>}
    </div>
  );
}
