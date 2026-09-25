# Design loop

- One pass (score + improved version + report): delegate to `design-loop:design-judge`.
- Governed convergence to a bar: run recipe `design-loop:recipes/design-converge.yaml`
  with context `source` (HTML path, URL, image path, or prompt), optional `brief`,
  and an absolute `work_dir`; other keys (bar, floors, budget, ...) have defaults
  documented in the recipe's `context:` block. There is no `target` parameter.
- Target HTML, screenshots, verdicts, and reports come only from the recipe or judge
  outputs; never invent them or grade your own work.
