import React from "react";
import type { NavigationTab } from "../../types";
import {
  NAVIGATION_TAB_PATHS,
  routeNavigationTabForPath,
} from "./routeRegistry";

export const TAB_PATHS = NAVIGATION_TAB_PATHS;

export function tabForPath(pathname: string): NavigationTab | undefined {
  return routeNavigationTabForPath(pathname);
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
