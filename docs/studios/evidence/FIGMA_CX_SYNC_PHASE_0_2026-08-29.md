# Figma CX Sync — Phase 0 discovery ledger

Date: 2026-08-29  
Status: discovery complete; no Figma mutation performed  
Canonical file: [Clicko](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko)  
File key: `9qNitJb73bJt4nwQ5zlhft`

## Authority order

1. `docs/studios/STUDIOS_CX_SCREEN_FLOW_AND_INTERACTION_MASTER_PLAN_2026-08-28.md`
2. Executable route, screen and action contracts in `src/app/experience/registry.ts`
3. Current verified product behavior and automated coverage
4. Local Clicko variables, styles and components already present in Figma
5. Legacy Figma explorations, retained only as reference
6. External libraries, used only when they match the Clicko contract and visual language

## Current Figma inventory

The file contains twelve existing pages:

- `00 — Cover & Approved Index`
- `05 — Screen Directory`
- `01 — Foundations`
- `02 — Components`
- `03 — Shell & Overlays`
- `10 — Discover & Plan`
- `20 — Create & Review`
- `30 — Publish & Learn`
- `90 — Flows & States`
- `40 — Studios`
- `35 — Social Integrations`
- `99 — Archive`

The current `40 — Studios` page includes explorations for Experiment Detail, Knowledge & Evidence,
Learning & Privacy, Video Studio pre-production/ingest/editor, Presenter & Rights Vault, Presenter
Capsule Setup, and one Presenter Production Cell marked approved.

## Reusable local design-system assets

The local Clicko system is the preferred source. Confirmed reusable assets include:

- App Shell and Primary Nav Item
- Workspace Selector and Global Search Trigger
- Button, Icon Button and Avatar variants
- Breadcrumb Item and product icons
- Production Rail
- Content Card, Project Row, Opportunity Card, Campaign Card and Template Card
- Approval Item, Activity Item and Integration Row
- Empty, error, skeleton, toast, modal and drawer patterns

Available product fonts match the code contract:

- Bricolage Grotesque for display hierarchy
- Manrope for interface and body text
- IBM Plex Mono for IDs, state and technical metadata

## Token parity

The Figma file already has local primitive color, semantic color, spacing/size and radius variable
collections plus nine text styles. The product code additionally establishes:

- action coral `#ff5c5c` and creative orange `#ff7a00`
- semantic success, warning, information and danger colors
- six radius levels, seven spacing levels and three motion durations
- explicit dark and light surface/text aliases
- reduced-motion behavior

Gaps to resolve in Phase 1:

- add WEB code syntax to local variables;
- validate aliases against `src/design-system/tokens.css`;
- complete light/dark semantic parity without changing the current dark default;
- document focus, disabled, pending, success, error and reduced-motion states;
- retain the existing brand palette and type hierarchy.

## External-library decision

The connected Simple Design System library returned no compatible component for the scoped
`Button` search. Material and platform kits use different visual and interaction contracts. They
are therefore rejected as canonical product sources. They may remain reference material, but no
external component will replace an existing Clicko component during this sync.

## Executable product contract

The current registry exposes 17 canonical screen contracts and 45 action contracts. The core Figma
frames must reference these IDs instead of inventing parallel names. Core screens:

- `SCREEN-HOME`, `SCREEN-CREATE-HUB`, `SCREEN-DIRECTION`, `SCREEN-EDITORIAL`
- `SCREEN-VISUAL`, `SCREEN-CAROUSEL`, `SCREEN-VIDEO`, `SCREEN-PRESENTER`
- `SCREEN-IDENTITY-LIBRARY`, `SCREEN-IMAGE-LAB`, `SCREEN-LIBRARY-ASSETS`
- `SCREEN-REVIEW`, `SCREEN-PUBLISH`, `SCREEN-REUSE`, `SCREEN-FACTORY`
- `SCREEN-FACTORY-ROUND`, `SCREEN-BATCH-REVIEW`

The Figma frame annotation contract is:

`screenId`, route, journey, state, breakpoint, requirement IDs, owner, status and date.

Only frames marked `CANONICAL + Approved` are eligible for the implementation allowlist.

## Canonical page plan

After checkpoint approval, preserve every existing frame and migrate the file additively:

1. Rename existing non-canonical pages with the prefix `LEGACY /`.
2. Keep `99 — Archive` intact.
3. Create the exact canonical structure from the master plan:
   - `00 — Readme & Decisions`
   - `01 — IA & Golden Flows`
   - `02 — Foundations`
   - `03 — Shared Shells`
   - `04 — Create & Direction`
   - `05 — Editorial & Visual`
   - `06 — Video & Presenter`
   - `07 — Factory & Library`
   - `08 — Review, Publish & Learn`
   - `09 — Responsive & Edge States`
   - `10 — Prototype Tests`
4. Reuse local components and variables. Add only missing Studio-specific components.
5. Add cross-links from canonical frames to retained legacy explorations when provenance is useful.

No page or frame will be deleted. Renames remain reversible.

## Screen allocation

| Canonical page | Primary executable screens and artifacts |
|---|---|
| `01 — IA & Golden Flows` | five destinations, five shells and journeys J1–J6 |
| `02 — Foundations` | variables, type, grids, focus, state and motion contracts |
| `03 — Shared Shells` | Global, Project, Studio, Decision and Operation shells; Production Rail |
| `04 — Create & Direction` | `SCREEN-HOME`, `SCREEN-CREATE-HUB`, `SCREEN-DIRECTION` |
| `05 — Editorial & Visual` | `SCREEN-EDITORIAL`, `SCREEN-VISUAL`, `SCREEN-CAROUSEL`, `SCREEN-IMAGE-LAB` |
| `06 — Video & Presenter` | `SCREEN-VIDEO`, `SCREEN-PRESENTER`, `SCREEN-IDENTITY-LIBRARY` |
| `07 — Factory & Library` | `SCREEN-LIBRARY-ASSETS`, `SCREEN-REUSE`, `SCREEN-FACTORY`, `SCREEN-FACTORY-ROUND`, `SCREEN-BATCH-REVIEW` |
| `08 — Review, Publish & Learn` | `SCREEN-REVIEW`, `SCREEN-PUBLISH`, analytics/learning handoff |
| `09 — Responsive & Edge States` | 360/768/1024/1440 plus loading, empty, error, permission, conflict, save and job states |
| `10 — Prototype Tests` | six clickable task prototypes and moderator entry points |

## Phase gates

- Phase 0: source of truth, conflicts and additive migration plan recorded — complete.
- Phase 1: page structure, tokens and shared component parity — awaiting checkpoint approval.
- Phase 2: five shells and Production Rail.
- Phase 3: screen families and the six golden flows.
- Phase 4: responsive/edge states and clickable prototype tasks.
- Phase 5: Figma-to-code audit using shared Screen and Action IDs.
- Phase 6: moderated first-click/tree test with real participants.

The product goal remains active until the Figma sync and real-user validation evidence are both
complete.
