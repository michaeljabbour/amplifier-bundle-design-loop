# amplifier-bundle-design-loop

An Amplifier bundle providing an on-demand **design-judge** agent and three supporting tools for AI-driven UI design critique and iteration.

## What it does

Delegate to `design-loop:design-judge` with any UI artifact — raw HTML, a URL, or an image — and the judge will:

1. **Score** the rendered design against an 8-criteria rubric. Each criterion is scored 0–4 (0 = absent or harmful, 4 = exemplary); the total ranges from 0–32:

   | Criterion | What it measures |
   |-----------|-----------------|
   | **clarity** | Hierarchy, purpose, and information scannability obvious to a first-time visitor |
   | **elegance** | Visual language feels refined and intentional rather than assembled from defaults |
   | **restraint** | Actively resists slop defaults (purple→blue gradients, heavy shadows, generic hero, Inter by default, equal-weight card grids) |
   | **empowerment** | User feels capable, informed, and in control |
   | **agency** | Affordances are clear; user immediately knows what they can do |
   | **ease** | Cognitive load is low; primary path to action is obvious |
   | **character** | Distinctive, memorable personality that sets it apart |
   | **point** | Clear, singular focus; design knows what it exists to accomplish |

2. **Build a target state** — improved HTML (document A) plus a reference screenshot (image B). B is always a Playwright render of A; it is never an image-generation dream. If the render fails, the tool returns `"unavailable"` rather than fabricating a result.

3. **Return** a self-contained editorial HTML report (no external HTTP/HTTPS resources, no `<script>` tags) plus a one-line verdict summary.

The judge runs **once and returns**. It does not enter a correction loop.

## Architecture

| Brick | Type | Responsibility |
|-------|------|----------------|
| `tool-render` | Tool | Renders HTML files, URLs, or passes images through; errors are surfaced as ToolResult failures, never crashes |
| `tool-render-report` | Tool | Assembles a self-contained HTML report from scores + images; handles `scores_unavailable` honestly |
| `tool-target-state` | Tool | Writes improved HTML (A), renders it to a screenshot (B), returns `"unavailable"` on any failure |
| `design-judge` | Agent (`model_role: vision`) | Orchestrates the render → score → target-state → report flow exactly once; carries the full 8-criteria rubric as a context sink |

The bundle is thin: it includes `amplifier-foundation` and `amplifier-bundle-design-intelligence` unchanged and adds only the measurement layer (render → score → target-state → report).

## Use it

```bash
# Register the bundle from the local checkout
amplifier bundle add ./bundle.md

# Run the judge on the sample slop fixture
amplifier run --bundle design-loop 'Judge fixtures/slop.html and show me a better version'
```

The judge accepts `kind: html`, `kind: url`, or `kind: image`. Pass a file path, a URL, or raw HTML in the prompt.

## Develop

See **[docs/DEV_SETUP.md](docs/DEV_SETUP.md)** for the full environment guide. Quick summary:

```bash
# 1 — create the repo-root virtualenv
uv venv
source .venv/bin/activate

# 2 — install runtime and test dependencies
uv pip install amplifier-core pytest pytest-asyncio playwright

# 3 — install Chromium (required by tool-render)
python -m playwright install chromium

# 4 — install the three tool modules editable
uv pip install -e ./modules/tool-render \
               -e ./modules/tool-render-report \
               -e ./modules/tool-target-state

# 5 — run the deterministic suite (unit tests pass; integration skipped)
python -m pytest modules tests -v

# 6 — run manual integration tests (requires a configured provider API key)
RUN_MANUAL=1 python -m pytest tests/integration -m manual -v -s
```

The integration tests are gated behind `RUN_MANUAL=1` so `pytest` never runs them in CI.

## Scope (MVP)

**Implemented**: judge-on-demand — one delegate call, one HTML report, one VERDICT.

**Deferred (future shapes)**:
- `tool:post` hook that auto-judges every file write
- Recipe-based convergence loop (judge → revise → re-judge until score threshold)
- Attractor DOT pipeline (visualize design quality over iterations)
- Deterministic slop detector integration (44-rule detector as a pre-filter)
- Image-generation dream target state (generate an aspirational image, not just a render of improved HTML)
- Auto-retry on low scores within a single session

**Eventual remote**: [github.com/michaeljabbour/amplifier-bundle-design-loop](https://github.com/michaeljabbour/amplifier-bundle-design-loop)
