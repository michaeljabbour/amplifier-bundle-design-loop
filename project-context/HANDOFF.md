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
