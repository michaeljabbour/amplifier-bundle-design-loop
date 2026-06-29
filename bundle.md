---
bundle:
  name: design-loop
  version: 0.2.0
  description: "Design-quality harness — score any UI, build a better version, and (governed loop) converge it to a bar."

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-design-intelligence@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main

tools:
  # MVP measurement bricks
  - module: tool-render
    source: ./modules/tool-render
  - module: tool-target-state
    source: ./modules/tool-target-state
  - module: tool-render-report
    source: ./modules/tool-render-report
  # Harness deterministic bricks (no LLM)
  - module: tool-design-lints
    source: ./modules/tool-design-lints
  - module: tool-design-ledger
    source: ./modules/tool-design-ledger
  - module: tool-design-controller
    source: ./modules/tool-design-controller

agents:
  include:
    - design-loop:design-judge      # MVP: one-pass judge (scores + builds + reports)
    - design-loop:design-critic     # Harness: blind critic (scores only)
    - design-loop:design-maker      # Harness: rubric-blind maker (builds only)
    - design-loop:design-planner    # Harness: firewall/triage (reads the ledger)
---

# Design Loop

Two ways to use this bundle.

## 1. Judge on demand (MVP — proven)

**Delegate to `design-loop:design-judge`** with any UI artifact (HTML file, image, or
URL). It renders → scores the 8-criteria rubric → builds an improved version (real HTML
+ a screenshot of it) → returns a self-contained editorial report. One pass, then returns.

## 2. The governed harness (tier B — the convergence loop)

A deterministic controller wraps a judge ↔ maker loop where the actor that **scores**
and the actor that **makes** are separate, an append-only **ledger** is the memory, and
you set the bar once and are paged only on escalation. See
[`docs/HARNESS_DESIGN.md`](docs/HARNESS_DESIGN.md) and the diagrams in `docs/`.

Run it with the recipes tool:

```
recipes execute design-loop:recipes/design-converge.yaml
  context: { source: <path|url>, task_class: <name>, bar: 26, floors: 2, budget: 8, epsilon: 1, k: 3 }
```

The control path (lints gate · MACA accept/reject · stopping rules) is deterministic —
the tools `design_lints`, `design_controller`, and `design_ledger` decide; only the
critic, maker, and planner are model calls.

- **`design-critic`** scores the render only (frozen rubric; never sees the maker).
- **`design-maker`** applies a fix-batch → real HTML (never sees the rubric).
- **`design-planner`** reads the ledger → the worst-quality fix-batch (skips dead fixes).

## Division of labour

`design-intelligence` agents do the design work; this bundle adds the **measurement and
governance** layer (render → lints → score → decide → ledger → report).

---

@foundation:context/shared/common-system-base.md
