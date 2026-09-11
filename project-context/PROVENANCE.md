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
