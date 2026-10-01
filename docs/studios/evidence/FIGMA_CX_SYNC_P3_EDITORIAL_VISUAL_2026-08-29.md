# Figma CX Sync — P3 Editorial and Visual

**Date:** 2026-08-29  
**File:** [Clicko](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko)  
**Page:** `05 — Editorial & Visual` (`272:7`)  
**Root:** `[CANONICAL][Approved] Editorial & Visual — Action-first` (`296:2`)  
**Status:** second P3 screen-family slice complete; P3 remains in progress

## Frames and contracts

| Screen | Frame | State | Primary action | Secondary contracts represented |
|---|---:|---|---|---|
| `SCREEN-EDITORIAL` | `297:4` | ready / 1440 | `EDITORIAL-OPEN-VISUAL` | `EDITORIAL-OPEN-CAROUSEL`, `EDITORIAL-OPEN-VIDEO`, `EDITORIAL-OPEN-PRESENTER` |
| `SCREEN-VISUAL` | `298:114` | ready + motion selected / 1440 | `VISUAL-SEND-REVIEW` | `VISUAL-OPEN-MOTION`, `MOTION-PREVIEW`, `MOTION-SAVE-SUGGESTION`, `MOTION-APPLY` |
| `SCREEN-CAROUSEL` | `299:205` | ready / 1440 | `CAROUSEL-VISUALIZE-SET` | `CAROUSEL-SEND-REVIEW` |
| `SCREEN-IMAGE-LAB` | `300:290` | ready / 1440 | `IMAGE-CREATE-DERIVATION` | `IMAGE-COMPARE`, `IMAGE-RETURN` |

## Action-first decisions represented

- Editorial makes the script the dominant object and groups all contract-backed Studio handoffs in
  one dock without changing `documentId`.
- Visual keeps the editable composition dominant. Motion is contextual to the selected Product
  layer and exposes preview, saved suggestion and reviewed apply as distinct actions.
- Carousel treats the ordered page set as one versioned object and separates local full-set preview
  from immutable review submission.
- Image Lab keeps source and derivative side by side, shows protected regions, creates a private
  derivative and returns through the validated internal origin.

## Automated Figma audit

- 228 text nodes scanned for emoji ranges: zero hits;
- 14 visible Button instances found;
- Button instances without one of the 14 registered Action IDs: zero;
- four expected screen-family frames found;
- App Shell, Production Rail and Button components reused;
- rendered root and Visual screenshots inspected after mutation; no clipped primary CTA or panel
  overlap was found.

## Remaining P3 allocation

- Video, Presenter and Identity Library;
- Asset Library, Reuse, Factory, Factory Round and Batch Review;
- Review and Publish;
- exact Screen/Action ID audit across all 17 screen families.
