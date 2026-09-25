# Structure

- `app/`: local FastAPI application, WebSocket runners, and vanilla browser UI.
- `app/storage.py`: shared data root, path validation, and active-run reservations.
- `modules/tool-render-report/`: report generation and shared history locking.
- `recipes/`: governed convergence flow; pass-zero scores are snapshotted here.
- `tests/test_app_runs.py`: temporary-storage HTTP/WebSocket and runner regressions.
- `fixtures/`: example inputs including `slop.html` and `target.html`.
- `docs/run-history.md`: run workflow, operations, and acceptance checks.
- `behaviors/design-loop.yaml`: default (lean) behavior; `behaviors/design-loop-full.yaml`: opt-in + design-intelligence.
- `scripts/measure_footprint.py`: per-request prompt footprint estimator; `tests/test_footprint.py` pins budgets and tool contracts.
