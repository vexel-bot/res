import React from "react";
import type { NavigationTab } from "../../types";

export const TAB_PATHS: Record<NavigationTab, string> = {
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

const PATH_TABS = (
  Object.entries(TAB_PATHS) as Array<[NavigationTab, string]>
).sort((left, right) => right[1].length - left[1].length);

export function tabForPath(pathname: string): NavigationTab | undefined {
  const cleanPath = pathname.replace(/\/+$/, "") || "/";
  if (cleanPath === "/") return "dashboard";
  const explicit = PATH_TABS.find(
    ([, path]) => cleanPath === path || cleanPath.startsWith(`${path}/`),
  )?.[0];
  if (explicit) return explicit;

  if (cleanPath === "/discover" || cleanPath === "/radar") return "workspace";
  if (cleanPath === "/copilot") return "ai-chat";
  if (cleanPath.startsWith("/content"))
    return cleanPath === "/content/new" ? "create-copy" : "library";
  if (cleanPath === "/projects" || cleanPath.startsWith("/projects/"))
    return "strategy";
  if (cleanPath.startsWith("/campaigns")) return "strategy";
  if (cleanPath.startsWith("/library")) return "library";
  if (cleanPath.startsWith("/approvals")) return "approvals";
  if (cleanPath.startsWith("/publish")) return "publisher";
  if (cleanPath.startsWith("/analytics")) return "analytics";
  if (cleanPath.startsWith("/automations")) return "automations";
  if (cleanPath.startsWith("/settings/team")) return "team";
  if (cleanPath.startsWith("/settings/billing")) return "subscription";
  if (cleanPath.startsWith("/settings/audit")) return "audit-logs";
  if (cleanPath.startsWith("/settings/channels")) return "connected-accounts";
  if (cleanPath.startsWith("/settings")) return "settings";
  return undefined;
}

export function useTabRouter(defaultTab: NavigationTab) {
  const [currentTab, setCurrentTab] = React.useState<NavigationTab>(
    () => tabForPath(window.location.pathname) || defaultTab,
  );
  const [locationKey, setLocationKey] = React.useState(
    () => `${window.location.pathname}${window.location.search}`,
  );

  React.useEffect(() => {
    const onPopState = () => {
      setCurrentTab(tabForPath(window.location.pathname) || defaultTab);
      setLocationKey(`${window.location.pathname}${window.location.search}`);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [defaultTab]);

  React.useEffect(() => {
    if (window.location.pathname === "/") {
      window.history.replaceState({}, "", TAB_PATHS[defaultTab]);
      setLocationKey(TAB_PATHS[defaultTab]);
    }
  }, [defaultTab]);

  const navigate = React.useCallback(
    (tab: NavigationTab, options?: { replace?: boolean }) => {
      const path = TAB_PATHS[tab];
      if (options?.replace) window.history.replaceState({}, "", path);
      else if (window.location.pathname !== path)
        window.history.pushState({}, "", path);
      setCurrentTab(tab);
      setLocationKey(path);
      window.scrollTo({ top: 0, behavior: "auto" });
    },
    [],
  );

  const navigatePath = React.useCallback(
    (path: string, options?: { replace?: boolean }) => {
      const target = path.startsWith("/") ? path : `/${path}`;
      if (options?.replace) window.history.replaceState({}, "", target);
      else if (
        `${window.location.pathname}${window.location.search}` !== target
      )
        window.history.pushState({}, "", target);
      setCurrentTab(tabForPath(window.location.pathname) || defaultTab);
      setLocationKey(`${window.location.pathname}${window.location.search}`);
      window.scrollTo({ top: 0, behavior: "auto" });
    },
    [defaultTab],
  );

  return {
    currentTab,
    pathname: window.location.pathname,
    search: window.location.search,
    locationKey,
    navigate,
    navigatePath,
  };
}
