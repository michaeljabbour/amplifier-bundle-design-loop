---
bundle:
  name: design-loop
  version: 0.1.0
  description: "On-demand design-quality judge \u2014 score any UI artifact, build a target-state, and return an editorial report."

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-design-intelligence@main

tools:
  - module: tool-render
    source: ./modules/tool-render
  - module: tool-target-state
    source: ./modules/tool-target-state
  - module: tool-render-report
    source: ./modules/tool-render-report

agents:
  include:
    - design-loop:design-judge
---

# Design Loop

This bundle adds an on-demand design-quality judge on top of foundation and design-intelligence, both of which are included unchanged.

**Delegate to `design-loop:design-judge`** for critiquing, scoring, or improving a UI artifact (HTML file, image, or URL).

## What the judge does

1. **Renders** the artifact to a screenshot (via `tool-render`).
2. **Scores** the rendered output against the 8-criteria design rubric.
3. **Builds a target state** — a written spec (A) and optionally a reference screenshot (B) that shows what the artifact should become.
4. **Returns a self-contained editorial HTML report** plus a one-line verdict.

The judge runs **once and returns** — it does not enter a correction loop. If you want iterative improvements, call it again with the revised artifact.

## Division of labour

- `design-intelligence` agents handle the design work (component design, layout, motion, voice).
- This bundle adds the **measurement layer**: render → score → target-state → report.

---

@foundation:context/shared/common-system-base.md
