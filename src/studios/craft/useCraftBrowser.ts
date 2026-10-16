import React from "react";
import { CraftBrowserCapacityError, CraftBrowserSession, type BrowserInspection } from "./craftBrowser";
import type { CraftCommand, CraftDocument } from "./craftApi";
import type { AssetRecord } from "../../api/productApi";
import { craftError } from "./useCraftStudio";

export function useCraftBrowser(document: CraftDocument | undefined, pageId: string | undefined, enabled: boolean) {
  const [state, setState] = React.useState<"loading" | "ready" | "unavailable">("loading");
  const [error, setError] = React.useState<string>();
  const [inspection, setInspection] = React.useState<BrowserInspection>();
  const [change, setChange] = React.useState(0);
  const [applying, setApplying] = React.useState(false);
  const [appliedCount, setAppliedCount] = React.useState(0);
  const applyingRef = React.useRef(false);
  const sessionRef = React.useRef<CraftBrowserSession>();
  const generation = React.useRef(0);
  React.useEffect(() => {
    const current = ++generation.current;
    const controller = new AbortController();
    sessionRef.current?.close(); sessionRef.current = undefined;
    setInspection(undefined); setError(undefined); setState("loading"); setAppliedCount(0);
    if (!document?.nativeEditorState || !enabled) { setState("unavailable"); return; }
    void CraftBrowserSession.open(document.documentId, document.nativeEditorState, pageId, controller.signal, document.revision).then(async (session) => {
      if (controller.signal.aborted || generation.current !== current) { session.close(); return; }
      sessionRef.current = session;
      const next = await session.inspect();
      if (controller.signal.aborted || generation.current !== current) { session.close(); return; }
      setInspection(next); setState("ready"); setChange((value) => value + 1);
    }).catch((cause) => {
      if (!controller.signal.aborted && generation.current === current) { setState("unavailable"); setError(craftError(cause)); }
    });
    return () => { controller.abort(); ++generation.current; sessionRef.current?.close(); sessionRef.current = undefined; };
  }, [document?.documentId, document?.revision, document?.nativeEditorState?.checksumSha256, pageId, enabled]);
  return {
    state, error, inspection, change, applying, appliedCount,
    async apply(command: CraftCommand, asset?: AssetRecord) {
      const session = sessionRef.current;
      if (!session || state !== "ready") return false;
      if (applyingRef.current) throw new Error("Aguarde a prévia da alteração anterior.");
      applyingRef.current = true; setApplying(true);
      const current = generation.current;
      try {
        const next = await session.apply(command, asset);
        if (generation.current !== current) throw new Error("O projeto mudou durante a alteração. Abra novamente a página.");
        setInspection(next); setChange((value) => value + 1); setAppliedCount((value) => value + 1); return true;
      } catch (cause) {
        if (cause instanceof CraftBrowserCapacityError) {
          session.close(); sessionRef.current = undefined; setState("unavailable"); setInspection(undefined); setError(cause.message);
          return false;
        }
        throw cause;
      } finally { applyingRef.current = false; setApplying(false); }
    },
    async preview(frame: number, fps: number): Promise<Blob> {
      if (!sessionRef.current) throw new Error("A sessão de edição foi encerrada.");
      return sessionRef.current.preview(frame, fps);
    },
  };
}
