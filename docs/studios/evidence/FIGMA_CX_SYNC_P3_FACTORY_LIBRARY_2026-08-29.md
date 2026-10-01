# Figma CX Sync — P3 Factory and Library

**Date:** 2026-08-29  
**File:** [Clicko](https://www.figma.com/design/9qNitJb73bJt4nwQ5zlhft/Clicko)  
**Page:** `07 — Factory & Library` (`272:9`)  
**Root:** `[CANONICAL][Approved] Factory & Library — Action-first operations` (`308:2`)  
**Status:** fourth P3 screen-family slice complete; P3 remains in progress

## Frames and contracts

| Screen | Frame | State | Primary action | Operational invariant |
|---|---:|---|---|---|
| `SCREEN-LIBRARY-ASSETS` | `309:4` | ready / 1440 | `LIBRARY-OPEN-IMAGE-LAB` | private source, authenticated thumbnail, rights and lineage |
| `SCREEN-REUSE` | `310:108` | ready / 1440 | `REUSE-GENERATE-DERIVATIONS` | one hypothesis and one identity per child document |
| `SCREEN-FACTORY` | `311:213` | ready / 1440 | `FACTORY-START-ROUND` | validated recipe, capacity, cost, human gates and idempotency |
| `SCREEN-FACTORY-ROUND` | `313:297` | job-running / 1440 | `FACTORY-OPEN-BATCH-REVIEW` | job and recovery state remain scoped to each cell |
| `SCREEN-BATCH-REVIEW` | `314:358` | ready / 1440 | `REVIEW-APPROVE` | only eligible immutable versions enter the decision set |

## Action-first decisions represented

- Asset Library acts on one selected immutable source and exposes rights and lineage beside the two
  available actions.
- Reuse keeps source evidence separate from child hypotheses and never copies performance metrics to
  the children.
- Factory validates the recipe before creating jobs and shows cost, capacity and human gates beside
  the single round-start action.
- Factory Round presents six independent cells with ready, running, blocked and queued states. A
  rights block is not represented as a provider failure.
- Batch Review contains only three eligible fixed outputs and records the approval against their
  exact versions.

## Automated Figma audit

- 258 text nodes scanned for emoji ranges: zero hits;
- seven visible Button instances found;
- Button instances without one of the seven registered Action IDs: zero;
- five expected screen-family frames found;
- rendered page and Factory Round screenshots inspected; no clipped primary CTA or panel overlap was
  found.

## Remaining P3 allocation

- Review and Publish;
- exact Screen/Action ID audit across all 17 screen families.
