"""DRY-mode design loop: a SCRIPTED, realistic 3-pass transcript.

No LLM calls, no recipe execution, no cost. This proves the whole pipe
(upload/URL/HTML -> WS -> live log -> in-app results) without ever invoking a
real maker/critic agent. It reuses the SAME renderer
(amplifier_module_tool_render_report.template.render) that a real
design-converge.yaml run would call in its `render_report` finalize step, so
the resulting report.html is byte-for-byte the same kind of artifact a real
run would produce -- only the upstream scores/records are synthetic.

Mirrors amplifier-app-bundlewizard-web's approach of driving a real kernel
session and letting kernel hooks stream events; here there is no kernel
session in dry mode, so we drive the SAME WebStreamingHook interface
directly with a scripted sequence of display / tool:pre / tool:post events.
"""

from __future__ import annotations

import asyncio
import pathlib
from typing import Any

from amplifier_module_tool_render_report import template as rr_template

from .protocols import WebStreamingHook

_FIXTURES = (
    pathlib.Path(rr_template.__file__).resolve().parent.parent / "fixtures" / "demo"
)
_SLOP = _FIXTURES / "slop.html"
_UPGRADED = _FIXTURES / "upgraded.html"

# Same durable location main.DURABLE_ROOT points at (kept as a local constant,
# not an import from .main, to avoid a main <-> ws_handler <-> dry_runner
# import cycle -- main imports ws_handler imports dry_runner).
_DURABLE_ROOT = pathlib.Path.home() / "Downloads" / "design-loop"

# Human-readable label per input kind, used in the first log line so the
# transcript honestly reflects what was actually submitted (image upload,
# pasted/uploaded HTML, a URL, or a free-text prompt) instead of always
# claiming "uploaded image" regardless of source.
_KIND_LABELS = {"image": "image", "html": "HTML", "url": "URL", "prompt": "prompt"}

_BASELINE_SCORES = {
    "clarity": 1,
    "elegance": 0,
    "restraint": 0,
    "empowerment": 1,
    "agency": 1,
    "ease": 1,
    "character": 0,
    "point": 1,
}
_PASS1_SCORES = {
    "clarity": 2,
    "elegance": 1,
    "restraint": 0,
    "empowerment": 2,
    "agency": 1,
    "ease": 2,
    "character": 1,
    "point": 1,
}
_CHAMPION_SCORES = {
    "clarity": 4,
    "elegance": 4,
    "restraint": 4,
    "empowerment": 3,
    "agency": 3,
    "ease": 4,
    "character": 4,
    "point": 3,
}


def _source_display(kind: str, source: str) -> str:
    """A short, honest string to show in the log for this run's source.

    URLs are shown verbatim. HTML/prompt text is flattened to one line and
    truncated so a large pasted document doesn't flood the transaction log.
    """
    source = (source or "").strip()
    if not source:
        return "(no source recorded)"
    if kind in ("html", "prompt"):
        flat = " ".join(source.split())
        return flat[:70] + ("\u2026" if len(flat) > 70 else "")
    return source


async def _pass(
    hook: WebStreamingHook,
    *,
    pass_no: int,
    maker_label: str,
    lint_ok: bool,
    lint_reason: str,
    critic_text: str,
    gate_text: str,
    step_delay: float,
) -> None:
    await hook.display(
        f"Pass {pass_no}: spawning design-loop:design-maker ({maker_label})",
        source="maker",
    )
    await asyncio.sleep(step_delay)

    await hook.tool_pre("design_lints", {"pass": pass_no})
    await asyncio.sleep(step_delay * 0.6)
    await hook.tool_post("design_lints", success=lint_ok, summary=lint_reason)
    await hook.display(f"LINTS: {lint_reason}", source="lints")
    await asyncio.sleep(step_delay * 0.3)

    if lint_ok:
        await hook.tool_pre("design-critic", {"pass": pass_no})
        await asyncio.sleep(step_delay * 0.6)
        await hook.tool_post("design-critic", success=True, summary=critic_text)
        await hook.display(f"CRITIC: {critic_text}", source="critic")
        await asyncio.sleep(step_delay * 0.3)

    await hook.tool_pre("design_controller", {"op": "gate", "pass": pass_no})
    await asyncio.sleep(step_delay * 0.4)
    await hook.tool_post("design_controller", success=True, summary=gate_text)
    await hook.display(f"GATE: {gate_text}", source="gate")
    await asyncio.sleep(step_delay * 0.4)


def _build_dry_state() -> dict[str, Any]:
    records = [
        {
            "pass": 0,
            "task_class": "landing-page-critique",
            "decision": "BASELINE",
            "outcome": "accepted",
            "scores": _BASELINE_SCORES,
            "fix_batch": [
                {
                    "criterion": "restraint",
                    "issue": "Three identical feature cards padded out with generic copy and emoji bullets.",
                    "fix": "Cut to the three claims that are actually true and differentiating.",
                }
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(_SLOP),
        },
        {
            "pass": 1,
            "decision": "NO_GAIN",
            "outcome": "rejected",
            "scores": _PASS1_SCORES,
            "fix_batch": [
                {
                    "criterion": "character",
                    "issue": "Swapped the gradient for a flat color but kept the same generic layout.",
                    "fix": "Needs an actual point of view, not a palette swap.",
                }
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(_SLOP),
        },
        {
            "pass": 2,
            "decision": "NEW_BEST",
            "outcome": "accepted",
            "scores": _CHAMPION_SCORES,
            "fix_batch": [
                {
                    "criterion": "restraint",
                    "issue": "Replaced the three equal feature cards with one asymmetric capability list.",
                    "fix": "Each capability earns its own space and makes one real claim.",
                }
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(_UPGRADED),
        },
    ]
    return {
        "records": records,
        "gate": {"action": "DONE", "reason": "bar_met"},
        "champion": {
            "scores": _CHAMPION_SCORES,
            "total": sum(_CHAMPION_SCORES.values()),
            "artifact_ref": str(_UPGRADED),
        },
        "converged": True,
    }


async def run_dry(
    run_id: str,
    out_dir: pathlib.Path,
    hook: WebStreamingHook,
    *,
    kind: str = "image",
    source: str = "",
) -> dict[str, Any]:
    """Run the scripted dry-mode transcript and render the report trio.

    `kind`/`source` (read by ws_handler from the run's meta.json) are used
    ONLY to make the first log line honestly reflect what was submitted --
    the scripted scores/records themselves are unaffected, since dry mode
    never actually looks at the input.

    Returns the render() result dict (upgraded_html/report_html/baseline_html
    absolute paths on disk, plus durable_* variants) with `total`, `converged`,
    and `reason` added so ws_handler can populate the result payload without
    re-deriving them from the (already-rendered) state.
    """
    if not _SLOP.exists() or not _UPGRADED.exists():
        raise RuntimeError(f"demo fixtures missing under {_FIXTURES}")

    label = _KIND_LABELS.get(kind, kind)
    display_value = _source_display(kind, source)
    intake_msg = (
        f"Received {label} {display_value} \u2014 classified as {kind}; "
        "starting governed design loop (DRY MODE -- no LLM calls)"
    )
    await hook.display(intake_msg, source="upload")
    await asyncio.sleep(0.3)

    await _pass(
        hook,
        pass_no=1,
        maker_label="produced baseline candidate",
        lint_ok=False,
        lint_reason="FAIL (restraint) -- three identical cards padded with generic copy",
        critic_text="skipped -- no judge spent (lint reject)",
        gate_text="BASELINE -> continue",
        step_delay=0.45,
    )
    await _pass(
        hook,
        pass_no=2,
        maker_label="produced revised candidate",
        lint_ok=True,
        lint_reason="PASS",
        critic_text="scored 10/32 -- worst: restraint 0/4",
        gate_text="NO_GAIN -> PLAN (regression on restraint, retry from best-so-far)",
        step_delay=0.45,
    )
    await _pass(
        hook,
        pass_no=3,
        maker_label="produced revised candidate",
        lint_ok=True,
        lint_reason="PASS",
        critic_text="scored 29/32 -- worst: agency 3/4",
        gate_text="NEW_BEST -> DONE (bar_met)",
        step_delay=0.45,
    )

    await hook.tool_pre("render_report", {"run_id": run_id})
    state = _build_dry_state()
    # durable_base set (was None) so every dry run also appends a
    # history.jsonl entry under ~/Downloads/design-loop, exactly like a real
    # design-converge.yaml run's render_report finalize step would.
    result = await asyncio.to_thread(
        rr_template.render, state, out_dir=str(out_dir), durable_base=str(_DURABLE_ROOT)
    )
    await hook.tool_post(
        "render_report", success=True, summary="wrote baseline/upgraded/report.html"
    )
    await hook.display(
        "Converged: champion scored 29/32 (bar_met). Report ready.", source="gate"
    )

    result["total"] = state["champion"]["total"]
    result["converged"] = state["converged"]
    result["reason"] = state["gate"].get("reason", "")
    return result
