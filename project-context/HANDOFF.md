# Handoff — 2026-09-24

Branch `perf/session-footprint`: reduced what `behaviors/design-loop.yaml` adds to
every request (~2.9k -> ~1.35k tok for its own components, chars/4) plus dropping
the unused design-intelligence include (opt-in via `behaviors/design-loop-full.yaml`).
Tool input contracts are unchanged except `design_controller.candidate_scores`,
which now uses `additionalProperties` (0-4 ints) instead of 8 enumerated properties.
playwright imports lazily; the ledger dir is created on first append.

Validation: deterministic suite only (`pytest modules tests`). No live `amplifier run`
was done (file:// module sources would install into the shared tool env).

Next: end-to-end check in a disposable Amplifier home — compose the behavior, confirm
the delegate catalog and tool list, run design-judge once and a 1-budget
design-converge with `bundle_ref` set. Not pushed.

## 2026-10-28 — isolated consolidation work

Added the optional Taste improvement-round/v1 consumer in the ledger, recipe-helper handoff, report and app review-readiness distinction. Existing ledgers remain readable; no source data was migrated or deleted. Work is in an isolated campaign clone based on committed 066af76; the original checkout’s unfinished work was not copied or changed. Run `.venv/bin/python -m pytest modules tests -q`. Provider efficacy and runtime authorization are not established by these checks. See docs/IMPROVEMENT-ROUNDS.md.

## 2026-10-28 — publication preflight

The committed improvement-round adapter is ready for source publication after a fresh full deterministic run: 277 passed, 3 skipped, with existing deprecation warnings retained. The public main branch is still the original 066af76 baseline, so no upstream reconciliation is needed. The source publication and CI readback are recorded in the campaign's supporting-publications record; local checks alone do not establish a remote result.

Next: inspect that publication record for final status, then address native host/provider acceptance separately. No runtime service was installed or activated, no source data was retired, and no human-benefit or live-provider result is established by these checks.

Clean CI exposed a missing test dependency after that publication: the new schema test imports `jsonschema`, which the local venv already contained. The ledger now declares it in the optional `test` extra and the workflow installs that extra. The initial failed run remains visible; wait for the corrected commit's CI before calling publication validation complete.
