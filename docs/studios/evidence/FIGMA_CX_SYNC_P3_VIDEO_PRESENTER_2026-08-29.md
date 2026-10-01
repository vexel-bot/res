# Figma CX Sync — P3 Video, Presenter and Identity Library

**Date:** 2026-08-29  
**File:** [Clicko](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko)  
**Page:** `06 — Video & Presenter` (`272:8`)  
**Root:** `[CANONICAL][Approved] Video & Presenter — Governed action-first` (`303:2`)  
**Status:** third P3 screen-family slice complete; P3 remains in progress

## Frames and contracts

| Screen | Frame | State | Primary action | Governance represented |
|---|---:|---|---|---|
| `SCREEN-VIDEO` | `304:4` | ready / 1440 | `VIDEO-RENDER-PREVIEW` | immutable source, edit decisions, job, checksum, QC and render-bound review |
| `SCREEN-PRESENTER` | `305:124` | ready / 1440 | `PRESENTER-GENERATE-SAMPLE` | identity, voice, scope, expiry, benchmark gate and private sample |
| `SCREEN-IDENTITY-LIBRARY` | `306:213` | ready / 1440 | `IDENTITY-START-ENROLLMENT` | licensed stock catalog, exact version return, enrollment and revocation |

## Action-first decisions represented

- Video keeps the private result, transcript and timeline visible together. Proxy, waveform,
  captions, cut, checkpoint, render and review remain separate contracts.
- A successful preview shows its job, checksum and QC result before review is allowed.
- Presenter begins with identity, voice, scene and rights already summarized beside the private
  sample surface. `Abrir no Video Studio` is visibly unavailable before a sample and human review.
- Identity Library includes six governed stock candidates — Ana, Lívia, Marina, Rafael, Caio and
  Bruno — split into three women and three men, each returning an exact active version.
- Personal identity enrollment, candidate submission and consent revocation are visually separated
  from content production.

## Automated Figma audit

- 178 text nodes scanned for emoji ranges: zero hits;
- 22 visible Button instances found;
- Button instances without a registered Video, Presenter or Identity Action ID: zero;
- six stock identity cards found;
- three expected screen-family frames found;
- rendered page and Identity Library screenshots inspected; no clipped primary CTA or panel overlap
  was found.

## Remaining P3 allocation

- Asset Library, Reuse, Factory, Factory Round and Batch Review;
- Review and Publish;
- exact Screen/Action ID audit across all 17 screen families.
