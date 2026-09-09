# Design-loop awareness

Use `design-loop:design-judge` for one pass: it renders the supplied source,
judges it, builds a target state, and reports that single pass. It does not
converge or retry.

Use `design-loop:recipes/design-converge.yaml` when a governed convergence run
is required. The recipe accepts `source` (HTML path, URL, image path, or prompt)
and an optional `brief`; it has no `target` parameter. Candidate target HTML,
screenshots, and reports are recipe outputs under `work_dir`, not claims the
caller or an agent may invent.

For example, invoke the governed recipe with its actual schema:

```yaml
recipe_path: design-loop:recipes/design-converge.yaml
context:
  source: /absolute/path/to/landing.html
  brief: Make the call to action easier to find.
  task_class: landing_page
  signature: landing-v1
  run_id: landing-v1-r1
  rubric_version: design-critic-sha
  bar: 24
  floors: 2
  budget: 12
  epsilon: 1
  k: 3
  tau: 0
  output: all
  work_dir: /tmp/design-loop/landing-v1-r1
  bundle_ref: design-loop
```

The critic independently judges rendered evidence; the planner proposes
bounded work; the maker creates candidates. Keep those roles separate: no
self-grading, fabricated verdicts, or fabricated after-images.