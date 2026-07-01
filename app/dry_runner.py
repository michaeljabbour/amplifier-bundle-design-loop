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

# ── Escalated variant scores ────────────────────────────────────────────────
# The "escalated" transcript climbs a little but never clears the bar: the
# best candidate plateaus in the high-teens and the loop gives up (budget /
# plateau) instead of converging. Used to make the non-converged UI state
# demoable without a real LLM run.
_ESC_PASS2_SCORES = {
    "clarity": 3,
    "elegance": 2,
    "restraint": 1,
    "empowerment": 2,
    "agency": 2,
    "ease": 3,
    "character": 1,
    "point": 2,
}
_ESC_CHAMPION_SCORES = {
    "clarity": 3,
    "elegance": 2,
    "restraint": 2,
    "empowerment": 2,
    "agency": 2,
    "ease": 3,
    "character": 2,
    "point": 2,
}

# Successive dry runs alternate converged -> escalated -> converged ... so a
# demo can show both terminal states without any UI knob (per product choice
# "auto-alternate per run"). Module-level: survives per server process.
_RUN_COUNTER = {"n": 0}


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
        f"Pass {pass_no}/{_TOTAL_PASSES}: spawning design-loop:design-maker ({maker_label})",
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


def _build_dry_state(run_id: str, variant: str) -> dict[str, Any]:
    """Build the scripted run `state` for the render step.

    `run_id` is stamped onto records[0] so the report renderer reuses the
    app's own run_id (instead of falling back to ``<task_class>_<ts>``). With
    the web app's out_dir == durable run dir, that reconciles every artifact,
    the history entry, and the WS result under a SINGLE id/dir.

    `variant` selects the terminal state: "converged" (champion clears the
    bar, DONE/bar_met) or "escalated" (champion plateaus below the bar, the
    loop gives up).
    """
    baseline_rec = {
        "pass": 0,
        "run_id": run_id,
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
    }

    if variant == "escalated":
        records = [
            baseline_rec,
            {
                "pass": 1,
                "decision": "NEW_BEST",
                "outcome": "accepted",
                "scores": _ESC_PASS2_SCORES,
                "fix_batch": [
                    {
                        "criterion": "elegance",
                        "issue": "Tightened spacing and type scale, but the layout is still three equal cards.",
                        "fix": "A real improvement needs structure, not just polish.",
                    }
                ],
                "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
                "artifact_ref": str(_UPGRADED),
            },
            {
                "pass": 2,
                "decision": "NO_GAIN",
                "outcome": "rejected",
                "scores": _ESC_CHAMPION_SCORES,
                "fix_batch": [
                    {
                        "criterion": "character",
                        "issue": "Third attempt reshuffled the same components without a point of view.",
                        "fix": "Escalate to a human: the loop can't find a differentiating direction.",
                    }
                ],
                "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
                "artifact_ref": str(_UPGRADED),
            },
        ]
        return {
            "records": records,
            "gate": {"action": "ESCALATE", "reason": "plateau"},
            "champion": {
                "scores": _ESC_CHAMPION_SCORES,
                "total": sum(_ESC_CHAMPION_SCORES.values()),
                "artifact_ref": str(_UPGRADED),
            },
            "converged": False,
        }

    records = [
        baseline_rec,
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


def _pick_variant(explicit: str | None) -> str:
    """Choose which scripted transcript to run.

    An explicit "converged"/"escalated" (e.g. from a re-run that wants to
    reproduce a state) wins. Otherwise successive runs auto-alternate so a
    demo can show both terminal states with no UI knob.
    """
    if explicit in ("converged", "escalated"):
        return explicit
    n = _RUN_COUNTER["n"]
    _RUN_COUNTER["n"] = n + 1
    return "converged" if n % 2 == 0 else "escalated"


# Total scripted passes -- surfaced in each "Pass N/TOTAL" line so the client
# can render a determinate progress bar without hard-coding the denominator.
_TOTAL_PASSES = 3


def _apply_focus(state: dict[str, Any], focus: str | None) -> None:
    """A focused re-run ('fix restraint') should visibly move THAT dimension.

    Bumps the champion's focused-dimension score (and mirrors it onto the
    winning record) so the score delta and scorecard reflect the steer. No-op
    if `focus` isn't one of the eight criteria.
    """
    from .results import _LABEL  # local import: avoids a hard dep at import time

    if not focus or focus not in _LABEL:
        return
    champ = state.get("champion") or {}
    scores = dict(champ.get("scores") or {})
    if not scores:
        return
    scores[focus] = min(4, int(scores.get(focus, 0)) + 1)
    champ["scores"] = scores
    champ["total"] = sum(v for v in scores.values() if isinstance(v, int))
    state["champion"] = champ
    for rec in reversed(state.get("records") or []):
        if rec.get("decision") in ("NEW_BEST", "BASELINE"):
            rec_scores = dict(rec.get("scores") or {})
            rec_scores[focus] = scores[focus]
            rec["scores"] = rec_scores
            break


async def run_dry(
    run_id: str,
    out_dir: pathlib.Path,
    hook: WebStreamingHook,
    *,
    kind: str = "image",
    source: str = "",
    variant: str | None = None,
    context: str = "",
    audience: str = "",
    focus: str | None = None,
    compare_url: str = "",
) -> dict[str, Any]:
    """Run the scripted dry-mode transcript and render the report trio.

    `kind`/`source` (read by ws_handler from the run's meta.json) are used
    ONLY to make the first log line honestly reflect what was submitted --
    the scripted scores/records themselves are unaffected, since dry mode
    never actually looks at the input.

    `variant` ("converged"/"escalated"/None) selects the terminal state; None
    auto-alternates per run so both outcomes are demoable.

    Returns the render() result dict (upgraded_html/report_html/baseline_html
    absolute paths on disk, plus durable_* variants) with `total`, `converged`,
    and `reason` added so ws_handler can populate the result payload without
    re-deriving them from the (already-rendered) state.
    """
    if not _SLOP.exists() or not _UPGRADED.exists():
        raise RuntimeError(f"demo fixtures missing under {_FIXTURES}")

    chosen = _pick_variant(variant)

    label = _KIND_LABELS.get(kind, kind)
    display_value = _source_display(kind, source)
    goal = " ".join((context or "").split())[:80]
    intake_msg = (
        f"Received {label} {display_value} \u2014 classified as {kind}"
        + (f'; goal: "{goal}"' if goal else "")
        + "; starting governed design loop (DRY MODE -- no LLM calls)"
    )
    await hook.display(intake_msg, source="upload")
    await asyncio.sleep(0.3)
    if focus:
        await hook.display(
            f"Focusing this run on: {focus}", source="loop"
        )
        await asyncio.sleep(0.15)

    # Ground-truth audit on the ACTUAL input (deterministic, no LLM) -- the
    # objective half of a senior review, run before any subjective scoring.
    from .audit import run_audit

    html_text = None
    if kind == "html":
        hp = out_dir / "input.html"
        if hp.exists():
            try:
                html_text = hp.read_text(encoding="utf-8")
            except Exception:
                html_text = None
    audit = await run_audit(
        kind=kind, html=html_text, url=(source if kind == "url" else None)
    )
    if audit.get("available"):
        s = audit["summary"]
        await hook.tool_pre("design_lints", {"op": "ground_truth"})
        await hook.tool_post(
            "design_lints",
            success=(s.get("fail", 0) == 0),
            summary=f"{s.get('pass',0)} pass / {s.get('warn',0)} warn / {s.get('fail',0)} fail",
        )
        await hook.display(
            f"GROUND-TRUTH: {s.get('pass',0)} pass, {s.get('warn',0)} warn, {s.get('fail',0)} fail "
            "(accessibility & hygiene, checked on your real markup)",
            source="lints",
        )
        await asyncio.sleep(0.2)

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

    if chosen == "escalated":
        await _pass(
            hook,
            pass_no=2,
            maker_label="produced revised candidate",
            lint_ok=True,
            lint_reason="PASS",
            critic_text="scored 17/32 -- worst: restraint 1/4",
            gate_text="NEW_BEST -> PLAN (small gain, keep climbing)",
            step_delay=0.45,
        )
        await _pass(
            hook,
            pass_no=3,
            maker_label="produced revised candidate",
            lint_ok=True,
            lint_reason="PASS",
            critic_text="scored 18/32 -- worst: character 2/4",
            gate_text="NO_GAIN -> ESCALATE (plateau below bar 26, human needed)",
            step_delay=0.45,
        )
        final_msg = (
            "Escalated: best candidate plateaued at 18/32, below the bar of 26 "
            "(plateau). Handing off to a human. Report ready."
        )
    else:
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
        final_msg = "Converged: champion scored 29/32 (bar_met). Report ready."

    await hook.tool_pre("render_report", {"run_id": run_id})
    state = _build_dry_state(run_id, chosen)
    _apply_focus(state, focus)
    # durable_base set (was None) so every dry run also appends a
    # history.jsonl entry under ~/Downloads/design-loop, exactly like a real
    # design-converge.yaml run's render_report finalize step would. Because
    # out_dir already lives under durable_base/runs/<run_id> and records[0]
    # carries that same run_id, render() writes ONE directory (no second copy).
    result = await asyncio.to_thread(
        rr_template.render, state, out_dir=str(out_dir), durable_base=str(_DURABLE_ROOT)
    )
    await hook.tool_post(
        "render_report", success=True, summary="wrote baseline/upgraded/report.html"
    )
    await hook.display(final_msg, source="gate")

    from .results import build_result_payload

    payload = build_result_payload(
        state, context=context, audience=audience, audit=audit
    )

    # Benchmark: same deterministic audit on a competitor URL (objective only).
    if compare_url:
        their = await run_audit(kind="url", url=compare_url)
        payload["benchmark"] = {
            "url": compare_url,
            "available": bool(their.get("available")),
            "you": audit.get("summary", {}) if audit.get("available") else {},
            "them": their.get("summary", {}),
            "you_findings": audit.get("findings", []) if audit.get("available") else [],
            "them_findings": their.get("findings", []),
            "note": "Objective ground-truth checks only -- subjective scoring needs the full critique.",
        }

    # Annotate the user's ACTUAL page (html input) with redline markers.
    if html_text:
        try:
            from .annotate import annotate_html

            (out_dir / "annotated.html").write_text(
                annotate_html(html_text), encoding="utf-8"
            )
            payload["has_annotated"] = True
        except Exception:
            payload["has_annotated"] = False

    result["total"] = payload["total"]
    result["converged"] = state["converged"]
    result["reason"] = state["gate"].get("reason", "")
    result["variant"] = chosen
    result["payload"] = payload
    return result
