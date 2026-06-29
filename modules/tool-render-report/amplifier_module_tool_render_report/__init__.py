"""Amplifier tool module for rendering design review reports."""
from __future__ import annotations

import base64
import logging
import tempfile
from pathlib import Path
from typing import Any

from amplifier_core import ModuleCoordinator, ToolResult

from .template import render_report
from .verdict import parse_verdict

logger = logging.getLogger(__name__)


class RenderReportTool:
    """Render a self-contained HTML design-review report.

    Input keys
    ----------
    verdict               (dict | None) — Raw verdict dict {scores, total, fixes}
    verdict_text          (str  | None) — Raw verdict string (alternative to verdict)
    target_html_path      (str  | None) — Path to the improved HTML candidate (A)
    target_screenshot_path(str  | None) — Path to the target screenshot PNG (B)
    out_path              (str  | None) — Destination for the report; a temp file if omitted

    Output keys
    -----------
    report_html_path — Absolute path to the written HTML report.

    Never crashes: errors are returned as ``success=False`` with an ``error`` dict.
    """

    @property
    def name(self) -> str:
        return "render_report"

    @property
    def description(self) -> str:
        return (
            "Render a self-contained HTML design-review report. "
            "Input: {verdict|verdict_text, target_html_path?, "
            "target_screenshot_path?, out_path?} → {report_html_path}. "
            "Never crashes: returns success=False with an error message instead."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "verdict": {
                    "type": "object",
                    "description": "Raw verdict dict {scores, total, fixes}.",
                },
                "verdict_text": {
                    "type": "string",
                    "description": "Raw verdict string (alternative to verdict dict).",
                },
                "target_html_path": {
                    "type": "string",
                    "description": "Path to the improved HTML candidate (A).",
                },
                "target_screenshot_path": {
                    "type": "string",
                    "description": "Path to the target screenshot PNG (B).",
                },
                "out_path": {
                    "type": "string",
                    "description": (
                        "Destination path for the report HTML. "
                        "Uses a temp file if omitted."
                    ),
                },
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:  # noqa: A002
        """Build the report and write it to disk.

        Parameters
        ----------
        input:
            Dict with keys as described in the class docstring.

        Returns
        -------
        ToolResult
            ``success=True`` with ``output={'report_html_path': str}`` on success,
            or ``success=False`` with an ``error`` dict on any failure.
        """
        try:
            # ── 1. Resolve verdict ────────────────────────────────────────────
            verdict_input = input.get("verdict")
            verdict_text = input.get("verdict_text")

            if verdict_input is not None:
                parsed = parse_verdict(verdict_input)
            elif verdict_text is not None:
                parsed = parse_verdict(verdict_text)
            else:
                return ToolResult(
                    success=False,
                    error={"message": "verdict or verdict_text is required"},
                )

            # render_report expects the full parse_verdict output:
            #   success shape: {"valid": True, "verdict": {...}}
            #   failure shape: {"valid": False, "scores_unavailable": True, "raw": str}
            verdict_for_template = parsed

            # ── 2. Read optional HTML candidate (A) ───────────────────────────
            target_html: str | None = None
            target_html_path = input.get("target_html_path")
            if target_html_path:
                p = Path(target_html_path).expanduser()
                if p.exists():
                    target_html = p.read_text(encoding="utf-8")

            # ── 3. Base64-encode optional screenshot (B) ──────────────────────
            target_b64: str | None = None
            target_screenshot_path = input.get("target_screenshot_path")
            if target_screenshot_path:
                p = Path(target_screenshot_path).expanduser()
                if p.exists():
                    target_b64 = base64.b64encode(p.read_bytes()).decode()

            # ── 4. Build HTML report ──────────────────────────────────────────
            html = render_report(verdict_for_template, target_html, target_b64)

            # ── 5. Determine output path ──────────────────────────────────────
            out_path_str = input.get("out_path")
            if out_path_str:
                out = Path(out_path_str).expanduser()
            else:
                _, tmp_name = tempfile.mkstemp(suffix=".html")
                out = Path(tmp_name)

            # ── 6. Write and return ───────────────────────────────────────────
            out.write_text(html, encoding="utf-8")
            return ToolResult(
                success=True,
                output={"report_html_path": str(out)},
            )

        except Exception as exc:
            logger.exception("RenderReportTool.execute failed")
            return ToolResult(
                success=False,
                error={"message": str(exc), "type": type(exc).__name__},
            )


async def mount(coordinator: Any = None, config: Any = None) -> RenderReportTool:
    """Mount the render-report tool onto the coordinator.

    Satisfies the Iron Law: mount() must call coordinator.mount('tools', tool, name=tool.name).
    """
    tool = RenderReportTool()
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("Mounted tool-render-report (name=%s)", tool.name)
    return tool
