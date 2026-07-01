"""Deterministic, no-LLM ground-truth audit of a page -- the "objective" half
of a senior design review (accessibility + hygiene), run against the user's
ACTUAL markup.

Two tiers, both free and deterministic (in the spirit of the loop's
tool-design-lints "deterministic bricks", which anchor the subjective critic):

* Static tier (always available, stdlib only): parses the HTML and checks
  viewport meta, lang, <title>, heading order, images missing alt, form inputs
  without labels, vague link text, and "slop" signals (gradient heroes, heavy
  shadows, default fonts) that map to the critic's `restraint` definition.

* Browser tier (best, when Playwright is importable): reuses the bundle's own
  `tool-design-lints.run_lints` for the metrics you can only get by rendering --
  `wcag_contrast_min`, `contrast_pass`, `focus_reachable`, `viewport_overflow`.

Each finding is {id, label, status: pass|warn|fail, detail}. The Results screen
renders these as the "Accessibility & ground truth" section so the critique is
demonstrably about the user's real page, not a rubric run in a vacuum.
"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import Any

logger = logging.getLogger(__name__)

_VAGUE_LINKS = {"click here", "here", "read more", "learn more", "more", "link"}
_DEFAULT_FONTS = ("inter", "roboto", "arial", "helvetica")


class _Collector(HTMLParser):
    """Single-pass collector of the few facts the static checks need."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.has_viewport = False
        self.has_lang = False
        self.title_parts: list[str] = []
        self._in_title = False
        self.headings: list[int] = []
        self.img_total = 0
        self.img_no_alt = 0
        self.inputs_total = 0
        self.inputs_labelled = 0
        self.has_any_label = False
        self.links: list[str] = []
        self._link_depth = 0
        self._cur_link = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html" and a.get("lang", "").strip():
            self.has_lang = True
        if tag == "meta" and a.get("name", "").lower() == "viewport":
            self.has_viewport = True
        if tag == "title":
            self._in_title = True
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        if tag == "img":
            self.img_total += 1
            if "alt" not in a:
                self.img_no_alt += 1
        if tag == "label":
            self.has_any_label = True
        if tag == "input":
            itype = a.get("type", "text").lower()
            if itype not in ("hidden", "submit", "button", "image"):
                self.inputs_total += 1
                if a.get("aria-label") or a.get("aria-labelledby") or a.get("id"):
                    self.inputs_labelled += 1
        if tag == "a":
            self._link_depth = 1
            self._cur_link = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._link_depth:
            self.links.append(self._cur_link.strip())
            self._link_depth = 0

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._link_depth:
            self._cur_link += data


def _f(fid: str, label: str, status: str, detail: str) -> dict[str, str]:
    return {"id": fid, "label": label, "status": status, "detail": detail}


def audit_html_static(html: str) -> list[dict[str, str]]:
    """Pure-Python accessibility/hygiene checks over raw HTML. Never raises."""
    findings: list[dict[str, str]] = []
    try:
        c = _Collector()
        c.feed(html or "")
    except Exception:
        logger.warning("static audit parse failed", exc_info=True)
        return findings

    findings.append(
        _f("viewport", "Mobile viewport", "pass", "Has a responsive viewport meta tag.")
        if c.has_viewport
        else _f(
            "viewport",
            "Mobile viewport",
            "fail",
            "No <meta name=viewport> -- the page won't adapt to phones.",
        )
    )
    findings.append(
        _f("lang", "Language set", "pass", "<html lang> is present for screen readers.")
        if c.has_lang
        else _f("lang", "Language set", "warn", "No lang attribute on <html>.")
    )
    title = " ".join(" ".join(c.title_parts).split())
    findings.append(
        _f("title", "Page title", "pass", "Has a <title>: " + (title[:50]))
        if title
        else _f("title", "Page title", "warn", "Missing or empty <title>.")
    )

    if not c.headings:
        findings.append(
            _f("headings", "Heading structure", "warn", "No headings found (no h1-h6).")
        )
    else:
        h1s = c.headings.count(1)
        skipped = any(
            b - a > 1 for a, b in zip(c.headings, c.headings[1:]) if b > a
        )
        if h1s == 0:
            findings.append(
                _f("headings", "Heading structure", "warn", "No <h1> -- unclear top-level topic.")
            )
        elif h1s > 1:
            findings.append(
                _f("headings", "Heading structure", "warn", f"{h1s} <h1>s -- there should be one.")
            )
        elif skipped:
            findings.append(
                _f("headings", "Heading structure", "warn", "Heading levels skip (e.g. h1 -> h3).")
            )
        else:
            findings.append(
                _f("headings", "Heading structure", "pass", "Single h1 with a sane outline.")
            )

    if c.img_total == 0:
        findings.append(_f("alt", "Image alt text", "pass", "No <img> tags to caption."))
    elif c.img_no_alt == 0:
        findings.append(
            _f("alt", "Image alt text", "pass", f"All {c.img_total} images have alt text.")
        )
    else:
        findings.append(
            _f(
                "alt",
                "Image alt text",
                "fail",
                f"{c.img_no_alt} of {c.img_total} images have no alt attribute.",
            )
        )

    if c.inputs_total:
        if c.inputs_labelled >= c.inputs_total and c.has_any_label:
            findings.append(_f("labels", "Form labels", "pass", "Inputs appear labelled."))
        else:
            findings.append(
                _f(
                    "labels",
                    "Form labels",
                    "warn",
                    f"{c.inputs_total} input(s); some may lack an associated <label>.",
                )
            )

    vague = [t for t in c.links if t.lower() in _VAGUE_LINKS]
    if c.links:
        if vague:
            findings.append(
                _f(
                    "linktext",
                    "Link text",
                    "warn",
                    f'{len(vague)} vague link(s) like "{vague[0]}" -- say where they go.',
                )
            )
        else:
            findings.append(_f("linktext", "Link text", "pass", "Links use descriptive text."))

    # Slop signals -> the critic's `restraint` ground truth.
    low = (html or "").lower()
    slop = []
    if "linear-gradient" in low:
        slop.append("gradient")
    if low.count("box-shadow") >= 3:
        slop.append("heavy shadows")
    if any(("font-family" in low and fnt in low) for fnt in _DEFAULT_FONTS) and (
        "@font-face" not in low
    ):
        slop.append("default fonts")
    if slop:
        findings.append(
            _f(
                "restraint",
                "Slop signals",
                "warn",
                "Detected " + ", ".join(slop) + " -- common 'AI default' tells (restraint).",
            )
        )

    return findings


async def browser_lints(
    *, html: str | None = None, url: str | None = None
) -> dict[str, Any] | None:
    """Reuse the bundle's deterministic render lints for metrics that require a
    real browser (WCAG contrast, focus, viewport overflow). Returns None if
    Playwright / the lints module isn't importable in this environment.
    """
    try:
        from amplifier_module_tool_design_lints.lints import run_lints
    except Exception:
        logger.info("browser lints unavailable (design-lints/playwright not importable)")
        return None
    try:
        return await run_lints(html=html, url=url)
    except Exception:
        logger.warning("browser lints failed", exc_info=True)
        return None


def _browser_findings(lint: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    cmin = lint.get("wcag_contrast_min")
    if cmin is not None:
        ok = bool(lint.get("contrast_pass", True))
        out.append(
            _f(
                "contrast",
                "Color contrast (WCAG)",
                "pass" if ok else "fail",
                f"Minimum contrast ratio {cmin}:1"
                + ("" if ok else " -- below the 4.5:1 AA minimum somewhere."),
            )
        )
    out.append(
        _f(
            "focus",
            "Keyboard focus",
            "pass" if lint.get("focus_reachable") else "warn",
            "Focusable elements keep a visible focus ring."
            if lint.get("focus_reachable")
            else "Focus ring may be suppressed or nothing is focusable.",
        )
    )
    out.append(
        _f(
            "overflow",
            "No horizontal scroll",
            "fail" if lint.get("viewport_overflow") else "pass",
            "Content overflows the viewport width."
            if lint.get("viewport_overflow")
            else "Fits the viewport width; no sideways scroll.",
        )
    )
    return out


async def run_audit(
    *,
    kind: str,
    html: str | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    """Produce the ground-truth section for a run.

    kind == 'html' -> static + browser checks on the markup.
    kind == 'url'  -> browser checks by navigating; static checks skipped
                      unless html was also fetched by the caller.
    kind == 'image'/'prompt' -> not applicable (no markup to inspect).

    Returns {available, findings:[...], summary:{pass,warn,fail}, note}.
    """
    if kind not in ("html", "url") or (not html and not url):
        return {
            "available": False,
            "findings": [],
            "summary": {"pass": 0, "warn": 0, "fail": 0},
            "note": "Paste HTML or a URL to get a real accessibility & hygiene audit "
            "of your page (screenshots can't be inspected structurally).",
        }

    findings: list[dict[str, str]] = []
    if html:
        findings.extend(audit_html_static(html))

    lint = await browser_lints(html=html, url=url)
    if lint:
        findings = _browser_findings(lint) + findings

    summary = {"pass": 0, "warn": 0, "fail": 0}
    for f in findings:
        summary[f["status"]] = summary.get(f["status"], 0) + 1

    return {
        "available": bool(findings),
        "findings": findings,
        "summary": summary,
        "note": "" if lint else "Rendered checks (contrast, focus) need Playwright; "
        "showing static checks only.",
    }
