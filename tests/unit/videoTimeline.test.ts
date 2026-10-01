import assert from "node:assert/strict";
import test from "node:test";

import {
  applyVideoTimelineCommand,
  setOriginalAudioMuted,
  snapTimelineFrame,
  timelineFrameToMicroseconds,
  timelineFrameToSourceMicroseconds,
  timelineFramesToMicroseconds,
  timelineMicrosecondsToFrame,
  VideoTimelineCommandError,
  type VideoTimeline,
} from "../../src/studios/videoTimeline.ts";

function sourceClip(
  id: string,
  startFrame: number,
  durationFrames: number,
  sourceStartMicroseconds: number,
  assetId = "asset-source",
) {
  return {
    id,
    assetId,
    timeline: { startFrame, durationFrames },
    source: {
      startMicroseconds: sourceStartMicroseconds,
      durationMicroseconds: timelineFramesToMicroseconds(durationFrames, {
        numerator: 30,
        denominator: 1,
      }),
    },
    enabled: true,
    locked: false,
    label: id,
    playbackRate: 1,
    transform: {},
    effects: [],
    keyframes: [],
  };
}

function fixture(): VideoTimeline {
  const video = [
    sourceClip("video-a", 0, 4, 0),
    sourceClip("video-b", 4, 4, 200_000),
    sourceClip("video-c", 8, 4, 400_000),
  ];
  const audio = video.map((clip) => ({
    ...structuredClone(clip),
    id: clip.id.replace("video", "audio"),
    gainDb: 0,
    pan: 0,
    fadeInFrames: 0,
    fadeOutFrames: 0,
  }));
  return {
    schemaVersion: "studio.media-timeline.v1",
    frameRate: { numerator: 30, denominator: 1 },
    durationFrames: 12,
    tracks: [
      {
        id: "video-main",
        kind: "video",
        name: "Vídeo principal",
        muted: false,
        locked: false,
        clips: video,
      },
      {
        id: "audio-main",
        kind: "audio",
        name: "Áudio correspondente",
        muted: false,
        locked: false,
        clips: audio,
      },
      {
        id: "captions-main",
        kind: "caption",
        name: "Legendas",
        locale: "pt-BR",
        locked: false,
        cues: [
          {
            id: "caption-crossing",
            timeline: { startFrame: 2, durationFrames: 4 },
            text: "Atravessa A e B",
          },
          {
            id: "caption-c",
            timeline: { startFrame: 9, durationFrames: 2 },
            text: "Dentro de C",
          },
        ],
      },
      {
        id: "brand-overlay",
        kind: "overlay",
        name: "Marca",
        locked: false,
        clips: [
          {
            id: "overlay-full",
            assetId: "asset-brand",
            timeline: { startFrame: 0, durationFrames: 12 },
            source: null,
            enabled: true,
            locked: false,
            label: "CTA",
            playbackRate: 1,
            transform: {},
            effects: [],
            keyframes: [],
          },
        ],
      },
      {
        id: "markers-main",
        kind: "marker",
        name: "Marcadores",
        markers: [
          { id: "marker-b", frame: 5, label: "B", markerType: "note" },
          { id: "marker-c", frame: 9, label: "C", markerType: "note" },
          { id: "marker-end", frame: 12, label: "Fim", markerType: "note" },
        ],
      },
    ],
  };
}

function track<T extends NonNullable<VideoTimeline["tracks"]>[number]["kind"]>(
  timeline: VideoTimeline,
  kind: T,
) {
  return timeline.tracks?.find((candidate) => candidate.kind === kind) as Extract<
    NonNullable<VideoTimeline["tracks"]>[number],
    { kind: T }
  >;
}

function expectCode(action: () => unknown, code: string) {
  assert.throws(action, (error: unknown) => {
    assert.ok(error instanceof VideoTimelineCommandError);
    assert.equal(error.code, code);
    return true;
  });
}

test("mute original é imutável, reversível e preserva ranges, legendas e duração", () => {
  const input = fixture();
  const before = structuredClone(input);
  const muted = setOriginalAudioMuted(input, true);
  assert.deepEqual(input, before);
  assert.equal(track(muted, "audio").muted, true);
  assert.equal(track(muted, "video").muted, true);
  assert.deepEqual(track(muted, "audio").clips, track(input, "audio").clips);
  assert.deepEqual(track(muted, "caption"), track(input, "caption"));
  assert.equal(muted.durationFrames, input.durationFrames);
  const restored = setOriginalAudioMuted(muted, false);
  assert.equal(track(restored, "audio").muted, false);
  assert.equal(track(restored, "video").muted, true);
  assert.equal(track(muted, "audio").muted, true);
  const trimmed = applyVideoTimelineCommand(muted, {
    type: "trim", trackId: "video-main", clipId: "video-c", edge: "end", targetFrame: 11,
  });
  assert.equal(track(trimmed, "audio").muted, true);
});

test("mute recusa tracks bloqueadas, áudio externo e ausência de track", () => {
  const locked = fixture();
  track(locked, "audio").locked = true;
  expectCode(() => setOriginalAudioMuted(locked, true), "video_timeline_track_locked");
  const external = fixture();
  track(external, "audio").clips![0].assetId = "external-foley";
  expectCode(() => setOriginalAudioMuted(external, true), "video_timeline_original_audio_required");
  const missing = fixture();
  missing.tracks = missing.tracks!.filter((item) => item.kind !== "audio");
  expectCode(() => setOriginalAudioMuted(missing, true), "video_timeline_single_paired_audio_required");
});

test("reorder-ripple mantém o input imutável e remapeia tracks dependentes", () => {
  const input = fixture();
  const snapshot = structuredClone(input);

  const result = applyVideoTimelineCommand(input, {
    type: "reorder-ripple",
    trackId: "video-main",
    clipId: "video-c",
    targetIndex: 0,
  });

  assert.deepEqual(input, snapshot);
  assert.notStrictEqual(result, input);
  assert.equal(result.durationFrames, 12);

  const video = track(result, "video");
  assert.deepEqual(
    video.clips?.map((clip) => [clip.id, clip.timeline]),
    [
      ["video-c", { startFrame: 0, durationFrames: 4 }],
      ["video-a", { startFrame: 4, durationFrames: 4 }],
      ["video-b", { startFrame: 8, durationFrames: 4 }],
    ],
  );

  const audio = track(result, "audio");
  assert.deepEqual(
    audio.clips?.map((clip) => [clip.id, clip.timeline, clip.source?.startMicroseconds]),
    [
      ["audio-c", { startFrame: 0, durationFrames: 4 }, 400_000],
      ["audio-a", { startFrame: 4, durationFrames: 4 }, 0],
      ["audio-b", { startFrame: 8, durationFrames: 4 }, 200_000],
    ],
  );

  const captions = track(result, "caption");
  assert.deepEqual(
    captions.cues?.map((cue) => [cue.id, cue.timeline]),
    [
      ["caption-c", { startFrame: 1, durationFrames: 2 }],
      ["caption-crossing:ripple:1", { startFrame: 6, durationFrames: 2 }],
      ["caption-crossing:ripple:2", { startFrame: 8, durationFrames: 2 }],
    ],
  );

  const overlay = track(result, "overlay");
  assert.deepEqual(
    overlay.clips?.map((clip) => [clip.id, clip.timeline]),
    [
      ["overlay-full:ripple:1", { startFrame: 0, durationFrames: 4 }],
      ["overlay-full:ripple:2", { startFrame: 4, durationFrames: 4 }],
      ["overlay-full:ripple:3", { startFrame: 8, durationFrames: 4 }],
    ],
  );

  const markers = track(result, "marker");
  assert.deepEqual(
    markers.markers?.map((marker) => [marker.id, marker.frame]),
    [
      ["marker-c", 1],
      ["marker-b", 9],
      ["marker-end", 12],
    ],
  );
});

test("trim-start remove frames, ajusta source ranges e faz ripple", () => {
  const result = applyVideoTimelineCommand(fixture(), {
    type: "trim",
    trackId: "video-main",
    clipId: "video-b",
    edge: "start",
    targetFrame: 6,
  });

  assert.equal(result.durationFrames, 10);
  const video = track(result, "video");
  assert.deepEqual(
    video.clips?.map((clip) => [
      clip.id,
      clip.timeline,
      clip.source?.startMicroseconds,
      clip.source?.durationMicroseconds,
    ]),
    [
      ["video-a", { startFrame: 0, durationFrames: 4 }, 0, 133_333],
      ["video-b", { startFrame: 4, durationFrames: 2 }, 266_667, 66_667],
      ["video-c", { startFrame: 6, durationFrames: 4 }, 400_000, 133_333],
    ],
  );
  const audio = track(result, "audio");
  assert.deepEqual(
    audio.clips?.map((clip) => [
      clip.id,
      clip.timeline,
      clip.source?.startMicroseconds,
    ]),
    [
      ["audio-a", { startFrame: 0, durationFrames: 4 }, 0],
      ["audio-b", { startFrame: 4, durationFrames: 2 }, 266_667],
      ["audio-c", { startFrame: 6, durationFrames: 4 }, 400_000],
    ],
  );
  assert.deepEqual(
    track(result, "marker").markers?.map((marker) => [marker.id, marker.frame]),
    [
      ["marker-c", 7],
      ["marker-end", 10],
    ],
  );
});

test("trim-end encurta o clip sem deslocar seu source start", () => {
  const result = applyVideoTimelineCommand(fixture(), {
    type: "trim",
    trackId: "video-main",
    clipId: "video-b",
    edge: "end",
    targetFrame: 6,
  });
  const videoB = track(result, "video").clips?.find((clip) => clip.id === "video-b");
  assert.deepEqual(videoB?.timeline, { startFrame: 4, durationFrames: 2 });
  assert.equal(videoB?.source?.startMicroseconds, 200_000);
  assert.equal(videoB?.source?.durationMicroseconds, 66_667);
  assert.equal(result.durationFrames, 10);
});

test("comando sem deslocamento devolve clone equivalente sem fragmentar tracks", () => {
  const input = fixture();
  const result = applyVideoTimelineCommand(input, {
    type: "reorder-ripple",
    trackId: "video-main",
    clipId: "video-b",
    targetIndex: 1,
  });
  assert.notStrictEqual(result, input);
  assert.deepEqual(result, input);
  assert.equal(track(result, "overlay").clips?.length, 1);
});

test("conversão racional usa o timebase, sem assumir 30 fps", () => {
  assert.equal(
    timelineFrameToMicroseconds(300, { numerator: 30_000, denominator: 1_001 }),
    10_010_000,
  );
  assert.equal(
    timelineMicrosecondsToFrame(
      10_010_000,
      { numerator: 30_000, denominator: 1_001 },
      "nearest",
    ),
    300,
  );
});

test("player mapeia frame de saída para o source correto após o intervalo removido", () => {
  const timeline = fixture();
  assert.equal(
    timelineFrameToSourceMicroseconds(timeline, "video-main", 3),
    100_000,
  );
  // O frame 4 é contíguo na saída, mas o clip B começa em 200ms na fonte.
  assert.equal(
    timelineFrameToSourceMicroseconds(timeline, "video-main", 4),
    200_000,
  );
  assert.equal(
    timelineFrameToSourceMicroseconds(timeline, "video-main", 12),
    533_333,
  );
});

test("timeline multi-asset mantém identidade e mapeia cada source", () => {
  const input = fixture();
  const video = track(input, "video");
  video.clips![2].assetId = "asset-other";
  track(input, "audio").clips![2].assetId = "asset-other";
  const snapshot = structuredClone(input);
  const result = applyVideoTimelineCommand(input, {
    type: "reorder-ripple",
    trackId: "video-main",
    clipId: "video-c",
    targetIndex: 0,
  });
  assert.deepEqual(input, snapshot);
  assert.deepEqual(
    track(result, "video").clips?.map((clip) => [clip.assetId, clip.timeline.startFrame]),
    [
      ["asset-other", 0],
      ["asset-source", 4],
      ["asset-source", 8],
    ],
  );
  assert.equal(timelineFrameToSourceMicroseconds(result, "video-main", 0), 400_000);
});

test("split divide vídeo e áudio pareado sem alterar duração ou tracks editoriais", () => {
  const input = fixture();
  const result = applyVideoTimelineCommand(input, {
    type: "split",
    trackId: "video-main",
    clipId: "video-b",
    targetFrame: 6,
  });

  assert.equal(result.durationFrames, 12);
  assert.deepEqual(
    track(result, "video").clips?.map((clip) => [
      clip.id,
      clip.timeline,
      clip.source?.startMicroseconds,
    ]),
    [
      ["video-a", { startFrame: 0, durationFrames: 4 }, 0],
      ["video-b:split:1", { startFrame: 4, durationFrames: 2 }, 200_000],
      ["video-b:split:2", { startFrame: 6, durationFrames: 2 }, 266_667],
      ["video-c", { startFrame: 8, durationFrames: 4 }, 400_000],
    ],
  );
  assert.deepEqual(
    track(result, "audio").clips?.map((clip) => clip.id),
    ["audio-a", "audio-b:split:1", "audio-b:split:2", "audio-c"],
  );
  assert.deepEqual(track(result, "caption"), track(input, "caption"));
  assert.deepEqual(track(result, "marker"), track(input, "marker"));
});

test("split rejeita bordas e colisões de ids gerados", () => {
  expectCode(
    () => applyVideoTimelineCommand(fixture(), {
      type: "split", trackId: "video-main", clipId: "video-b", targetFrame: 4,
    }),
    "video_timeline_split_out_of_bounds",
  );
  const collision = fixture();
  track(collision, "overlay").clips![0].id = "video-b:split:1";
  expectCode(
    () => applyVideoTimelineCommand(collision, {
      type: "split", trackId: "video-main", clipId: "video-b", targetFrame: 6,
    }),
    "video_timeline_generated_id_collision",
  );
});

test("propriedades visuais e de áudio são validadas e aplicadas imutavelmente", () => {
  const input = fixture();
  const transformed = applyVideoTimelineCommand(input, {
    type: "set-transform",
    trackId: "video-main",
    clipId: "video-a",
    transform: {
      fit: "contain",
      anchor: "top",
      x: 12,
      y: -8,
      scale: 1.1,
      rotation: 2,
      crop: { top: 0.05, right: 0, bottom: 0.1, left: 0 },
    },
  });
  assert.deepEqual(track(input, "video").clips![0].transform, {});
  assert.equal(track(transformed, "video").clips![0].transform.fit, "contain");

  const mixed = applyVideoTimelineCommand(transformed, {
    type: "set-audio",
    trackId: "audio-main",
    clipId: "audio-a",
    gainDb: -6,
    pan: 0.25,
    fadeInFrames: 1,
    fadeOutFrames: 2,
  });
  assert.equal(track(mixed, "audio").clips![0].gainDb, -6);
  assert.equal(track(mixed, "audio").clips![0].fadeOutFrames, 2);

  expectCode(
    () => applyVideoTimelineCommand(input, {
      type: "set-audio", trackId: "audio-main", clipId: "audio-a",
      gainDb: 25, pan: 0, fadeInFrames: 0, fadeOutFrames: 0,
    }),
    "video_timeline_audio_gain_out_of_bounds",
  );
});

test("velocidade altera duração, sincroniza áudio e faz ripple editorial", () => {
  const input = fixture();
  const result = applyVideoTimelineCommand(input, {
    type: "set-speed",
    trackId: "video-main",
    clipId: "video-b",
    playbackRate: 2,
  });

  assert.equal(input.durationFrames, 12);
  assert.equal(result.durationFrames, 10);
  assert.deepEqual(
    track(result, "video").clips?.map((clip) => [
      clip.id,
      clip.timeline.startFrame,
      clip.timeline.durationFrames,
      clip.playbackRate,
    ]),
    [
      ["video-a", 0, 4, 1],
      ["video-b", 4, 2, 2],
      ["video-c", 6, 4, 1],
    ],
  );
  assert.deepEqual(
    track(result, "audio").clips?.map((clip) => [
      clip.id,
      clip.timeline.startFrame,
      clip.timeline.durationFrames,
      clip.playbackRate,
    ]),
    [
      ["audio-a", 0, 4, 1],
      ["audio-b", 4, 2, 2],
      ["audio-c", 6, 4, 1],
    ],
  );
  assert.deepEqual(
    track(result, "caption").cues?.map((cue) => cue.timeline),
    [
      { startFrame: 2, durationFrames: 3 },
      { startFrame: 7, durationFrames: 2 },
    ],
  );
  assert.equal(track(result, "overlay").clips?.[0].timeline.durationFrames, 10);
  assert.deepEqual(
    track(result, "marker").markers?.map((marker) => marker.frame),
    [5, 7, 10],
  );
  assert.equal(
    timelineFrameToSourceMicroseconds(result, "video-main", 5),
    266_667,
  );
});

test("velocidade rejeita limites inválidos e áudio externo sobreposto", () => {
  expectCode(
    () => applyVideoTimelineCommand(fixture(), {
      type: "set-speed", trackId: "video-main", clipId: "video-b", playbackRate: 2.1,
    }),
    "video_timeline_speed_out_of_bounds",
  );
  const overlapping = fixture();
  overlapping.tracks?.push({
    id: "music-main",
    kind: "audio",
    name: "Trilha",
    muted: false,
    locked: false,
    clips: [{
      ...sourceClip("music", 3, 4, 0, "asset-music"),
      gainDb: 0,
      pan: 0,
      fadeInFrames: 0,
      fadeOutFrames: 0,
    }],
  });
  expectCode(
    () => applyVideoTimelineCommand(overlapping, {
      type: "set-speed", trackId: "video-main", clipId: "video-b", playbackRate: 2,
    }),
    "video_timeline_speed_overlapping_audio_unsupported",
  );
});

test("snap escolhe o limite mais próximo dentro da tolerância", () => {
  assert.equal(snapTimelineFrame(19, [0, 10, 20, 30], 2), 20);
  assert.equal(snapTimelineFrame(25, [20, 30], 5), 20);
  assert.equal(snapTimelineFrame(17, [10, 20], 2), 17);
});

test("bloqueia tracks e clips protegidos", async (t) => {
  await t.test("source track", () => {
    const input = fixture();
    track(input, "video").locked = true;
    expectCode(
      () =>
        applyVideoTimelineCommand(input, {
          type: "trim",
          trackId: "video-main",
          clipId: "video-b",
          edge: "end",
          targetFrame: 6,
        }),
      "video_timeline_track_locked",
    );
  });

  await t.test("source clip", () => {
    const input = fixture();
    track(input, "video").clips![0].locked = true;
    expectCode(
      () =>
        applyVideoTimelineCommand(input, {
          type: "reorder-ripple",
          trackId: "video-main",
          clipId: "video-c",
          targetIndex: 0,
        }),
      "video_timeline_clip_locked",
    );
  });

  await t.test("dependent track", () => {
    const input = fixture();
    track(input, "caption").locked = true;
    expectCode(
      () =>
        applyVideoTimelineCommand(input, {
          type: "trim",
          trackId: "video-main",
          clipId: "video-b",
          edge: "end",
          targetFrame: 6,
        }),
      "video_timeline_dependent_track_locked",
    );
  });

  await t.test("dependent clip", () => {
    const input = fixture();
    track(input, "audio").clips![0].locked = true;
    expectCode(
      () =>
        applyVideoTimelineCommand(input, {
          type: "trim",
          trackId: "video-main",
          clipId: "video-b",
          edge: "end",
          targetFrame: 6,
        }),
      "video_timeline_dependent_clip_locked",
    );
  });
});

test("rejeita gaps, frames fracionários e trims que estendem source handles", () => {
  const gapped = fixture();
  track(gapped, "video").clips![1].timeline.startFrame = 5;
  expectCode(
    () =>
      applyVideoTimelineCommand(gapped, {
        type: "reorder-ripple",
        trackId: "video-main",
        clipId: "video-c",
        targetIndex: 0,
      }),
    "video_timeline_source_track_must_be_contiguous",
  );

  expectCode(
    () =>
      applyVideoTimelineCommand(fixture(), {
        type: "trim",
        trackId: "video-main",
        clipId: "video-b",
        edge: "start",
        targetFrame: 4.5,
      }),
    "video_timeline_frame_must_be_integer",
  );

  expectCode(
    () =>
      applyVideoTimelineCommand(fixture(), {
        type: "trim",
        trackId: "video-main",
        clipId: "video-b",
        edge: "end",
        targetFrame: 9,
      }),
    "video_timeline_trim_out_of_bounds",
  );
});
