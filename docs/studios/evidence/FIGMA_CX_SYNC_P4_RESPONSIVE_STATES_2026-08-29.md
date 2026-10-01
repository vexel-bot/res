# Figma CX Sync — P4 responsive and edge states

**Date:** 2026-08-29  
**File:** [Clicko](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko)  
**Page:** `09 — Responsive & Edge States` (`272:11`)  
**Root:** `[CANONICAL][Approved] Responsive & Edge States` (`318:2`)  
**Status:** P4 complete; P5 in progress

## Responsive specimens

| Breakpoint | Frame | Primary action | In viewport |
|---:|---:|---|---:|
| 1440 | `319:6` | `VIDEO-RENDER-PREVIEW` | yes |
| 1024 | `319:39` | `VIDEO-RENDER-PREVIEW` | yes |
| 768 | `319:69` | `VIDEO-RENDER-PREVIEW` | yes |
| 360 | `319:93` | `VIDEO-RENDER-PREVIEW` | yes |

The wide layout keeps Production Rail, Stage and Inspector visible. At 1024 the Inspector is removed
before the Stage is reduced. At 768 the Production Rail becomes a compact progress strip. At 360 the
player, scene strip, transcript summary and Action Dock become one vertical flow and the primary CTA
remains inside the viewport.

## State matrix

The matrix `320:10` contains exactly one specimen for each required state:

`loading`, `empty`, `ready`, `dirty`, `saving`, `saved`, `recoverable-error`, `terminal-error`,
`readonly`, `forbidden`, `offline`, `stale`, `conflict`, `job-queued`, `job-running`,
`job-cancelling` and `job-cancelled`.

Each state states what happened, what the user may do and what remains preserved. Status never relies
on color alone.

## Recovery specimens

The recovery section `321:10` covers:

- failed video render with `VIDEO-RETRY-JOB` and `VIDEO-REFRESH-JOB`;
- running video job with `VIDEO-CANCEL-JOB`, explicitly preserving the source;
- revoked Presenter consent with `PRESENTER-OPEN-IDENTITIES` as the safe resolution path.

## Automated Figma audit

- four expected exact widths found;
- four primary CTAs fully contained by their screen frames;
- 17 required state cards found exactly once;
- eight visible Button instances found;
- buttons with an unexpected Action ID: zero;
- emoji hits: zero;
- rendered page and 360 screenshots inspected; the action remains reachable and no horizontal
  overflow is visible.
