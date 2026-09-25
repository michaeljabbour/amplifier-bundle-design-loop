"""Amplifier tool module: deterministic design lints via headless Chromium.

This is "asset 3" of the design harness — the un-gameable ground-truth gate
that runs BEFORE any LLM judge.  No external network access is permitted during
linting; any request attempt is recorded as a hard-fail signal.
"""
from __future__ import annotations

import logging
from typing import Any

from amplifier_core import ModuleCoordinator, ToolResult

from .lints import run_lints

logger = logging.getLogger(__name__)


class DesignLintsTool:
    """Run deterministic WCAG / self-containment lints on an HTML design.

    Input keys
    ----------
    html      (str)  — Raw HTML string to lint.
    html_path (str)  — Path to an HTML file to lint.
    url       (str)  — HTTP/HTTPS URL to navigate to and lint.
    viewport  (dict) — Optional. ``{"width": int, "height": int}``.
                       Defaults to 1280×800.

    Exactly one of *html*, *html_path*, or *url* must be supplied.
    Images (png/jpg/…) have no HTML DOM and are out of scope for this tool.

    Output keys  (always ``success=True``; never raises)
    -----------
    renders_ok          bool   — Page loaded, body non-empty, no uncaught JS errors.
    network_request     bool   — True → page attempted an external network request (hard-fail).
    wcag_contrast_min   float  — Minimum contrast ratio across visible text elements (WCAG).
    contrast_pass       bool   — All visible text meets WCAG AA (4.5:1 normal / 3:1 large).
    focus_reachable     bool   — At least one focusable element, no global outline suppression.
    dom_nodes           int    — Total element count (``querySelectorAll('*').length``).
    text_to_chrome_ratio float — ``len(body.innerText) / dom_nodes``.
    viewport_overflow   bool   — Page requires horizontal scrolling at the given viewport width.
    hard_fail           bool   — Any of: not renders_ok, network_request, not contrast_pass.
    hard_fail_reasons   list   — Names of the failing lint rules.
    """

    @property
    def name(self) -> str:
        return "design_lints"

    @property
    def description(self) -> str:
        # Terse on purpose: sent on every request. Output keys: class docstring.
        return (
            "Deterministic design lints via headless Chromium: WCAG contrast, "
            "self-containment (no network), focus, DOM metrics, overflow. Give one of "
            "html|html_path|url. Returns lint facts incl. hard_fail, hard_fail_reasons. "
            "HTML only (use render for images)."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "html": {"type": "string"},
                "html_path": {"type": "string"},
                "url": {"type": "string"},
                "viewport": {
                    "type": "object",
                    "description": "Default 1280x800.",
                    "properties": {
                        "width": {"type": "integer"},
                        "height": {"type": "integer"},
                    },
                    "required": ["width", "height"],
                },
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:  # noqa: A002
        """Execute design lints.

        Parameters
        ----------
        input:
            Dict with keys ``html`` | ``html_path`` | ``url``, plus optional ``viewport``.

        Returns
        -------
        ToolResult
            Always ``success=True``.  ``output`` is the full lint dict.
        """
        try:
            lints = await run_lints(
                html=input.get("html"),
                html_path=input.get("html_path"),
                url=input.get("url"),
                viewport=input.get("viewport"),
            )
            return ToolResult(success=True, output=lints)
        except Exception as exc:
            # Belt-and-suspenders: run_lints itself never raises, but guard anyway.
            logger.exception("DesignLintsTool.execute: unexpected exception")
            return ToolResult(
                success=True,
                output={
                    "renders_ok":           False,
                    "network_request":      False,
                    "wcag_contrast_min":    None,
                    "contrast_pass":        False,
                    "focus_reachable":      False,
                    "dom_nodes":            0,
                    "text_to_chrome_ratio": 0.0,
                    "viewport_overflow":    False,
                    "hard_fail":            True,
                    "hard_fail_reasons":    [f"unexpected error: {exc}"],
                },
            )


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None) -> DesignLintsTool:
    tool = DesignLintsTool()
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("Mounted tool-design-lints")
    return tool
