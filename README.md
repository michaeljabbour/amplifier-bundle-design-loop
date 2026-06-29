# amplifier-bundle-design-loop

An Amplifier bundle providing a **design-judge** agent and supporting tools for AI-driven UI design iteration.

## Overview

The `design-loop` bundle enables autonomous design critique and iteration by composing:

- **design-judge agent** — Reviews rendered UI designs against a target state specification, identifies gaps, and drives iterative refinement
- **tool-render** — Renders HTML/CSS designs to images for visual comparison
- **tool-target-state** — Manages target-state specifications describing desired design outcomes
- **tool-render-report** — Generates structured design critique reports with actionable feedback

## Usage

```bash
amplifier bundle add git+https://github.com/your-org/amplifier-bundle-design-loop@main
amplifier bundle use design-loop
```

## Structure

```
agents/               Agent definitions
behaviors/            Reusable behavior bundles
fixtures/             Test fixtures and sample designs
modules/
  tool-render/        Render HTML/CSS to image tool
  tool-target-state/  Target-state management tool
  tool-render-report/ Design critique report tool
tests/                Bundle-level tests
```

## Status

Early development. See individual module READMEs for details.
