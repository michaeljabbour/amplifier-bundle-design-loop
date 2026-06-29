"""Amplifier tool module: render HTML pages to PNG via headless Chromium."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from amplifier_core import ModuleCoordinator, ToolResult

from .render import render_to_png

logger = logging.getLogger(__name__)

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _detect_kind(source: str) -> str:
    """Detect the kind of source from its URL prefix or file extension.

    Returns
    -------
    'url'   — starts with http:// or https://
    'image' — file extension is a known image type
    'html'  — everything else
    """
    if source.startswith("http://") or source.startswith("https://"):
        return "url"
    ext = Path(source).suffix.lower()
    if ext in _IMAGE_EXTS:
        return "image"
    return "html"


class RenderTool:
    """Render HTML files or URLs to PNG screenshots.

    Input keys
    ----------
    source   (required) — path to an HTML file, an http/https URL, or an image file
    kind     (optional) — one of 'html', 'url', 'image'; auto-detected when omitted
    out_path (optional) — destination path for the PNG; a temp file is used when omitted

    Output keys
    -----------
    screenshot_path — absolute path to the resulting PNG (or the original image path)

    This tool never crashes: any failure is returned as ``success=False`` with an
    ``error`` dict containing at least a ``message`` key.
    """

    @property
    def name(self) -> str:
        return "render"

    @property
    def description(self) -> str:
        return (
            "Render an HTML file or URL to a PNG screenshot. "
            "Input: {source, kind? (html|url|image), out_path?} → {screenshot_path}. "
            "For kind='image', returns the source path unchanged. "
            "Never crashes: returns success=False with an error message instead."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": (
                        "Path to an HTML file, an http/https URL, or an image file path."
                    ),
                },
                "kind": {
                    "type": "string",
                    "enum": ["html", "url", "image"],
                    "description": "Kind of source. Auto-detected from source if omitted.",
                },
                "out_path": {
                    "type": "string",
                    "description": "Destination path for the output PNG. Uses a temp file if omitted.",
                },
            },
            "required": ["source"],
        }

    async def execute(self, input: dict) -> ToolResult:  # noqa: A002
        """Execute the render tool.

        Parameters
        ----------
        input:
            Dict with keys ``source``, ``kind`` (optional), ``out_path`` (optional).

        Returns
        -------
        ToolResult
            ``success=True`` with ``output={'screenshot_path': str}`` on success,
            or ``success=False`` with an ``error`` dict on any failure.
        """
        source = input.get("source")
        if not source:
            return ToolResult(
                success=False,
                error={"message": "source is required"},
            )

        kind = input.get("kind") or _detect_kind(source)

        try:
            if kind == "image":
                img_path = Path(source).expanduser()
                if not img_path.exists() or img_path.stat().st_size == 0:
                    return ToolResult(
                        success=False,
                        error={
                            "message": f"Image file not found or empty: {img_path}",
                            "type": "FileNotFoundError",
                        },
                    )
                return ToolResult(
                    success=True,
                    output={"screenshot_path": str(img_path)},
                )

            # kind is 'html' or 'url'
            out_path = input.get("out_path")
            if out_path:
                out = Path(out_path).expanduser()
            else:
                _, tmp_name = tempfile.mkstemp(suffix=".png")
                out = Path(tmp_name)

            if kind == "url":
                target = source
            else:
                # html — resolve to a file:// URI
                html_path = Path(source).expanduser().resolve()
                if not html_path.exists():
                    return ToolResult(
                        success=False,
                        error={
                            "message": f"HTML file not found: {html_path}",
                            "type": "FileNotFoundError",
                        },
                    )
                target = html_path.as_uri()

            shot = await render_to_png(target, out)
            return ToolResult(
                success=True,
                output={"screenshot_path": str(shot)},
            )

        except Exception as exc:
            logger.exception("RenderTool.execute failed")
            return ToolResult(
                success=False,
                error={"message": str(exc), "type": type(exc).__name__},
            )


async def mount(coordinator: ModuleCoordinator, config=None) -> "RenderTool":
    tool = RenderTool()
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("Mounted tool-render")
    return tool
