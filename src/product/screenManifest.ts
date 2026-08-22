export type StitchProject = 'approved' | 'creative-lab';

export type SurfaceKind =
  | 'global'
  | 'discovery'
  | 'campaign'
  | 'content'
  | 'library'
  | 'editor'
  | 'governance'
  | 'approval'
  | 'analytics'
  | 'automation'
  | 'workspace';

export interface StitchScreen {
  id: string;
  project: StitchProject;
  frame: string;
  route: string;
  kind: SurfaceKind;
  state?: string;
  implementation: 'existing' | 'evolved' | 'new' | 'shared-state';
}

const approved = (id: string, frame: string, route: string, kind: SurfaceKind, implementation: StitchScreen['implementation'], state?: string): StitchScreen => ({
  id, project: 'approved', frame, route, kind, implementation, state,
});

const lab = (id: string, frame: string, route: string, kind: SurfaceKind, implementation: StitchScreen['implementation'], state?: string): StitchScreen => ({
  id, project: 'creative-lab', frame, route, kind, implementation, state,
});

/**
 * Executable traceability manifest for the two valid Stitch projects.
 * The discarded Creative OS Redesign project is deliberately absent.
 */
export const STITCH_SCREENS: readonly StitchScreen[] = [
  approved('A01', 'Campaign Room V3', '/campaigns/active', 'campaign', 'evolved'),
  approved('A02', 'Contextual Copilot V5.1', '/copilot?context=campaign', 'global', 'evolved', 'contextual'),
  approved('A03', 'Lineage Library V5', '/library/lineage', 'library', 'new'),
  approved('A04', 'Tool Atlas V7.2 — Atlas completo aberto', '/today?atlas=open', 'global', 'shared-state', 'open'),
  approved('A05', 'Newsroom V3', '/discover', 'discovery', 'new'),
  approved('A06', 'Settings Command V5', '/settings/ai-governance', 'governance', 'evolved'),
  approved('A07', 'Navigation V6.5 — Visual Editor / Focus Mode', '/content/draft/edit?mode=visual&focus=1', 'editor', 'shared-state', 'focus'),
  approved('A08', 'Channel Connections V5', '/settings/channels', 'governance', 'evolved'),
  approved('A09', 'Reuse Workshop V5', '/content/post-1/remix', 'content', 'evolved', 'reuse'),
  approved('A10', 'Tool Atlas V7.3 — Busca por intenção', '/today?atlas=search', 'global', 'shared-state', 'search'),
  approved('A11', 'Tool Atlas V7.4 — Personalizar e retomar', '/today?atlas=customize', 'global', 'shared-state', 'customize'),
  approved('A12', 'Template Systems V5', '/templates', 'content', 'evolved'),
  approved('A13', 'Essential Menu V8.2 — Aberto', '/today?menu=open', 'global', 'shared-state', 'open'),
  approved('A14', 'Approval Room V5', '/approvals/post-1', 'approval', 'evolved'),
  approved('A15', 'Radar Room V4', '/radar', 'discovery', 'new'),
  approved('A16', 'Studio Composer V5', '/campaigns/active/studio', 'editor', 'evolved', 'campaign'),
  approved('A17', 'Team Access Room V5', '/settings/team', 'governance', 'evolved'),
  approved('A18', 'Navigation V6.1 — Hoje / Descobrir', '/today', 'global', 'evolved', 'today'),
  approved('A19', 'Publisher Control V5', '/publish/active', 'approval', 'evolved', 'publisher'),
  approved('A20', 'Navigation V6.4 — Campaign Room contextual', '/campaigns/active?nav=context', 'campaign', 'shared-state', 'contextual-nav'),
  approved('A21', 'Top Dropdown V9 — Criar aberto', '/content/new?create=open', 'global', 'shared-state', 'create-open'),
  approved('A22', 'Subscription Capacity V5', '/settings/billing', 'governance', 'evolved'),
  approved('A23', 'Workspace Entry V5', '/workspaces/new', 'workspace', 'evolved'),
  approved('A24', 'Workspace Switcher V5', '/today?workspace=dialog', 'global', 'shared-state', 'dialog'),
  approved('A25', 'Global Spotlight V5', '/today?spotlight=open', 'global', 'evolved', 'open'),
  approved('A26', 'Audit Trail V5', '/settings/audit', 'governance', 'evolved'),
  approved('A27', 'Brand Memory V4.1', '/brand-memory', 'workspace', 'evolved'),
  approved('A28', 'Automation Workshop V5', '/automations/active', 'automation', 'evolved'),
  approved('A29', 'Essential Menu V8.1 — Fechado', '/today?menu=closed', 'global', 'shared-state', 'closed'),
  approved('A30', 'Editorial Calendar V5', '/calendar', 'content', 'evolved'),
  approved('A31', 'Tool Atlas V7.1 — Menu fechado', '/today?atlas=closed', 'global', 'shared-state', 'closed'),
  approved('A32', 'Navigation V6.2 — Etapa Criar aberta', '/content/new', 'content', 'new', 'create-hub'),
  approved('A33', 'Video Studio V5', '/content/draft/edit?mode=video', 'editor', 'evolved', 'video'),
  approved('A34', 'Performance Observatory V5.3', '/analytics/learning', 'analytics', 'evolved'),
  approved('A35', 'Carousel Builder V5', '/content/draft/edit?mode=carousel', 'editor', 'evolved', 'carousel'),
  approved('A36', 'Campaign Intake V4.1', '/campaigns/new', 'campaign', 'new', 'intake'),
  approved('A37', 'Visual Editor V5', '/content/draft/edit?mode=visual', 'editor', 'evolved', 'visual'),
  approved('A38', 'Navigation V6.3 — Workspace Switcher', '/today?workspace=menu', 'global', 'shared-state', 'menu'),

  lab('B01', 'Campaign Moodboard', '/campaigns/active/moodboard', 'campaign', 'new', 'moodboard'),
  lab('B02', 'Visual Content Board V2', '/content', 'content', 'evolved', 'board'),
  lab('B03', 'Pro Composition Canvas V2', '/content/draft/edit?mode=visual&canvas=pro', 'editor', 'shared-state', 'canvas'),
  lab('B04', 'Campaign World', '/campaigns/active/world', 'campaign', 'new', 'world'),
  lab('B05', 'Editorial Creation Desk V2', '/content/draft/edit?mode=editorial', 'editor', 'evolved', 'editorial'),
  lab('B06', 'Creative Review Room V2', '/approvals/post-1?view=creative', 'approval', 'shared-state', 'creative'),
  lab('B07', 'Precision & Type (Canvas State)', '/content/draft/edit?mode=visual&panel=typography', 'editor', 'shared-state', 'typography'),
  lab('B08', 'Content Inventory V1', '/content?view=inventory', 'content', 'shared-state', 'inventory'),
  lab('B09', 'Brand Asset Library', '/library/assets', 'library', 'evolved', 'assets'),
  lab('B10', 'Format & Variation Board', '/content/post-1/variations', 'content', 'new', 'variations'),
  lab('B11', 'Visual Composition Handoff V1', '/content/draft/edit?mode=visual&handoff=1', 'editor', 'new', 'handoff'),
  lab('B12', 'Visual Remix Lab V2', '/content/post-1/remix?lab=visual', 'content', 'shared-state', 'visual-remix'),
  lab('B13', 'Carousel Builder', '/content/draft/edit?mode=carousel&variant=lab', 'editor', 'shared-state', 'carousel-lab'),
  lab('B14', 'Motion Studio (Canvas State)', '/content/draft/edit?mode=video&panel=motion', 'editor', 'shared-state', 'motion'),
  lab('B15', 'Post Detail & Performance V1', '/content/post-1', 'content', 'new', 'detail'),
  lab('B16', 'Content Command Dashboard V1', '/content/dashboard', 'content', 'new', 'dashboard'),
  lab('B17', 'Post Creation Workspace V1', '/content/new?type=post', 'content', 'evolved', 'post-create'),
  lab('B18', 'Element Vault (Canvas State)', '/content/draft/edit?mode=visual&panel=elements', 'editor', 'shared-state', 'elements'),
  lab('B19', 'Effects & Light (Canvas State)', '/content/draft/edit?mode=visual&panel=effects', 'editor', 'shared-state', 'effects'),
] as const;

export const SCREEN_TOTALS = {
  approved: STITCH_SCREENS.filter((screen) => screen.project === 'approved').length,
  creativeLab: STITCH_SCREENS.filter((screen) => screen.project === 'creative-lab').length,
  total: STITCH_SCREENS.length,
} as const;

export function screenForLocation(pathname: string, search: string): StitchScreen | undefined {
  const location = `${pathname}${search}`;
  return STITCH_SCREENS.find((screen) => screen.route === location)
    || STITCH_SCREENS.find((screen) => screen.route.split('?')[0] === pathname && screen.kind !== 'global');
}

