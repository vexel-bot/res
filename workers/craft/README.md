# Clicko Craft runtime

The complete PhotoCraft, FilmCraft and EffectCraft sources are pinned under
`third_party/craft`. Their original interfaces remain source/reference tools;
the customer experience is the Clicko React Studios. Independent Rust adapters
use the original native models, command registries, codecs and renderers.

## Build

Docker with the Linux engine is required for the development Windows runner.
The builder uses Rust 1.95.0. Every adapter has its own dependency lockfile;
EffectCraft keeps its upstream FilmCraft revision instead of using the newer
standalone FilmCraft workspace. `scripts/craft/provenance.py` verifies every
upstream source blob against `sources.lock.json`.

```powershell
python scripts/craft/provenance.py
python scripts/craft/build.py
python scripts/craft/build.py --wasm
python scripts/craft/mirror.py --bundle
```

Native builds produce `clicko-craft-runtime:local`, containing the three real
adapter binaries, provenance, checksums and bundled asset license notices.
Linux workers may configure `STUDIO_CRAFT_PHOTOCRAFT_BINARY`,
`STUDIO_CRAFT_FILMCRAFT_BINARY` and `STUDIO_CRAFT_EFFECTCRAFT_BINARY` with their
installed binaries. Otherwise the host invokes `run_adapter.py`, materializing
only the authenticated job directory in a networkless container. An unavailable
engine is reported explicitly. No legacy editor or renderer is invoked.

The JSON-lines transport is `protocolVersion: 1`, `requestId`, `engine`,
`method`, `params`, returning a matching `result` or typed `error`. Filesystem
paths belong to the materialized job; native media references remain relative
and are resolved from checksummed workspace manifests on every invocation.

## Validation

```powershell
python -m pytest backend/tests/test_craft*.py
node --import tsx --test tests/unit/craft*.test.ts
npm run lint
npm run build
```

Each Rust adapter also includes actual pixel/render and native format
round-trip tests. The CI runs these separately from mocked backend failure tests.
Browser previews and final outputs use their respective Craft renderers.
Browser sessions use dedicated Web Workers with project/revision identities,
bounded media memory and cancellation by worker termination. When an external
font or oversized media cannot be reproduced locally, the same native server
engine renders the preview explicitly.
AI planning uses the existing configured provider and budget controls; its
output is validated against the exact engine command schemas.

PhotoCraft carousel pages are separate native `.pcraft` projects within one
Clicko document, keeping page order, versioning and complete native editing.
Original pre-migration documents are immutable archives. Unsupported conversion
details are surfaced as migration warnings, never replaced silently.

With an isolated QA API on port 8018 and frontend on 3018, run the real checks:

```powershell
python scripts/craft/acceptance.py
python scripts/craft/media_acceptance.py
node scripts/validation/craft-browser-parity.mjs
node scripts/validation/craft-wasm-reference.mjs
node scripts/validation/craft-wasm-effects.mjs
```

These checks exercise real native byte round trips, history, revision conflicts,
exports, checksums, audio, transparent links and browser/native pixel equality.
QA credentials and generated artifacts remain in ignored `.codex-runtime/craft`.
The WASM reference check also works while the native service is unavailable,
using saved native acceptance artifacts with verified checksums. It does not
replace the current-build HTTP export and linked-composition acceptance.
Contract tests use process-boundary doubles for failure cases and do not prove
renderer fidelity. The real acceptance checks are separate.

Full Git mirrors and verified portable bundles retain all upstream refs/history;
the source trees imported with subtree are independently immutable and verified.
The older FilmCraft revision required by EffectCraft is preserved separately.
Archived former renderers/workers live under `docs/studios/archive`, outside app
imports, frontend builds and worker images. They are not runtime alternatives.
