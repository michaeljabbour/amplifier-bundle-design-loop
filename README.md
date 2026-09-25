# amplifier-bundle-design-loop

An Amplifier bundle that adds an on-demand **design judge**: give it any UI — a web
page, a link, or a screenshot — and it scores the design, builds a better version,
and hands back a clean report.

## How it works

![How the design judge works](docs/design-loop-workflow.png)

1. **You share a design** — raw HTML, a URL, or an image.
2. **It scores the design** against 8 plain-language qualities (0–4 each, 32 total).
3. **It builds a better version** — improved HTML, plus a screenshot of that improved page.
4. **You get a report** — the score, the highest-value fixes, and a before → after.

The judge runs **once and returns**. It does not loop.

### The 8 qualities

| Quality | What it asks |
|---------|--------------|
| **clarity** | Can a first-time visitor instantly tell what this is and where to look? |
| **elegance** | Does it feel refined and intentional, not assembled from defaults? |
| **restraint** | Does it resist slop defaults (purple→blue gradients, heavy shadows, generic hero, default Inter, equal-weight card grids)? |
| **empowerment** | Does the user feel capable and in control? |
| **agency** | Is it obvious what the user can do? |
| **ease** | Is the path to the main action low-effort and clear? |
| **character** | Does it have a distinctive, memorable personality? |
| **point** | Does the design know the one thing it exists to do? |

## Quick start

Add the behavior, then just talk to the judge:

```bash
amplifier bundle add 'git+https://github.com/michaeljabbour/amplifier-bundle-design-loop@main#subdirectory=behaviors/design-loop.yaml' --app --name design-loop
amplifier
```

Add `behaviors/design-loop.yaml`, not the repo root. `bundle.md` is the standalone root
(`amplifier run --bundle ...`): its markdown body is a system prompt, so composing it onto
another host makes the loader drop it with a "carries a markdown body" warning.

```text
> Use the design-judge to judge fixtures/slop.html — score it, build a better
  version, and give me the report.
```

You can point it at a file path, a URL, or paste raw HTML.

> **One-time setup:** the judge takes screenshots with a headless browser. If you
> see an error about a missing Chromium browser, run this once:
> `uvx --from playwright playwright install chromium`

## Architecture

A thin bundle: it includes `amplifier-foundation` (which already ships
`amplifier-bundle-design-intelligence` and recipes) unchanged, and adds only the
measurement layer.

**Per-request footprint.** Composing `behaviors/design-loop.yaml` onto another bundle
adds ~365 tokens (chars/4 estimate) to every request: 4 short agent descriptions
(`design-critic`/`-maker`/`-planner` are recipe-internal) and a small awareness file --
**no tool schemas at all**. The 6 deterministic tools cost real per-request tokens (they
carry full JSON input schemas) but are mounted on demand, not on every session:

- `design-judge` carries its own 3 (`render`, `target_state`, `render_report`) in its own
  frontmatter (`agents/design-judge.md`) -- they mount only in its spawned child session,
  when someone actually delegates to it.
- The governed recipe (`design-converge.yaml`) resolves all 6 tools via an explicit
  `bundle_ref` default pointing at `behaviors/design-loop-recipe-tools.yaml` -- a
  tools-only companion behavior that is never composed onto a session directly, so it
  never appears in anyone's baseline. This also makes the recipe self-sufficient: it
  works regardless of what the calling session composed.

End-to-end measured effect (leave-one-out, Haiku tokenizer): composing the old
(pre-0.3.0) behavior cost ~1,822 tokens on every request; composing this one costs
~365 (agent descriptions + awareness) -- the tool cost (~1,450 tokens) now shows up
only inside design-judge's own session, or the recipe's own bash-step invocations.
Check with `python scripts/measure_footprint.py`; budgets are pinned in
`tests/test_footprint.py`. The behavior no longer pulls in design-intelligence (unused
here; foundation already includes it). To get the old design-intelligence composition
on a base without it, compose `behaviors/design-loop-full.yaml` instead.

| Component | Type | Responsibility |
|-----------|------|----------------|
| `design-judge` | Agent (`model_role: vision`) | Runs the whole flow once; carries the 8-quality rubric and its own 3 tools |
| `tool-render` | Tool (agent-scoped on `design-judge`) | Turns HTML / a URL / an image into a screenshot |
| `tool-target-state` | Tool (agent-scoped on `design-judge`) | Writes the improved HTML and renders it; returns `"unavailable"` on failure |
| `tool-render-report` | Tool (agent-scoped on `design-judge`) | Builds the self-contained HTML report |

`design-critic`/`design-maker`/`design-planner` and all 6 tools also live in
`behaviors/design-loop-recipe-tools.yaml` and the 4 agent descriptions in
`behaviors/design-loop.yaml` -- the recipe resolves tools from the former (via
`bundle_ref`) and agents from whatever composed `behaviors/design-loop.yaml` (a legacy
recipe; see `docs/RECIPE_SCHEMA.md` "Schema v2" for why that's the caller-bound default).

Two honest guarantees: the "after" picture is always a real render of the improved
HTML (never an AI-generated dream), and the judge always returns a verdict rather
than fabricating one.

## Develop

See **[docs/DEV_SETUP.md](docs/DEV_SETUP.md)** for the full environment guide.

```bash
uv venv && source .venv/bin/activate
uv pip install amplifier-core pytest pytest-asyncio playwright
python -m playwright install chromium
python -m pytest modules tests -v          # deterministic suite
RUN_MANUAL=1 python -m pytest tests/integration -m manual -v -s   # needs a provider key
```

Integration tests are gated behind `RUN_MANUAL=1` so they never run in CI.

## Roadmap

Today this ships the simplest useful shape — **judge on demand**. Natural next steps,
all reusing the same tools unchanged:

- A `tool:post` hook that auto-judges every UI file as it's written.
- A convergence loop: judge → revise → re-judge until the score clears a bar.
- A deterministic slop detector as a fast pre-filter before the model scores.

## Target architecture (the harness)

The roadmap above converges on one shape: a **deterministic controller** wrapping a
**judge ↔ maker loop**, where the thing that *scores* and the thing that *makes* are
separate actors, an append-only **ledger** is the memory, and you are relocated to
setting the bar once and handling only real escalations.

![The design harness](docs/design-loop-harness.png)

Validated with `amplifier:amplifier-expert` and `foundation:zen-architect`. The
controller is realized by composition (a `recipes` convergence recipe for the greedy
loop; the `attractor` `loop-pipeline` for beam/evolutionary width) — not a bespoke
orchestrator. See the design notes in `docs/`.

### Compounding (the metaharness)

The governed loop above is *automation* (tier B): it converges one artifact. The
**compounding** tier (C) comes from a second, slower clock — the harness improving
itself. Recurring judgments the (expensive) Judge keeps making get ratcheted
**leftward** into cheap deterministic lints, shipped as **pull requests** to this
bundle (new lint + regression test + rubric-version bump), ratified by a human merge,
and inherited free by the next run. The ledger is the shared capital account between
the two clocks.

![The two-clock metaharness](docs/design-loop-metaharness.png)

The C-signal: escalation-rate per run falls while quality holds, and judge-tokens per
run fall. Full spec in [`docs/HARNESS_DESIGN.md`](docs/HARNESS_DESIGN.md).
