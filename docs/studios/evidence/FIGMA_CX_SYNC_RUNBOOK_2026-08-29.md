# Figma CX Sync — MCP runbook

Date: 2026-08-29  
File key: `9qNitJb73bJt4nwQ5zlhft`  
Execution mode: sequential `use_figma` calls only  
Current state: prepared; no mutation authorized at this checkpoint

## Safety contract

- Use the Figma MCP only. Do not use Chrome or desktop automation.
- Execute one mutation batch at a time and inspect the result before continuing.
- Never delete an existing page, frame, component, style or variable.
- Preserve existing node and page IDs wherever possible.
- Rename legacy pages only; page links remain attached to their original IDs.
- Return every created or modified node ID from each MCP call.
- Stop on the first API or validation error; do not continue with partial assumptions.
- Load every font before creating or changing text nodes.
- Change the current page at most once in each MCP call.
- Record the resulting IDs in the synchronization manifest after every accepted batch.

## Existing pages and preservation mapping

| Page ID | Current name | Planned name |
|---|---|---|
| `0:1` | `00 — Cover & Approved Index` | `LEGACY / 00 — Cover & Approved Index` |
| `200:2` | `05 — Screen Directory` | `LEGACY / 05 — Screen Directory` |
| `1:2` | `01 — Foundations` | `LEGACY / 01 — Foundations` |
| `1:3` | `02 — Components` | `LEGACY / 02 — Components` |
| `1:4` | `03 — Shell & Overlays` | `LEGACY / 03 — Shell & Overlays` |
| `1:5` | `10 — Discover & Plan` | `LEGACY / 10 — Discover & Plan` |
| `1:6` | `20 — Create & Review` | `LEGACY / 20 — Create & Review` |
| `1:7` | `30 — Publish & Learn` | `LEGACY / 30 — Publish & Learn` |
| `1:8` | `90 — Flows & States` | `LEGACY / 90 — Flows & States` |
| `178:2` | `40 — Studios` | `LEGACY / 40 — Studios` |
| `244:2` | `35 — Social Integrations` | `LEGACY / 35 — Social Integrations` |
| `178:3` | `99 — Archive` | unchanged |

## Batch P1.1 — Preserve the current taxonomy

Operation:

1. Resolve the eleven listed page IDs.
2. Verify that current names still equal the inventory above.
3. Prefix their names with `LEGACY /`.
4. Do not alter `178:3`.

Accept only if:

- all eleven expected pages were found;
- exactly eleven names changed;
- no child count changed;
- `99 — Archive` remains present and unchanged.

Rollback:

- restore each name from the table using its stable page ID.

## Batch P1.2 — Create the canonical page structure

Create exactly these pages in this order:

1. `00 — Readme & Decisions`
2. `01 — IA & Golden Flows`
3. `02 — Foundations`
4. `03 — Shared Shells`
5. `04 — Create & Direction`
6. `05 — Editorial & Visual`
7. `06 — Video & Presenter`
8. `07 — Factory & Library`
9. `08 — Review, Publish & Learn`
10. `09 — Responsive & Edge States`
11. `10 — Prototype Tests`

Accept only if:

- all eleven names are unique;
- the preserved archive remains present;
- every created page ID is returned and recorded;
- no legacy page is removed or moved into the archive.

Rollback:

- because deletion is forbidden, prefix incomplete new pages with `WIP / ROLLBACK /` and leave
  their IDs recorded for later repair.

## Batch P1.3 — Foundations parity

On `02 — Foundations`, create documentation frames for:

- primitive and semantic color aliases;
- dark and light modes;
- Bricolage Grotesque, Manrope and IBM Plex Mono hierarchy;
- spacing, radius and layout grid;
- focus, hover, active, disabled, pending, success and error states;
- 120/180/240 ms motion durations and reduced-motion behavior;
- breakpoints 360, 768, 1024 and 1440.

Variable changes are allowed only after comparing each local variable with
`src/design-system/tokens.css`. Add WEB code syntax without changing existing semantic meaning.

Accept only if:

- the Clicko palette remains unchanged;
- local variables are reused rather than duplicated;
- light and dark aliases are explicit;
- no external library variable is bound to a canonical Clicko frame.

Rollback:

- restore changed variable values from the captured pre-mutation snapshot;
- retain new documentation frames with `WIP / ROLLBACK /` if a batch cannot be completed.

## Batch P1.4 — Readme and canonical index

On `00 — Readme & Decisions`, create:

- title and product thesis;
- authority order;
- canonical/legacy status legend;
- links to pages 01–10 and 99;
- current counts: 17 Screen Contracts and 45 Action Contracts;
- gate language: only `CANONICAL + Approved` enters the implementation allowlist;
- provenance links to the master plan, registry and token source.

The prior claim of 27 screens must not be copied into the canonical index.

Accept only if every link resolves to the page ID returned by P1.2.

## Batch P2 — Shared shells

Build on `03 — Shared Shells` by reusing local App Shell, Primary Nav, Workspace Selector, Button,
Avatar, Breadcrumb and Production Rail components. Cover:

- Global shell;
- Project shell;
- Studio shell;
- Decision shell;
- Operation shell.

The Studio shell must implement the action-first hierarchy defined in
`docs/studios/research/ACTION_FIRST_STUDIO_REFERENCE_SYNTHESIS_2026-08-29.md`:

- compact Context bar;
- Production Rail;
- dominant Stage;
- persistent Action Dock;
- contextual Inspector;
- progressive Details drawer;
- Quick, Directed and Pro views over the same document.

Each shell receives desktop 1440 and compact 1024 examples. Mobile behavior is documented in P4.

Accept only if:

- navigation hierarchy is shared rather than redrawn per screen;
- the Studio shell keeps the global product identity;
- the Stage and next executable action dominate over explanatory copy;
- the Action Dock has one primary CTA, no more than four context chips and a `More control` entry;
- no emoji is used; semantic status uses text, color and accessible design-system vector icons;
- primary action, save/job state and current context are visible;
- keyboard focus order is annotated.

## Batch P3 — Screen families and golden flows

Create canonical frames in the page allocation recorded by
`FIGMA_CX_SYNC_MANIFEST_2026-08-29.json`. Every frame must contain the required frame properties and
use the exact Screen and Action IDs from `src/app/experience/registry.ts`.

Golden flows:

- J1: quick post creation;
- J2: campaign to multiple formats;
- J3: edit existing media;
- J4: raw video to finished ad;
- J5: authorized face/voice to presenter ad;
- J6: review, publish and learn.

For Studio families, show the result-first loop `request → draft → scoped refinement → compare →
fixed version → review`. Any prompt-based change must identify its scope (document, scene, layer,
range or selection). Full regeneration cannot be the default for a selected sub-target.

Accept only if every transition is backed by an Action Contract and no decorative button appears.

## Batch P4 — Responsive and edge states

On `09 — Responsive & Edge States`, cover:

- 360 mobile stacked layout;
- 768 compact/tablet layout;
- 1024 compact desktop layout;
- 1440 wide desktop reference;
- loading, empty, ready, dirty, saving, saved;
- recoverable and terminal errors;
- readonly, forbidden, offline, stale and conflict;
- queued, running, cancelling and cancelled jobs.

Accept only if the page itself can scroll, the main canvas remains movable where required, and
critical actions are reachable without relying on hover.

## Batch P5 — Clickable prototype tests

On `10 — Prototype Tests`, create one clearly labelled entry point for each golden flow and add:

- task statement;
- expected first click;
- completion condition;
- failure/recovery branch;
- Screen/Action IDs used;
- breakpoint under test.

Prototype connections must mirror the executable route graph. The Figma sync is not complete until
all six tasks can be traversed without dead ends.

## Batch P6 — Evidence and human validation

After the Figma-to-code audit:

1. Run the protocol in `docs/studios/CX_USER_VALIDATION_PROTOCOL_2026-08-29.md`.
2. Measure first-click success for Create, Edit video, Edit image, Review and Publish.
3. Require at least 80% success at the architecture gate.
4. Record accessibility and recovery observations.
5. Iterate failed tasks before marking the product goal complete.

This batch requires real participants and cannot be simulated by the implementation agent.
