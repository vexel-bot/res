/** The persisted MediaTimelineV1, using frames and source microseconds. */
export type Motion = {
  originalAudioEnabled?: boolean;
  x?: number;
  y?: number;
  scale?: number;
  opacity?: number;
  rotation?: number;
  gainDb?: number;
  fadeInFrames?: number;
  fadeOutFrames?: number;
  backgroundColor?: string | null;
};
export type Key = {
  property: "x" | "y" | "scale" | "opacity";
  frame: number;
  value: number;
};
export type Item = {
  id: string;
  assetId?: string;
  label?: string;
  text?: string;
  enabled?: boolean;
  locked?: boolean;
  playbackRate?: number;
  timeline: { startFrame: number; durationFrames: number };
  source?: { startMicroseconds: number; durationMicroseconds: number };
  transform?: Motion;
  motion?: Motion;
  keyframes?: Key[];
  effects?: unknown[];
  gainDb?: number;
  fadeInFrames?: number;
  fadeOutFrames?: number;
  style?: {
    fontFamily?: "system" | "Liberation Sans";
    color: string;
    fontSize: number;
    outlineWidth: number;
    maxLines: number;
  };
};
export type Track = {
  id: string;
  kind: "video" | "audio" | "overlay" | "caption" | "marker";
  name: string;
  muted?: boolean;
  locked?: boolean;
  clips?: Item[];
  cues?: Item[];
};
export type Timeline = {
  schemaVersion: "studio.media-timeline.v1";
  frameRate: { numerator: number; denominator: number };
  durationFrames: number;
  tracks: Track[];
};
export const items = (track: Track) =>
  track.kind === "caption" ? track.cues || [] : track.clips || [];
export const fpsOf = (timeline: Timeline) =>
  timeline.frameRate.numerator / timeline.frameRate.denominator;
export function patchItem(
  timeline: Timeline,
  id: string,
  change: (item: Item) => Item,
): Timeline {
  return {
    ...timeline,
    tracks: timeline.tracks.map((track) =>
      track.kind === "marker"
        ? track
        : {
            ...track,
            [track.kind === "caption" ? "cues" : "clips"]: items(track).map(
              (item) =>
                item.id === id && !track.locked && !item.locked
                  ? change(item)
                  : item,
            ),
          },
    ),
  };
}
export function split(
  timeline: Timeline,
  id: string,
  frame: number,
  newId: string,
): Timeline {
  return {
    ...timeline,
    tracks: timeline.tracks.map((track) => {
      if (track.kind === "caption" || track.kind === "marker" || track.locked)
        return track;
      return {
        ...track,
        clips: items(track).flatMap((item) => {
          const offset = frame - item.timeline.startFrame;
          if (
            item.id !== id ||
            item.locked ||
            offset <= 0 ||
            offset >= item.timeline.durationFrames ||
            item.keyframes?.length
          )
            return [item];
          const sourceOffset = Math.round(
            (offset / fpsOf(timeline)) * (item.playbackRate || 1) * 1e6,
          );
          const sourceStart = item.source?.startMicroseconds || 0;
          return [
            {
              ...item,
              timeline: { ...item.timeline, durationFrames: offset },
              source: {
                startMicroseconds: sourceStart,
                durationMicroseconds: sourceOffset,
              },
            },
            {
              ...item,
              id: newId,
              timeline: {
                startFrame: frame,
                durationFrames: item.timeline.durationFrames - offset,
              },
              source: {
                startMicroseconds: sourceStart + sourceOffset,
                durationMicroseconds: Math.round(
                  ((item.timeline.durationFrames - offset) / fpsOf(timeline)) *
                    (item.playbackRate || 1) *
                    1e6,
                ),
              },
            },
          ];
        }),
      };
    }),
  };
}

export function moveToTrack(timeline: Timeline, id: string, targetId: string, frame: number): Timeline {
  const source = timeline.tracks.find(t => items(t).some(i => i.id === id));
  const target = timeline.tracks.find(t => t.id === targetId);
  const item = source && items(source).find(i => i.id === id);
  if (!source || !target || !item || source.kind !== target.kind || source.locked || target.locked || item.locked) return timeline;
  const moved = { ...item, timeline: { ...item.timeline, startFrame: Math.max(0, Math.min(Math.round(frame), timeline.durationFrames-item.timeline.durationFrames)) } };
  return { ...timeline, tracks: timeline.tracks.map(track => {
    if (track.id !== source.id && track.id !== target.id) return track;
    const next = items(track).filter(i => i.id !== id);
    if (track.id === targetId) next.push(moved);
    return { ...track, [track.kind === "caption" ? "cues" : "clips"]: next };
  }) };
}
export function animate(item: Item, preset: string, fps: number): Item {
  const end = item.timeline.durationFrames;
  const fade = Math.min(Math.round(fps * 0.4), Math.floor(end / 3));
  const motion = {
    ...(item.text !== undefined ? item.motion : item.transform),
    fadeInFrames: preset === "none" ? 0 : fade,
    fadeOutFrames: preset === "none" ? 0 : fade,
  };
  const keys: Key[] =
    preset === "slide"
      ? [
          { property: "y", frame: 0, value: 60 },
          { property: "y", frame: fade, value: 0 },
          { property: "y", frame: Math.max(fade + 1, end - fade), value: 0 },
          { property: "y", frame: end, value: -40 },
        ]
      : preset === "zoom"
        ? [
            { property: "scale", frame: 0, value: 0.9 },
            { property: "scale", frame: end, value: 1.05 },
          ]
        : [];
  return {
    ...item,
    [item.text !== undefined ? "motion" : "transform"]: motion,
    keyframes: keys,
  };
}
