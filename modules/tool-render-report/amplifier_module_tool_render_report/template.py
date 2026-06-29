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

import html as _html
from typing import Any

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
