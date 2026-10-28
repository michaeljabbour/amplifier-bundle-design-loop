# Changelog

## Unreleased — bounded improvement-round adapter

- Consume Taste's optional improvement-round/v1 contract with deterministic gate, immutable artifact, same-brief, decision-source and budget checks in the existing ledger package.
- Carry supplied round records through the recipe helper and show their reported keep/undo, evidence and rollback separately from score rank. Retain all legacy records; do not fabricate a missing receipt.
- Label a passing score bar Ready for review, expose `review_ready`, and keep the legacy `ship` flag false. A score/convergence result does not authorize adoption or shipping.
- Add fictional keep/undo/budget examples and schema, ledger, recipe, report and payload tests. No live-provider or outside-use result is claimed.
