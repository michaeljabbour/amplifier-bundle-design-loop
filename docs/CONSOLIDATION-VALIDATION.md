# Improvement-round local validation — 2026-10-28

**Deterministic conformance passed; human benefit and live-provider quality are not measured.** The optional contract comes from Taste; the existing Design Loop remains its own execution adapter.

- Full isolated suite: `.venv/bin/python -m pytest modules tests -q` — **277 passed, 3 skipped**. Skipped cases are the existing manual/provider integration tier. Existing deprecation warnings remain visible.
- The new cases validate the canonical schema and actual artifact hashes; keep/undo/budget records; critical unknown/fail blocking; immutable brief/baseline/candidate; same-brief comparison; authority-source presence without authentication; run-budget reset/expansion rejection; the real ledger append/query/champion path; recipe-helper byte identity and round threading; malformed input; report escaping; and app review-readiness/shipping separation.
- The native Taste guide/ZIP build, source/reference fidelity check and JavaScript syntax check passed after adding the portable schema/reference/MIT files. The pinned canonical local commit and SHA-256 are in `contracts/improvement-round.source.json`.
- The report was inspected in a normal desktop browser and at 390-pixel phone width. The document fit each viewport. The three fictional comparison receipts were readable and expandable; temporary viewport sizing was restored. A remaining “Ship it” instruction was caught in the first visual inspection and removed before the final check. No score-based shipping or usefulness assertion remains in that report path.

The two YAML recipe helpers were regenerated from canonical `recipes/dlx.py`; byte-identity tests pass. The recipe orchestration was not run through a live Amplifier provider. The `recipes` tool was unavailable in this task; offline YAML structure and helper behavior are covered by the existing suite, but this is not a live recipe execution claim.

The contract records a claimed human/delegated source; it does not authenticate that source, enforce an arbitrary host sandbox, recompute arbitrary file hashes at append, or establish audience outcomes. Legacy `accepted` remains internal score ranking; `review_ready` is not adoption. Before release, consumers must account for the historical `ship` flag now being false. Existing ledgers and source history remain untouched. No global installation, remote mutation, publication or original-checkout edits occurred.

## Source publication check

The first publication CI run ([40705496833](https://github.com/michaeljabbour/amplifier-bundle-design-loop/actions/runs/40705496833)) failed at collection because the clean runner lacked `jsonschema`; the earlier local environment already had it. The ledger now declares an optional `test` extra, installed explicitly in CI and the development instructions. This adds no runtime dependency. The initial failure is retained; source publication is separate from live-provider or user acceptance.
