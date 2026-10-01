import React from "react";
import { productApi, type StudioDocumentRecord } from "../api/productApi";
import type { VideoTimeline } from "./videoTimeline";
import { NaturalSoundPreview, naturalSoundPreviewPlan } from "./naturalSoundPreview";

export function useNaturalSoundPreview(scope: string, timeline: VideoTimeline | undefined,
  assets: StudioDocumentRecord["assets"], player: React.RefObject<HTMLVideoElement | null>) {
  const engine = React.useRef<NaturalSoundPreview>();
  const attempt = React.useRef(0);
  const [state, setState] = React.useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = React.useState<string>();
  const key = JSON.stringify([scope, timeline, assets]);

  const cancel = React.useCallback(() => {
    attempt.current += 1;
    engine.current?.cancel();
    player.current?.pause();
    setState("idle"); setError(undefined);
  }, [player]);

  React.useEffect(() => {
    const current = new NaturalSoundPreview((id, signal) => productApi.studioAssetBlob(id, signal));
    engine.current = current;
    return () => { attempt.current += 1; current.dispose(); };
  }, [scope]);

  React.useEffect(() => { cancel(); }, [key, cancel]);
  React.useEffect(() => {
    const hide = () => { if (document.hidden) cancel(); };
    document.addEventListener("visibilitychange", hide);
    return () => document.removeEventListener("visibilitychange", hide);
  }, [cancel]);

  const prepare = async () => {
    const current = ++attempt.current;
    setState("loading"); setError(undefined);
    try {
      if (!engine.current) throw new Error("Player ainda não disponível.");
      await engine.current.prepare(naturalSoundPreviewPlan(timeline, assets));
      if (current !== attempt.current) return false;
      setState("ready");
      return true;
    } catch (failure) {
      if (current !== attempt.current) return false;
      engine.current?.cancel();
      player.current?.pause();
      setState("error");
      setError(failure instanceof Error ? failure.message : "Não foi possível carregar o som privado.");
      return false;
    }
  };
  const stop = () => engine.current?.stop();
  const sync = (seconds: number) => {
    try { engine.current?.sync(seconds); }
    catch (failure) {
      engine.current?.cancel(); player.current?.pause(); setState("error");
      setError(failure instanceof Error ? failure.message : "Falha na escuta do preview.");
    }
  };
  return { state, error, prepare, stop, sync, cancel };
}
