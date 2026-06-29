"""Headless-Chromium design linter — deterministic, no-LLM quality checks.

All public entry point: :func:`run_lints`.

Design decisions / documented heuristics
-----------------------------------------
* **Contrast** — we resolve each visible leaf-text element's foreground color
  and the nearest non-transparent ancestor background color.  We do NOT blend
  partial-alpha layers (opacity < 1 on ancestors); that case is treated as if
  opacity == 1.  ``wcag_contrast_min`` is rounded to 2 d.p.
  Large-text threshold: font-size ≥ 24 px, OR font-size ≥ 18.66 px AND
  font-weight ≥ 700 → AA minimum 3.0; otherwise minimum 4.5.

* **Focus reachability** — heuristic only: we check for the presence of
  interactive elements AND whether a global ``*:focus`` or ``:focus`` CSS rule
  suppresses ``outline``.  We do NOT check ``focus-visible`` replacements, nor
  do we walk the actual computed focus ring styles.

* **Network blocking** — for ``set_content`` (html / html_path mode) every
  network request is classified as external because there is no main-document
  origin to allow.  For ``goto`` (url mode) we allow requests whose
  resource_type == "document" (covers the main frame and any sub-frame
  navigations) and block/flag everything else (images, scripts, stylesheets,
  fonts, XHR, etc.).

* **No-crash contract** — this module never raises.  All errors are surfaced
  inside the returned dict (``renders_ok=False``, ``hard_fail=True``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

_DEFAULT_VIEWPORT: dict[str, int] = {"width": 1280, "height": 800}

# ---------------------------------------------------------------------------
# In-page JavaScript probe
# ---------------------------------------------------------------------------
# The probe is a self-contained IIFE that computes all lint values from the
# live DOM and returns a plain object.  It runs synchronously inside
# page.evaluate() so there are no async/await complications.

_PROBE_JS = r"""
() => {
  // ── colour helpers ──────────────────────────────────────────────────────
  function parseColor(css) {
    // Matches: rgb(r, g, b)  or  rgba(r, g, b, a)
    var m = css.match(
      /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)/
    );
    if (!m) return null;
    return [+m[1], +m[2], +m[3], m[4] !== undefined ? +m[4] : 1];
  }

  function linearize(v) {
    var s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  }

  function luminance(r, g, b) {
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
  }

  function contrastRatio(fg, bg) {
    var l1 = luminance(fg[0], fg[1], fg[2]) + 0.05;
    var l2 = luminance(bg[0], bg[1], bg[2]) + 0.05;
    return (l1 > l2) ? l1 / l2 : l2 / l1;
  }

  // Walk up the ancestor chain to find the first non-transparent background.
  // Falls back to browser-default white [255, 255, 255, 1].
  function getEffectiveBg(el) {
    var node = el;
    while (node) {
      var bg = window.getComputedStyle(node).backgroundColor;
      var c  = parseColor(bg);
      if (c && c[3] > 0.01) return c;
      if (node === document.documentElement) break;
      node = node.parentElement;
    }
    return [255, 255, 255, 1];
  }

  // ── visible leaf-text element collection ────────────────────────────────
  var allEls  = Array.from(document.querySelectorAll('*'));
  var textEls = allEls.filter(function(el) {
    // Must have at least one non-empty direct text node
    var hasDirectText = Array.from(el.childNodes).some(function(n) {
      return n.nodeType === Node.TEXT_NODE && n.textContent.trim().length > 0;
    });
    if (!hasDirectText) return false;
    var s = window.getComputedStyle(el);
    if (s.display === 'none') return false;
    if (s.visibility === 'hidden' || s.visibility === 'collapse') return false;
    if (parseFloat(s.opacity) < 0.01) return false;
    return true;
  });

  // ── WCAG contrast ────────────────────────────────────────────────────────
  // Pragmatic heuristic: fg from computed color, bg from nearest opaque ancestor.
  // We do NOT blend partial-opacity layers — documented limitation.
  var minContrast  = null;
  var contrastPass = true;   // vacuously true when no text elements

  for (var i = 0; i < textEls.length; i++) {
    var el = textEls[i];
    var s  = window.getComputedStyle(el);
    var fg = parseColor(s.color);
    if (!fg) continue;
    var bg    = getEffectiveBg(el);
    var ratio = contrastRatio(fg, bg);

    if (minContrast === null || ratio < minContrast) minContrast = ratio;

    var fontSize   = parseFloat(s.fontSize);   // computed px value
    var fontWeight = parseInt(s.fontWeight, 10) || 400;
    // WCAG large-text definition: ≥24 px, or ≥18.66 px bold (≥700 weight)
    var isLarge   = fontSize >= 24 || (fontSize >= 18.66 && fontWeight >= 700);
    var threshold = isLarge ? 3.0 : 4.5;
    if (ratio < threshold) contrastPass = false;
  }

  // ── focus reachability (heuristic) ──────────────────────────────────────
  // Heuristic: (1) at least one keyboard-focusable element exists, AND
  //            (2) no global *:focus or :focus rule completely suppresses outline.
  var FOCUSABLE_SEL = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(', ');
  var hasFocusable = document.querySelectorAll(FOCUSABLE_SEL).length > 0;

  var focusSuppressed = false;
  try {
    var sheets = Array.from(document.styleSheets);
    for (var si = 0; si < sheets.length; si++) {
      try {
        var rules = Array.from(sheets[si].cssRules || []);
        for (var ri = 0; ri < rules.length; ri++) {
          var rule = rules[ri];
          if (!rule.selectorText) continue;
          var sel = rule.selectorText.trim();
          // Match global *:focus and :focus selectors (not element-specific ones)
          if (sel === '*:focus' || sel === ':focus' ||
              sel === '*:focus-visible' || sel === ':focus-visible') {
            if (rule.style) {
              var outline = rule.style.getPropertyValue('outline');
              if (outline === 'none' || outline === '0') {
                focusSuppressed = true;
              }
            }
          }
        }
      } catch (_) { /* cross-origin or browser-restricted stylesheet */ }
    }
  } catch (_) { /* no styleSheets access */ }

  var focusReachable = hasFocusable && !focusSuppressed;

  // ── other objective metrics ──────────────────────────────────────────────
  var domNodes      = document.querySelectorAll('*').length;
  var visibleText   = document.body ? (document.body.innerText || '') : '';
  var textToChrome  = domNodes > 0 ? visibleText.length / domNodes : 0;

  // Horizontal viewport overflow (horizontal scroll required)
  var viewportOverflow = document.documentElement.scrollWidth > window.innerWidth;

  // Body non-empty check (JS errors from the Python side supplement this)
  var bodyNonEmpty = !!(document.body && document.body.innerHTML.trim().length > 0);

  return {
    renders_ok_body:      bodyNonEmpty,
    wcag_contrast_min:    minContrast !== null
                            ? Math.round(minContrast * 100) / 100
                            : null,
    contrast_pass:        contrastPass,
    focus_reachable:      focusReachable,
    dom_nodes:            domNodes,
    text_to_chrome_ratio: Math.round(textToChrome * 100) / 100,
    viewport_overflow:    viewportOverflow
  };
}
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_lints(
    *,
    html: str | None = None,
    html_path: str | None = None,
    url: str | None = None,
    viewport: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Run deterministic design lints via headless Chromium.

    Exactly one of *html*, *html_path*, or *url* must be provided.

    Parameters
    ----------
    html:
        Raw HTML string to inject via ``page.set_content()``.
    html_path:
        Path to an HTML file; read and passed to ``page.set_content()``.
    url:
        HTTP/HTTPS URL to navigate to via ``page.goto()``.
    viewport:
        Dict with ``width`` and ``height`` keys.  Defaults to 1280×800.

    Returns
    -------
    dict
        All lint results plus ``hard_fail`` (bool) and ``hard_fail_reasons``
        (list[str]).  Never raises — errors surface as ``renders_ok=False``
        inside the returned dict.
    """
    vp = viewport or _DEFAULT_VIEWPORT

    # ---------- input validation ------------------------------------------------
    if not any([html, html_path, url]):
        return _error_result("no source provided: supply 'html', 'html_path', or 'url'")

    # Resolve html_path → html string early so file errors surface cleanly
    if html_path and not html:
        try:
            html = Path(html_path).expanduser().read_text(encoding="utf-8")
        except Exception as exc:
            return _error_result(f"cannot read html_path: {exc}")

    # ---------- Playwright session ----------------------------------------------
    external_requested: list[bool] = [False]
    page_errors: list[str] = []

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            try:
                context = await browser.new_context(viewport=vp)
                page = await context.new_page()

                # Capture uncaught JS errors
                page.on("pageerror", lambda err: page_errors.append(str(err)))

                if url:
                    # ── url mode ───────────────────────────────────────────────
                    # Allow main-document requests (navigation); block and flag
                    # all other resource types (images, scripts, stylesheets …).
                    async def _route_url(route):  # type: ignore[no-untyped-def]
                        if route.request.resource_type == "document":
                            await route.continue_()
                        else:
                            external_requested[0] = True
                            await route.abort()

                    await page.route("**/*", _route_url)
                    try:
                        await page.goto(url, wait_until="load", timeout=15_000)
                    except Exception as nav_err:
                        logger.warning("goto(%r) error (proceeding with partial DOM): %s", url, nav_err)

                else:
                    # ── set_content mode (html / html_path) ────────────────────
                    # There is no main-document origin: every network request is
                    # an external resource attempt → block all and flag them.
                    async def _route_content(route):  # type: ignore[no-untyped-def]
                        external_requested[0] = True
                        await route.abort()

                    await page.route("**/*", _route_content)
                    try:
                        await page.set_content(
                            html or "", wait_until="load", timeout=15_000
                        )
                    except Exception as sc_err:
                        logger.warning("set_content error (proceeding with partial DOM): %s", sc_err)

                # ── run the in-page probe ──────────────────────────────────────
                try:
                    probe = await page.evaluate(_PROBE_JS)
                except Exception as probe_err:
                    logger.warning("JS probe failed: %s", probe_err)
                    probe = {
                        "renders_ok_body":     False,
                        "wcag_contrast_min":   None,
                        "contrast_pass":       False,
                        "focus_reachable":     False,
                        "dom_nodes":           0,
                        "text_to_chrome_ratio": 0.0,
                        "viewport_overflow":   False,
                    }

            finally:
                await browser.close()

    except Exception as exc:
        logger.exception("run_lints: Playwright session failed")
        return _error_result(f"Playwright error: {exc}")

    # ---------- assemble final result ------------------------------------------
    renders_ok = bool(probe.get("renders_ok_body")) and len(page_errors) == 0

    hard_fail_reasons: list[str] = []
    if not renders_ok:
        hard_fail_reasons.append("renders_ok")
    if external_requested[0]:
        hard_fail_reasons.append("network_request")
    if not probe.get("contrast_pass", True):
        hard_fail_reasons.append("contrast_pass")

    return {
        "renders_ok":          renders_ok,
        "network_request":     external_requested[0],
        "wcag_contrast_min":   probe.get("wcag_contrast_min"),
        "contrast_pass":       bool(probe.get("contrast_pass", True)),
        "focus_reachable":     bool(probe.get("focus_reachable", False)),
        "dom_nodes":           int(probe.get("dom_nodes", 0)),
        "text_to_chrome_ratio": float(probe.get("text_to_chrome_ratio", 0.0)),
        "viewport_overflow":   bool(probe.get("viewport_overflow", False)),
        "hard_fail":           bool(hard_fail_reasons),
        "hard_fail_reasons":   hard_fail_reasons,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _error_result(reason: str) -> dict[str, Any]:
    """Return a hard-fail lint dict for non-Playwright errors (e.g. bad input)."""
    return {
        "renders_ok":          False,
        "network_request":     False,
        "wcag_contrast_min":   None,
        "contrast_pass":       False,
        "focus_reachable":     False,
        "dom_nodes":           0,
        "text_to_chrome_ratio": 0.0,
        "viewport_overflow":   False,
        "hard_fail":           True,
        "hard_fail_reasons":   [reason],
    }
