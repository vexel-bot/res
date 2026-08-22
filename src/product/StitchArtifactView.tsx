import { useEffect } from "react";
import { STITCH_ARTIFACTS } from "./stitchArtifacts.generated";
import { screenForLocation } from "./screenManifest";

interface StitchArtifactViewProps {
  pathname: string;
  search: string;
  onNavigate: (path: string) => void;
}

export function stitchArtifactForLocation(pathname: string, search: string) {
  const alias = legacyRouteAlias(pathname, search);
  const screen = screenForLocation(alias.pathname, alias.search);
  if (!screen) return undefined;
  return STITCH_ARTIFACTS.find((artifact) => artifact.id === screen.id);
}

function legacyRouteAlias(pathname: string, search: string) {
  const exactAliases: Record<string, string> = {
    "/projects": "/campaigns/active",
    "/campaigns": "/campaigns/active",
    "/studio": "/campaigns/active/studio",
    "/library": "/library/assets",
    "/approvals": "/approvals/post-1",
    "/publish": "/publish/active",
    "/analytics": "/analytics/learning",
    "/automations": "/automations/active",
    "/copilot": "/copilot?context=campaign",
    "/settings/profile": "/settings/ai-governance",
    "/create/image": "/content/draft/edit?mode=visual",
    "/create/video": "/content/draft/edit?mode=video",
  };
  let target = exactAliases[pathname];
  if (/^\/projects\/[^/]+\/creative$/.test(pathname))
    target = "/content/dashboard";
  else if (/^\/projects\/[^/]+$/.test(pathname)) target = "/campaigns/active";
  if (!target) return { pathname, search };
  const [aliasPathname, aliasQuery = ""] = target.split("?");
  return {
    pathname: aliasPathname,
    search: aliasQuery ? `?${aliasQuery}` : "",
  };
}

/**
 * Runs the exact HTML exported by Google Stitch in an isolated document.
 * This keeps each approved canvas pixel-faithful while the application logic
 * is progressively connected behind the source UI.
 */
export function StitchArtifactView({
  pathname,
  search,
  onNavigate,
}: StitchArtifactViewProps) {
  const artifact = stitchArtifactForLocation(pathname, search);
  useEffect(() => {
    const receiveNavigation = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (
        event.data?.type !== "clicko:stitch-navigate" ||
        typeof event.data.route !== "string"
      )
        return;
      onNavigate(event.data.route);
    };
    window.addEventListener("message", receiveNavigation);
    return () => window.removeEventListener("message", receiveNavigation);
  }, [onNavigate]);

  if (!artifact) return null;

  return (
    <main
      className="fixed inset-0 z-[200] bg-[#0f1011]"
      data-stitch-screen={artifact.id}
    >
      <iframe
        key={artifact.screenId}
        title={artifact.title}
        src={artifact.htmlPath}
        className="h-full w-full border-0 bg-[#0f1011]"
        allow="clipboard-read; clipboard-write"
      />
    </main>
  );
}
