import type { BackendSchema } from "../api/client";

export type VideoTimeline = BackendSchema<"MediaTimelineV1-Output">;

type TimelineTrack = NonNullable<VideoTimeline["tracks"]>[number];
type VideoTrack = Extract<TimelineTrack, { kind: "video" }>;
type TimedClip = BackendSchema<"MediaClipV1">;
type CaptionCue = BackendSchema<"CaptionCueV1">;
type Marker = BackendSchema<"MarkerV1">;

export type VideoTimelineCommand =
  | {
      type: "trim";
      trackId: string;
      clipId: string;
      edge: "start" | "end";
      /**
       * Boundary in the pre-command output timebase. The first slice only
       * removes source handles; extending beyond the current clip is rejected.
       */
      targetFrame: number;
    }
  | {
      type: "reorder-ripple";
      trackId: string;
      clipId: string;
      /** Final chronological index after the selected clip is removed. */
      targetIndex: number;
    }
  | {
      type: "split";
      trackId: string;
      clipId: string;
      /** Split boundary in output frames; both resulting clips remain contiguous. */
      targetFrame: number;
    }
  | {
      type: "set-transform";
      trackId: string;
      clipId: string;
      transform: VideoClipTransform;
    }
  | {
      type: "set-audio";
      trackId: string;
      clipId: string;
      gainDb: number;
      pan: number;
      fadeInFrames: number;
      fadeOutFrames: number;
    }
  | {
      type: "set-speed";
      trackId: string;
      clipId: string;
      /** Bounded source playback rate; the edit ripples all later content. */
      playbackRate: number;
    };

export interface VideoClipTransform {
  fit: "cover" | "contain" | "fill";
  anchor:
    | "center"
    | "top"
    | "bottom"
    | "left"
    | "right"
    | "top-left"
    | "top-right"
    | "bottom-left"
    | "bottom-right";
  x: number;
  y: number;
  scale: number;
  rotation: number;
  crop: { top: number; right: number; bottom: number; left: number };
}

export class VideoTimelineCommandError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "VideoTimelineCommandError";
    this.code = code;
  }
}

interface RetainedRange {
  oldStart: number;
  oldEnd: number;
  newStart: number;
}

interface ClipWithRetainedRange {
  clip: TimedClip;
  retainedStart: number;
  retainedEnd: number;
}

function fail(code: string): never {
  throw new VideoTimelineCommandError(code);
}

function assertInteger(value: number, code: string) {
  if (!Number.isSafeInteger(value)) fail(code);
}

function timelineTracks(timeline: VideoTimeline) {
  return timeline.tracks ?? [];
}

function trackClips(track: TimelineTrack): TimedClip[] {
  if (track.kind === "video" || track.kind === "audio" || track.kind === "overlay") {
    return (track.clips ?? []) as TimedClip[];
  }
  return [];
}

function frameRate(timeline: VideoTimeline) {
  const rate = timeline.frameRate ?? { numerator: 30, denominator: 1 };
  assertFrameRate(rate);
  return rate;
}

function assertFrameRate(rate: { numerator: number; denominator: number }) {
  if (
    !Number.isSafeInteger(rate.numerator) ||
    !Number.isSafeInteger(rate.denominator) ||
    rate.numerator <= 0 ||
    rate.denominator <= 0
  ) {
    fail("video_timeline_invalid_frame_rate");
  }
}

export function timelineFrameToMicroseconds(
  frame: number,
  rate: { numerator: number; denominator: number },
) {
  assertInteger(frame, "video_timeline_frame_must_be_integer");
  assertFrameRate(rate);
  const microseconds = Math.round(
    (frame * 1_000_000 * rate.denominator) / rate.numerator,
  );
  if (!Number.isSafeInteger(microseconds)) {
    fail("video_timeline_source_time_overflow");
  }
  return microseconds;
}

/** Backwards-compatible plural spelling for callers dealing with durations. */
export const timelineFramesToMicroseconds = timelineFrameToMicroseconds;

export function timelineMicrosecondsToFrame(
  microseconds: number,
  rate: { numerator: number; denominator: number },
  rounding: "floor" | "ceil" | "nearest" = "nearest",
) {
  if (!Number.isSafeInteger(microseconds)) {
    fail("video_timeline_source_time_must_be_integer");
  }
  assertFrameRate(rate);
  const raw =
    (microseconds * rate.numerator) /
    (1_000_000 * rate.denominator);
  const frame =
    rounding === "floor"
      ? Math.floor(raw)
      : rounding === "ceil"
        ? Math.ceil(raw)
        : Math.round(raw);
  if (!Number.isSafeInteger(frame)) fail("video_timeline_frame_overflow");
  return frame;
}

/**
 * Maps an output frame to the source media time for the active video clip.
 * This is the player bridge needed after split, trim or reorder: output time
 * is never assumed to equal source time.
 */
export function timelineFrameToSourceMicroseconds(
  timeline: VideoTimeline,
  trackId: string,
  frame: number,
) {
  assertInteger(frame, "video_timeline_frame_must_be_integer");
  if (frame < 0 || frame > timeline.durationFrames) {
    fail("video_timeline_frame_out_of_bounds");
  }
  const track = timelineTracks(timeline).find((candidate) => candidate.id === trackId);
  if (!track) fail("video_timeline_track_not_found");
  if (track.kind !== "video") fail("video_timeline_source_track_required");
  const rate = frameRate(timeline);
  const clips = [...(track.clips ?? [])]
    .filter((clip) => clip.enabled)
    .sort(
      (left, right) =>
        left.timeline.startFrame - right.timeline.startFrame ||
        left.id.localeCompare(right.id),
    );
  const clip =
    frame === timeline.durationFrames
      ? clips.find(
          (candidate) =>
            candidate.timeline.startFrame + candidate.timeline.durationFrames === frame,
        )
      : clips.find(
          (candidate) =>
            candidate.timeline.startFrame <= frame &&
            frame < candidate.timeline.startFrame + candidate.timeline.durationFrames,
        );
  if (!clip) fail("video_timeline_frame_has_no_source");
  if (!clip.source) fail("video_timeline_source_range_required");
  const playbackRate = clip.playbackRate ?? 1;
  return (
    clip.source.startMicroseconds +
    timelineFrameToMicroseconds(
      Math.round((frame - clip.timeline.startFrame) * playbackRate),
      rate,
    )
  );
}

function sourceMicrosecondsForTimelineFrames(
  frames: number,
  rate: { numerator: number; denominator: number },
  playbackRate = 1,
) {
  return timelineFramesToMicroseconds(Math.round(frames * playbackRate), rate);
}

function chronologicalSourceClips(track: VideoTrack, timeline: VideoTimeline) {
  const clips = [...(track.clips ?? [])] as TimedClip[];
  if (!clips.length) fail("video_timeline_source_clip_required");

  const ids = new Set<string>();
  for (const clip of clips) {
    if (ids.has(clip.id)) fail("video_timeline_duplicate_clip_id");
    ids.add(clip.id);
    if (!clip.enabled) fail("video_timeline_disabled_source_clip_not_supported");
    if (clip.locked) fail("video_timeline_clip_locked");
    if (!clip.source) fail("video_timeline_source_range_required");
    assertInteger(clip.timeline.startFrame, "video_timeline_frame_must_be_integer");
    assertInteger(clip.timeline.durationFrames, "video_timeline_frame_must_be_integer");
  }

  clips.sort(
    (left, right) =>
      left.timeline.startFrame - right.timeline.startFrame ||
      left.id.localeCompare(right.id),
  );
  let cursor = 0;
  for (const clip of clips) {
    if (clip.timeline.startFrame !== cursor || clip.timeline.durationFrames < 1) {
      fail("video_timeline_source_track_must_be_contiguous");
    }
    cursor += clip.timeline.durationFrames;
  }
  if (cursor !== timeline.durationFrames) {
    fail("video_timeline_source_track_must_cover_duration");
  }
  return clips;
}

function assertDependentTracksMutable(timeline: VideoTimeline, sourceTrackId: string) {
  for (const track of timelineTracks(timeline)) {
    if (track.id === sourceTrackId) continue;
    const clips = trackClips(track);
    const cues = track.kind === "caption" ? track.cues ?? [] : [];
    const changesTimedContent = clips.length > 0 || cues.length > 0;
    if (changesTimedContent && "locked" in track && track.locked) {
      fail("video_timeline_dependent_track_locked");
    }
    if (clips.some((clip) => clip.locked)) {
      fail("video_timeline_dependent_clip_locked");
    }
  }
}

function findSourceTrack(timeline: VideoTimeline, trackId: string) {
  const track = timelineTracks(timeline).find((candidate) => candidate.id === trackId);
  if (!track) fail("video_timeline_track_not_found");
  if (track.kind !== "video") fail("video_timeline_source_track_required");
  if ("locked" in track && track.locked) fail("video_timeline_track_locked");
  return track;
}

function trimClip(
  clip: TimedClip,
  edge: "start" | "end",
  targetFrame: number,
  rate: { numerator: number; denominator: number },
): ClipWithRetainedRange {
  const oldStart = clip.timeline.startFrame;
  const oldEnd = oldStart + clip.timeline.durationFrames;
  const source = clip.source;
  if (!source) fail("video_timeline_source_range_required");
  const playbackRate = clip.playbackRate ?? 1;

  if (edge === "start") {
    if (targetFrame < oldStart || targetFrame >= oldEnd) {
      fail("video_timeline_trim_out_of_bounds");
    }
    const removedFrames = targetFrame - oldStart;
    const durationFrames = oldEnd - targetFrame;
    return {
      clip: {
        ...clip,
        timeline: { startFrame: oldStart, durationFrames },
        source: {
          ...source,
          startMicroseconds:
            source.startMicroseconds +
            sourceMicrosecondsForTimelineFrames(removedFrames, rate, playbackRate),
          durationMicroseconds: sourceMicrosecondsForTimelineFrames(
            durationFrames,
            rate,
            playbackRate,
          ),
        },
      },
      retainedStart: targetFrame,
      retainedEnd: oldEnd,
    };
  }

  if (targetFrame <= oldStart || targetFrame > oldEnd) {
    fail("video_timeline_trim_out_of_bounds");
  }
  const durationFrames = targetFrame - oldStart;
  return {
    clip: {
      ...clip,
      timeline: { startFrame: oldStart, durationFrames },
      source: {
        ...source,
        durationMicroseconds: sourceMicrosecondsForTimelineFrames(
          durationFrames,
          rate,
          playbackRate,
        ),
      },
    },
    retainedStart: oldStart,
    retainedEnd: targetFrame,
  };
}

function plannedClips(
  clips: TimedClip[],
  command: VideoTimelineCommand,
  rate: { numerator: number; denominator: number },
) {
  const selectedIndex = clips.findIndex((clip) => clip.id === command.clipId);
  if (selectedIndex < 0) fail("video_timeline_clip_not_found");

  let ordered = clips.map<ClipWithRetainedRange>((clip) => ({
    clip,
    retainedStart: clip.timeline.startFrame,
    retainedEnd: clip.timeline.startFrame + clip.timeline.durationFrames,
  }));
  let changed = true;

  if (command.type === "trim") {
    assertInteger(command.targetFrame, "video_timeline_frame_must_be_integer");
    const selected = clips[selectedIndex];
    const selectedEnd =
      selected.timeline.startFrame + selected.timeline.durationFrames;
    changed =
      command.edge === "start"
        ? command.targetFrame !== selected.timeline.startFrame
        : command.targetFrame !== selectedEnd;
    ordered[selectedIndex] = trimClip(
      selected,
      command.edge,
      command.targetFrame,
      rate,
    );
  } else if (command.type === "reorder-ripple") {
    assertInteger(command.targetIndex, "video_timeline_target_index_must_be_integer");
    if (command.targetIndex < 0 || command.targetIndex >= clips.length) {
      fail("video_timeline_target_index_out_of_bounds");
    }
    changed = command.targetIndex !== selectedIndex;
    const [selected] = ordered.splice(selectedIndex, 1);
    ordered.splice(command.targetIndex, 0, selected);
  } else {
    fail("video_timeline_command_does_not_change_duration");
  }

  let cursor = 0;
  const retained: RetainedRange[] = [];
  const nextClips = ordered.map(({ clip, retainedStart, retainedEnd }) => {
    const durationFrames = retainedEnd - retainedStart;
    retained.push({ oldStart: retainedStart, oldEnd: retainedEnd, newStart: cursor });
    const nextClip = {
      ...clip,
      timeline: { startFrame: cursor, durationFrames },
    };
    cursor += durationFrames;
    return nextClip;
  });
  return { nextClips, retained, durationFrames: cursor, changed };
}

function remapTimedItems<T extends TimedClip | CaptionCue>(
  items: T[],
  retained: RetainedRange[],
  rate: { numerator: number; denominator: number },
) {
  const result: T[] = [];
  for (const item of items) {
    const itemStart = item.timeline.startFrame;
    const itemEnd = itemStart + item.timeline.durationFrames;
    const pieces: T[] = [];
    for (const range of retained) {
      const start = Math.max(itemStart, range.oldStart);
      const end = Math.min(itemEnd, range.oldEnd);
      if (end <= start) continue;
      const next = structuredClone(item) as T;
      next.timeline = {
        startFrame: range.newStart + start - range.oldStart,
        durationFrames: end - start,
      };
      if ("source" in next && next.source) {
        const playbackRate = "playbackRate" in next ? next.playbackRate ?? 1 : 1;
        next.source = {
          ...next.source,
          startMicroseconds:
            next.source.startMicroseconds +
            sourceMicrosecondsForTimelineFrames(
              start - itemStart,
              rate,
              playbackRate,
            ),
          durationMicroseconds: sourceMicrosecondsForTimelineFrames(
            end - start,
            rate,
            playbackRate,
          ),
        };
      }
      pieces.push(next);
    }
    if (pieces.length > 1) {
      pieces.forEach((piece, index) => {
        piece.id = `${item.id}:ripple:${index + 1}`;
      });
    }
    result.push(...pieces);
  }
  result.sort(
    (left, right) =>
      left.timeline.startFrame - right.timeline.startFrame ||
      left.id.localeCompare(right.id),
  );
  const ids = result.map((item) => item.id);
  if (new Set(ids).size !== ids.length) {
    fail("video_timeline_generated_id_collision");
  }
  return result;
}

function remapMarkers(
  markers: Marker[],
  retained: RetainedRange[],
  oldDurationFrames: number,
  newDurationFrames: number,
) {
  return markers
    .flatMap((marker) => {
      if (marker.frame === oldDurationFrames) {
        return [{ ...marker, frame: newDurationFrames }];
      }
      const range = retained.find(
        (candidate) =>
          candidate.oldStart <= marker.frame && marker.frame < candidate.oldEnd,
      );
      return range
        ? [
            {
              ...marker,
              frame: range.newStart + marker.frame - range.oldStart,
            },
          ]
        : [];
    })
    .sort((left, right) => left.frame - right.frame || left.id.localeCompare(right.id));
}

/**
 * Reversibly mutes the paired source audio without changing source ranges,
 * caption cues, or original bytes. The returned timeline is an independent tree.
 */
export function setOriginalAudioMuted(input: VideoTimeline, muted: boolean): VideoTimeline {
  const timeline = structuredClone(input);
  const videoTracks = timelineTracks(timeline).filter((track) => track.kind === "video");
  const sourceIds = new Set(videoTracks.flatMap((track) => (track.clips ?? []).map((clip) => clip.assetId)));
  const audioTracks = timelineTracks(timeline).filter((track) => track.kind === "audio")
    .filter((track) => track.id === "audio-main" || (track.clips?.length && track.clips.every((clip) => sourceIds.has(clip.assetId))));
  if (audioTracks.length !== 1 || videoTracks.length !== 1) {
    fail("video_timeline_single_paired_audio_required");
  }
  const audio = audioTracks[0];
  const video = videoTracks[0];
  if (audio.locked || video.locked) fail("video_timeline_track_locked");
  if (!(audio.clips ?? []).length || (audio.clips ?? []).some((clip) => !sourceIds.has(clip.assetId))) {
    fail("video_timeline_original_audio_required");
  }
  audio.muted = muted;
  // Embedded audio is always suppressed; audio-main owns the sound once.
  video.muted = true;
  return timeline;
}

function assertFiniteNumber(value: number, code: string) {
  if (!Number.isFinite(value)) fail(code);
}

function splitClip<T extends TimedClip>(
  clip: T,
  targetFrame: number,
  rate: { numerator: number; denominator: number },
  occupiedIds: Set<string>,
) {
  assertInteger(targetFrame, "video_timeline_frame_must_be_integer");
  const start = clip.timeline.startFrame;
  const end = start + clip.timeline.durationFrames;
  if (targetFrame <= start || targetFrame >= end) {
    fail("video_timeline_split_out_of_bounds");
  }
  if (!clip.source) fail("video_timeline_source_range_required");
  const leftDuration = targetFrame - start;
  const rightDuration = end - targetFrame;
  const leftId = `${clip.id}:split:1`;
  const rightId = `${clip.id}:split:2`;
  if (occupiedIds.has(leftId) || occupiedIds.has(rightId)) {
    fail("video_timeline_generated_id_collision");
  }
  const leftSourceDuration = sourceMicrosecondsForTimelineFrames(
    leftDuration,
    rate,
    clip.playbackRate ?? 1,
  );
  const left = structuredClone(clip) as T;
  const right = structuredClone(clip) as T;
  left.id = leftId;
  left.timeline = { startFrame: start, durationFrames: leftDuration };
  left.source = {
    ...clip.source,
    durationMicroseconds: leftSourceDuration,
  };
  right.id = rightId;
  right.timeline = { startFrame: targetFrame, durationFrames: rightDuration };
  right.source = {
    ...clip.source,
    startMicroseconds: clip.source.startMicroseconds + leftSourceDuration,
    durationMicroseconds: sourceMicrosecondsForTimelineFrames(
      rightDuration,
      rate,
      clip.playbackRate ?? 1,
    ),
  };
  if ("fadeInFrames" in left && "fadeOutFrames" in left) {
    const audioLeft = left as unknown as BackendSchema<"AudioClipV1">;
    const audioRight = right as unknown as BackendSchema<"AudioClipV1">;
    audioLeft.fadeInFrames = Math.min(audioLeft.fadeInFrames ?? 0, leftDuration);
    audioLeft.fadeOutFrames = 0;
    audioRight.fadeInFrames = 0;
    audioRight.fadeOutFrames = Math.min(audioRight.fadeOutFrames ?? 0, rightDuration);
  }
  return [left, right] as const;
}

function applySplitCommand(
  timeline: VideoTimeline,
  command: Extract<VideoTimelineCommand, { type: "split" }>,
) {
  const sourceTrack = findSourceTrack(timeline, command.trackId);
  const clips = chronologicalSourceClips(sourceTrack, timeline);
  const selected = clips.find((clip) => clip.id === command.clipId);
  if (!selected) fail("video_timeline_clip_not_found");
  assertDependentTracksMutable(timeline, sourceTrack.id);
  const rate = frameRate(timeline);
  const occupiedIds = new Set(
    timelineTracks(timeline).flatMap((track) => trackClips(track).map((clip) => clip.id)),
  );
  const [left, right] = splitClip(selected, command.targetFrame, rate, occupiedIds);
  sourceTrack.clips = sourceTrack.clips?.flatMap((clip) =>
    clip.id === selected.id ? [left, right] : [clip],
  );

  timeline.tracks = timelineTracks(timeline).map((track) => {
    if (track.id === sourceTrack.id || track.kind !== "audio") return track;
    return {
      ...track,
      clips: (track.clips ?? []).flatMap((clip) => {
        const exactPair =
          clip.assetId === selected.assetId &&
          clip.timeline.startFrame === selected.timeline.startFrame &&
          clip.timeline.durationFrames === selected.timeline.durationFrames &&
          clip.source?.startMicroseconds === selected.source?.startMicroseconds;
        return exactPair ? splitClip(clip, command.targetFrame, rate, occupiedIds) : [clip];
      }),
    };
  });
  return timeline;
}

function validateTransform(transform: VideoClipTransform) {
  for (const value of [
    transform.x,
    transform.y,
    transform.scale,
    transform.rotation,
    transform.crop.top,
    transform.crop.right,
    transform.crop.bottom,
    transform.crop.left,
  ]) {
    assertFiniteNumber(value, "video_timeline_transform_must_be_finite");
  }
  if (transform.scale < 0.05 || transform.scale > 20) {
    fail("video_timeline_transform_scale_out_of_bounds");
  }
  if (transform.rotation < -360 || transform.rotation > 360) {
    fail("video_timeline_transform_rotation_out_of_bounds");
  }
  const crop = transform.crop;
  if (
    Object.values(crop).some((value) => value < 0 || value >= 1) ||
    crop.left + crop.right >= 1 ||
    crop.top + crop.bottom >= 1
  ) {
    fail("video_timeline_transform_crop_out_of_bounds");
  }
}

function applySpeedCommand(
  timeline: VideoTimeline,
  command: Extract<VideoTimelineCommand, { type: "set-speed" }>,
) {
  assertFiniteNumber(command.playbackRate, "video_timeline_speed_must_be_finite");
  if (command.playbackRate < 0.5 || command.playbackRate > 2) {
    fail("video_timeline_speed_out_of_bounds");
  }
  const sourceTrack = findSourceTrack(timeline, command.trackId);
  const clips = chronologicalSourceClips(sourceTrack, timeline);
  const selected = clips.find((clip) => clip.id === command.clipId);
  if (!selected) fail("video_timeline_clip_not_found");
  if (!selected.source) fail("video_timeline_source_range_required");
  if (Math.abs((selected.playbackRate ?? 1) - command.playbackRate) < 1e-9) {
    return timeline;
  }
  assertDependentTracksMutable(timeline, sourceTrack.id);
  const rate = frameRate(timeline);
  const sourceDurationFrames = timelineMicrosecondsToFrame(
    selected.source.durationMicroseconds,
    rate,
  );
  const newDurationFrames = Math.max(
    1,
    Math.round(sourceDurationFrames / command.playbackRate),
  );
  if (
    Math.abs(newDurationFrames * command.playbackRate - sourceDurationFrames) > 0.5
  ) {
    fail("video_timeline_speed_frame_alignment_required");
  }
  const oldStart = selected.timeline.startFrame;
  const oldDurationFrames = selected.timeline.durationFrames;
  const oldEnd = oldStart + oldDurationFrames;
  const durationDelta = newDurationFrames - oldDurationFrames;
  const nextDurationFrames = timeline.durationFrames + durationDelta;
  const mapFrame = (frame: number) => {
    if (frame <= oldStart) return frame;
    if (frame >= oldEnd) return frame + durationDelta;
    return oldStart + Math.round(
      ((frame - oldStart) * newDurationFrames) / oldDurationFrames,
    );
  };

  sourceTrack.clips = (sourceTrack.clips ?? []).map((clip) => {
    if (clip.id === selected.id) {
      return {
        ...clip,
        playbackRate: command.playbackRate,
        timeline: { ...clip.timeline, durationFrames: newDurationFrames },
      };
    }
    return clip.timeline.startFrame >= oldEnd
      ? {
          ...clip,
          timeline: {
            ...clip.timeline,
            startFrame: clip.timeline.startFrame + durationDelta,
          },
        }
      : clip;
  });

  timeline.tracks = timelineTracks(timeline).map((track) => {
    if (track.id === sourceTrack.id) return track;
    if (track.kind === "audio") {
      return {
        ...track,
        clips: (track.clips ?? []).map((clip) => {
          const start = clip.timeline.startFrame;
          const end = start + clip.timeline.durationFrames;
          const exactPair =
            clip.assetId === selected.assetId &&
            start === oldStart &&
            clip.timeline.durationFrames === oldDurationFrames &&
            clip.source?.startMicroseconds === selected.source?.startMicroseconds &&
            clip.source?.durationMicroseconds === selected.source?.durationMicroseconds;
          if (exactPair) {
            const fadeInFrames = Math.min(clip.fadeInFrames ?? 0, newDurationFrames);
            return {
              ...clip,
              playbackRate: command.playbackRate,
              timeline: { ...clip.timeline, durationFrames: newDurationFrames },
              fadeInFrames,
              fadeOutFrames: Math.min(
                clip.fadeOutFrames ?? 0,
                newDurationFrames - fadeInFrames,
              ),
            };
          }
          if (start < oldEnd && end > oldStart) {
            fail("video_timeline_speed_overlapping_audio_unsupported");
          }
          return start >= oldEnd
            ? {
                ...clip,
                timeline: { ...clip.timeline, startFrame: start + durationDelta },
              }
            : clip;
        }),
      };
    }
    if (track.kind === "caption") {
      return {
        ...track,
        cues: (track.cues ?? []).map((cue) => {
          const startFrame = mapFrame(cue.timeline.startFrame);
          const mappedEnd = mapFrame(
            cue.timeline.startFrame + cue.timeline.durationFrames,
          );
          return {
            ...cue,
            timeline: {
              startFrame,
              durationFrames: Math.max(1, mappedEnd - startFrame),
            },
          };
        }),
      };
    }
    if (track.kind === "overlay") {
      return {
        ...track,
        clips: (track.clips ?? []).map((clip) => {
          const startFrame = mapFrame(clip.timeline.startFrame);
          const mappedEnd = mapFrame(
            clip.timeline.startFrame + clip.timeline.durationFrames,
          );
          return {
            ...clip,
            timeline: {
              startFrame,
              durationFrames: Math.max(1, mappedEnd - startFrame),
            },
          };
        }),
      };
    }
    if (track.kind === "marker") {
      return {
        ...track,
        markers: (track.markers ?? []).map((marker) => ({
          ...marker,
          frame: marker.frame === timeline.durationFrames
            ? nextDurationFrames
            : mapFrame(marker.frame),
        })),
      };
    }
    return track;
  });
  timeline.durationFrames = nextDurationFrames;
  return timeline;
}

function applyPropertyCommand(
  timeline: VideoTimeline,
  command: Extract<VideoTimelineCommand, { type: "set-transform" | "set-audio" }>,
) {
  const track = timelineTracks(timeline).find((candidate) => candidate.id === command.trackId);
  if (!track) fail("video_timeline_track_not_found");
  if ("locked" in track && track.locked) fail("video_timeline_track_locked");
  if (command.type === "set-transform" && track.kind !== "video" && track.kind !== "overlay") {
    fail("video_timeline_visual_track_required");
  }
  if (command.type === "set-audio" && track.kind !== "audio") {
    fail("video_timeline_audio_track_required");
  }
  if (track.kind !== "video" && track.kind !== "overlay" && track.kind !== "audio") {
    fail("video_timeline_clip_track_required");
  }
  const clip = (track.clips ?? []).find((candidate) => candidate.id === command.clipId);
  if (!clip) fail("video_timeline_clip_not_found");
  if (clip.locked) fail("video_timeline_clip_locked");
  if (command.type === "set-transform") {
    validateTransform(command.transform);
    clip.transform = structuredClone(command.transform) as unknown as Record<string, unknown>;
  } else {
    for (const value of [command.gainDb, command.pan]) {
      assertFiniteNumber(value, "video_timeline_audio_property_must_be_finite");
    }
    for (const value of [command.fadeInFrames, command.fadeOutFrames]) {
      assertInteger(value, "video_timeline_frame_must_be_integer");
    }
    if (command.gainDb < -96 || command.gainDb > 24) {
      fail("video_timeline_audio_gain_out_of_bounds");
    }
    if (command.pan < -1 || command.pan > 1) {
      fail("video_timeline_audio_pan_out_of_bounds");
    }
    if (
      command.fadeInFrames < 0 ||
      command.fadeOutFrames < 0 ||
      command.fadeInFrames + command.fadeOutFrames > clip.timeline.durationFrames
    ) {
      fail("video_timeline_audio_fade_out_of_bounds");
    }
    const audio = clip as BackendSchema<"AudioClipV1">;
    audio.gainDb = command.gainDb;
    audio.pan = command.pan;
    audio.fadeInFrames = command.fadeInFrames;
    audio.fadeOutFrames = command.fadeOutFrames;
  }
  return timeline;
}

export function snapTimelineFrame(
  targetFrame: number,
  candidateFrames: number[],
  toleranceFrames: number,
) {
  assertInteger(targetFrame, "video_timeline_frame_must_be_integer");
  assertInteger(toleranceFrames, "video_timeline_snap_tolerance_must_be_integer");
  if (toleranceFrames < 0) fail("video_timeline_snap_tolerance_out_of_bounds");
  let best = targetFrame;
  let bestDistance = toleranceFrames + 1;
  for (const candidate of candidateFrames) {
    assertInteger(candidate, "video_timeline_frame_must_be_integer");
    const distance = Math.abs(candidate - targetFrame);
    if (distance < bestDistance || (distance === bestDistance && candidate < best)) {
      best = candidate;
      bestDistance = distance;
    }
  }
  return bestDistance <= toleranceFrames ? best : targetFrame;
}

/** Applies non-destructive clip edits to the canonical Clicko media timeline. */
export function applyVideoTimelineCommand(
  input: VideoTimeline,
  command: VideoTimelineCommand,
): VideoTimeline {
  const timeline = structuredClone(input);
  assertInteger(timeline.durationFrames, "video_timeline_frame_must_be_integer");
  if (command.type === "split") return applySplitCommand(timeline, command);
  if (command.type === "set-speed") return applySpeedCommand(timeline, command);
  if (command.type === "set-transform" || command.type === "set-audio") {
    return applyPropertyCommand(timeline, command);
  }
  const rate = frameRate(timeline);
  const sourceTrack = findSourceTrack(timeline, command.trackId);
  const clips = chronologicalSourceClips(sourceTrack, timeline);
  const { nextClips, retained, durationFrames, changed } = plannedClips(
    clips,
    command,
    rate,
  );
  if (!changed) return timeline;
  assertDependentTracksMutable(timeline, sourceTrack.id);
  const oldDurationFrames = timeline.durationFrames;

  timeline.durationFrames = durationFrames;
  timeline.tracks = timelineTracks(timeline).map((track) => {
    if (track.id === sourceTrack.id && track.kind === "video") {
      return { ...track, clips: nextClips };
    }
    if (track.kind === "video" || track.kind === "audio" || track.kind === "overlay") {
      return {
        ...track,
        clips: remapTimedItems(
          (track.clips ?? []) as TimedClip[],
          retained,
          rate,
        ).map((clip) => {
          if (track.kind !== "audio") return clip;
          const sound = clip as BackendSchema<"AudioClipV1">;
          const fadeInFrames = Math.min(sound.fadeInFrames ?? 0, clip.timeline.durationFrames);
          return { ...sound, fadeInFrames, fadeOutFrames: Math.min(sound.fadeOutFrames ?? 0, clip.timeline.durationFrames - fadeInFrames) };
        }),
      } as typeof track;
    }
    if (track.kind === "caption") {
      return {
        ...track,
        cues: remapTimedItems(track.cues ?? [], retained, rate),
      };
    }
    if (track.kind === "marker") {
      return {
        ...track,
        markers: remapMarkers(
          track.markers ?? [],
          retained,
          oldDurationFrames,
          durationFrames,
        ),
      };
    }
    return track;
  });
  return timeline;
}
