# Working and verification

Use an isolated worktree when the main checkout contains unfinished work. Keep
bundle composition changes separate from app behavior. Install all six local
modules editable in the worktree's own venv so tests exercise the correct source.

Run `python -m pytest modules tests -q`; offline composition tests also require
`amplifier_foundation`. Browser QA requires Chromium and the app dependencies.
Always set `DESIGN_LOOP_DATA_DIR` to temporary storage for destructive history
checks. Wait for the new Working view before asserting a re-run's completion;
the previous Results DOM remains visible until the input-copy request finishes.

Do not label DRY or mocked CLI checks as paid-provider validation.
