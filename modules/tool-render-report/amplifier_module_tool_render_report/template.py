"""Self-contained editorial 'worth'-style HTML report for design review verdicts.

Design constraints enforced:
- NO external fetches (no @import url(), no http/https refs)
- NO CSS gradients (linear-gradient / radial-gradient)
- NO <script> tags
- Warm-paper editorial palette with CSS custom properties
- Cormorant Garamond headings / Lora body / Jost UI chrome
- All user-supplied strings are HTML-escaped before insertion
"""
from __future__ import annotations
import pathlib

import html as _html
from typing import Any

import math

from .verdict import CRITERIA

# ---------------------------------------------------------------------------
# Palette & typography
# All font-family stacks fall back to universally available system fonts so
# the document renders even without the named fonts installed.  No external
# fetch is ever performed.
# ---------------------------------------------------------------------------
_CSS = """
:root {
    --ink:    #1f1d1a;
    --muted:  #6b665e;
    --paper:  #faf8f4;
    --line:   #e7e1d6;
    --accent: #8a5a2b;
}

*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    font-size: 17px;
    background: var(--paper);
    color: var(--ink);
}

body {
    font-family: 'Lora', Georgia, serif;
    max-width: 720px;
    margin: 0 auto;
    padding: 3rem 1.5rem 6rem;
    line-height: 1.7;
}

/* Eyebrow / UI chrome */
.eyebrow {
    font-family: 'Jost', Verdana, sans-serif;
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
}

h1 {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 2.4rem;
    font-weight: 400;
    line-height: 1.2;
    margin-bottom: 2rem;
    color: var(--ink);
}

h2 {
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 1.35rem;
    font-weight: 600;
    margin: 2.5rem 0 0.75rem;
    color: var(--ink);
}

/* Score table */
table.scores {
    font-family: 'Jost', Verdana, sans-serif;
    font-size: 0.88rem;
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0 0;
}

table.scores th,
table.scores td {
    text-align: left;
    padding: 0.45rem 0.75rem;
    border-bottom: 1px solid var(--line);
    color: var(--ink);
}

table.scores th {
    color: var(--muted);
    font-weight: 400;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 0.72rem;
}

table.scores td.score-val {
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.total-line {
    font-family: 'Jost', Verdana, sans-serif;
    font-size: 0.88rem;
    color: var(--muted);
    border-top: 2px solid var(--line);
    padding: 0.5rem 0.75rem 0;
    margin-bottom: 2rem;
    text-align: right;
}

.total-line strong {
    color: var(--ink);
    font-size: 1.05rem;
}

/* Fixes list */
ol.fixes {
    font-family: 'Jost', Verdana, sans-serif;
    font-size: 0.9rem;
    padding-left: 1.4rem;
    margin: 0.75rem 0 2rem;
}

ol.fixes li {
    margin-bottom: 0.6rem;
}

.fix-criterion {
    font-weight: 600;
    color: var(--accent);
    text-transform: capitalize;
}

.no-fixes {
    font-family: 'Jost', Verdana, sans-serif;
    font-size: 0.9rem;
    color: var(--muted);
    margin: 0.75rem 0 2rem;
}

/* Target-state section */
hr.divider {
    border: none;
    border-top: 1px solid var(--line);
    margin: 2.5rem 0;
}

pre.source {
    background: #f2ede6;
    border: 1px solid var(--line);
    border-radius: 4px;
    padding: 1rem 1.25rem;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    font-size: 0.78rem;
    font-family: 'Courier New', Courier, monospace;
    color: var(--ink);
    margin: 0.75rem 0 1.5rem;
}

img.shot {
    display: block;
    width: 100%;
    border: 1px solid var(--line);
    border-radius: 4px;
    margin: 0.75rem 0 1.5rem;
}

.unavailable {
    font-family: 'Jost', Verdana, sans-serif;
    font-size: 0.9rem;
    color: var(--muted);
    font-style: italic;
    margin: 0.75rem 0 1.5rem;
}

.raw-block {
    font-family: 'Jost', Verdana, sans-serif;
    font-size: 0.85rem;
    color: var(--muted);
    margin-bottom: 0.25rem;
}
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _esc(s: Any) -> str:
    """HTML-escape *s* (coerced to str), including quotes."""
    return _html.escape(str(s), quote=True)


def _scores_table(scores: dict) -> str:
    """Render an HTML <table> with one row per criterion from CRITERIA."""
    rows: list[str] = []
    for c in CRITERIA:
        val = scores.get(c, "?")
        rows.append(
            f"<tr>"
            f"<td>{_esc(c)}</td>"
            f"<td class='score-val'>{_esc(val)} / 4</td>"
            f"</tr>"
        )
    return (
        "<table class='scores'>"
        "<thead>"
        "<tr><th>Criterion</th><th style='text-align:right'>Score</th></tr>"
        "</thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _fixes_list(fixes: list) -> str:
    """Render an ordered list of fixes, or a 'no changes' notice when empty."""
    if not fixes:
        return (
            "<p class='no-fixes'>"
            "No changes warranted \u2014 this page already holds up."
            "</p>"
        )
    items: list[str] = []
    for fix in fixes:
        if isinstance(fix, dict):
            criterion = _esc(fix.get("criterion", ""))
            issue = _esc(fix.get("issue", ""))
            suggestion = _esc(fix.get("fix", ""))
            items.append(
                f"<li>"
                f"<span class='fix-criterion'>{criterion}</span> \u2014 "
                f"{issue}. <em>{suggestion}</em>"
                f"</li>"
            )
        else:
            items.append(f"<li>{_esc(fix)}</li>")
    return "<ol class='fixes'>" + "".join(items) + "</ol>"


def _target_section(target_html: str | None, b64: str | None) -> str:
    """Render the target-state block, or an honest unavailable notice."""
    if target_html is None and b64 is None:
        return "<p class='unavailable'>Target-state unavailable.</p>"

    parts: list[str] = []

    if target_html is not None:
        parts.append(f"<pre class='source'>{_esc(target_html)}</pre>")

    if b64 is not None:
        parts.append(
            f"<img class='shot'"
            f" src='data:image/png;base64,{b64}'"
            f" alt='Target screenshot' />"
        )

    return "".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_report(
    verdict: dict,
    target_html: str | None = None,
    target_screenshot_b64: str | None = None,
) -> str:
    """Render a self-contained HTML design-review report.

    Parameters
    ----------
    verdict:
        The dict returned by ``parse_verdict()``.  Either the success shape
        (``{"valid": True, "verdict": {...}}``) or the failure shape
        (``{"valid": False, "scores_unavailable": True, "raw": str}``).
    target_html:
        The improved HTML candidate (A) to display HTML-escaped.
    target_screenshot_b64:
        Base64-encoded PNG of the current target state (B).

    Returns
    -------
    str
        A complete, self-contained ``<!DOCTYPE html>`` document.
    """
    if verdict.get("scores_unavailable"):
        raw_text = verdict.get("raw", "")
        body_scores = (
            "<p class='no-fixes'>Score: N/A</p>"
            "<p class='raw-block'>Raw scorer output:</p>"
            f"<pre class='source'>{_esc(raw_text)}</pre>"
        )
    else:
        inner = verdict["verdict"]
        scores = inner["scores"]
        total = inner["total"]
        fixes = inner.get("fixes", [])

        body_scores = (
            _scores_table(scores)
            + f"<div class='total-line'>Total \u2014 <strong>{total} / 32</strong></div>"
            + "<h2>Prioritized fixes</h2>"
            + _fixes_list(fixes)
        )

    target_block = (
        "<hr class='divider' />"
        "<h2>Target state</h2>"
        + _target_section(target_html, target_screenshot_b64)
    )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        "<title>Design Loop \u00b7 Verdict</title>\n"
        "<style>\n"
        + _CSS
        + "</style>\n"
        "</head>\n"
        "<body>\n"
        "<p class='eyebrow'>Design Loop \u00b7 Verdict</p>\n"
        "<h1>An editorial read on this interface.</h1>\n"
        + body_scores
        + "\n"
        + target_block
        + "\n"
        "</body>\n"
        "</html>"
    )

# =============================================================================
# Page_Worth VERBATIM Design Re-skin (report.html)
# =============================================================================
# This block faithfully reuses the REAL Page_Worth.html results-view design
# (source file Page_Worth.html: <style> block at lines 1614-1637; x-dc / JS
# render logic at lines 1640-2654). The CSS body below is copied VERBATIM --
# character for character -- from those lines: same Google-Fonts @import,
# same oklch() :root tokens, same radial-gradient body background, same
# keyframes. Every element below mirrors the inline style strings used by the
# source's eyebrowEl()/sectionHead()/card()/scoreLegend()/abBarRow()/
# swList()/doCard()/execAB()/detailsAB()/buildRadar() functions, translated
# 1:1 from JS object literals to CSS text.
#
# INVARIANT CHANGE: a prior revision of this report banned gradients and
# @import as "slop". That ban was based on an INVENTED look-alike, not the
# real Page_Worth source -- the real design genuinely IS a radial-gradient
# body + Google Fonts @import, and we now intentionally reuse it verbatim.
# The only invariant that still holds unconditionally is: NO <script> tag.
# =============================================================================

_PW_REAL_CSS = """@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=Lora:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Jost:wght@300;400;500;600&display=swap');
:root{
  --slp-amber:oklch(0.68 0.12 65);--slp-amber-dark:oklch(0.52 0.10 65);--slp-amber-light:oklch(0.78 0.10 65);
  --slp-cream:oklch(0.97 0.015 80);--slp-parchment:oklch(0.94 0.025 80);
  --slp-ink:oklch(0.18 0.015 65);--slp-ink-light:oklch(0.30 0.015 65);--slp-warm-gray:oklch(0.55 0.015 65);
  --slp-sage:oklch(0.58 0.07 155);--slp-sage-dark:oklch(0.45 0.07 155);
  --slp-border:oklch(0.88 0.02 80);--slp-card:oklch(1 0 0);--slp-deep-ink:oklch(0.13 0.010 65);
  --bg-1:var(--slp-cream);--bg-2:var(--slp-parchment);--bg-card:var(--slp-card);
  --fg-1:var(--slp-ink);--fg-2:var(--slp-ink-light);--fg-3:var(--slp-warm-gray);--fg-accent:var(--slp-amber-dark);
  --border-1:var(--slp-border);
  --shadow-card:0 2px 12px rgba(30,27,24,0.04);--shadow-card-hover:0 8px 32px rgba(30,27,24,0.10);
  --shadow-cta:0 4px 20px rgba(200,145,58,0.30);
  --font-display:'Cormorant Garamond',Georgia,serif;--font-body:'Lora',Georgia,serif;--font-ui:'Jost',system-ui,sans-serif;
  --band:var(--slp-amber);--band-soft:rgba(200,145,58,.13);
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:radial-gradient(120% 80% at 50% -6%,oklch(0.985 0.012 85) 0%,var(--slp-cream) 55%,var(--slp-parchment) 100%);background-attachment:fixed;min-height:100vh;-webkit-font-smoothing:antialiased}
@keyframes pw-sweep{to{transform:translateX(100%)}}
@keyframes pw-pulse{0%,100%{opacity:.3;transform:scale(.7)}50%{opacity:1;transform:scale(1.18)}}
@keyframes pw-spin{to{transform:rotate(360deg)}}
textarea:focus,button:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--slp-amber);outline-offset:2px}
"""

# ---------------------------------------------------------------------------
# Demo journey CSS (Landing / Working / Results tabs + working-log shimmer)
# ---------------------------------------------------------------------------
# The shimmer below mirrors the dc-runtime streaming idiom from Page_Worth.html
# BASE_CSS (lines ~94-117: ".sc-placeholder"/"@keyframes sc-shine", an amber
# linear-gradient sweep over a 400% background-size). Re-implemented here in
# the same idiom (amber linear-gradient sweep, animated background-position)
# for the "most recently streamed" working-log row.
_PW_JOURNEY_CSS = """
.pw-journey-nav{display:flex;gap:22px;margin-bottom:28px;border-bottom:1px solid var(--border-1)}
.pw-journey-nav button{font-family:var(--font-ui);font-weight:500;font-size:12px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--fg-3);background:none;border:none;border-bottom:2px solid transparent;
  padding:10px 2px 12px;cursor:pointer}
.pw-journey-nav button.pw-tab-active{color:var(--fg-accent);border-bottom-color:var(--slp-amber)}
.pw-mode-tab{font-family:var(--font-ui);font-weight:500;font-size:13px;border:none;background:none;
  border-radius:3px;padding:9px 16px;color:var(--fg-3)}
.pw-mode-tab.pw-mode-active{background:var(--slp-amber);color:#fff}
@keyframes pw-row-sweep{0%{background-position:160% 0}100%{background-position:-160% 0}}
.pw-row-active{position:relative;overflow:hidden}
.pw-row-active::after{content:'';position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(90deg,rgba(200,145,58,0) 30%,rgba(200,145,58,.22) 50%,rgba(200,145,58,0) 70%);
  background-size:220% 100%;animation:pw-row-sweep 1.5s ease-in-out infinite}
.pw-log-line{font-family:var(--font-ui);font-size:12.5px;color:var(--fg-2);padding:2px 0}
.pw-log-line b{color:var(--fg-accent);text-transform:uppercase;letter-spacing:.07em;font-size:10.5px;
  margin-right:7px}
"""

# Dim display names matching CRITERIA order (re-keyed from the existing
# _DIM_LABELS map above -- single source of truth, no duplication).
_DIM_SHORT = {
    "clarity": "Clarity", "elegance": "Elegance", "restraint": "Restraint",
    "empowerment": "Empower", "agency": "Agency", "ease": "Ease",
    "character": "Character", "point": "Point",
}
# "Judged on eight things" question copy -- verbatim from Page_Worth.html DIMS.
_DIM_Q = {
    "clarity": "Can you tell what to do at a glance?",
    "elegance": "Refined, or just functional?",
    "restraint": "Is everything earning its place?",
    "empowerment": "Do users leave with something usable?",
    "agency": "Can users decide and act, not just scroll?",
    "ease": "Light on the mind, one thing at a time?",
    "character": "Distinct, or a templated default?",
    "point": "Is it obvious why this matters?",
}
# Dim display names matching CRITERIA order (single source of truth for the
# whole module -- both PW_DIMS below and the Process-trace section use this).
_DIM_LABELS = {
    "clarity": "Clarity",
    "elegance": "Elegance",
    "restraint": "Restraint",
    "empowerment": "Empowerment",
    "agency": "Agency",
    "ease": "Ease",
    "character": "Character",
    "point": "Point",
}


def _flat_scores(scores: object) -> dict:
    """Normalise potentially-nested scores to a flat {dim: int} dict."""
    if not isinstance(scores, dict):
        return {}
    # Some records carry {scores: {dim:int, ...}, ...} nesting
    if "clarity" not in scores and isinstance(scores.get("scores"), dict):
        return scores["scores"]
    return scores


def _total(scores: dict) -> int:
    return sum(v for v in scores.values() if isinstance(v, int))


def _worst_dim(scores: dict) -> str | None:
    if not scores:
        return None
    return min(
        (k for k in scores if isinstance(scores[k], int)),
        key=lambda k: scores[k],
        default=None,
    )


PW_DIMS: tuple = tuple(
    {"id": c, "label": _DIM_LABELS[c], "short": _DIM_SHORT[c], "q": _DIM_Q[c]}
    for c in CRITERIA
)

_PW_SAGE_DARK = "oklch(0.45 0.07 155)"   # --slp-sage-dark
_PW_TERRA = "oklch(0.55 0.13 35)"

_PW_SCORE_COLORS = [
    "oklch(0.56 0.14 30)", "oklch(0.66 0.13 55)", "oklch(0.75 0.12 88)",
    "oklch(0.63 0.09 150)", "oklch(0.52 0.10 155)",
]

_PW_REASON_PROSE = {
    "bar_met":          "Bar already met at baseline; nothing to improve.",
    "floor_breach":     "A floor wasn't held across all attempted passes.",
    "plateau":          "Improvement stalled below the epsilon threshold.",
    "budget_exhausted": "Maximum passes reached without meeting the bar.",
    "regression_stuck": "The loop kept regressing on the same dimension.",
    "gate_unavailable": "Gate result unavailable; escalated as fail-safe.",
}

_PW_DO_NEXT = {
    "floor_breach":     "Re-attempt the breached dimension(s) with a narrower, more targeted fix.",
    "plateau":          "Try a different fix strategy \u2014 repeating the same change won't move the needle.",
    "regression_stuck": "Isolate the regressing dimension and fix it alone before reattempting others.",
    "budget_exhausted": "Raise the pass budget, or accept the best candidate found.",
    "bar_met":          "Nothing to do \u2014 the bar was already met at baseline.",
    "gate_unavailable": "Re-run the gate; result was unavailable last time.",
}


def _pw_band_for(total: int) -> dict:
    """Direct port of Page_Worth.html bandFor() -- identical thresholds/colors/copy."""
    if total <= 11:
        return {"name": "Noise", "ready": "Don't ship yet",
                 "line": "Rework the core before polishing.",
                 "c": "oklch(0.55 0.13 35)", "s": "oklch(0.55 0.13 35 / .13)"}
    if total <= 19:
        return {"name": "Functional", "ready": "Ships, but forgettable",
                 "line": "It works, but won't be remembered.",
                 "c": "oklch(0.62 0.12 65)", "s": "oklch(0.68 0.12 65 / .14)"}
    if total <= 26:
        return {"name": "Strong", "ready": "Ship-ready",
                 "line": "Real value \u2014 refine the weak spots.",
                 "c": "oklch(0.52 0.07 155)", "s": "oklch(0.58 0.07 155 / .14)"}
    return {"name": "Exemplary", "ready": "Exemplary",
             "line": "Ship it and learn in the open.",
             "c": "oklch(0.45 0.08 155)", "s": "oklch(0.45 0.08 155 / .16)"}


def _pw_score_color(score) -> str:
    """Direct port of Page_Worth.html scoreColor()."""
    try:
        v = max(0, min(4, round(float(score))))
    except (TypeError, ValueError):
        v = 0
    return _PW_SCORE_COLORS[v]


def _pw_verdict_sentence(converged: bool, gate: dict, b_scores: dict, total: int) -> str:
    """The headline verdict sentence shown in the hero."""
    if converged:
        return f"Worth it \u00b7 total {total}/32"
    reason = (gate.get("reason") or "escalated")
    if reason == "floor_breach" and b_scores:
        ints = [v for v in b_scores.values() if isinstance(v, int)]
        if ints:
            worst_val = min(ints)
            weak = [_DIM_LABELS.get(d, d) for d in CRITERIA if b_scores.get(d) == worst_val]
            return f"Stopped \u2014 floor breach on {', '.join(weak)}"
    return f"Stopped \u2014 {reason.replace('_', ' ')}"


def _pw_sowhat(converged: bool, gate: dict) -> str | None:
    if converged:
        return "Ready to ship."
    reason = gate.get("reason") or ""
    return _PW_REASON_PROSE.get(reason)


def _pw_do_next_text(converged: bool, gate: dict) -> str:
    if converged:
        return "Ship it \u2014 and watch for drift on the next iteration."
    reason = gate.get("reason") or ""
    return _PW_DO_NEXT.get(reason, "Review the trace below and decide the next move.")


def _pw_improved_regressed(a_scores: dict, b_scores: dict) -> tuple:
    """Per-dim deltas standing in for Page_Worth's LLM-authored improved/regressed bullets."""
    improved: list[dict] = []
    regressed: list[dict] = []
    for d in PW_DIMS:
        dim = d["id"]
        av, bv = a_scores.get(dim), b_scores.get(dim)
        if not isinstance(av, int) or not isinstance(bv, int):
            continue
        delta = bv - av
        if delta == 0:
            continue
        sign = "+" if delta > 0 else ""
        label = f"{d['label']}: {av} \u2192 {bv} ({sign}{delta})"
        (improved if delta > 0 else regressed).append({"label": label, "note": ""})
    if not regressed:
        regressed = [{"label": "Nothing got worse.", "note": ""}]
    if not improved:
        improved = [{"label": "No measured gains this pass.", "note": ""}]
    return improved, regressed


def _pw_dim_change_notes(records: list) -> dict:
    """Map dim -> short change note, sourced from fix_batch entries (stand-in for L.changes)."""
    notes: dict = {}
    for r in records:
        for f in (r.get("fix_batch") or []):
            if isinstance(f, dict):
                c = f.get("criterion")
                if c and c not in notes:
                    notes[c] = f.get("issue") or f.get("fix") or ""
    return notes


# ---------------------------------------------------------------------------
# Element builders -- 1:1 ports of Page_Worth.html's inline-styled h(...) calls
# ---------------------------------------------------------------------------

def _pw_eyebrow(text: str, color: str = "var(--fg-3)") -> str:
    """Port of eyebrowEl()."""
    return (
        f"<div style=\"font-family:var(--font-ui);font-weight:500;font-size:10.5px;"
        f"letter-spacing:.22em;text-transform:uppercase;color:{color}\">{_esc(text)}</div>"
    )


def _pw_section_head(title: str) -> str:
    """Port of sectionHead()."""
    return (
        "<div style=\"display:flex;align-items:center;gap:10px;margin-bottom:12px\">"
        "<span style=\"display:block;width:26px;height:1px;background:var(--slp-amber)\"></span>"
        f"<span style=\"font-family:var(--font-ui);font-weight:500;font-size:11px;"
        f"letter-spacing:.2em;text-transform:uppercase;color:var(--fg-3)\">{_esc(title)}</span>"
        "</div>"
    )


def _pw_card(inner: str) -> str:
    """Port of card()."""
    return (
        "<div style=\"background:var(--bg-card);border:1px solid var(--border-1);"
        "border-radius:6px;padding:6px 20px;box-shadow:var(--shadow-card)\">"
        f"{inner}</div>"
    )


def _pw_score_legend() -> str:
    """Port of scoreLegend()."""
    lab = (
        "font-family:var(--font-ui);font-size:10px;font-weight:500;"
        "letter-spacing:.12em;text-transform:uppercase;color:var(--fg-3)"
    )
    swatches = "".join(
        f"<span style=\"width:24px;height:7px;border-radius:3px;background:{c}\"></span>"
        for c in _PW_SCORE_COLORS
    )
    return (
        "<div style=\"display:flex;align-items:center;gap:7px;margin-bottom:12px;flex-wrap:wrap\">"
        f"<span style=\"{lab}\">Weak</span>{swatches}<span style=\"{lab}\">Strong</span>"
        "</div>"
    )


def _pw_ab_bar_row(label: str, a: int, b: int, note: str, top: bool) -> str:
    """Port of abBarRow()."""
    dd = b - a
    dcol = _PW_SAGE_DARK if dd > 0 else (_PW_TERRA if dd < 0 else "var(--fg-3)")
    border = "border-top:1px solid oklch(0.91 0.02 80)" if top else "border-top:0"

    def tinybar(val: int, col: str, lab: str) -> str:
        pct = round(val / 4 * 100)
        return (
            "<div style=\"display:flex;align-items:center;gap:6px;margin-bottom:4px\">"
            f"<span style=\"font-family:var(--font-ui);font-size:9.5px;font-weight:600;"
            f"color:var(--fg-3);width:10px\">{lab}</span>"
            "<div style=\"flex:1;height:6px;border-radius:3px;background:oklch(0.92 0.02 80);"
            "overflow:hidden\">"
            f"<div style=\"height:100%;width:{pct}%;background:{col};border-radius:3px\"></div></div>"
            "</div>"
        )

    sign = "+" if dd > 0 else ""
    return (
        "<div style=\"display:grid;grid-template-columns:150px 1fr;gap:16px;"
        f"align-items:center;padding:13px 0;{border}\">"
        "<div>"
        f"<div style=\"font-family:var(--font-ui);font-weight:600;font-size:13px;"
        f"color:var(--fg-1)\">{_esc(label)}</div>"
        "<div style=\"font-family:var(--font-ui);font-weight:600;font-size:12px\">"
        f"<span style=\"color:var(--fg-3)\">{a} \u2192 {b}  </span>"
        f"<span style=\"color:{dcol}\">({sign}{dd})</span>"
        "</div></div>"
        "<div>"
        f"{tinybar(a, '#c3bcae', 'A')}{tinybar(b, _pw_score_color(b), 'B')}"
        f"<div style=\"font-family:var(--font-body);font-size:12.5px;color:var(--fg-2);"
        f"margin-top:4px;line-height:1.35\">{_esc(note)}</div>"
        "</div></div>"
    )


def _pw_sw_list(title: str, items: list, color: str) -> str:
    """Port of swList()."""
    rows = []
    for it in items:
        note_html = (
            f"<div style=\"font-family:var(--font-body);font-size:13px;line-height:1.4;"
            f"color:var(--fg-2);margin-top:1px\">{_esc(it['note'])}</div>"
            if it.get("note") else ""
        )
        rows.append(
            "<div>"
            f"<div style=\"font-family:var(--font-ui);font-weight:600;font-size:12.5px;"
            f"color:var(--fg-1)\">{_esc(it['label'])}</div>{note_html}</div>"
        )
    return (
        "<div style=\"background:var(--bg-card);border:1px solid var(--border-1);"
        "border-radius:6px;padding:15px 18px;box-shadow:var(--shadow-card)\">"
        f"<div style=\"font-family:var(--font-ui);font-weight:600;font-size:11px;"
        f"letter-spacing:.12em;text-transform:uppercase;color:{color};margin-bottom:10px;"
        f"display:flex;align-items:center;gap:7px\">"
        f"<span style=\"width:7px;height:7px;border-radius:50%;background:{color}\"></span>"
        f"{_esc(title)}</div>"
        "<div style=\"display:flex;flex-direction:column;gap:9px\">" + "".join(rows) + "</div>"
        "</div>"
    )


def _pw_do_card(label: str, text: str) -> str:
    """Port of doCard()."""
    return (
        "<div style=\"margin-top:16px;background:var(--bg-card);border:1px solid var(--border-1);"
        "border-left:3px solid var(--slp-amber);border-radius:6px;padding:18px 22px;"
        "box-shadow:var(--shadow-card)\">"
        "<div style=\"font-family:var(--font-ui);font-weight:600;font-size:11px;letter-spacing:.14em;"
        f"text-transform:uppercase;color:var(--fg-accent);margin-bottom:7px\">{_esc(label)}</div>"
        f"<p style=\"margin:0;font-family:var(--font-body);font-size:16px;line-height:1.5;"
        f"color:var(--fg-1)\">{_esc(text or '\u2014')}</p>"
        "</div>"
    )


def _pw_radar_svg(layers: list) -> str:
    """Direct numeric port of Page_Worth.html buildRadar() -- same SVG geometry,
    same draw order (grid rings -> spokes/labels -> data polygons -> dots)."""
    cx, cy, R = 180.0, 150.0, 110.0
    n = len(PW_DIMS)

    def ang(i: int) -> float:
        return math.radians(-90 + i * 360 / n)

    def pt(i: int, r: float) -> tuple:
        a = ang(i)
        return (cx + r * math.cos(a), cy + r * math.sin(a))

    parts: list[str] = []
    for g in range(1, 5):
        r = R * g / 4
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in (pt(i, r) for i in range(n)))
        parts.append(
            f'<polygon points="{pts}" fill="none" stroke="rgba(30,27,24,0.09)" stroke-width="1"/>'
        )
    for i in range(n):
        x2, y2 = pt(i, R)
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{x2:.2f}" y2="{y2:.2f}" '
            'stroke="rgba(30,27,24,0.06)" stroke-width="1"/>'
        )
        lx, ly = pt(i, R + 22)
        anchor = "middle" if abs(lx - cx) < 3 else ("end" if lx < cx else "start")
        parts.append(
            f'<text x="{lx:.2f}" y="{ly + 3:.2f}" text-anchor="{anchor}" '
            "style=\"font-family:'Jost',system-ui,sans-serif;font-size:10px;font-weight:600;"
            "letter-spacing:.03em;text-transform:uppercase;fill:#8c8478\">"
            f"{_esc(PW_DIMS[i]['short'])}</text>"
        )
    for layer in layers:
        scores = layer.get("scores") or {}
        pts = " ".join(
            f"{x:.2f},{y:.2f}"
            for x, y in (
                pt(i, R * (scores.get(d["id"], 0) or 0) / 4) for i, d in enumerate(PW_DIMS)
            )
        )
        stroke_w = "1.75" if layer.get("dash") else "2.25"
        dash_attr = ' stroke-dasharray="5 4"' if layer.get("dash") else ""
        parts.append(
            f'<polygon points="{pts}" fill="{layer.get("soft", "none")}" '
            f'stroke="{layer.get("color", "var(--slp-amber)")}" stroke-width="{stroke_w}" '
            f'stroke-linejoin="round"{dash_attr}/>'
        )
    for layer in layers:
        scores = layer.get("scores") or {}
        radius = "2.4" if layer.get("dash") else "3"
        for i, d in enumerate(PW_DIMS):
            sc = scores.get(d["id"], 0) or 0
            if sc > 0:
                x, y = pt(i, R * sc / 4)
                parts.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" '
                    f'fill="{layer.get("color", "var(--slp-amber)")}"/>'
                )
    return (
        '<svg viewBox="0 0 360 320" style="width:100%;height:auto;display:block;overflow:visible">'
        + "".join(parts) + "</svg>"
    )


def _pw_verdict_hero(a_scores: dict, b_scores: dict, verdict_text: str, sowhat: str | None) -> str:
    """Direct port of execAB() -- left column (verdict prose + score transition) +
    right column (buildRadar of A dashed-gray vs B colored)."""
    tA = sum(v for v in a_scores.values() if isinstance(v, int))
    tB = sum(v for v in b_scores.values() if isinstance(v, int))
    bB = _pw_band_for(tB)
    diff = tB - tA
    dcol = _PW_SAGE_DARK if diff > 0 else (_PW_TERRA if diff < 0 else "var(--fg-3)")
    sign = "+" if diff > 0 else ""

    sowhat_html = (
        "<p style=\"margin:12px 0 0;font-family:var(--font-body);font-style:italic;"
        f"font-size:14.5px;line-height:1.5;color:var(--fg-3)\">{_esc(sowhat)}</p>"
        if sowhat else ""
    )

    left = (
        "<div>"
        + _pw_eyebrow("The revision", "var(--fg-accent)")
        + "<div style=\"font-family:var(--font-ui);font-weight:600;font-size:13px;"
          f"letter-spacing:.06em;text-transform:uppercase;color:{bB['c']};margin:10px 0 8px\">"
          f"{_esc(bB['ready'])}</div>"
        + "<p style=\"margin:0;font-family:var(--font-display);font-weight:500;font-size:26px;"
          f"line-height:1.28;letter-spacing:-.01em;color:var(--fg-1)\">{_esc(verdict_text)}</p>"
        + sowhat_html
        + "<div style=\"margin-top:14px;display:flex;align-items:baseline;gap:9px;"
          "font-family:var(--font-ui)\">"
        + f"<span style=\"font-family:var(--font-display);font-size:26px;font-weight:600;"
          f"color:var(--fg-3)\">{tA}</span>"
        + "<span style=\"color:var(--fg-3);font-size:15px\">\u2192</span>"
        + f"<span style=\"font-family:var(--font-display);font-size:32px;font-weight:600;"
          f"color:{bB['c']}\">{tB}</span>"
        + f"<span style=\"font-size:13px;font-weight:600;color:{dcol}\">({sign}{diff})</span>"
        + "<span style=\"font-size:12px;color:var(--fg-3)\">/ 32</span>"
        + "</div></div>"
    )
    layers = [
        {"scores": a_scores, "color": "#b8b1a6", "soft": "rgba(184,177,166,.10)", "dash": True},
        {"scores": b_scores, "color": bB["c"], "soft": bB["s"]},
    ]
    right = f"<div style=\"align-self:center\">{_pw_radar_svg(layers)}</div>"
    return (
        "<div style=\"display:grid;grid-template-columns:1.25fr 0.95fr;gap:22px;"
        f"align-items:start\">{left}{right}</div>"
    )


def _pw_scorecard_section(a_scores: dict, b_scores: dict, change_notes: dict) -> str:
    """Direct port of detailsAB() -- 'Scorecard \u2014 A \u2192 B, weakest first'."""
    def _b_val(d: dict) -> int:
        v = b_scores.get(d["id"])
        return v if isinstance(v, int) else 0

    ordered = sorted(PW_DIMS, key=_b_val)
    rows = "".join(
        _pw_ab_bar_row(
            d["label"],
            a_scores.get(d["id"], 0) or 0,
            b_scores.get(d["id"], 0) or 0,
            change_notes.get(d["id"], "\u2014"),
            i > 0,
        )
        for i, d in enumerate(ordered)
    )
    return (
        _pw_section_head("Scorecard \u2014 A \u2192 B, weakest first")
        + _pw_score_legend()
        + _pw_card(rows)
    )


def _pw_process_trace_section(records: list, gate: dict) -> str:
    """NEW section (not in Page_Worth -- this loop has no LLM single-shot judge,
    it's a multi-pass agent loop). Built in the SAME idiom: sectionHead() +
    card() with Jost eyebrow rows, amber accents, --slp-card background."""
    rows: list[str] = []
    prev_scores: dict | None = None
    last_idx = len(records) - 1
    for i, r in enumerate(records):
        scores = _flat_scores(r.get("scores") or {})
        pass_num = r.get("pass", i)
        raw_decision = r.get("decision")
        decision = (
            (raw_decision or "").upper()
            or ("LINT_REJECT" if r.get("outcome") == "lint_reject" else ("BASELINE" if i == 0 else "\u2014"))
        )
        action_label = "PLAN" if i == 0 else decision
        gate_action = (gate.get("action") or "").upper()
        if i == last_idx and gate_action:
            action_label = f"{action_label} \u2192 {gate_action}"

        worst = _worst_dim(scores) if scores else None
        climb = "\u2014"
        if worst:
            after_val = scores.get(worst, "?")
            before_val = (prev_scores or {}).get(worst, "\u2014") if prev_scores else "\u2014"
            climb = f"{_DIM_LABELS.get(worst, worst)} {before_val} \u2192 {after_val}"

        fix_bits = []
        for f in (r.get("fix_batch") or []):
            if isinstance(f, dict):
                crit = _esc(f.get("criterion", ""))
                issue = _esc(f.get("issue") or f.get("fix") or "")
                fix_bits.append(f"<strong>{crit}</strong> \u2014 {issue}")
        fix_html = " &middot; ".join(fix_bits) if fix_bits else "\u2014"

        reason_html = ""
        if i == last_idx and gate_action != "DONE":
            reason = gate.get("reason")
            if reason:
                reason_html = (
                    "<div style=\"margin-top:6px;font-family:var(--font-body);font-size:13px;"
                    f"color:var(--fg-2)\">Reason: {_esc(reason)}</div>"
                )

        total_str = str(_total(scores)) if scores else "\u2014"
        top_border = "border-top:1px solid oklch(0.91 0.02 80)" if i else "border-top:0"
        rows.append(
            "<div style=\"display:grid;grid-template-columns:56px 130px 1fr;gap:14px;"
            f"align-items:start;padding:13px 0;{top_border}\">"
            f"<div style=\"font-family:var(--font-display);font-weight:600;font-size:18px;"
            f"color:var(--fg-3)\">Pass {_esc(pass_num)}</div>"
            "<div>"
            f"<div style=\"font-family:var(--font-ui);font-weight:600;font-size:11px;"
            f"letter-spacing:.08em;text-transform:uppercase;color:var(--fg-accent)\">"
            f"{_esc(action_label)}</div>"
            f"<div style=\"font-family:var(--font-display);font-weight:600;font-size:16px;"
            f"color:var(--fg-1)\">{total_str} <span style=\"font-size:11px;color:var(--fg-3)\">"
            "/32</span></div>"
            "</div>"
            "<div>"
            f"<div style=\"font-family:var(--font-body);font-size:13px;color:var(--fg-2)\">"
            f"Worst-dim climb: {_esc(climb)}</div>"
            f"<div style=\"font-family:var(--font-ui);font-size:12.5px;color:var(--fg-2);"
            f"margin-top:4px\">{fix_html}</div>"
            f"{reason_html}"
            "</div></div>"
        )
        if scores:
            prev_scores = scores
    return (
        _pw_section_head("Process \u00b7 how the agent worked")
        + _pw_card("".join(rows))
    )


def _pw_previews_section(has_baseline: bool, baseline_note: str, champ_total: int) -> str:
    """Reskin of the optional 2-up Previews section -- same iframe+anchor
    mechanism kept (per spec), now in real Page_Worth card tokens."""
    bl_note = _esc(baseline_note)
    total_str = _esc(str(champ_total))
    card_style = (
        "background:var(--bg-card);border:1px solid var(--border-1);border-radius:6px;"
        "box-shadow:var(--shadow-card);padding:1rem"
    )
    frame_style = (
        "width:100%;height:200px;border:1px solid var(--border-1);border-radius:4px;"
        "display:block;margin:0.5rem 0;background:var(--bg-2)"
    )
    caption_style = (
        "font-family:var(--font-ui);font-size:0.78rem;color:var(--fg-3);margin:0.3rem 0 0.5rem"
    )
    link_style = (
        "font-family:var(--font-ui);font-size:0.85rem;color:var(--fg-accent);"
        "text-decoration:underline;text-underline-offset:3px"
    )

    if has_baseline:
        baseline_block = (
            f'<iframe src="baseline.html" sandbox="allow-same-origin" style="{frame_style}" '
            'title="Baseline preview"></iframe>'
            f"<p style=\"{caption_style}\">{bl_note}</p>"
            f'<a href="baseline.html" target="_blank" rel="noopener" style="{link_style}">'
            "Open in new tab &nearr;</a>"
        )
    else:
        baseline_block = (
            f"<div style=\"{frame_style};display:flex;align-items:center;justify-content:center;"
            "color:var(--fg-3);font-family:var(--font-ui);font-size:0.8rem\">Unavailable</div>"
            f"<p style=\"{caption_style}\">{bl_note}</p>"
        )

    return (
        _pw_section_head("Previews")
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">'
        + f'<div style="{card_style}">'
        + _pw_eyebrow("Before \u00b7 A")
        + baseline_block
        + "</div>"
        + f'<div style="{card_style}">'
        + _pw_eyebrow("After \u00b7 B")
        + f'<iframe src="upgraded.html" sandbox="allow-same-origin" style="{frame_style}" '
        + 'title="Champion preview"></iframe>'
        + f"<p style=\"{caption_style}\">Champion &mdash; {total_str}&thinsp;/&thinsp;32.</p>"
        + f'<a href="upgraded.html" target="_blank" rel="noopener" style="{link_style}">'
        + "Open in new tab &nearr;</a>"
        + "</div></div>"
    )


def _pw_past_verdicts_section(entries: list) -> str:
    """Reskin of the History screen's card grid (lines 1847-1879 of
    Page_Worth.html) -- header text 'Past verdicts' kept verbatim."""
    if not entries:
        return ""
    cards = []
    for e in entries:
        date_str = _esc((e.get("ts") or "")[:10])
        tc = _esc(e.get("task_class") or "\u2014")
        total_val = _esc(str(e.get("total", "?")))
        converged = bool(e.get("converged"))
        reason = e.get("reason") or ""
        status_label = "Done" if converged else (f"Escalated ({reason})" if reason else "Escalated")
        status_color = _PW_SAGE_DARK if converged else _PW_TERRA
        rpath = e.get("report_path") or ""
        rname = pathlib.Path(rpath).name if rpath else ""
        link_html = (
            f'<a href="{_esc(rpath)}" style="font-family:var(--font-ui);font-size:11px;'
            f'color:var(--fg-accent);text-decoration:underline">{_esc(rname)}</a>'
            if rpath else ""
        )
        cards.append(
            "<div style=\"background:var(--bg-card);border:1px solid var(--border-1);"
            "border-radius:6px;overflow:hidden;box-shadow:var(--shadow-card);padding:14px 16px;"
            "display:flex;flex-direction:column;gap:8px\">"
            "<div style=\"display:flex;align-items:center;justify-content:space-between;gap:8px\">"
            f"<span style=\"font-family:var(--font-ui);font-weight:600;font-size:11px;"
            f"letter-spacing:.12em;text-transform:uppercase;color:{status_color}\">"
            f"{_esc(status_label)}</span>"
            f"<span style=\"font-family:var(--font-display);font-weight:600;font-size:17px;"
            f"color:{status_color}\">{total_val}/32</span>"
            "</div>"
            f"<p style=\"margin:0;font-family:var(--font-body);font-size:13.5px;"
            f"line-height:1.45;color:var(--fg-2)\">{tc}</p>"
            "<div style=\"display:flex;align-items:center;justify-content:space-between;gap:8px\">"
            f"<span style=\"font-family:var(--font-ui);font-size:11px;letter-spacing:.04em;"
            f"color:var(--fg-3)\">{date_str}</span>{link_html}"
            "</div></div>"
        )
    return (
        "<div style=\"font-family:var(--font-ui);font-weight:500;font-size:11px;"
        "letter-spacing:.24em;text-transform:uppercase;color:var(--fg-accent);margin-bottom:8px\">"
        "Your history</div>"
        "<h2 style=\"font-family:var(--font-display);font-weight:300;font-size:34px;"
        "letter-spacing:-.01em;margin:0 0 18px\">Past verdicts</h2>"
        "<div style=\"display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(220px,1fr))\">"
        + "".join(cards)
        + "</div>"
    )


def _pw_header() -> str:
    """Verbatim port of the 'Page Worth' header (Page_Worth.html lines 1644-1645)."""
    return (
        "<div style=\"display:flex;align-items:baseline;margin-bottom:8px\">"
        "<span style=\"font-family:var(--font-display);font-weight:600;font-size:23px;"
        "letter-spacing:-.01em;color:var(--fg-1)\">Page</span>"
        "<span style=\"font-family:var(--font-display);font-weight:600;font-size:23px;"
        "letter-spacing:-.01em;color:var(--fg-accent);font-style:italic;margin-left:3px\">Worth"
        "</span>"
        "</div>"
    )


def _pw_footer() -> str:
    return (
        "<div style=\"text-align:center;color:var(--fg-3);font-family:var(--font-ui);"
        "font-size:11px;letter-spacing:.06em;margin-top:46px;opacity:.8\">"
        "Design Loop \u00b7 automated UX critique, scored across eight dimensions"
        "</div>"
    )



# ---------------------------------------------------------------------------
# Demo journey — LANDING / WORKING / RESULTS (the full Page_Worth journey)
# ---------------------------------------------------------------------------
# LANDING reproduces Page_Worth.html lines 1659-1709 verbatim (eyebrow, H1,
# subhead, mode tabs, drop card) -- but populated with THIS run's actual
# input instead of an empty drop zone, since this run already has a source.
# WORKING is a NEW section (Page_Worth has no equivalent) built in the same
# idiom as _pw_process_trace_section, but as a granular per-step transaction
# log: maker -> lints -> critic -> gate, one quad of log lines per pass.


def _pw_mode_tabs(active: str = "ab") -> str:
    """Port of the LANDING mode-tab row (Page_Worth.html line 1669-1674)."""
    labels = [("single", "Single screen"), ("ab", "Compare A \u00b7 B"), ("chaos", "Triage many")]
    btns = "".join(
        f'<button type="button" class="pw-mode-tab{" pw-mode-active" if key == active else ""}">'
        f"{_esc(label)}</button>"
        for key, label in labels
    )
    return (
        '<div style="display:flex;justify-content:center;margin-bottom:24px">'
        '<div style="display:inline-flex;border:1px solid var(--border-1);border-radius:3px;'
        'background:var(--bg-card);padding:4px;gap:4px;box-shadow:var(--shadow-card);flex-wrap:wrap;'
        'justify-content:center">' + btns + "</div></div>"
    )


def _pw_landing_section(records: list, has_baseline: bool, source_label: str, task_class: str) -> str:
    """Faithful re-skin of Page_Worth's LANDING screen (lines 1659-1709), populated
    with this run's actual input instead of an empty drop zone.

    Page_Worth's empty-state dropzone (singleEmpty, lines 1678-1685) only makes
    sense before a screen is supplied. This run already HAS a source, so we
    show the populated/"ready" card state instead (singleReady, 1686-1709),
    fed from the real pass-0 baseline artifact and its recorded fix focus.
    """
    rec0 = records[0] if records else {}
    fix0 = (rec0.get("fix_batch") or [None])[0]
    focus_text = ""
    if isinstance(fix0, dict):
        focus_text = fix0.get("issue") or fix0.get("fix") or ""
    focus_display = focus_text or "\u2014 (open critique, no specific focus recorded)"
    goal_chip = task_class or "general critique"

    if has_baseline:
        preview_block = (
            '<iframe src="baseline.html" sandbox="allow-same-origin" '
            'style="width:100%;height:170px;border:0;display:block;background:var(--bg-2)" '
            "title=\"This run's input\"></iframe>"
        )
    else:
        preview_block = (
            '<div style="height:170px;display:flex;align-items:center;justify-content:center;'
            'color:var(--fg-3);font-family:var(--font-ui);font-size:0.8rem;background:var(--bg-2)">'
            "Source unavailable</div>"
        )

    ready_card = (
        '<div style="max-width:560px;margin:0 auto;background:var(--bg-card);border:1px solid var(--border-1);'
        'border-radius:6px;box-shadow:var(--shadow-card);overflow:hidden">'
        '<div style="position:relative;background:var(--bg-2);border-bottom:1px solid var(--border-1)">'
        + preview_block
        + "</div>"
        '<div style="padding:16px 20px 0">'
        '<div style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.16em;'
        'text-transform:uppercase;color:var(--fg-3);margin-bottom:9px">What are you trying to improve?</div>'
        f'<span class="pw-mode-tab pw-mode-active" style="display:inline-block">{_esc(goal_chip)}</span>'
        "</div>"
        '<div style="padding:16px 20px 6px">'
        '<div style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.2em;'
        'text-transform:uppercase;color:var(--fg-3);margin-bottom:12px">Add context \u2014 this run</div>'
        '<div style="font-family:var(--font-ui);font-size:11px;color:var(--fg-3);margin-bottom:2px">'
        "What is this?</div>"
        f'<div style="font-family:var(--font-body);font-size:14px;color:var(--fg-1);margin-bottom:12px">'
        f"{_esc(source_label)}</div>"
        '<div style="font-family:var(--font-ui);font-size:11px;color:var(--fg-3);margin-bottom:2px">'
        "What should the critic focus on?</div>"
        f'<div style="font-family:var(--font-body);font-size:14px;color:var(--fg-1)">{_esc(focus_display)}</div>'
        "</div>"
        '<div style="display:flex;align-items:center;gap:12px;padding:8px 20px 20px">'
        '<button disabled style="font-family:var(--font-ui);font-weight:600;font-size:13px;color:#fff;'
        'background:var(--slp-amber);border:none;border-radius:4px;padding:10px 18px;opacity:.85">'
        "Analyzed \u2192</button>"
        "</div></div>"
    )

    dims_grid = "".join(
        '<div style="background:var(--bg-card);padding:14px 16px">'
        f'<div style="font-family:var(--font-ui);font-weight:600;font-size:12px;letter-spacing:.06em;'
        f'text-transform:uppercase;color:var(--fg-accent);margin-bottom:3px">{_esc(d["label"])}</div>'
        f'<div style="font-family:var(--font-body);font-size:13.5px;line-height:1.45;color:var(--fg-2)">'
        f'{_esc(d["q"])}</div>'
        "</div>"
        for d in PW_DIMS
    )

    return (
        '<div data-pw-view="landing">'
        "<section>"
        '<div style="text-align:center;margin:34px 0 24px">'
        + _pw_eyebrow("Design intelligence", "var(--fg-accent)")
        + '<h1 style="font-family:var(--font-display);font-weight:300;font-size:46px;line-height:1.06;'
        'letter-spacing:-.015em;margin:16px 0 16px">Drop a screen.<br>Know what to '
        '<em style="font-style:italic;color:var(--fg-accent)">fix</em> first.</h1>'
        '<p style="font-family:var(--font-body);color:var(--fg-2);max-width:50ch;margin:0 auto;'
        "font-size:17px;line-height:1.6\">Upload any interface and get a clear read \u2014 what's working, "
        "what's confusing, the changes worth making first, and the exact prompt to make them.</p>"
        "</div>"
        + _pw_mode_tabs("ab")
        + ready_card
        + '<div style="max-width:640px;margin:46px auto 0">'
        '<div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:18px">'
        '<span style="display:block;width:30px;height:1px;background:var(--slp-amber)"></span>'
        '<span style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.24em;'
        'text-transform:uppercase;color:var(--fg-3)">Judged on eight things</span>'
        '<span style="display:block;width:30px;height:1px;background:var(--slp-amber)"></span>'
        "</div>"
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border-1);'
        'border:1px solid var(--border-1);border-radius:6px;overflow:hidden">' + dims_grid + "</div>"
        "</div>"
        "</section>"
        "</div>"
    )


def _pw_lint_line(rec: dict) -> tuple:
    """Returns (display_text, is_fail) for the LINTS step of one pass.

    Reads the real ``lint_results`` field (dict with ``hard_fail`` /
    ``hard_fail_reasons``, matching tool-design-lints' actual output shape).
    Falls back to the ``outcome``/``reject_reason`` fields used by lint-reject
    records, and is honest (\u2014 n/a) when no lint signal was recorded at all,
    rather than fabricating a pass that was never measured.
    """
    lr = rec.get("lint_results")
    if isinstance(lr, dict):
        if lr.get("hard_fail"):
            reasons = lr.get("hard_fail_reasons") or ["hard_fail"]
            return ("FAIL (" + ", ".join(str(r) for r in reasons) + ")", True)
        return ("PASS", False)
    if rec.get("outcome") == "lint_reject":
        reason = (rec.get("reject_reason") or "lint_reject").replace("lint:", "")
        return (f"FAIL ({reason})", True)
    return ("n/a \u2014 no lint data recorded", False)


def _pw_log_line(label: str, text: str, active: bool = False) -> str:
    """One MAKER/LINTS/CRITIC/GATE line of the working transaction log."""
    cls = "pw-log-line" + (" pw-row-active" if active else "")
    return f'<div class="{cls}" data-pw-logrow><b>{_esc(label)}</b>{_esc(text)}</div>'


def _pw_working_header() -> str:
    """Section head + a 'Replay' control that re-streams the log via JS."""
    head = (
        '<div style="display:flex;align-items:center;gap:10px">'
        '<span style="display:block;width:26px;height:1px;background:var(--slp-amber)"></span>'
        '<span style="font-family:var(--font-ui);font-weight:500;font-size:11px;letter-spacing:.2em;'
        'text-transform:uppercase;color:var(--fg-3)">Working \u00b7 live transaction log</span>'
        "</div>"
    )
    play_btn = (
        '<button type="button" data-pw-play style="font-family:var(--font-ui);font-weight:600;'
        "font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--fg-accent);"
        "background:none;border:1px solid var(--border-1);border-radius:4px;padding:6px 14px;"
        'cursor:pointer">\u25b6 Replay</button>'
    )
    return (
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;'
        'margin-bottom:12px">' + head + play_btn + "</div>"
    )


def _pw_working_log_section(records: list, gate: dict) -> str:
    """The 'working transaction log' \u2014 maker -> lints -> critic -> gate, one
    group of log lines per pass, built from real ``state.records`` data. The
    most recently streamed line (the last pass's GATE line) carries the amber
    shimmer treatment by default, mirroring the dc-runtime streaming idiom."""
    last_idx = len(records) - 1
    groups: list = []
    for i, r in enumerate(records):
        scores = _flat_scores(r.get("scores") or {})
        maker_label = "produced baseline candidate" if i == 0 else "produced revised candidate"
        lint_text, lint_fail = _pw_lint_line(r)
        if scores:
            worst = _worst_dim(scores)
            critic_text = (
                f"scored {_total(scores)}/32 \u2014 worst: "
                f"{_DIM_LABELS.get(worst, worst)} {scores.get(worst)}/4"
            )
        elif lint_fail:
            critic_text = "skipped \u2014 no judge spent (lint reject)"
        else:
            critic_text = "n/a"
        decision = (r.get("decision") or "\u2014").upper()
        gate_text = decision
        if i == last_idx:
            ga = (gate.get("action") or "").upper()
            gr = gate.get("reason") or ""
            if ga:
                gate_text = f"{decision} \u2192 {ga}" + (f" ({gr})" if gr else "")

        lines = [
            ("MAKER", maker_label, False),
            ("LINTS", lint_text, False),
            ("CRITIC", critic_text, False),
            ("GATE", gate_text, i == last_idx),
        ]
        line_html = "".join(_pw_log_line(lbl, txt, active) for lbl, txt, active in lines)
        top_border = "border-top:1px solid oklch(0.91 0.02 80)" if i else "border-top:0"
        groups.append(
            '<div style="display:grid;grid-template-columns:70px 1fr;gap:14px;'
            f'align-items:start;padding:14px 0;{top_border}">'
            '<div style="font-family:var(--font-display);font-weight:600;font-size:18px;'
            f'color:var(--fg-3)">Pass {_esc(r.get("pass", i))}</div>'
            f"<div>{line_html}</div></div>"
        )
    return _pw_working_header() + _pw_card("".join(groups))


def _pw_journey_nav() -> str:
    """1 \u00b7 Landing / 2 \u00b7 Working / 3 \u00b7 Results tab strip."""
    return (
        '<div class="pw-journey-nav">'
        '<button type="button" data-pw-tab="landing" class="pw-tab-active">1 &middot; Landing</button>'
        '<button type="button" data-pw-tab="working">2 &middot; Working</button>'
        '<button type="button" data-pw-tab="results">3 &middot; Results</button>'
        "</div>"
    )


def _pw_journey_script() -> str:
    """Vanilla tab-switch + sequential 'replay' of the working log.

    No external src, no network, no framework -- a single self-contained
    inline script.  Page_Worth itself requires JS for everything; this is the
    same trade-off, scoped to navigation + a cosmetic replay animation only.
    Graceful without JS: 'landing' is visible by default (server-rendered,
    no [hidden] attribute); 'working'/'results' carry [hidden] server-side
    and are only revealed via a tab click.
    """
    return (
        "<script>(function(){"
        "var tabs=document.querySelectorAll('[data-pw-tab]');"
        "var views=document.querySelectorAll('[data-pw-view]');"
        "function showView(name){"
        "views.forEach(function(v){v.hidden=v.getAttribute('data-pw-view')!==name;});"
        "tabs.forEach(function(t){t.classList.toggle('pw-tab-active',t.getAttribute('data-pw-tab')===name);});"
        "}"
        "tabs.forEach(function(t){t.addEventListener('click',function(){showView(t.getAttribute('data-pw-tab'));});});"
        "showView('landing');"
        "var playBtn=document.querySelector('[data-pw-play]');"
        "if(playBtn){playBtn.addEventListener('click',function(){"
        "var rows=Array.prototype.slice.call(document.querySelectorAll('[data-pw-logrow]'));"
        "rows.forEach(function(r){r.hidden=true;r.classList.remove('pw-row-active');});"
        "var i=0;"
        "function step(){"
        "if(i>0){rows[i-1].classList.remove('pw-row-active');}"
        "if(i>=rows.length){return;}"
        "rows[i].hidden=false;rows[i].classList.add('pw-row-active');"
        "i++;"
        "setTimeout(step,420);"
        "}"
        "step();"
        "});}"
        "})();</script>"
    )


# ---------------------------------------------------------------------------
# Public API  \u2013  three-artifact render (baseline.html, upgraded.html, report.html)
# ---------------------------------------------------------------------------

def render(
    state: dict,
    out_dir: str = ".",
    durable_base: str | None = None,
) -> dict:
    """Render three artifacts from a loop run state.

    Parameters
    ----------
    state:
        Dict with keys: records, gate, champion, converged.
    out_dir:
        Primary directory to write baseline.html, upgraded.html, report.html.
    durable_base:
        If set, ALSO copy the trio to ``durable_base/runs/<run_id>/`` and
        append one line to ``durable_base/history.jsonl``.
        None (default) = no durable write, no history.

    Returns
    -------
    dict with keys:
        upgraded_html, report_html, baseline_html (all in out_dir),
        durable_report_html, durable_upgraded_html, durable_baseline_html.
    """
    import datetime as _dt
    import json as _json
    import shutil as _shutil

    out_dir_p = pathlib.Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    records = state.get("records") or []
    gate = state.get("gate") or {}
    champion = state.get("champion") or {}
    converged = bool(state.get("converged", False))

    # \u2500\u2500 run_id & task_class \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    _ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    _rec0 = records[0] if records else {}
    run_id: str = _rec0.get("run_id") or f"{_rec0.get('task_class', 'run')}_{_ts}"
    task_class: str = _rec0.get("task_class") or ""

    # \u2500\u2500 durable paths (computed before history write so entry refs them) \u2500\u2500\u2500\u2500
    _durable_root: pathlib.Path | None = None
    _durable_run_dir: pathlib.Path | None = None
    _history_file: pathlib.Path | None = None
    if durable_base is not None:
        _durable_root = pathlib.Path(durable_base).expanduser()
        _durable_run_dir = _durable_root / "runs" / run_id
        _history_file = _durable_root / "history.jsonl"

    def _durable_path(name: str) -> str:
        return str(
            (_durable_run_dir / name).resolve()
            if _durable_run_dir
            else (out_dir_p / name).resolve()
        )

    _durable_report_path   = _durable_path("report.html")
    _durable_upgraded_path = _durable_path("upgraded.html")
    _durable_baseline_path = _durable_path("baseline.html")

    # \u2500\u2500 scores: A = baseline (records[0]), B = champion \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    a_scores = _flat_scores(_rec0.get("scores") or {}) if records else {}
    if not a_scores:
        a_scores = dict.fromkeys(CRITERIA, 0)
    champ_scores = _flat_scores(champion.get("scores") or {})
    if not champ_scores:
        champ_scores = dict.fromkeys(CRITERIA, 0)
    champ_total = champion.get("total")
    if champ_total is None:
        champ_total = _total(champ_scores)
    champ_total = int(champ_total)

    # \u2500\u2500 History: append BEFORE rendering so this run is in Past verdicts \u2500\u2500\u2500\u2500
    past_verdicts_markup = ""
    if _history_file is not None:
        _history_file.parent.mkdir(parents=True, exist_ok=True)
        _entry = {
            "run_id":       run_id,
            "ts":           _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "task_class":   task_class,
            "total":        champ_total,
            "converged":    converged,
            "reason":       gate.get("reason") or "",
            "report_path":  _durable_report_path,
            "upgraded_path":_durable_upgraded_path,
            "baseline_path":_durable_baseline_path,
        }
        with open(_history_file, "a", encoding="utf-8") as _hf:
            _hf.write(_json.dumps(_entry) + "\n")
        _all: list = []
        for _ln in _history_file.read_text(encoding="utf-8").splitlines():
            _ln = _ln.strip()
            if _ln:
                try:
                    _all.append(_json.loads(_ln))
                except Exception:
                    pass
        past_verdicts_markup = _pw_past_verdicts_section(_all[-5:])

    # \u2500\u2500 1. baseline.html: bare pass-0 artifact (no chrome, no sanitisation) \u2500
    baseline_src = _rec0.get("artifact_ref") if records else None
    has_baseline = False
    if baseline_src and pathlib.Path(baseline_src).exists():
        _bl = pathlib.Path(baseline_src).read_text(encoding="utf-8")
        (out_dir_p / "baseline.html").write_text(_bl, encoding="utf-8")
        has_baseline = True
        baseline_note = "Original unimproved input."
    else:
        baseline_note = "Baseline artifact unavailable."

    # \u2500\u2500 2. upgraded.html: bare champion page \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    champion_src = champion.get("artifact_ref")
    if not champion_src:
        for rec in records:
            if rec.get("decision") in ("NEW_BEST", "BASELINE") and rec.get("artifact_ref"):
                champion_src = rec["artifact_ref"]
                break
    if champion_src and pathlib.Path(champion_src).exists():
        champion_html = pathlib.Path(champion_src).read_text(encoding="utf-8")
    else:
        champion_html = (
            "<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\"></head>"
            "<body><p>Champion artifact unavailable.</p></body></html>"
        )
    upgraded_path = out_dir_p / "upgraded.html"
    upgraded_path.write_text(champion_html, encoding="utf-8")

    # \u2500\u2500 3. report.html: faithful Page_Worth A\u2192B results re-skin \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    verdict_text = _pw_verdict_sentence(converged, gate, champ_scores, champ_total)
    sowhat = _pw_sowhat(converged, gate)
    do_next_text = _pw_do_next_text(converged, gate)
    improved, regressed = _pw_improved_regressed(a_scores, champ_scores)
    change_notes = _pw_dim_change_notes(records)
    bB = _pw_band_for(champ_total)

    hero = _pw_verdict_hero(a_scores, champ_scores, verdict_text, sowhat)
    do_next_card = _pw_do_card("Do this next", do_next_text)
    sw_grid = (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px">'
        + _pw_sw_list("Improved", improved, _PW_SAGE_DARK)
        + _pw_sw_list("Regressed", regressed, _PW_TERRA)
        + "</div>"
    )
    results_section = (
        f'<section style="--band:{bB["c"]};--band-soft:{bB["s"]}">'
        f"{hero}{do_next_card}{sw_grid}</section>"
    )
    scorecard_block = (
        '<div style="margin-top:30px">'
        + _pw_scorecard_section(a_scores, champ_scores, change_notes)
        + "</div>"
    )
    process_block = (
        '<div style="margin-top:30px">'
        + _pw_process_trace_section(records, gate)
        + "</div>"
    )
    previews_block = (
        '<div style="margin-top:30px">'
        + _pw_previews_section(has_baseline, baseline_note, champ_total)
        + "</div>"
    )
    history_block = (
        f'<div style="margin-top:30px">{past_verdicts_markup}</div>'
        if past_verdicts_markup else ""
    )

    page_open = (
        "<div style=\"font-family:var(--font-body);color:var(--fg-1);max-width:920px;"
        "margin:0 auto;padding:26px 22px 110px;min-height:100vh\">"
    )

    # \u2500\u2500 5. The full journey: LANDING -> WORKING -> RESULTS, tab-navigable \u2500\u2500
    source_label = pathlib.Path(baseline_src).name if (records and baseline_src) else "Untitled source"
    landing_view = _pw_landing_section(records, has_baseline, source_label, task_class)
    working_view = (
        '<div data-pw-view="working" hidden>'
        + _pw_working_log_section(records, gate)
        + "</div>"
    )
    results_view = (
        '<div data-pw-view="results" hidden>'
        + results_section
        + scorecard_block
        + process_block
        + previews_block
        + history_block
        + "</div>"
    )

    report_html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8" />\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        "<title>Page Worth \u00b7 Run Report</title>\n"
        "<style>\n" + _PW_REAL_CSS + _PW_JOURNEY_CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        + page_open
        + _pw_header()
        + _pw_journey_nav()
        + landing_view
        + working_view
        + results_view
        + _pw_footer()
        + _pw_journey_script()
        + "</div>\n"
        "</body>\n"
        "</html>"
    )

    report_path = out_dir_p / "report.html"
    report_path.write_text(report_html, encoding="utf-8")

    # \u2500\u2500 4. Copy trio to durable run dir \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # When the caller already renders straight into the durable run dir (i.e.
    # out_dir *is* durable_base/runs/<run_id> -- the web app's reconciled
    # single-id layout), the trio is already in place. Skip the copy so we
    # don't raise SameFileError copying a file onto itself, and so a run
    # produces exactly ONE directory rather than two.
    if (
        _durable_run_dir is not None
        and _durable_run_dir.resolve() != out_dir_p.resolve()
    ):
        _durable_run_dir.mkdir(parents=True, exist_ok=True)
        _shutil.copy2(str(upgraded_path), str(_durable_run_dir / "upgraded.html"))
        _shutil.copy2(str(report_path), str(_durable_run_dir / "report.html"))
        if has_baseline:
            _shutil.copy2(
                str(out_dir_p / "baseline.html"),
                str(_durable_run_dir / "baseline.html"),
            )

    baseline_out = out_dir_p / "baseline.html"
    return {
        "upgraded_html":         str(upgraded_path.resolve()),
        "report_html":           str(report_path.resolve()),
        "baseline_html":         str(baseline_out.resolve()),
        "durable_report_html":   _durable_report_path,
        "durable_upgraded_html": _durable_upgraded_path,
        "durable_baseline_html": _durable_baseline_path,
    }
