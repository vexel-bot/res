# Figma CX Sync — P3 Create and Direction

**Date:** 2026-08-29  
**File:** [Clicko](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko)  
**Page:** `04 — Create & Direction` (`272:6`)  
**Root:** `[CANONICAL][Approved] Create & Direction — Action-first` (`294:2`)  
**Status:** first P3 screen-family slice complete; P3 remains in progress

## Frames and contracts

| Screen | Frame | State | Primary action | Visible secondary action |
|---|---:|---|---|---|
| `SCREEN-HOME` | `294:9` | ready / 1440 | `HOME-OPEN-CREATE` | `HOME-OPEN-LIBRARY` |
| `SCREEN-CREATE-HUB` | `294:141` | ready / 1440 | `CREATE-START-DIRECTION` | none |
| `SCREEN-DIRECTION` | `294:254` | dirty / 1440 | `DIRECTION-APPROVE` | none |

## Action-first decisions represented

- Home leads with “what do you want to finish now?” and preserves recent work below the primary
  task rather than leading with metrics.
- Create Hub exposes only the creation action currently backed by the executable registry. Other
  entry points are not presented as clickable controls.
- Direction compares two theses, shows the selected thesis evidence and guardrail, exposes honest
  dirty state and fixes the direction only through `DIRECTION-APPROVE`.
- Every visible Button instance encodes its Action Contract ID in the Figma node name.

## Automated Figma audit

- text nodes scanned for emoji ranges: zero hits;
- Button instances found: four;
- Button instances without one of the four registered Action IDs: zero;
- local App Shell and Button components reused;
- generated screenshot inspected after mutation; no clipping or overlapping primary CTA was found.

## Remaining P3 allocation

- Editorial, Visual, Carousel and Image Lab;
- Video, Presenter and Identity Library;
- Asset Library, Reuse, Factory, Factory Round and Batch Review;
- Review and Publish;
- exact Screen/Action ID audit across all 17 screen families.
