# Hybrid generation qualification

This benchmark keeps deterministic editing qualification separate from local
diffusion qualification. A valid MP4 does not qualify a candidate on its own.

## Gates

1. A contextual V2 plan is explicitly recompiled with the current compiler.
2. The manifest binds source direction, executable direction, assets, fonts and
   executable composition by digest.
3. Geometric findings with severity `correction` or `blocker` stop application
   and production, with at most two local correction rounds.
4. Preview/export observations consume the executable direction persisted by
   the compiler and the export's actual DOM geometry.
5. Diffusion preflight runs before any model import or download.
6. A generated candidate remains unincorporated until visual admission and a
   current document-revision check.

The original host result is recorded in `local-preflight-2026-09-10.json`. It
documents why Wan 2.1 could not be admitted on this machine.

`local-environment-qualification-2026-09-10.json` records the later CUDA
environment qualification and the independent storage/load blocks. It does not
claim that a model or generated candidate has been qualified.

`local-model-provisioning-2026-09-10.json` records the successful pinned model
provisioning. It remains separate from inference and editorial qualification.

## Local diffusion result

`animatediff-lightning-a-seed-20260911.mp4` is a real offline inference made by
the res worker on the local RTX 2050. Its request, immutable model revisions,
checksums, timings and observed memory usage are stored beside it. The contact
sheet exposes every generated frame.

The execution passes the technical generation gate and remains experimental.
It fails editorial admission because the saturated abstract imagery does not
represent the requested distribution concept precisely enough for automatic
catalog incorporation. `animatediff-lightning-a-seed-20260912-rejection.json`
also records that a second seed was rejected by the content checker before
export. Neither result is represented as production-ready footage.
