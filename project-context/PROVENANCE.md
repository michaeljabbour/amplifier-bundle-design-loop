# Decisions

- 2026-09-11: base the app changes on the existing bodyless bundle fix. Preserve
  capabilities and root-instruction behavior rather than reintroducing bundle prose.
- Re-runs receive new IDs so history remains a record of distinct results and
  milestone watchers cannot observe the previous run's terminal files.
- Baseline progress reads an immutable pass-zero snapshot because
  `best_scores.json` changes when the champion improves.
- Shared file locking and atomic index rewrites protect report appends during
  history deletion/clearing. Reservations are intentionally single-worker state.
- Raw local research-session exports are outside this implementation PR.
- 2026-09-24: per-request footprint cut. Tool/agent descriptions are sent on every
  turn, so they are terse routing text; semantics stay in docstrings and agent
  bodies. design-intelligence moved to opt-in `behaviors/design-loop-full.yaml`
  (nothing depends on it; foundation ships it). recipes stays included (the
  governed loop needs it; deduplicated on foundation). Harness agents stay
  registered because legacy recipes resolve agents from the caller's agent map.
  playwright is imported on first use, and the ledger dir is created on first
  append, so mount() does no heavy work.
