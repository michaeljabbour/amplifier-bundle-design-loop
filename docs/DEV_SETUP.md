# Dev Environment Setup

This guide provisions the local development environment for
`amplifier-bundle-design-loop`.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.12+ available on your `PATH`

## Quick Start

Run the following commands from the repository root:

```bash
# Step 1 — create the repo-root virtualenv
uv venv
source .venv/bin/activate   # (.venv) prompt confirms activation

# Step 2 — install runtime and test dependencies
uv pip install amplifier-core pytest pytest-asyncio playwright

# Step 3 — install the Chromium browser binary (required for real-render tests)
python -m playwright install chromium

# Step 4 — verify the toolchain
python -c "from amplifier_core import ToolResult; from amplifier_core.testing import create_test_coordinator; from playwright.async_api import async_playwright; print('env ok')"
# Expected output: env ok

# Step 5 — run the baseline sanity test
python -m pytest tests/test_sanity.py -v
# Expected: 1 passed
```

## About `amplifier-core`

`amplifier-core` is a **peer dependency** provided by the Amplifier host runtime
at execution time.  It is installed here in the dev virtualenv **only** so that
unit tests can import `ToolResult` and `create_test_coordinator`.

Consequently, `amplifier-core` is **intentionally absent** from the `dependencies`
list in each module's `pyproject.toml`.  Adding it as a runtime dependency would
cause installation failures because the host runtime already supplies it and it is
not on PyPI as an independently installable package for end-users.

## About Chromium

`python -m playwright install chromium` downloads the Playwright-managed Chromium
binary into `~/.cache/ms-playwright/` (macOS: `~/Library/Caches/ms-playwright/`).
The `tool-render` integration tests use this binary via the Playwright API and are
deliberately **not mocked** — they exercise real browser rendering to catch
regressions in CSS/layout that mocks would miss.

## Fallback: install `amplifier-core` from source

If the PyPI wheel is incompatible with your environment, install from the GitHub
repository instead:

```bash
uv pip install "amplifier-core @ git+https://github.com/microsoft/amplifier-core" \
    pytest pytest-asyncio playwright
```

## Running the Test Suite

```bash
# All tests (excluding manual integration tests)
python -m pytest tests/ -v

# Integration tests that hit a real provider (run explicitly)
python -m pytest tests/ -v -m manual
```

## Running Manual Integration Tests

The `@pytest.mark.manual` integration tests load `bundle.md` end-to-end using
`amplifier_foundation`. Install it from GitHub before running them (it is **not**
on PyPI under the bare name):

```bash
# Install amplifier-foundation for manual test support
uv pip install "amplifier-foundation @ git+https://github.com/microsoft/amplifier-foundation@main"
```

Then run with:

```bash
RUN_MANUAL=1 uv run pytest tests/integration -m manual -v -s
```

Requirements:
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` set in the environment
- Chromium installed (`python -m playwright install chromium`)
- `bundle.md` at the repo root and `agents/design-judge.md` present
- Network access to resolve `amplifier-bundle-design-intelligence` during `prepare()`

### Known constraint: `prepare()` and offline dev environments

`bundle.md` includes `amplifier-bundle-design-intelligence@main`. During `prepare()`,
`amplifier_foundation` activates each included bundle's Python package dependencies.
The design-intelligence bundle pulls in the `amplifier` meta-package (from the local
Amplifier cache), which depends on:

```
amplifier → amplifier-app-cli → amplifier-foundation
```

`amplifier-foundation` is **not on PyPI**; it only installs via git URL. When `prepare()`
runs `uv pip install -e <cached-package> --no-sources` in the test venv, the solver
cannot resolve `amplifier-foundation` and the install fails with:

> No solution found when resolving dependencies: Because there are no versions of
> amplifier-foundation…

**Workaround (in progress):** The manual tests are correctly written to the real
`amplifier_foundation` API. Running them end-to-end requires an Amplifier environment
where the full dependency chain is pre-installed in the active venv (e.g. a uv-managed
Amplifier tool venv, not a `uv run --with` ephemeral venv).
