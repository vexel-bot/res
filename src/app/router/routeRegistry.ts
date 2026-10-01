import type { NavigationTab } from "../../types";

export type RouteOwner = "canonical" | "product-surface" | "legacy";
export const CANONICAL_CX_ROUTE_FLAG = "VITE_CANONICAL_CX_ROUTES";

export interface RouteRollout {
  featureFlag: typeof CANONICAL_CX_ROUTE_FLAG;
  rollbackOwner: RouteOwner;
}
export type RouteShell =
  | "global"
  | "project"
  | "studio"
  | "decision"
  | "operation";

export interface RouteDefinition {
  routeId: string;
  template: string;
  family: string;
  owner: RouteOwner;
  shell: RouteShell;
  canonical: boolean;
  rollout?: RouteRollout;
  navigationTab?: NavigationTab;
  matches: (pathname: string) => boolean;
}

export const NAVIGATION_TAB_PATHS: Readonly<Record<NavigationTab, string>> = {
  dashboard: "/dashboard",
  workspace: "/discover",
  brain: "/brand-memory",
  strategy: "/projects",
  studio: "/campaigns/active/studio",
  library: "/library/assets",
  "create-image": "/content/draft/edit?mode=visual",
  "create-video": "/content/draft/edit?mode=video",
  "create-copy": "/content/new?type=post",
  "ai-chat": "/copilot?context=campaign",
  templates: "/templates",
  "connected-accounts": "/settings/channels",
  calendar: "/calendar",
  publisher: "/publish/active",
  analytics: "/analytics/learning",
  automations: "/automations/active",
  approvals: "/approvals/post-1",
  team: "/settings/team",
  subscription: "/settings/billing",
  "audit-logs": "/settings/audit",
  settings: "/settings/ai-governance",
};

export function normalizePathname(pathname: string) {
  const clean = pathname.split(/[?#]/, 1)[0].replace(/\/+$/, "");
  return clean || "/";
}

const exact = (
  routeId: string,
  path: string,
  family: string,
  owner: RouteOwner,
  shell: RouteShell,
  canonical = owner === "canonical",
  navigationTab?: NavigationTab,
): RouteDefinition => ({
  routeId,
  template: path,
  family,
  owner,
  shell,
  canonical,
  rollout:
    owner === "canonical"
      ? {
          featureFlag: CANONICAL_CX_ROUTE_FLAG,
          rollbackOwner: "legacy",
        }
      : undefined,
  navigationTab,
  matches: (pathname) => normalizePathname(pathname) === path,
});

const pattern = (
  routeId: string,
  template: string,
  expression: RegExp,
  family: string,
  owner: RouteOwner,
  shell: RouteShell,
  canonical = owner === "canonical",
  navigationTab?: NavigationTab,
): RouteDefinition => ({
  routeId,
  template,
  family,
  owner,
  shell,
  canonical,
  rollout:
    owner === "canonical"
      ? {
          featureFlag: CANONICAL_CX_ROUTE_FLAG,
          rollbackOwner: "legacy",
        }
      : undefined,
  navigationTab,
  matches: (pathname) => expression.test(normalizePathname(pathname)),
});

/**
 * Single executable ownership map. It deliberately preserves the current
 * render owners while the strangler migration moves one route family at a
 * time. Matchers are non-overlapping so one URL can never have two owners.
 */
export const ROUTE_REGISTRY: readonly RouteDefinition[] = [
  exact("ROUTE-ROOT", "/", "home", "canonical", "global", true, "dashboard"),
  exact("ROUTE-DASHBOARD", "/dashboard", "home", "canonical", "global", true, "dashboard"),
  exact("ROUTE-TODAY", "/today", "home", "canonical", "global", true, "dashboard"),
  exact("ROUTE-RADAR", "/radar", "radar", "canonical", "global", true, "workspace"),
  pattern("ROUTE-OPPORTUNITY", "/radar/opportunities/:opportunityId", /^\/radar\/opportunities\/[^/]+$/, "radar", "canonical", "decision"),
  exact("ROUTE-CAMPAIGN-NEW", "/campaigns/new", "campaign", "canonical", "decision", true, "strategy"),
  pattern("ROUTE-CAMPAIGN", "/campaigns/:campaignId", /^\/campaigns\/(?!new$)[^/]+$/, "campaign", "canonical", "project", true, "strategy"),
  pattern("ROUTE-CAMPAIGN-WORLD", "/campaigns/:campaignId/world", /^\/campaigns\/[^/]+\/world$/, "campaign", "canonical", "project"),
  pattern("ROUTE-CAMPAIGN-MOODBOARD", "/campaigns/:campaignId/moodboard", /^\/campaigns\/[^/]+\/moodboard$/, "campaign", "canonical", "project"),
  exact("ROUTE-CONTENT", "/content", "content", "canonical", "global", true, "library"),
  pattern("ROUTE-CONTENT-DETAIL", "/content/:contentId", /^\/content\/(?!new$|dashboard$)[^/]+$/, "content", "canonical", "project"),
  pattern("ROUTE-CONTENT-EDIT", "/content/:contentId/edit", /^\/content\/[^/]+\/edit$/, "editor", "canonical", "studio", true, "library"),
  pattern("ROUTE-CONTENT-REMIX", "/content/:contentId/remix", /^\/content\/[^/]+\/remix$/, "reuse", "canonical", "studio"),
  pattern("ROUTE-APPROVAL", "/approvals/:contentId", /^\/approvals\/[^/]+$/, "review", "canonical", "decision", true, "approvals"),
  exact("ROUTE-CALENDAR", "/calendar", "publish", "canonical", "global", true, "calendar"),
  pattern("ROUTE-PUBLISH", "/publish/:contentId", /^\/publish\/[^/]+$/, "publish", "canonical", "decision", true, "publisher"),
  exact("ROUTE-BRAND-MEMORY", "/brand-memory", "brand", "canonical", "operation", true, "brain"),
  exact("ROUTE-LIBRARY-ASSETS", "/library/assets", "library", "canonical", "global", true, "library"),
  pattern("ROUTE-IMAGE-LAB", "/library/assets/:assetId/edit", /^\/library\/assets\/[^/]+\/edit$/, "library", "canonical", "studio", true, "create-image"),
  exact("ROUTE-LIBRARY-IDENTITIES", "/library/identities", "identity", "canonical", "operation", true, "library"),
  exact("ROUTE-ANALYTICS", "/analytics/learning", "analytics", "canonical", "global", true, "analytics"),
  exact("ROUTE-FACTORY", "/factory", "factory", "canonical", "operation"),
  pattern("ROUTE-FACTORY-ROUND", "/factory/:roundId", /^\/factory\/[^/]+$/, "factory", "canonical", "operation"),
  exact("ROUTE-PROJECTS", "/projects", "projects", "canonical", "global", true, "strategy"),
  exact("ROUTE-APPS", "/apps", "apps", "canonical", "operation"),
  pattern("ROUTE-APP-DETAIL", "/apps/:appId", /^\/apps\/[^/]+$/, "apps", "canonical", "operation"),

  exact("ROUTE-DISCOVER", "/discover", "radar", "product-surface", "global", false, "workspace"),
  exact("ROUTE-CAMPAIGNS", "/campaigns", "campaign", "product-surface", "global", false, "strategy"),
  pattern("ROUTE-CAMPAIGN-STUDIO", "/campaigns/:campaignId/studio", /^\/campaigns\/[^/]+\/studio$/, "campaign", "product-surface", "studio", false, "studio"),
  pattern("ROUTE-PROJECT", "/projects/:projectId", /^\/projects\/[^/]+$/, "projects", "product-surface", "project", false),
  pattern("ROUTE-PROJECT-CREATIVE", "/projects/:projectId/creative", /^\/projects\/[^/]+\/creative$/, "projects", "product-surface", "studio", false),
  exact("ROUTE-CONTENT-NEW", "/content/new", "create", "product-surface", "decision", false, "create-copy"),
  exact("ROUTE-CONTENT-DASHBOARD", "/content/dashboard", "content", "product-surface", "global", false),
  pattern("ROUTE-CONTENT-VARIATIONS", "/content/:contentId/variations", /^\/content\/[^/]+\/variations$/, "reuse", "product-surface", "studio", false),
  exact("ROUTE-WORKSPACE-NEW", "/workspaces/new", "workspace", "product-surface", "operation", false),
  exact("ROUTE-LIBRARY-LINEAGE", "/library/lineage", "library", "product-surface", "global", false),
  exact("ROUTE-TEMPLATES", "/templates", "library", "product-surface", "global", false, "templates"),
  exact("ROUTE-AI-GOVERNANCE", "/settings/ai-governance", "settings", "product-surface", "operation", false, "settings"),
  exact("ROUTE-CHANNELS", "/settings/channels", "settings", "product-surface", "operation", false, "connected-accounts"),
  exact("ROUTE-TEAM", "/settings/team", "settings", "product-surface", "operation", false, "team"),
  exact("ROUTE-BILLING", "/settings/billing", "settings", "product-surface", "operation", false, "subscription"),
  exact("ROUTE-AUDIT", "/settings/audit", "settings", "product-surface", "operation", false, "audit-logs"),
  pattern("ROUTE-AUTOMATION", "/automations/:automationId", /^\/automations\/[^/]+$/, "automation", "product-surface", "operation", false, "automations"),
  exact("ROUTE-REFERENCE-SCREENS", "/reference/screens", "reference", "product-surface", "operation", false),

  exact("ROUTE-COPILOT", "/copilot", "copilot", "legacy", "global", false, "ai-chat"),
] as const;

export function matchingRoutesForPath(pathname: string) {
  return ROUTE_REGISTRY.filter((route) => route.matches(pathname));
}

export function routeForPath(pathname: string): RouteDefinition | undefined {
  const matches = matchingRoutesForPath(pathname);
  if (matches.length > 1) {
    throw new Error(
      `Route ownership conflict for ${normalizePathname(pathname)}: ${matches
        .map((route) => route.routeId)
        .join(", ")}`,
    );
  }
  return matches[0];
}

export function routeOwnerForPath(pathname: string): RouteOwner | undefined {
  return routeForPath(pathname)?.owner;
}

function runtimeFeatureFlag(name: string): string | undefined {
  const viteValue = import.meta.env?.[name];
  if (viteValue !== undefined) return viteValue;
  return typeof process !== "undefined" ? process.env[name] : undefined;
}

/**
 * Runtime strangler switch. Ownership remains canonical in the registry and
 * evidence graph, while the renderer can fall back without deleting routes,
 * documents or versions.
 */
export function effectiveRouteOwnerForPath(
  pathname: string,
  featureFlags: Readonly<Record<string, string | undefined>> = {},
): RouteOwner | undefined {
  const route = routeForPath(pathname);
  if (!route) return undefined;
  if (!route.rollout) return route.owner;
  const value =
    featureFlags[route.rollout.featureFlag] ??
    runtimeFeatureFlag(route.rollout.featureFlag);
  return value?.trim().toLowerCase() === "false"
    ? route.rollout.rollbackOwner
    : route.owner;
}

export function routeNavigationTabForPath(pathname: string): NavigationTab | undefined {
  const route = routeForPath(pathname);
  if (route?.routeId === "ROUTE-CONTENT-EDIT") {
    const query = pathname.includes("?") ? pathname.slice(pathname.indexOf("?")) : "";
    const mode = new URLSearchParams(query).get("mode");
    if (mode === "visual") return "create-image";
    if (mode === "video" || mode === "presenter" || mode === "motion") {
      return "create-video";
    }
  }
  return route?.navigationTab;
}

export function validateRouteRegistry(): string[] {
  const issues: string[] = [];
  const ids = new Set<string>();
  const templates = new Set<string>();
  for (const route of ROUTE_REGISTRY) {
    if (ids.has(route.routeId)) issues.push(`duplicate routeId ${route.routeId}`);
    if (templates.has(route.template)) issues.push(`duplicate template ${route.template}`);
    ids.add(route.routeId);
    templates.add(route.template);
    if (!route.template.startsWith("/")) {
      issues.push(`non-absolute template ${route.template}`);
    }
    if (route.owner === "canonical" && !route.rollout) {
      issues.push(`canonical route ${route.routeId} has no rollout contract`);
    }
    if (route.rollout?.rollbackOwner === route.owner) {
      issues.push(`route ${route.routeId} rollback owner equals active owner`);
    }
  }
  for (const [tab, path] of Object.entries(NAVIGATION_TAB_PATHS) as Array<[
    NavigationTab,
    string,
  ]>) {
    const route = routeForPath(path);
    const resolvedTab = routeNavigationTabForPath(path);
    if (!route) issues.push(`navigation tab ${tab} points to orphan route ${path}`);
    else if (resolvedTab !== tab) {
      issues.push(
        `navigation tab ${tab} resolves to ${route.routeId} mapped as ${resolvedTab ?? "none"}`,
      );
    }
  }
  return issues;
}
