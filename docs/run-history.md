# Run history and progress

The web app saves the final WebSocket result as `runs/<id>/result.json`. The
landing dashboard can search by goal, filter by convergence, reopen results,
open available reports, delete a run, or clear the list while keeping artifacts.
Older runs without a snapshot open their existing report instead of inventing a
scorecard. Re-run and Focus copy the input into a new run ID; previous results stay
available for comparison.

Progress cards summarize render, baseline, plan, make, score, and decision. Raw
agent output remains expandable. Live baseline scores come from the immutable
`pass0/scores.json`; candidate cards show the first valid observed candidate.
Only `bar_met` counts as convergence. Budget exhaustion, plateau, and floor
breaches are completed runs that did not reach the quality bar.

DRY mode uses illustrative subjective scores and generated examples. Its input
audit is real; DRY browser checks do not validate a live model critique.

## Storage and operation

The default data directory is `~/Downloads/design-loop`. To isolate a demo or test:

```bash
DESIGN_LOOP_DATA_DIR=/tmp/design-loop-demo DESIGN_LOOP_DRY=1 ./run.sh
```

Use one web worker, as `run.sh` does. Run reservations protect active runs from
concurrent starts and deletion within that worker. Report writers and history
edits share a file lock, and index rewrites are atomic. Upgrade the local
`tool-render-report` installation with this app; older writers do not participate
in the lock protocol. Deletion reports filesystem failures rather than claiming
success. This remains a local application, not a multi-user service.

## Verification

`python -m pytest modules tests -q` covers deterministic modules, offline bundle
composition, run management, saved results, and progress/completion handling.
`tests/test_app_runs.py` uses temporary storage and mocked provider boundaries.
The optional provider tests remain gated by `RUN_MANUAL=1`.

Browser acceptance uses DRY mode and temporary data: submit HTML, observe six
cards, reopen the result, focus a fresh run, verify the original is unchanged,
delete one run, and clear history without deleting remaining files. Check the
390px mobile layout and browser console as well as desktop results.

Screenshots from isolated DRY acceptance:
[progress cards](./run-history-working.png) · [mobile history](./run-history-mobile.png).
