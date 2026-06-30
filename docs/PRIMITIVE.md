# The Design Loop as a Reusable Primitive

This bundle is a concrete instance of a **generic convergence loop**:

> propose → gate (hard lints) → critique (score) → evaluate (champion) →
> record (ledger) → render (artifacts) → repeat until DONE / ESCALATE / budget

The *design* specifics (HTML makers, WCAG/offline lints, an 8-dimension taste
rubric) are swappable. The control machinery — the maximin gate, the
append-only ledger, the two-artifact render, the fail-loud JSON contract — is
domain-agnostic and is the part worth reusing elsewhere.

## Bricks and studs

The studs are **JSON tool contracts** (`amplifier tool invoke <tool> --output json`),
not Python imports. `recipes/dlx.py` is the deterministic glue; the recipes
(`design-converge.yaml`, `design-pass.yaml`) are the wiring.

| Brick | Tool / seam | Contract (in → out) | Generic? |
|-------|-------------|---------------------|----------|
| Front door | `dlx classify_input` + normalize | source string → `{kind: html\|image\|url\|prompt}` + baseline | generic |
| Maker | `tool-target-state` | brief/baseline → candidate artifact | domain |
| Lints | `tool-design-lints` | artifact → `{hard_fail, reasons[]}` | domain |
| Critic | `design-critic` (agent) | artifact → 8-dim scorecard (int 0..4) | domain |
| Evaluate | `dlx extract` / `normscores` | raw tool output → validated scores (fail-loud) | generic |
| Gate | `tool-design-controller` | scores+history+budget → `PLAN\|DONE\|ESCALATE` (+reason) | generic |
| Ledger | `tool-design-ledger` | per-pass record → append-only run state | generic |
| Render | `tool-render-report.render(state)` | run state → `{upgraded.html, report.html}` | generic |

## The maximin gate (the heart of the primitive)

`tool-design-controller._gate` decides DONE only when **total ≥ bar AND every
dimension ≥ floor**. It escalates to a human on `floor_breach`, `plateau`
(no ≥ε gain across k passes), `regression_stuck`, or `budget_exhausted`.
F2 refinement: a sub-floor dimension keeps spending budget (PLAN) while the
run is still improving and the bar is met — it only escalates once genuinely
stalled. This is the reusable "converge or honestly stop" contract.

## To extract for a non-design pipeline

1. Keep `tool-design-controller` (gate), `tool-design-ledger` (ledger),
   `tool-render-report` (render), and the `dlx` glue (`extract`, `normscores`,
   `classify_input`, `designspec`, `render_two`).
2. Replace the three **domain** bricks: maker (`tool-target-state`), lints
   (`tool-design-lints`), critic (`design-critic`) with your domain's
   propose / hard-gate / score tools — keeping the same JSON shapes
   (scores = flat `{dim: int 0..4}`, lints = `{hard_fail, reasons[]}`).
3. Re-point the rubric/bar/floors in the APS (the authorize-aps approval gate).

The seam is the contract, not the code: any maker/critic that honors the JSON
shapes drops into the same loop. No package split is required — the boundaries
are named in `recipes/dlx.py` (BRICK MAP) and enforced by the tool contracts.
