# Design-Loop Bundle Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.
> Work top-to-bottom. Each task is one TDD cycle (write failing test → run-fail → minimal
> impl → run-pass → commit). Do not skip the run-fail step. Commit after every task.

**Goal:** Ship `amplifier-bundle-design-loop` — a thin Amplifier bundle whose `design-judge`
agent takes any UI artifact (HTML / image / URL), scores it against an 8-criteria rubric,
builds a target-state (improved code A + a screenshot of that code B), and returns it all as a
self-contained "worth"-style editorial HTML report.

**Architecture:** Three deterministic tool "bricks" (`tool-render`, `tool-target-state`,
`tool-render-report`) connected by JSON contracts, orchestrated by one `design-judge` agent
(the thing you `delegate()` to). The agent is the only model touchpoint: it vision-scores the
screenshot and writes the improved HTML; the tools deterministically render, persist, and
present. A thin `bundle.md` wires the three tools + the agent on top of `foundation` and
`design-intelligence` (both included unchanged).

**Tech Stack:** Python ≥3.11 · Playwright (Chromium, headless) · pytest + pytest-asyncio ·
hatchling build backend · Amplifier module/bundle conventions.

---

## Ground Rules (read once, apply everywhere)

These are verified against the real `amplifier-core` Tool contract and the canonical
`amplifier-bundle-recipes` module — they are NOT guesses. Follow them exactly.

1. **Tool protocol.** Each tool class exposes three `@property` members — `name` (snake_case),
   `description` (str), `input_schema` (JSON-schema dict) — and one coroutine
   `async def execute(self, input: dict[str, Any]) -> ToolResult`. The parameter is literally
   named `input` and is a dict.
2. **Result type.** Return `ToolResult(success=..., output=..., error=...)`.
   - `from amplifier_core import ToolResult` (and `ModuleCoordinator` for typing).
   - Success: `ToolResult(success=True, output=<dict>)`.
   - Failure: `ToolResult(success=False, error={"message": "...", "type": "..."})`. **Never crash.**
3. **mount() contract — the Iron Law.** Every module's `mount()` MUST call
   `await coordinator.mount("tools", tool, name=tool.name)` and then `return tool`. A `mount()`
   that logs and returns `None` fails with `protocol_compliance: No tool was mounted`.
4. **No `amplifier-core` in module runtime deps.** It is a *peer dependency*, provided by the
   host (and by our dev `.venv`). Declaring it in `[project].dependencies` breaks installs.
5. **Bundle/YAML rules.** Namespace = `bundle.name` (`design-loop`), never the repo name.
   Never use the `@` prefix inside YAML sections. Keep any `context.include` light (<~1k tokens);
   the heavy rubric lives in the `design-judge` agent body (context-sink pattern).
6. **Honesty spine.** B is always a render of A (never an image-gen dream). The judge always
   returns a verdict. Missing data is surfaced as `N/A — <reason>`, never fabricated.
7. **Commits.** Conventional-commit messages (`feat:` / `test:` / `chore:` / `docs:`). Small and
   frequent. **Do NOT** run `git push`, `gh pr create`, or `git merge` — those belong to `/finish`.
8. **Eventual remote (informational only):** `github.com/michaeljabbour/amplifier-bundle-design-loop`.
   Do not create or push it in this plan.

---

## Scope Boundaries

**In scope (v1 = judge-on-demand):** the three tool bricks, the `design-judge` agent, the thin
`bundle.md`, two fixtures, and two integration tests.

**Out of scope — DO NOT build (these are future shapes that reuse these same bricks unchanged):**
- ❌ Hook (`tool:post`) shape
- ❌ Recipe convergence / `while` loop
- ❌ Attractor DOT pipeline
- ❌ Deterministic impeccable-style detector
- ❌ Independent image-gen "dream" mockup for B
- ❌ Any auto-retry / convergence. **The judge runs once and returns.**

---

## Final Repository Layout (what you will have built)

```
~/dev/amplifier-bundle-design-loop/
├── .gitignore
├── README.md
├── pyproject.toml                       # root: pytest config only (NOT a package)
├── bundle.md                            # thin bundle: name=design-loop
├── agents/
│   └── design-judge.md                  # the agent you delegate to (model_role: vision)
├── fixtures/
│   ├── slop.html                        # dark, Roboto, purple gradient
│   └── excellent.html                   # clean editorial
├── modules/
│   ├── tool-render/
│   │   ├── pyproject.toml
│   │   ├── amplifier_module_tool_render/
│   │   │   ├── __init__.py              # RenderTool + mount()
│   │   │   └── render.py               # pure async render helper
│   │   └── tests/
│   │       ├── test_render.py
│   │       ├── test_render_tool.py
│   │       └── test_mount.py
│   ├── tool-target-state/
│   │   ├── pyproject.toml
│   │   ├── amplifier_module_tool_target_state/
│   │   │   └── __init__.py              # TargetStateTool + mount()
│   │   └── tests/
│   │       ├── test_orchestration.py
│   │       └── test_mount.py
│   └── tool-render-report/
│       ├── pyproject.toml
│       ├── amplifier_module_tool_render_report/
│       │   ├── __init__.py              # RenderReportTool + mount()
│       │   ├── verdict.py              # parse_verdict() deterministic helper
│       │   └── template.py            # render_report() deterministic template
│       └── tests/
│           ├── test_verdict.py
│           ├── test_template.py
│           └── test_mount.py
├── tests/
│   ├── test_sanity.py                   # scaffold baseline
│   ├── test_bundle_structure.py         # parses bundle.md frontmatter
│   ├── test_agent_structure.py          # parses agents/design-judge.md
│   └── integration/
│       ├── test_golden_slop.py          # @manual — hits a real provider
│       └── test_excellent_page.py       # @manual — hits a real provider
└── docs/plans/
    └── 2026-06-29-design-loop-implementation.md   # this file
```

---

## JSON Contracts (the studs between bricks)

```
INPUT  : { "source": "<path|url>", "kind": "html" | "url" | "image" }
           │  tool-render  (skipped when kind == "image")
SHOT   : { "screenshot_path": "<png path>" }
           │  design-judge (vision) — scores against rubric
VERDICT: { "scores": { clarity, elegance, restraint, empowerment,
                       agency, ease, character, point },   # each 0–4 int
           "total": <0–32>,                                 # == sum(scores)
           "fixes": [ { "criterion", "issue", "fix" } ] }   # prioritized, may be []
           │  tool-target-state (agent supplies improved_html) → writes A → tool-render → B
TARGET : { "target_html_path": "<A>", "target_screenshot_path": "<B>" }
           │  tool-render-report (deterministic template)
REPORT : { "report_html_path": "<path>" }
           │  design-judge returns
RESULT : { "report_html_path": "<path>", "total": <int>, "top_fixes": [ ...up to 3 ] }
```

**The 8 criteria (each scored 0–4, total 0–32):**
`clarity`, `elegance`, `restraint`, `empowerment`, `agency`, `ease`, `character`, `point`.

---

# Tasks

> Every code block below is complete and copy-pasteable. Run commands from the repo root
> (`~/dev/amplifier-bundle-design-loop`) with the dev `.venv` activated (after Task 2).

---

## Task 1: Repo scaffold + clean green baseline

**Files:**
- Create: `~/dev/amplifier-bundle-design-loop/.gitignore`
- Create: `~/dev/amplifier-bundle-design-loop/pyproject.toml`
- Create: `~/dev/amplifier-bundle-design-loop/README.md`
- Create: `~/dev/amplifier-bundle-design-loop/tests/test_sanity.py`

**Step 1: Initialize the repo and directory tree**

Run:
```bash
cd ~/dev/amplifier-bundle-design-loop
git init
mkdir -p agents fixtures tests/integration \
  modules/tool-render/amplifier_module_tool_render modules/tool-render/tests \
  modules/tool-target-state/amplifier_module_tool_target_state modules/tool-target-state/tests \
  modules/tool-render-report/amplifier_module_tool_render_report modules/tool-render-report/tests
```
Expected: no output, exit code 0. `docs/plans/` already exists (this file lives there).

**Step 2: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.venv/
venv/

# Build
dist/
build/

# Generated artifacts (screenshots, reports)
*.png
*.jpg
*.jpeg
*.webp
/tmp_output/
fixtures/*.png

# OS
.DS_Store
```

**Step 3: Write root `pyproject.toml` (pytest config only — this repo is NOT a package)**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "manual: integration tests that hit a real provider; run explicitly, not in CI",
]
```

**Step 4: Write `README.md` (stub — expanded in Task 17)**

```markdown
# amplifier-bundle-design-loop

On-demand design-quality judge for Amplifier. Delegate to the `design-judge` agent with any UI
artifact (HTML file, image, or URL); it scores the design against an 8-criteria rubric, builds a
target-state (improved code + a screenshot of that code), and returns a self-contained editorial
HTML report.

Status: MVP (judge-on-demand). See `docs/plans/` for the design and implementation plan.
```

**Step 5: Write the baseline test `tests/test_sanity.py`**

```python
"""Scaffold baseline: proves the repo layout exists and pytest runs green."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_repo_scaffold_exists():
    for rel in [
        "agents",
        "fixtures",
        "modules/tool-render/amplifier_module_tool_render",
        "modules/tool-target-state/amplifier_module_tool_target_state",
        "modules/tool-render-report/amplifier_module_tool_render_report",
        "tests/integration",
    ]:
        assert (REPO / rel).is_dir(), f"missing directory: {rel}"
```

**Step 6: Verify the file parses (the venv lands in Task 2; run the green check there)**

Run: `python3 -c "import ast; ast.parse(open('tests/test_sanity.py').read()); print('ok')"`
Expected: `ok`

**Step 7: Commit**
```bash
git add -A
git commit -m "chore: scaffold design-loop bundle repo with green baseline test"
```

---

## Task 2: Provision the dev environment (Playwright + Chromium + amplifier-core)

This is an infrastructure task (no TDD cycle). It makes every later test runnable.

**Step 1: Create and activate a single repo-root virtualenv**

Run:
```bash
cd ~/dev/amplifier-bundle-design-loop
uv venv
source .venv/bin/activate
```
Expected: `.venv` created; prompt shows `(.venv)` or similar.

**Step 2: Install test + runtime dependencies**

Run:
```bash
uv pip install amplifier-core pytest pytest-asyncio playwright
```
Expected: all four resolve and install. `amplifier-core` installs a pre-built wheel from PyPI
(no Rust toolchain needed).

> Fallback only if the PyPI version is incompatible:
> `uv pip install "amplifier-core @ git+https://github.com/microsoft/amplifier-core" pytest pytest-asyncio playwright`

**Step 3: Install the Chromium browser binary Playwright drives**

Run:
```bash
python -m playwright install chromium
```
Expected: downloads Chromium; ends with a success line. This is required for `tool-render`'s
real-render tests — they are deliberately not mocked.

**Step 4: Verify the toolchain**

Run:
```bash
python -c "from amplifier_core import ToolResult; from amplifier_core.testing import create_test_coordinator; from playwright.async_api import async_playwright; print('env ok')"
```
Expected: `env ok`

**Step 5: Run the baseline test green**

Run: `python -m pytest tests/test_sanity.py -v`
Expected: `1 passed`.

**Step 6: Capture the provisioning requirement in the repo**

Create: `docs/DEV_SETUP.md`
```markdown
# Dev setup

```bash
uv venv && source .venv/bin/activate
uv pip install amplifier-core pytest pytest-asyncio playwright
python -m playwright install chromium     # one-time: installs the Chromium binary
python -m pytest                          # run all unit tests
```

`amplifier-core` is a peer dependency provided by the host runtime; it is installed here only so
the unit tests can import `ToolResult` and `create_test_coordinator`. It is intentionally absent
from each module's `pyproject.toml` runtime dependencies.
```
```bash
git add -A
git commit -m "chore: document dev environment provisioning (playwright chromium + amplifier-core peer dep)"
```

---

## Task 3: Fixtures (golden slop + excellent page)

**Files:**
- Create: `fixtures/slop.html`
- Create: `fixtures/excellent.html`

No test of its own — these feed the render tests and the two integration tests.

**Step 1: Write `fixtures/slop.html` (intentionally bad: dark, Roboto, purple gradient)**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Synergize</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Roboto, "Helvetica Neue", Arial, sans-serif;
      background: linear-gradient(135deg, #7b2ff7 0%, #2a6cf6 100%);
      color: #e0e0e0;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
    }
    .hero { padding: 40px; }
    h1 { font-size: 56px; font-weight: 700; margin: 0 0 16px; color: #ffffff; }
    p  { font-size: 18px; opacity: 0.8; }
    .btn {
      margin-top: 24px; padding: 14px 28px; border: none; border-radius: 999px;
      background: linear-gradient(90deg, #7b2ff7, #2a6cf6); color: #fff; font-size: 16px;
    }
  </style>
</head>
<body>
  <div class="hero">
    <h1>Synergize Your Workflow</h1>
    <p>The all-in-one platform that leverages AI to unlock your potential.</p>
    <button class="btn">Get Started Now</button>
  </div>
</body>
</html>
```

**Step 2: Write `fixtures/excellent.html` (clean editorial: light, serif display, restrained)**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Field Notes</title>
  <style>
    :root { --ink: #1f1d1a; --muted: #6b665e; --paper: #faf8f4; --accent: #8a5a2b; }
    * { box-sizing: border-box; }
    body {
      margin: 0; background: var(--paper); color: var(--ink);
      font-family: Georgia, "Times New Roman", serif; line-height: 1.55;
    }
    .wrap { max-width: 680px; margin: 0 auto; padding: 96px 24px; }
    .eyebrow { font-family: Verdana, sans-serif; font-size: 12px; letter-spacing: .18em;
      text-transform: uppercase; color: var(--accent); margin-bottom: 20px; }
    h1 { font-size: 44px; line-height: 1.1; margin: 0 0 20px; font-weight: 600; }
    p  { font-size: 18px; color: var(--muted); margin: 0 0 16px; }
    a.cta { display: inline-block; margin-top: 16px; color: var(--ink);
      border-bottom: 2px solid var(--accent); text-decoration: none; padding-bottom: 2px; }
  </style>
</head>
<body>
  <main class="wrap">
    <div class="eyebrow">Field Notes</div>
    <h1>A quiet place to keep what you notice.</h1>
    <p>Write down the small observations that would otherwise slip away. No accounts, no clutter —
       just a page and a cursor.</p>
    <p>Your notes stay on your device. Export them whenever you like.</p>
    <a class="cta" href="#">Start a notebook →</a>
  </main>
</body>
</html>
```

**Step 3: Commit**
```bash
git add -A
git commit -m "test: add slop and excellent HTML fixtures for render + integration tests"
```

---

## Task 4: `tool-render` — pure async render helper (TDD)

**Files:**
- Create: `modules/tool-render/pyproject.toml`
- Create: `modules/tool-render/amplifier_module_tool_render/__init__.py` (empty for now)
- Create: `modules/tool-render/amplifier_module_tool_render/render.py`
- Test: `modules/tool-render/tests/test_render.py`

**Step 1: Write the module `pyproject.toml`** (Chromium driver is the only runtime dep)

```toml
[project]
name = "amplifier-module-tool-render"
version = "0.1.0"
description = "Render any UI artifact (HTML/URL/image) to a screenshot PNG"
requires-python = ">=3.11"
dependencies = [
    "playwright>=1.40",
]

[project.entry-points."amplifier.modules"]
tool-render = "amplifier_module_tool_render:mount"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["amplifier_module_tool_render"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create an empty package init so imports resolve** (real `mount()` lands in Task 6)

Create `modules/tool-render/amplifier_module_tool_render/__init__.py`:
```python
"""tool-render: normalize any UI artifact to a screenshot PNG."""
```

**Step 3: Install this module editable into the shared venv**

Run: `uv pip install -e ./modules/tool-render`
Expected: installs `amplifier-module-tool-render` (editable). Imports now resolve.

**Step 4: Write the failing test `modules/tool-render/tests/test_render.py`**

```python
"""Pure render helper: a fixture HTML file becomes a non-empty PNG."""
from pathlib import Path

import pytest

from amplifier_module_tool_render.render import render_to_png

REPO = Path(__file__).resolve().parents[3]
SLOP = REPO / "fixtures" / "slop.html"


async def test_render_html_file_produces_nonempty_png(tmp_path):
    out = tmp_path / "shot.png"
    url = SLOP.resolve().as_uri()  # file:///.../fixtures/slop.html
    result = await render_to_png(url, out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


async def test_render_bad_url_raises(tmp_path):
    out = tmp_path / "shot.png"
    with pytest.raises(Exception):
        await render_to_png("file:///definitely/not/here-12345.html", out)
```

**Step 5: Run the test to verify it fails**

Run: `python -m pytest modules/tool-render/tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'amplifier_module_tool_render.render'`.

**Step 6: Write the minimal implementation `modules/tool-render/amplifier_module_tool_render/render.py`**

```python
"""Deterministic headless-Chromium rendering. No model involved."""
from pathlib import Path

from playwright.async_api import async_playwright

_VIEWPORT = {"width": 1280, "height": 800}


async def render_to_png(url: str, out_path: Path) -> Path:
    """Render a URL (http(s):// or file://) to a full-page PNG at ``out_path``.

    Raises on navigation/render failure so callers can convert it to a ToolResult error.
    """
    out_path = Path(out_path)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page(viewport=_VIEWPORT)
            response = await page.goto(url, wait_until="load")
            # file:// navigations return None for response; treat a hard failure as an error.
            if response is not None and not response.ok:
                raise RuntimeError(f"navigation failed ({response.status}) for {url}")
            await page.screenshot(path=str(out_path), full_page=True)
        finally:
            await browser.close()
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise RuntimeError(f"screenshot not produced for {url}")
    return out_path
```

> Note: a missing `file://` path makes Chromium fail to load; `page.goto` raises, satisfying the
> bad-URL test. We also guard with the size check.

**Step 7: Run the test to verify it passes**

Run: `python -m pytest modules/tool-render/tests/test_render.py -v`
Expected: `2 passed`.

**Step 8: Commit**
```bash
git add -A
git commit -m "feat(tool-render): deterministic async render_to_png helper with TDD"
```

---

## Task 5: `tool-render` — `RenderTool.execute` (kind detection + passthrough + errors) (TDD)

**Files:**
- Modify: `modules/tool-render/amplifier_module_tool_render/__init__.py`
- Test: `modules/tool-render/tests/test_render_tool.py`

**Step 1: Write the failing test `modules/tool-render/tests/test_render_tool.py`**

```python
"""RenderTool.execute: html→render, image→passthrough, bad input→error (no crash)."""
from pathlib import Path

from amplifier_module_tool_render import RenderTool

REPO = Path(__file__).resolve().parents[3]
SLOP = REPO / "fixtures" / "slop.html"


async def test_html_input_renders(tmp_path):
    tool = RenderTool()
    out = tmp_path / "a.png"
    res = await tool.execute({"source": str(SLOP), "kind": "html", "out_path": str(out)})
    assert res.success
    assert Path(res.output["screenshot_path"]).exists()
    assert Path(res.output["screenshot_path"]).stat().st_size > 0


async def test_kind_autodetected_from_extension(tmp_path):
    tool = RenderTool()
    out = tmp_path / "b.png"
    # no "kind" provided -> .html extension auto-detects as html
    res = await tool.execute({"source": str(SLOP), "out_path": str(out)})
    assert res.success


async def test_image_input_passes_through(tmp_path):
    # An existing PNG is returned unchanged (no render).
    img = tmp_path / "already.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n fake-but-nonempty")
    tool = RenderTool()
    res = await tool.execute({"source": str(img), "kind": "image"})
    assert res.success
    assert res.output["screenshot_path"] == str(img)


async def test_missing_source_is_error_not_crash():
    tool = RenderTool()
    res = await tool.execute({})
    assert res.success is False
    assert "source" in res.error["message"].lower()


async def test_image_passthrough_missing_file_is_error(tmp_path):
    tool = RenderTool()
    res = await tool.execute({"source": str(tmp_path / "nope.png"), "kind": "image"})
    assert res.success is False
    assert res.error is not None
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest modules/tool-render/tests/test_render_tool.py -v`
Expected: FAIL — `ImportError: cannot import name 'RenderTool'`.

**Step 3: Write the implementation in `modules/tool-render/amplifier_module_tool_render/__init__.py`**

```python
"""tool-render: normalize any UI artifact (HTML / URL / image) to a screenshot PNG."""
import logging
import tempfile
from pathlib import Path
from typing import Any

from amplifier_core import ModuleCoordinator
from amplifier_core import ToolResult

from .render import render_to_png

logger = logging.getLogger(__name__)

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _detect_kind(source: str) -> str:
    low = source.lower()
    if low.startswith(("http://", "https://")):
        return "url"
    if Path(source).suffix.lower() in _IMAGE_EXTS:
        return "image"
    return "html"


class RenderTool:
    """Deterministic renderer. HTML/URL → screenshot; image → passthrough."""

    @property
    def name(self) -> str:
        return "render"

    @property
    def description(self) -> str:
        return (
            "Render a UI artifact to a screenshot PNG. Input: {source, kind?}. "
            "kind 'html' renders a local HTML file, 'url' renders a web page, "
            "'image' passes an existing image through unchanged. "
            "Returns {screenshot_path}. On failure returns an error (never crashes)."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Path or URL to the artifact."},
                "kind": {
                    "type": "string",
                    "enum": ["html", "url", "image"],
                    "description": "Artifact kind. Auto-detected from source if omitted.",
                },
                "out_path": {
                    "type": "string",
                    "description": "Optional output PNG path. A temp file is used if omitted.",
                },
            },
            "required": ["source"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        source = input.get("source")
        if not source:
            return ToolResult(success=False, error={"message": "source is required"})

        kind = input.get("kind") or _detect_kind(source)

        try:
            if kind == "image":
                p = Path(source).expanduser()
                if not p.exists() or p.stat().st_size == 0:
                    return ToolResult(
                        success=False,
                        error={"message": f"image not found or empty: {source}"},
                    )
                return ToolResult(success=True, output={"screenshot_path": str(p)})

            # html or url -> render
            out_path = input.get("out_path")
            if out_path:
                out = Path(out_path).expanduser()
            else:
                fd, tmp = tempfile.mkstemp(suffix=".png")
                Path(tmp).unlink(missing_ok=True)  # we only wanted the name
                out = Path(tmp)

            if kind == "url":
                target = source
            else:  # html
                html_path = Path(source).expanduser().resolve()
                if not html_path.exists():
                    return ToolResult(
                        success=False, error={"message": f"html file not found: {source}"}
                    )
                target = html_path.as_uri()

            shot = await render_to_png(target, out)
            return ToolResult(success=True, output={"screenshot_path": str(shot)})

        except Exception as e:
            logger.error("render failed: %s", e, exc_info=True)
            return ToolResult(
                success=False, error={"message": str(e), "type": type(e).__name__}
            )


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    """Placeholder mount — real registration is implemented and tested in Task 6."""
    raise NotImplementedError("mount implemented in Task 6")
```

**Step 4: Run the test to verify it passes**

Run: `python -m pytest modules/tool-render/tests/test_render_tool.py -v`
Expected: `5 passed`.

**Step 5: Commit**
```bash
git add -A
git commit -m "feat(tool-render): RenderTool.execute with kind detection, image passthrough, error handling"
```

---

## Task 6: `tool-render` — `mount()` registers the tool (TDD)

**Files:**
- Modify: `modules/tool-render/amplifier_module_tool_render/__init__.py` (replace the placeholder mount)
- Test: `modules/tool-render/tests/test_mount.py`

**Step 1: Write the failing test `modules/tool-render/tests/test_mount.py`**

```python
"""mount() must register the tool on the coordinator and return it."""
from amplifier_core.testing import create_test_coordinator

from amplifier_module_tool_render import RenderTool, mount


async def test_mount_registers_render_tool():
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {})
    assert isinstance(returned, RenderTool)
    assert coordinator.mount_points["tools"]["render"] is returned
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest modules/tool-render/tests/test_mount.py -v`
Expected: FAIL — `NotImplementedError: mount implemented in Task 6`.

**Step 3: Replace the placeholder `mount()` at the bottom of `__init__.py`**

Replace the placeholder function with:
```python
async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    """Register the render tool. Iron Law: must call coordinator.mount and return the tool."""
    tool = RenderTool()
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("Mounted tool-render")
    return tool
```

**Step 4: Run the test to verify it passes**

Run: `python -m pytest modules/tool-render/tests -v`
Expected: all `tool-render` tests pass (render + tool + mount).

**Step 5: Commit**
```bash
git add -A
git commit -m "feat(tool-render): mount() registers render tool per amplifier-core contract"
```

---

## Task 7: `tool-render-report` — `parse_verdict()` deterministic helper (TDD)

**Files:**
- Create: `modules/tool-render-report/pyproject.toml`
- Create: `modules/tool-render-report/amplifier_module_tool_render_report/__init__.py` (empty for now)
- Create: `modules/tool-render-report/amplifier_module_tool_render_report/verdict.py`
- Test: `modules/tool-render-report/tests/test_verdict.py`

**Step 1: Write the module `pyproject.toml`** (no external runtime deps)

```toml
[project]
name = "amplifier-module-tool-render-report"
version = "0.1.0"
description = "Render a design verdict + target-state into a self-contained editorial HTML report"
requires-python = ">=3.11"
dependencies = []

[project.entry-points."amplifier.modules"]
tool-render-report = "amplifier_module_tool_render_report:mount"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["amplifier_module_tool_render_report"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Create empty package init**

Create `modules/tool-render-report/amplifier_module_tool_render_report/__init__.py`:
```python
"""tool-render-report: turn a verdict + target-state into an editorial HTML report."""
```

**Step 3: Install editable**

Run: `uv pip install -e ./modules/tool-render-report`
Expected: installs editable.

**Step 4: Write the failing test `modules/tool-render-report/tests/test_verdict.py`**

```python
"""Deterministic verdict parsing/validation. 8 scores in 0-4; total == sum."""
import json

from amplifier_module_tool_render_report.verdict import CRITERIA, parse_verdict


def _good_scores():
    return {c: (i % 5) for i, c in enumerate(CRITERIA)}  # values 0..4 cycling


def test_parse_valid_dict():
    scores = _good_scores()
    obj = {"scores": scores, "total": sum(scores.values()), "fixes": []}
    out = parse_verdict(obj)
    assert out["valid"] is True
    assert out["verdict"]["total"] == sum(scores.values())
    assert set(out["verdict"]["scores"]) == set(CRITERIA)


def test_total_is_repaired_when_wrong():
    scores = _good_scores()
    obj = {"scores": scores, "total": 999, "fixes": []}  # wrong total
    out = parse_verdict(obj)
    assert out["valid"] is True
    assert out["verdict"]["total"] == sum(scores.values())  # recomputed, not trusted


def test_parse_valid_json_string_with_fences():
    scores = _good_scores()
    raw = "```json\n" + json.dumps({"scores": scores, "total": sum(scores.values())}) + "\n```"
    out = parse_verdict(raw)
    assert out["valid"] is True
    assert out["verdict"]["fixes"] == []  # defaults to empty list


def test_missing_criterion_flags_unavailable():
    scores = _good_scores()
    del scores["clarity"]
    out = parse_verdict({"scores": scores, "total": 10})
    assert out["valid"] is False
    assert out["scores_unavailable"] is True


def test_out_of_range_score_flags_unavailable():
    scores = _good_scores()
    scores["point"] = 7  # > 4
    out = parse_verdict({"scores": scores})
    assert out["valid"] is False
    assert out["scores_unavailable"] is True


def test_garbage_string_flags_unavailable():
    out = parse_verdict("not json at all")
    assert out["valid"] is False
    assert out["scores_unavailable"] is True
    assert "raw" in out
```

**Step 5: Run the test to verify it fails**

Run: `python -m pytest modules/tool-render-report/tests/test_verdict.py -v`
Expected: FAIL — `ModuleNotFoundError: ...verdict`.

**Step 6: Write `modules/tool-render-report/amplifier_module_tool_render_report/verdict.py`**

```python
"""Deterministic verdict validation.

This is the *deterministic* half of the design's "one reparse retry then flag" rule. The LLM
retry lives in the design-judge agent body; this function never invents numbers. It validates
that the 8 scores are present and in 0..4, recomputes the total from the scores (never trusting a
supplied total), and otherwise flags scores_unavailable.
"""
import json
import re
from typing import Any

CRITERIA = (
    "clarity",
    "elegance",
    "restraint",
    "empowerment",
    "agency",
    "ease",
    "character",
    "point",
)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _coerce_to_dict(obj: Any) -> dict | None:
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        text = obj.strip()
        m = _FENCE.search(text)
        if m:
            text = m.group(1).strip()
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def parse_verdict(obj: Any) -> dict:
    """Return {valid: True, verdict: {...}} or {valid: False, scores_unavailable: True, raw}."""
    data = _coerce_to_dict(obj)
    if data is None:
        return {"valid": False, "scores_unavailable": True, "raw": str(obj)}

    scores = data.get("scores")
    if not isinstance(scores, dict):
        return {"valid": False, "scores_unavailable": True, "raw": str(obj)}

    clean: dict[str, int] = {}
    for c in CRITERIA:
        v = scores.get(c)
        if not isinstance(v, int) or isinstance(v, bool) or not (0 <= v <= 4):
            return {"valid": False, "scores_unavailable": True, "raw": str(obj)}
        clean[c] = v

    fixes = data.get("fixes")
    if not isinstance(fixes, list):
        fixes = []

    return {
        "valid": True,
        "verdict": {"scores": clean, "total": sum(clean.values()), "fixes": fixes},
    }
```

**Step 7: Run the test to verify it passes**

Run: `python -m pytest modules/tool-render-report/tests/test_verdict.py -v`
Expected: `6 passed`.

**Step 8: Commit**
```bash
git add -A
git commit -m "feat(tool-render-report): deterministic parse_verdict() with TDD (validate + repair total)"
```

---

## Task 8: `tool-render-report` — editorial template + dogfood assertions (TDD)

**Files:**
- Create: `modules/tool-render-report/amplifier_module_tool_render_report/template.py`
- Test: `modules/tool-render-report/tests/test_template.py`

**Step 1: Write the failing test `modules/tool-render-report/tests/test_template.py`**

```python
"""render_report(): self-contained editorial HTML. The slop-judge cannot emit slop."""
import base64

from amplifier_module_tool_render_report.template import render_report
from amplifier_module_tool_render_report.verdict import CRITERIA


def _verdict(total=12):
    scores = {c: (1 if i % 2 == 0 else 2) for i, c in enumerate(CRITERIA)}
    return {
        "scores": scores,
        "total": total,
        "fixes": [
            {"criterion": "restraint", "issue": "purple gradient", "fix": "use a flat surface"},
            {"criterion": "character", "issue": "generic sans", "fix": "use a serif display face"},
        ],
    }


def test_report_is_self_contained_and_shows_scores():
    html = render_report(_verdict(), target_html="<h1>A</h1>",
                         target_screenshot_b64=base64.b64encode(b"PNGDATA").decode())
    assert html.lstrip().lower().startswith("<!doctype html")
    # every criterion appears
    for c in CRITERIA:
        assert c in html
    assert "12 / 32" in html or "12/32" in html
    # target-state present as embedded data URI (B) + escaped code (A)
    assert "data:image/png;base64," in html
    assert "&lt;h1&gt;A&lt;/h1&gt;" in html  # A is HTML-escaped, not executed


def test_report_handles_target_unavailable():
    html = render_report(_verdict(), target_html=None, target_screenshot_b64=None)
    assert "target-state unavailable" in html.lower()
    assert "data:image/png;base64," not in html


def test_dogfood_no_slop_markers():
    html = render_report(_verdict(), target_html="<h1>A</h1>",
                         target_screenshot_b64=base64.b64encode(b"PNGDATA").decode())
    low = html.lower()
    # honesty spine: the report that judges slop must not BE slop
    assert "linear-gradient" not in low
    assert "radial-gradient" not in low
    assert "'inter'" not in low and '"inter"' not in low      # no Inter font
    assert "cormorant garamond" in low                         # editorial display face present
    assert "http://" not in low and "https://" not in low      # no external deps
    assert "<script" not in low                                # static, no JS


def test_scores_unavailable_renders_honestly():
    html = render_report({"scores_unavailable": True, "raw": "garbled"},
                         target_html=None, target_screenshot_b64=None)
    assert "n/a" in html.lower() or "unavailable" in html.lower()
    assert "garbled" in html  # raw model text surfaced, nothing invented
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest modules/tool-render-report/tests/test_template.py -v`
Expected: FAIL — `ModuleNotFoundError: ...template`.

**Step 3: Write `modules/tool-render-report/amplifier_module_tool_render_report/template.py`**

```python
"""Deterministic, self-contained 'worth'-style editorial report template.

No external dependencies: fonts are named in the CSS stack (with safe fallbacks) but never
fetched; the target screenshot (B) is embedded as a base64 data URI; the improved code (A) is
HTML-escaped into a <pre>. No <script>, no gradients, light background, one accent.
"""
import html as _html
from typing import Any

from .verdict import CRITERIA

_CSS = """
:root { --ink:#1f1d1a; --muted:#6b665e; --paper:#faf8f4; --line:#e7e1d6; --accent:#8a5a2b; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
  font-family:'Lora', Georgia, serif; line-height:1.55; }
.wrap { max-width:760px; margin:0 auto; padding:72px 28px; }
.eyebrow { font-family:'Jost', Verdana, sans-serif; font-size:12px; letter-spacing:.2em;
  text-transform:uppercase; color:var(--accent); margin-bottom:16px; }
h1 { font-family:'Cormorant Garamond', Georgia, serif; font-weight:600; font-size:46px;
  line-height:1.05; margin:0 0 8px; }
h2 { font-family:'Cormorant Garamond', Georgia, serif; font-weight:600; font-size:26px;
  margin:48px 0 12px; }
.total { font-family:'Jost', sans-serif; font-size:15px; color:var(--muted); margin-bottom:8px; }
table { width:100%; border-collapse:collapse; margin:8px 0 8px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line);
  font-family:'Jost', sans-serif; font-size:14px; }
th { color:var(--muted); font-weight:500; letter-spacing:.04em; }
td.score { text-align:right; font-variant-numeric:tabular-nums; }
ol.fixes { padding-left:20px; }
ol.fixes li { margin:0 0 12px; }
.fix-crit { font-family:'Jost', sans-serif; font-size:12px; letter-spacing:.08em;
  text-transform:uppercase; color:var(--accent); }
.ab { display:flex; gap:20px; flex-wrap:wrap; }
.ab > div { flex:1 1 300px; }
img.shot { width:100%; border:1px solid var(--line); }
pre { white-space:pre-wrap; background:#f3efe7; border:1px solid var(--line); padding:14px;
  font-family:'Jost', ui-monospace, monospace; font-size:12px; overflow:auto; }
.note { color:var(--muted); font-style:italic; }
"""


def _esc(s: Any) -> str:
    return _html.escape(str(s), quote=True)


def _scores_table(scores: dict) -> str:
    rows = "".join(
        f"<tr><th>{_esc(c)}</th><td class='score'>{_esc(scores[c])} / 4</td></tr>"
        for c in CRITERIA
    )
    return f"<table><thead><tr><th>Criterion</th><th class='score'>Score</th></tr></thead><tbody>{rows}</tbody></table>"


def _fixes_list(fixes: list) -> str:
    if not fixes:
        return "<p class='note'>No changes warranted — this page already holds up.</p>"
    items = []
    for f in fixes:
        crit = _esc(f.get("criterion", ""))
        issue = _esc(f.get("issue", ""))
        fix = _esc(f.get("fix", ""))
        items.append(f"<li><span class='fix-crit'>{crit}</span><br>{issue} — <strong>{fix}</strong></li>")
    return "<ol class='fixes'>" + "".join(items) + "</ol>"


def _target_section(target_html: str | None, target_screenshot_b64: str | None) -> str:
    if not target_html and not target_screenshot_b64:
        return "<h2>Target-state</h2><p class='note'>target-state unavailable.</p>"
    b_html = (
        f"<img class='shot' alt='target render' src='data:image/png;base64,{target_screenshot_b64}'>"
        if target_screenshot_b64
        else "<p class='note'>render (B) unavailable.</p>"
    )
    a_html = (
        f"<pre>{_esc(target_html)}</pre>"
        if target_html
        else "<p class='note'>improved code (A) unavailable.</p>"
    )
    return (
        "<h2>Target-state</h2>"
        "<div class='ab'>"
        f"<div><div class='eyebrow'>A — improved code</div>{a_html}</div>"
        f"<div><div class='eyebrow'>B — render of A</div>{b_html}</div>"
        "</div>"
    )


def render_report(
    verdict: dict,
    target_html: str | None = None,
    target_screenshot_b64: str | None = None,
) -> str:
    """Build a self-contained editorial HTML report string."""
    if verdict.get("scores_unavailable"):
        body_scores = (
            "<p class='total'>Score: N/A — the judge could not produce structured scores.</p>"
            f"<pre>{_esc(verdict.get('raw', ''))}</pre>"
        )
    else:
        scores = verdict.get("scores", {})
        total = verdict.get("total", sum(scores.values()) if scores else 0)
        body_scores = (
            f"<p class='total'>Total — {_esc(total)} / 32</p>"
            + _scores_table(scores)
            + "<h2>Prioritized fixes</h2>"
            + _fixes_list(verdict.get("fixes", []))
        )

    target = _target_section(target_html, target_screenshot_b64)

    return (
        "<!DOCTYPE html>\n<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Design Verdict</title>"
        f"<style>{_CSS}</style></head><body><main class='wrap'>"
        "<div class='eyebrow'>Design Loop · Verdict</div>"
        "<h1>An editorial read on this interface.</h1>"
        f"{body_scores}{target}"
        "</main></body></html>"
    )
```

**Step 4: Run the test to verify it passes**

Run: `python -m pytest modules/tool-render-report/tests/test_template.py -v`
Expected: `4 passed`.

**Step 5: Commit**
```bash
git add -A
git commit -m "feat(tool-render-report): self-contained editorial template with dogfood anti-slop assertions"
```

---

## Task 9: `tool-render-report` — `RenderReportTool.execute` + `mount()` (TDD)

**Files:**
- Modify: `modules/tool-render-report/amplifier_module_tool_render_report/__init__.py`
- Test: `modules/tool-render-report/tests/test_mount.py`

**Step 1: Write the failing test `modules/tool-render-report/tests/test_mount.py`**

```python
"""RenderReportTool writes a self-contained report file; mount() registers it."""
import base64
from pathlib import Path

from amplifier_core.testing import create_test_coordinator

from amplifier_module_tool_render_report import RenderReportTool, mount
from amplifier_module_tool_render_report.verdict import CRITERIA


def _verdict():
    return {"scores": {c: 2 for c in CRITERIA}, "total": 16, "fixes": []}


async def test_execute_writes_report_file(tmp_path):
    a = tmp_path / "A.html"
    a.write_text("<h1>Improved</h1>", encoding="utf-8")
    b = tmp_path / "B.png"
    b.write_bytes(b"PNGDATA")
    out = tmp_path / "report.html"

    tool = RenderReportTool()
    res = await tool.execute({
        "verdict": _verdict(),
        "target_html_path": str(a),
        "target_screenshot_path": str(b),
        "out_path": str(out),
    })
    assert res.success
    report_path = Path(res.output["report_html_path"])
    assert report_path.exists()
    html = report_path.read_text(encoding="utf-8")
    assert "data:image/png;base64," in html
    assert base64.b64encode(b"PNGDATA").decode() in html


async def test_execute_accepts_raw_verdict_text(tmp_path):
    out = tmp_path / "r.html"
    tool = RenderReportTool()
    res = await tool.execute({"verdict_text": "garbled-not-json", "out_path": str(out)})
    assert res.success  # report still produced (honest stopping)
    assert "garbled-not-json" in out.read_text(encoding="utf-8")


async def test_mount_registers_tool():
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {})
    assert isinstance(returned, RenderReportTool)
    assert coordinator.mount_points["tools"]["render_report"] is returned
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest modules/tool-render-report/tests/test_mount.py -v`
Expected: FAIL — `ImportError: cannot import name 'RenderReportTool'`.

**Step 3: Write the implementation in `modules/tool-render-report/amplifier_module_tool_render_report/__init__.py`**

```python
"""tool-render-report: turn a verdict + target-state into a self-contained editorial report."""
import base64
import logging
import tempfile
from pathlib import Path
from typing import Any

from amplifier_core import ModuleCoordinator
from amplifier_core import ToolResult

from .template import render_report
from .verdict import parse_verdict

logger = logging.getLogger(__name__)


class RenderReportTool:
    """Deterministic. Verdict (+ optional A/B) -> self-contained HTML report on disk."""

    @property
    def name(self) -> str:
        return "render_report"

    @property
    def description(self) -> str:
        return (
            "Render a design verdict and (optional) target-state into a self-contained editorial "
            "HTML report. Input: {verdict|verdict_text, target_html_path?, "
            "target_screenshot_path?, out_path?}. Returns {report_html_path}."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "verdict": {"type": "object", "description": "Parsed verdict dict."},
                "verdict_text": {"type": "string", "description": "Raw verdict text to parse."},
                "target_html_path": {"type": "string", "description": "Path to improved HTML (A)."},
                "target_screenshot_path": {"type": "string", "description": "Path to render (B)."},
                "out_path": {"type": "string", "description": "Optional output HTML path."},
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            if "verdict" in input and input["verdict"] is not None:
                parsed = parse_verdict(input["verdict"])
            elif input.get("verdict_text") is not None:
                parsed = parse_verdict(input["verdict_text"])
            else:
                return ToolResult(
                    success=False,
                    error={"message": "verdict or verdict_text is required"},
                )

            verdict_for_template = parsed["verdict"] if parsed["valid"] else parsed

            target_html = None
            a_path = input.get("target_html_path")
            if a_path and Path(a_path).expanduser().exists():
                target_html = Path(a_path).expanduser().read_text(encoding="utf-8")

            target_b64 = None
            b_path = input.get("target_screenshot_path")
            if b_path and Path(b_path).expanduser().exists():
                target_b64 = base64.b64encode(
                    Path(b_path).expanduser().read_bytes()
                ).decode("ascii")

            html = render_report(verdict_for_template, target_html, target_b64)

            out_path = input.get("out_path")
            if out_path:
                out = Path(out_path).expanduser()
            else:
                fd, tmp = tempfile.mkstemp(suffix=".html")
                out = Path(tmp)
            out.write_text(html, encoding="utf-8")

            return ToolResult(success=True, output={"report_html_path": str(out)})

        except Exception as e:
            logger.error("render_report failed: %s", e, exc_info=True)
            return ToolResult(
                success=False, error={"message": str(e), "type": type(e).__name__}
            )


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    tool = RenderReportTool()
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("Mounted tool-render-report")
    return tool
```

**Step 4: Run the test to verify it passes**

Run: `python -m pytest modules/tool-render-report/tests -v`
Expected: all `tool-render-report` tests pass (verdict + template + mount).

**Step 5: Commit**
```bash
git add -A
git commit -m "feat(tool-render-report): RenderReportTool.execute + mount() with TDD"
```

---

## Task 10: `tool-target-state` — orchestration success path (TDD, stubbed)

**Files:**
- Create: `modules/tool-target-state/pyproject.toml`
- Create: `modules/tool-target-state/amplifier_module_tool_target_state/__init__.py`
- Test: `modules/tool-target-state/tests/test_orchestration.py`

**Step 1: Write the module `pyproject.toml`** (no external runtime deps — render is injected)

```toml
[project]
name = "amplifier-module-tool-target-state"
version = "0.1.0"
description = "Persist improved UI HTML (A) and render its screenshot (B) via the render brick"
requires-python = ">=3.11"
dependencies = []

[project.entry-points."amplifier.modules"]
tool-target-state = "amplifier_module_tool_target_state:mount"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["amplifier_module_tool_target_state"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

**Step 2: Install editable**

Run: `uv pip install -e ./modules/tool-target-state`
Expected: installs editable.

**Step 3: Write the failing test `modules/tool-target-state/tests/test_orchestration.py`**

```python
"""TargetStateTool orchestration: write A, render B via injected render_fn. Stubbed model."""
from pathlib import Path

from amplifier_module_tool_target_state import TargetStateTool


def _fake_render_factory(png_path: Path):
    async def _render(html_path: str) -> dict:
        # Pretend we rendered html_path; return a path to a pre-made PNG.
        assert Path(html_path).exists()  # A must have been written first
        return {"screenshot_path": str(png_path)}
    return _render


async def test_success_with_supplied_improved_html(tmp_path):
    png = tmp_path / "B.png"
    png.write_bytes(b"PNGDATA")
    tool = TargetStateTool(render_fn=_fake_render_factory(png))

    res = await tool.execute({
        "original": {"source": "x.html", "kind": "html"},
        "fixes": [{"criterion": "restraint", "issue": "gradient", "fix": "flat surface"}],
        "improved_html": "<!DOCTYPE html><h1>Better</h1>",
        "out_dir": str(tmp_path),
    })
    assert res.success
    a = Path(res.output["target_html_path"])
    b = Path(res.output["target_screenshot_path"])
    assert a.exists() and a.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert b == png


async def test_success_with_injected_generator(tmp_path):
    png = tmp_path / "B.png"
    png.write_bytes(b"PNGDATA")

    def fake_generator(original_html: str, fixes: list) -> str:
        return "<!DOCTYPE html><h1>Generated A</h1>"

    tool = TargetStateTool(render_fn=_fake_render_factory(png), generator=fake_generator)
    res = await tool.execute({
        "original": {"source": "x.html", "kind": "html"},
        "fixes": [],
        "out_dir": str(tmp_path),
    })
    assert res.success
    assert "Generated A" in Path(res.output["target_html_path"]).read_text(encoding="utf-8")
```

**Step 4: Run the test to verify it fails**

Run: `python -m pytest modules/tool-target-state/tests/test_orchestration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'amplifier_module_tool_target_state'` /
`ImportError: cannot import name 'TargetStateTool'`.

**Step 5: Write the implementation `modules/tool-target-state/amplifier_module_tool_target_state/__init__.py`**

```python
"""tool-target-state: persist improved HTML (A), render its screenshot (B) via the render brick.

The improved HTML may be supplied directly (`improved_html`, the production path where the
design-judge agent acts as the ui-coding generator) OR produced by an injected `generator`
callable (used by tests and standalone callers). Rendering is delegated to an injected
`render_fn` so the orchestration is deterministic and fully testable; mount() wires render_fn to
the live `render` tool on the coordinator.
"""
import logging
import tempfile
from pathlib import Path
from typing import Any, Awaitable, Callable

from amplifier_core import ModuleCoordinator
from amplifier_core import ToolResult

logger = logging.getLogger(__name__)

# render_fn(html_path: str) -> {"screenshot_path": str}
RenderFn = Callable[[str], Awaitable[dict]]
# generator(original_html: str, fixes: list) -> improved_html: str
GeneratorFn = Callable[[str, list], str]


class TargetStateTool:
    def __init__(self, render_fn: RenderFn | None = None, generator: GeneratorFn | None = None):
        self._render_fn = render_fn
        self._generator = generator

    @property
    def name(self) -> str:
        return "target_state"

    @property
    def description(self) -> str:
        return (
            "Build a target-state from an original artifact and a verdict's fixes. Provide "
            "improved_html (A) directly, or rely on a configured generator. Writes A to disk, "
            "then renders B (a screenshot of A). Returns {target_html_path, target_screenshot_path}. "
            "On failure returns 'target-state unavailable' without inventing anything."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "original": {
                    "type": "object",
                    "description": "{source, kind} of the artifact being improved.",
                },
                "fixes": {"type": "array", "description": "Prioritized fixes from the verdict."},
                "improved_html": {
                    "type": "string",
                    "description": "Improved HTML (A). If omitted, a configured generator is used.",
                },
                "out_dir": {"type": "string", "description": "Optional directory for A and B."},
            },
        }

    def _read_original_html(self, original: dict) -> str:
        if original.get("kind") == "html":
            p = Path(str(original.get("source", ""))).expanduser()
            if p.exists():
                return p.read_text(encoding="utf-8")
        return ""

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            improved_html = input.get("improved_html")
            if improved_html is None:
                if self._generator is None:
                    return ToolResult(
                        success=False,
                        error={"message": "target-state unavailable: no improved_html and no generator configured"},
                    )
                original_html = self._read_original_html(input.get("original", {}) or {})
                improved_html = self._generator(original_html, input.get("fixes", []) or [])

            if self._render_fn is None:
                return ToolResult(
                    success=False,
                    error={"message": "target-state unavailable: no renderer configured"},
                )

            out_dir = input.get("out_dir")
            if out_dir:
                base = Path(out_dir).expanduser()
                base.mkdir(parents=True, exist_ok=True)
                a_path = base / "target.html"
            else:
                fd, tmp = tempfile.mkstemp(suffix=".html")
                a_path = Path(tmp)
            a_path.write_text(improved_html, encoding="utf-8")

            render_out = await self._render_fn(str(a_path))
            shot = render_out.get("screenshot_path")
            if not shot or not Path(shot).exists():
                return ToolResult(
                    success=False,
                    error={"message": "target-state unavailable: render of A failed"},
                )

            return ToolResult(
                success=True,
                output={"target_html_path": str(a_path), "target_screenshot_path": str(shot)},
            )

        except Exception as e:
            logger.error("target-state failed: %s", e, exc_info=True)
            return ToolResult(
                success=False,
                error={"message": f"target-state unavailable: {e}", "type": type(e).__name__},
            )


def _make_render_fn(coordinator: ModuleCoordinator) -> RenderFn:
    """Late-binding renderer: looks up the live 'render' tool at call time (mount-order safe)."""
    async def _render(html_path: str) -> dict:
        render_tool = coordinator.mount_points["tools"].get("render")
        if render_tool is None:
            raise RuntimeError("render tool not mounted")
        result = await render_tool.execute({"source": html_path, "kind": "html"})
        if not result.success:
            raise RuntimeError((result.error or {}).get("message", "render failed"))
        return result.output
    return _render


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    tool = TargetStateTool(render_fn=_make_render_fn(coordinator))
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("Mounted tool-target-state")
    return tool
```

**Step 6: Run the test to verify it passes**

Run: `python -m pytest modules/tool-target-state/tests/test_orchestration.py -v`
Expected: `2 passed`.

**Step 7: Commit**
```bash
git add -A
git commit -m "feat(tool-target-state): orchestration (write A, render B via injected render_fn) with TDD"
```

---

## Task 11: `tool-target-state` — failure path (unavailable, verdict intact) (TDD)

**Files:**
- Modify: `modules/tool-target-state/tests/test_orchestration.py` (add failure cases)

> The implementation from Task 10 already handles these paths. This task proves them with tests
> (the honesty spine: a broken target-state never erases the verdict and never fabricates).

**Step 1: Append failing tests to `modules/tool-target-state/tests/test_orchestration.py`**

```python
async def test_generator_raises_returns_unavailable(tmp_path):
    png = tmp_path / "B.png"
    png.write_bytes(b"PNGDATA")

    def boom(original_html, fixes):
        raise RuntimeError("model down")

    tool = TargetStateTool(render_fn=_fake_render_factory(png), generator=boom)
    res = await tool.execute({"original": {"kind": "html", "source": "x"}, "fixes": []})
    assert res.success is False
    assert "unavailable" in res.error["message"].lower()


async def test_render_failure_returns_unavailable(tmp_path):
    async def render_returns_missing(html_path: str) -> dict:
        return {"screenshot_path": str(tmp_path / "does-not-exist.png")}

    tool = TargetStateTool(render_fn=render_returns_missing)
    res = await tool.execute({
        "improved_html": "<!DOCTYPE html><h1>A</h1>",
        "out_dir": str(tmp_path),
    })
    assert res.success is False
    assert "unavailable" in res.error["message"].lower()


async def test_no_html_and_no_generator_returns_unavailable():
    tool = TargetStateTool(render_fn=None)
    res = await tool.execute({"original": {"kind": "html", "source": "x"}, "fixes": []})
    assert res.success is False
    assert "unavailable" in res.error["message"].lower()
```

**Step 2: Run to verify they pass** (impl already present from Task 10 — confirm green)

Run: `python -m pytest modules/tool-target-state/tests/test_orchestration.py -v`
Expected: `5 passed` total.

> If any of the three new tests FAIL, fix `execute()` in `__init__.py` so failures return
> `success=False` with a message containing "unavailable" — then re-run until green.

**Step 3: Commit**
```bash
git add -A
git commit -m "test(tool-target-state): prove failure paths return 'unavailable' without fabricating"
```

---

## Task 12: `tool-target-state` — `mount()` wires render_fn from coordinator (TDD)

**Files:**
- Test: `modules/tool-target-state/tests/test_mount.py`

> `mount()` and `_make_render_fn()` were written in Task 10. This task proves the live wiring:
> after both tools are mounted on one coordinator, target_state renders B through the real
> render tool.

**Step 1: Write the failing test `modules/tool-target-state/tests/test_mount.py`**

```python
"""mount() registers target_state and wires render_fn to the live render tool."""
from pathlib import Path

from amplifier_core.testing import create_test_coordinator

from amplifier_module_tool_render import mount as mount_render
from amplifier_module_tool_target_state import TargetStateTool, mount as mount_target

REPO = Path(__file__).resolve().parents[3]


async def test_mount_registers_target_state():
    coordinator = create_test_coordinator()
    returned = await mount_target(coordinator, {})
    assert isinstance(returned, TargetStateTool)
    assert coordinator.mount_points["tools"]["target_state"] is returned


async def test_target_state_renders_b_through_live_render_tool(tmp_path):
    # Wire BOTH bricks onto one coordinator, then run target_state end-to-end (real Chromium).
    coordinator = create_test_coordinator()
    await mount_render(coordinator, {})
    target = await mount_target(coordinator, {})

    res = await target.execute({
        "improved_html": (REPO / "fixtures" / "excellent.html").read_text(encoding="utf-8"),
        "out_dir": str(tmp_path),
    })
    assert res.success
    b = Path(res.output["target_screenshot_path"])
    assert b.exists() and b.stat().st_size > 0
```

**Step 2: Run the test to verify it fails, then passes**

Run: `python -m pytest modules/tool-target-state/tests/test_mount.py -v`
Expected: if `mount`/`_make_render_fn` were correctly written in Task 10 → `2 passed`. If the
import of `mount as mount_target` or the wiring is wrong, it FAILS first — fix `__init__.py`
until green. (This test needs `tool-render` installed editable — done in Task 4.)

**Step 3: Run the full module suite**

Run: `python -m pytest modules/tool-target-state/tests -v`
Expected: all pass.

**Step 4: Commit**
```bash
git add -A
git commit -m "test(tool-target-state): prove mount() wires render_fn to live render brick"
```

---

## Task 13: `agents/design-judge.md` — the agent you delegate to (+ structural test)

**Files:**
- Create: `agents/design-judge.md`
- Test: `tests/test_agent_structure.py`

> The agent is markdown, not Python. We TDD its *structure* (a cheap guard against typos in the
> rubric / frontmatter) with a pytest that parses it.

**Step 1: Write the failing test `tests/test_agent_structure.py`**

```python
"""design-judge agent: correct frontmatter (model_role: vision) + full rubric in body."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENT = REPO / "agents" / "design-judge.md"

CRITERIA = ["clarity", "elegance", "restraint", "empowerment",
            "agency", "ease", "character", "point"]


def _frontmatter(text: str) -> str:
    assert text.startswith("---"), "agent must start with YAML frontmatter"
    return text.split("---", 2)[1]


def test_agent_exists_and_has_vision_role():
    text = AGENT.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "name: design-judge" in fm
    assert "model_role: vision" in fm


def test_agent_body_contains_full_rubric_and_contract():
    body = AGENT.read_text(encoding="utf-8").split("---", 2)[2].lower()
    for c in CRITERIA:
        assert c in body, f"rubric missing criterion: {c}"
    assert "verdict" in body                     # contract keyword
    assert "render_report" in body               # orchestrates the report tool
    assert "target_state" in body                # orchestrates the target-state tool
    assert "render" in body                      # orchestrates the render tool
    assert "n/a" in body or "never" in body      # honesty rule present
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_agent_structure.py -v`
Expected: FAIL — file does not exist.

**Step 3: Write `agents/design-judge.md`**

Use a fenced block carefully: the file itself contains triple-backtick code fences for the JSON
contract, so write the file with your editor / `write_file` tool (not a shell heredoc).

````markdown
---
meta:
  name: design-judge
  description: "Use to judge the design quality of any UI artifact (an HTML file, an image, or a URL). Renders the artifact, scores it against an 8-criteria design rubric, builds a target-state (improved code plus a screenshot of that code), and returns a self-contained editorial HTML report plus a one-line verdict. Delegate to this agent whenever the user asks 'is this design any good?', 'critique this page', 'score this UI', or 'make this look better and show me'. Examples:\n\n<example>\nContext: user has an HTML mockup\nuser: 'Critique fixtures/landing.html and show me a better version'\nassistant: 'I'll delegate to design-judge to render, score, and build a target-state.'\n<commentary>Design judging + target-state is exactly this agent's job.</commentary>\n</example>\n\n<example>\nContext: user pastes a URL\nuser: 'How good is the design at https://example.com?'\nassistant: 'Let me use design-judge to render and score it against the rubric.'\n<commentary>URL input is normalized to a screenshot by the render brick.</commentary>\n</example>"
  model_role: vision
---

# design-judge

You are **design-judge**, the orchestrator of an on-demand design-quality loop. You take one UI
artifact and return a scored verdict, a built target-state, and a self-contained editorial report.
You have three deterministic tools available: `render`, `target_state`, and `render_report`.

## The flow (run exactly once — do NOT loop)

1. **Normalize -> screenshot.** Call `render` with `{source, kind}`.
   - `kind` is `html` for a local HTML file, `url` for a web page, `image` for an existing image.
   - If `render` returns an error, STOP and report `"could not render — <reason>"`. Do **not**
     guess scores.
   - If the input is already an image, you may skip rendering and score it directly.
2. **Vision-score the screenshot.** Look at the screenshot and score the 8 criteria below, each
   an integer 0–4. Compute `total` as the sum (0–32). Produce `VERDICT` as strict JSON.
3. **Build the target-state.** Decide the prioritized fixes. Then YOU write the improved HTML (A)
   — restrained, light, no gradients, a serif display face, one accent — and call `target_state`
   with `{original, fixes, improved_html}`. It writes A and renders B (a screenshot of A).
   - If `target_state` returns "unavailable", continue WITHOUT A/B — the critique alone is useful.
   - If the page is already excellent (high `total`, `fixes: []`), the target-state IS the
     original. Say "no changes warranted." This is honest stopping, not a failure.
4. **Render the report.** Call `render_report` with `{verdict, target_html_path,
   target_screenshot_path}` (omit the target paths if unavailable). It returns `report_html_path`.
   - If `render_report` fails, fall back to returning the verdict JSON and any paths directly.
5. **Return** `RESULT`: `{report_html_path, total, top_fixes, target_html_path}` (up to 3
   highest-leverage fixes; include `target_html_path` so the result can be re-judged).

## The rubric — 8 criteria, each scored 0–4 (total 0–32)

Score what you SEE in the screenshot. 0 = absent/actively harmful, 2 = competent but unremarkable,
4 = exemplary.

- **clarity** — Is the primary message and next action immediately legible? Visual hierarchy guides
  the eye without effort.
- **elegance** — Is the composition refined? Spacing, rhythm, and alignment feel considered, not
  accidental.
- **restraint** — Does it resist slop defaults (purple->blue gradients, heavy drop shadows, generic
  hero + centered everything, Inter/Roboto-by-default)? Less, but better.
- **empowerment** — Does the design make the user feel capable and in control, rather than sold to?
- **agency** — Are the controls honest and direct? The user can act without dark patterns or
  manufactured urgency.
- **ease** — Low cognitive load. Reading order, contrast, and tap targets make use effortless.
- **character** — Does it have a point of view? A distinct, intentional aesthetic rather than a
  template.
- **point** — Does the page know what it is for? Every element serves the one job; nothing is
  decorative filler.

## VERDICT — strict JSON contract

```json
{
  "scores": {
    "clarity": 0, "elegance": 0, "restraint": 0, "empowerment": 0,
    "agency": 0, "ease": 0, "character": 0, "point": 0
  },
  "total": 0,
  "fixes": [
    { "criterion": "restraint", "issue": "purple->blue gradient hero", "fix": "flat warm-paper surface, one accent" }
  ]
}
```

- `total` MUST equal the sum of the 8 scores.
- `fixes` is prioritized highest-leverage first; it MAY be empty for an excellent page.

## Honesty rules (non-negotiable)

- **Always produce a VERDICT** — even for a great page (`fixes: []`, high `total`). Never fabricate
  scores to fill a gap.
- **B is always a render of A.** Never substitute an image-gen "dream" mockup; the visual must come
  from the real improved code.
- If you cannot produce structured scores after one careful re-read, return the raw assessment and
  mark scores as `N/A — <reason>`. Surface missing data as `N/A`, never as a plausible guess.
- Run the flow **once** and return. Do not enter retry/convergence loops — that is a future shape's
  job.
````

**Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_agent_structure.py -v`
Expected: `2 passed`.

**Step 5: Commit**
```bash
git add -A
git commit -m "feat(agent): design-judge orchestrator with 8-criteria rubric as context sink"
```

---

## Task 14: `bundle.md` — thin bundle wiring tools + agent (+ structural test)

**Files:**
- Create: `bundle.md`
- Test: `tests/test_bundle_structure.py`

**Step 1: Write the failing test `tests/test_bundle_structure.py`**

```python
"""bundle.md: thin design-loop bundle that includes foundation + design-intelligence,
declares the three local tools, and wires the design-judge agent."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUNDLE = REPO / "bundle.md"


def _frontmatter(text: str) -> str:
    assert text.startswith("---"), "bundle.md must start with YAML frontmatter"
    return text.split("---", 2)[1]


def test_bundle_name_is_design_loop():
    fm = _frontmatter(BUNDLE.read_text(encoding="utf-8"))
    assert "name: design-loop" in fm


def test_bundle_includes_foundation_and_design_intelligence():
    fm = _frontmatter(BUNDLE.read_text(encoding="utf-8"))
    assert "amplifier-foundation" in fm
    assert "amplifier-bundle-design-intelligence" in fm


def test_bundle_declares_three_local_tools():
    fm = _frontmatter(BUNDLE.read_text(encoding="utf-8"))
    assert "./modules/tool-render" in fm
    assert "./modules/tool-target-state" in fm
    assert "./modules/tool-render-report" in fm


def test_bundle_wires_design_judge_agent():
    fm = _frontmatter(BUNDLE.read_text(encoding="utf-8"))
    # namespace is the bundle.name, never the repo name; no '@' inside YAML
    assert "design-loop:design-judge" in fm
    assert "@design-loop" not in fm


def test_local_tool_dirs_exist():
    for d in ["tool-render", "tool-target-state", "tool-render-report"]:
        assert (REPO / "modules" / d / "pyproject.toml").exists()
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_bundle_structure.py -v`
Expected: FAIL — `bundle.md` does not exist.

**Step 3: Write `bundle.md`**

```markdown
---
bundle:
  name: design-loop
  version: 0.1.0
  description: On-demand design-quality judge — score any UI artifact, build a target-state, and return an editorial report.

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

This bundle adds an on-demand **design-quality judge** on top of foundation and
design-intelligence (both included unchanged).

When the user wants a UI artifact (an HTML file, an image, or a URL) critiqued, scored, or
improved-and-shown, **delegate to the `design-loop:design-judge` agent**. It renders the artifact,
scores it against an 8-criteria rubric, builds a target-state (improved code A plus a screenshot
of that code B), and returns a self-contained editorial HTML report plus a one-line verdict.

The judge runs once and returns — it does not loop. The design-intelligence agents continue to do
the design *work*; this bundle adds the *measurement* layer on top.

---

@foundation:context/shared/common-system-base.md
```

**Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_bundle_structure.py -v`
Expected: `5 passed`.

**Step 5: Commit**
```bash
git add -A
git commit -m "feat(bundle): thin design-loop bundle wiring render/target-state/report tools + design-judge"
```

---

## Task 15: Integration test 1 — golden slop page (manual, hits a real provider)

**Files:**
- Create: `tests/integration/__init__.py` (empty)
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/test_golden_slop.py`

> These tests exercise the assembled flow through a real model. They are marked `@manual` and are
> **not** part of the default unit run. They are the headline proof of the honesty spine.

**Step 1: Create `tests/integration/__init__.py`** (empty file)

```python
```

**Step 2: Create `tests/integration/conftest.py` — how to run the manual suite**

```python
"""Integration tests run the assembled design-loop flow against a REAL provider.

They are skipped unless explicitly requested:

    RUN_MANUAL=1 python -m pytest tests/integration -m manual -v -s

Prerequisites: a configured Amplifier provider (e.g. ANTHROPIC_API_KEY) and the design-loop
bundle loadable from the repo root. These tests are intentionally excluded from CI.
"""
import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_MANUAL") != "1":
        skip = pytest.mark.skip(reason="manual integration test; set RUN_MANUAL=1 to run")
        for item in items:
            if "manual" in item.keywords:
                item.add_marker(skip)
```

**Step 3: Write `tests/integration/test_golden_slop.py`**

> The exact loading/delegation API depends on the host (foundation `load_bundle` →
> `prepare()` → `spawn`/`create_session`). The test documents the *evidence requirements* and
> drives the flow through the bundle. Keep the body honest: assert real outputs, never stub.

```python
"""Headline proof: a slop page scores low, gets specific fixes, and the target-state re-judges
HIGHER. Mirrors the impeccable A/B comparison. Manual — hits a real provider."""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SLOP = REPO / "fixtures" / "slop.html"


async def _judge(source: str, kind: str) -> dict:
    """Load the design-loop bundle and delegate to design-judge. Returns the RESULT dict.

    Implementation note for the runner: use foundation to load the bundle from the repo root and
    spawn the `design-judge` agent with instruction referencing {source, kind}. Parse the agent's
    returned RESULT JSON ({report_html_path, total, top_fixes, target_html_path}). Do NOT stub the
    model.
    """
    from amplifier_foundation import load_bundle

    bundle = await load_bundle(str(REPO / "bundle.md"))
    prepared = await bundle.prepare()
    agent = await load_bundle(str(REPO / "agents" / "design-judge.md"))
    result = await prepared.spawn(
        child_bundle=agent,
        instruction=(
            f"Judge this artifact. source={source} kind={kind}. "
            "Return only the RESULT JSON: {report_html_path, total, top_fixes, target_html_path}."
        ),
    )
    output = result["output"]
    return json.loads(output) if isinstance(output, str) else output


@pytest.mark.manual
async def test_slop_scores_low_with_specific_fixes():
    result = await _judge(str(SLOP), "html")
    assert result["total"] <= 16, f"slop page should score low, got {result['total']}"
    assert result["top_fixes"], "slop page must yield specific fixes"
    assert Path(result["report_html_path"]).exists()
    report = Path(result["report_html_path"]).read_text(encoding="utf-8")
    # the report itself must be clean (dogfood): no gradient, no Inter
    assert "linear-gradient" not in report.lower()
    assert "'inter'" not in report.lower() and '"inter"' not in report.lower()


@pytest.mark.manual
async def test_target_state_rejudges_higher():
    first = await _judge(str(SLOP), "html")
    report = Path(first["report_html_path"]).read_text(encoding="utf-8")
    assert "target-state unavailable" not in report.lower(), "expected a built target-state"
    target_html_path = first.get("target_html_path")
    assert target_html_path, "RESULT must expose target_html_path for re-judging"
    second = await _judge(target_html_path, "html")
    assert second["total"] > first["total"], (
        f"target-state must re-judge higher: {first['total']} -> {second['total']}"
    )
```

**Step 4: Verify the test is collected but skipped by default**

Run: `python -m pytest tests/integration/test_golden_slop.py -v`
Expected: `2 skipped` (manual gate). To actually run it (with a provider configured):
`RUN_MANUAL=1 python -m pytest tests/integration/test_golden_slop.py -m manual -v -s`

**Step 5: Commit**
```bash
git add -A
git commit -m "test(integration): golden slop page scores low + target-state re-judges higher (manual)"
```

---

## Task 16: Integration test 2 — already-excellent page (manual, honest stopping)

**Files:**
- Create: `tests/integration/test_excellent_page.py`

**Step 1: Write `tests/integration/test_excellent_page.py`**

```python
"""Honest stopping: an excellent page scores high, yields no fixes, and the target-state is the
original (no changes warranted). Manual — hits a real provider."""
from pathlib import Path

import pytest

from tests.integration.test_golden_slop import _judge  # reuse the loader/delegator

REPO = Path(__file__).resolve().parents[2]
EXCELLENT = REPO / "fixtures" / "excellent.html"


@pytest.mark.manual
async def test_excellent_page_scores_high_and_stops_honestly():
    result = await _judge(str(EXCELLENT), "html")
    assert result["total"] >= 24, f"excellent page should score high, got {result['total']}"
    assert not result["top_fixes"], "an excellent page should warrant no fixes"
    assert Path(result["report_html_path"]).exists()
    report = Path(result["report_html_path"]).read_text(encoding="utf-8")
    assert "no changes warranted" in report.lower()
```

> If `from tests.integration.test_golden_slop import _judge` does not resolve, run pytest from the
> repo root (`python -m pytest tests/integration ...`) so the `tests` package is importable, or
> move `_judge` into `conftest.py` as a fixture. Keep ONE implementation of the loader — do not
> duplicate it.

**Step 2: Verify collected-but-skipped**

Run: `python -m pytest tests/integration/test_excellent_page.py -v`
Expected: `1 skipped`.

**Step 3: Commit**
```bash
git add -A
git commit -m "test(integration): excellent page scores high with honest stopping (manual)"
```

---

## Task 17: Full green run, README, final commit

**Files:**
- Modify: `README.md`

**Step 1: Run the entire deterministic suite (everything except manual integration)**

Run from the repo root with the venv active:
```bash
python -m pytest modules tests -v
```
Expected: ALL unit tests pass; the two integration files report `skipped` (manual gate). Concretely:
`tool-render` (render + tool + mount), `tool-render-report` (verdict + template + mount),
`tool-target-state` (orchestration + failure + mount), `test_sanity`, `test_agent_structure`,
`test_bundle_structure` — all green.

> If any module's tests are not discovered, confirm it was installed editable:
> `uv pip install -e ./modules/tool-render -e ./modules/tool-render-report -e ./modules/tool-target-state`

**Step 2: Expand `README.md`**

```markdown
# amplifier-bundle-design-loop

On-demand **design-quality judge** for Amplifier. Delegate to the `design-judge` agent with any UI
artifact — an HTML file, an image, or a URL — and it will:

1. **Score** the design against an 8-criteria rubric (clarity, elegance, restraint, empowerment,
   agency, ease, character, point — each 0–4, total 0–32).
2. **Build a target-state** — improved real HTML (A) plus a screenshot of that code (B). B is
   always a render of A, never an image-gen dream.
3. **Return a self-contained editorial HTML report** plus a one-line verdict.

The judge runs **once** and returns. It adds a measurement layer on top of design-intelligence's
agents, which it reuses unchanged.

## Architecture

Three deterministic tool bricks orchestrated by one agent:

| Brick | Role |
|---|---|
| `tool-render` | Normalize {html\|url\|image} -> screenshot PNG (headless Chromium). |
| `tool-target-state` | Persist improved HTML (A), render its screenshot (B) via `tool-render`. |
| `tool-render-report` | Verdict + A + B -> self-contained editorial HTML report. |
| `design-judge` (agent) | Vision-scores, writes A, and orchestrates the three tools. |

## Use it

```bash
amplifier bundle add ./bundle.md
amplifier run --bundle design-loop "Judge fixtures/slop.html and show me a better version"
```

## Develop

See [docs/DEV_SETUP.md](docs/DEV_SETUP.md). In short:

```bash
uv venv && source .venv/bin/activate
uv pip install amplifier-core pytest pytest-asyncio playwright
python -m playwright install chromium
uv pip install -e ./modules/tool-render -e ./modules/tool-target-state -e ./modules/tool-render-report
python -m pytest modules tests          # deterministic suite
RUN_MANUAL=1 python -m pytest tests/integration -m manual -v -s   # real-provider proofs
```

## Scope (MVP)

Judge-on-demand only. Deferred (future shapes that reuse these bricks unchanged): a `tool:post`
hook, a recipe convergence loop, the attractor DOT pipeline, a deterministic detector, and any
auto-retry. The eventual remote is `github.com/michaeljabbour/amplifier-bundle-design-loop`.
```

**Step 3: Final commit**
```bash
git add -A
git commit -m "docs: README with usage, architecture, and dev workflow; full green deterministic suite"
```

---

## Done — Definition of Complete

- [ ] `python -m pytest modules tests` is fully green; integration tests show as `skipped` (manual).
- [ ] Three tool modules each: Tool protocol (`name`/`description`/`input_schema`/`execute`),
      `mount()` calls `coordinator.mount("tools", tool, name=tool.name)` and returns the tool,
      no `amplifier-core` in runtime deps.
- [ ] `tool-render` renders html/url and passes images through; bad input → error, never a crash.
- [ ] `tool-render-report` output is self-contained (no `http(s)://`, no `<script>`), passes the
      dogfood anti-slop assertions, and surfaces `scores_unavailable`/raw text honestly.
- [ ] `tool-target-state` writes A, renders B via the injected/live render brick, and returns
      "unavailable" (verdict intact) on any failure.
- [ ] `design-judge.md` has `model_role: vision`, the full 8-criteria rubric in its body
      (context sink, not `context.include`), the VERDICT contract, and the honesty rules.
- [ ] `bundle.md` is thin: `name: design-loop`, includes foundation + design-intelligence,
      declares the three local tools, wires `design-loop:design-judge`, no `@` in YAML.
- [ ] Every task committed with a conventional-commit message. No `git push` / `gh` / `merge`.

## Explicitly NOT done in this plan (handoff to later shapes / `/finish`)

- No hook, no recipe loop, no attractor pipeline, no deterministic detector, no image-gen dream,
  no auto-retry/convergence.
- No remote created or pushed; that is `/finish`'s job. Eventual origin:
  `github.com/michaeljabbour/amplifier-bundle-design-loop`.
