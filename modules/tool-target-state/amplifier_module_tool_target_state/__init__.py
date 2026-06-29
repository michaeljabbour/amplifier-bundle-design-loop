"""Amplifier tool module: write the target-state HTML (A) and render it to PNG (B)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Awaitable, Callable

from amplifier_core import ToolResult

logger = logging.getLogger(__name__)

# Type aliases for injected functions
RenderFn = Callable[[str], Awaitable[dict]]
GeneratorFn = Callable[[str, list], str]


class TargetStateTool:
    """Write improved HTML (A) and render it to a screenshot (B).

    The tool accepts an ``improved_html`` string directly *or* uses an injected
    ``generator`` callable to produce it.  Rendering is always delegated to an
    injected ``render_fn``.

    When ``render_fn`` is ``None`` at call time the tool returns
    ``"target-state unavailable"`` without inventing a renderer.

    Returns
    -------
    dict with keys:
        ``target_html_path``       — absolute path of the written HTML file (A)
        ``target_screenshot_path`` — absolute path of the rendered PNG (B)
    """

    def __init__(
        self,
        render_fn: RenderFn | None = None,
        generator: GeneratorFn | None = None,
    ) -> None:
        self._render_fn = render_fn
        self._generator = generator

    @property
    def name(self) -> str:
        return "target_state"

    @property
    def description(self) -> str:
        return (
            "Produce the target-state design artefact. "
            "Provide `improved_html` (A) directly, or rely on a configured generator. "
            "Writes A to disk, renders it to a screenshot (B) via an injected renderer, "
            "and returns {target_html_path, target_screenshot_path}. "
            "On any failure returns 'target-state unavailable' — never invents content."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "original": {
                    "type": "object",
                    "description": "The original design reference with 'source' and 'kind' fields.",
                    "properties": {
                        "source": {"type": "string"},
                        "kind": {"type": "string"},
                    },
                },
                "fixes": {
                    "type": "array",
                    "description": "List of fixes/changes to apply.",
                    "items": {"type": "object"},
                },
                "improved_html": {
                    "type": "string",
                    "description": "Pre-generated improved HTML to write as A. "
                    "If omitted, the configured generator is used.",
                },
                "out_dir": {
                    "type": "string",
                    "description": "Directory where target.html (A) will be written. "
                    "Created if it does not exist. If omitted, a temp dir is used.",
                },
            },
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_original_html(self, original: dict) -> str:
        """Return the text of the original HTML file, or '' if unavailable."""
        source = original.get("source", "")
        kind = original.get("kind", "")
        if kind == "html":
            p = Path(source).expanduser()
            if p.exists():
                return p.read_text(encoding="utf-8")
        return ""

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    async def execute(self, input_data: dict) -> ToolResult:
        try:
            improved_html: str | None = input_data.get("improved_html")
            original = input_data.get("original", {})
            fixes = input_data.get("fixes", [])
            out_dir_str: str | None = input_data.get("out_dir")

            # Determine HTML content (A)
            if improved_html is None:
                if self._generator is None:
                    return ToolResult(
                        success=False,
                        output=None,
                        error={
                            "message": "target-state unavailable: no improved_html and no generator configured",
                            "type": "ConfigurationError",
                        },
                    )
                original_html = self._read_original_html(original)
                improved_html = self._generator(original_html, fixes)

            # Ensure we have a renderer
            if self._render_fn is None:
                return ToolResult(
                    success=False,
                    output=None,
                    error={
                        "message": "target-state unavailable: no renderer configured",
                        "type": "ConfigurationError",
                    },
                )

            # Determine output path for A
            if out_dir_str:
                base = Path(out_dir_str).expanduser()
                base.mkdir(parents=True, exist_ok=True)
                a_path = base / "target.html"
            else:
                tmp_dir = tempfile.mkdtemp()
                a_path = Path(tmp_dir) / "target.html"

            # Write A
            a_path.write_text(improved_html, encoding="utf-8")

            # Render B
            render_out = await self._render_fn(str(a_path))
            shot: str | None = render_out.get("screenshot_path")
            if not shot or not Path(shot).exists():
                return ToolResult(
                    success=False,
                    output=None,
                    error={
                        "message": "target-state unavailable: render of A failed",
                        "type": "RenderError",
                    },
                )

            return ToolResult(
                success=True,
                output={
                    "target_html_path": str(a_path),
                    "target_screenshot_path": shot,
                },
                error=None,
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error={
                    "message": f"target-state unavailable: {e}",
                    "type": type(e).__name__,
                },
            )


# ------------------------------------------------------------------
# Late-binding render_fn factory
# ------------------------------------------------------------------


def _make_render_fn(coordinator) -> RenderFn:
    """Return a render_fn that resolves the render tool at call time (mount-order safe)."""

    async def _render(html_path: str) -> dict:
        tools = getattr(coordinator, "mount_points", {}).get("tools", {})
        render_tool = tools.get("render")
        if render_tool is None:
            raise RuntimeError(
                "target-state: 'render' tool not found in coordinator mount points"
            )
        result = await render_tool.execute({"source": html_path, "kind": "html"})
        if not result.success:
            raise RuntimeError(
                f"target-state: render tool returned failure: {result.error}"
            )
        return result.output

    return _render


# ------------------------------------------------------------------
# mount
# ------------------------------------------------------------------


async def mount(coordinator, config: dict | None = None) -> TargetStateTool:
    """Mount the target-state tool into the coordinator."""
    tool = TargetStateTool(render_fn=_make_render_fn(coordinator))
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("tool-target-state: mounted as '%s'", tool.name)
    return tool
