# Design Loop — docs index

## Start here
- [HANDOFF.md](./HANDOFF.md) — comprehensive handoff: everything changed this session,
  file-by-file map, data model, how to run, verification, screenshots, and open items.

## Product & workflow
- [persona-and-user-stories.md](./persona-and-user-stories.md) — who we serve (Maya, the
  solo builder), the coin-operated user stories, and the gap analysis vs. today's app.
- [senior-design-lead-workflow.md](./senior-design-lead-workflow.md) — the recipe a
  senior design lead runs for a site review, scored stage-by-stage against our workflow,
  with a running note of what's been shipped.

## Harness & architecture
- [HARNESS_DESIGN.md](./HARNESS_DESIGN.md) — the governed-convergence harness: firewall
  chain (critic ≠ maker), deterministic control path, promotion ratchet.
- [PRIMITIVE.md](./PRIMITIVE.md) — the core primitive the loop is built on.
- [DEV_SETUP.md](./DEV_SETUP.md) — local setup.
- [plans/](./plans) — implementation plans.

## Diagrams
- `design-loop-workflow.{dot,svg,png}` — the pass flow (maker → lints → critic → gate).
- `design-loop-harness.{dot,svg,png}` — the harness structure.
- `design-loop-metaharness.{dot,svg,png}` — the meta/evolution loop.

## The web app (this repo's `app/`)
Runs the loop as a live UI (`./run.sh` → http://localhost:8010). DRY mode (default) streams
a scripted transcript at zero cost but runs a **real** deterministic ground-truth audit on
your actual markup/URL (`app/audit.py`). Set `DESIGN_LOOP_DRY=0` for the real critique.
