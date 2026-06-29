"""Tests for tool-target-state mount() live wiring.

Test 1: mount() registers 'target_state' and returns the tool.
Test 2: with both tool-render and tool-target-state mounted, execute() renders
        B through the real Chromium-backed render tool.
"""
from __future__ import annotations

from pathlib import Path

from amplifier_core.testing import create_test_coordinator
from amplifier_module_tool_render import mount as mount_render
from amplifier_module_tool_target_state import TargetStateTool
from amplifier_module_tool_target_state import mount as mount_target

# Resolve the repo root: this file lives at
#   <REPO>/modules/tool-target-state/tests/test_mount.py
# so parents[3] is the repo root.
REPO = Path(__file__).parents[3]


async def test_mount_registers_target_state() -> None:
    """mount() should register the tool at 'target_state' and return it."""
    coordinator = create_test_coordinator()

    returned = await mount_target(coordinator, {})

    assert isinstance(returned, TargetStateTool), (
        f"Expected TargetStateTool, got {type(returned)}"
    )
    assert coordinator.mount_points["tools"]["target_state"] is returned, (
        "tool not registered under 'target_state' in coordinator.mount_points['tools']"
    )


async def test_target_state_renders_b_through_live_render_tool(
    tmp_path: Path,
) -> None:
    """With both bricks mounted, execute() renders B via the live render tool (real Chromium)."""
    coordinator = create_test_coordinator()

    # Mount render FIRST so the render tool is available when target_state calls it
    await mount_render(coordinator, {})

    # Mount target-state — it closes over coordinator via _make_render_fn
    target = await mount_target(coordinator, {})

    # Read the excellent.html fixture as the improved_html
    improved_html = (REPO / "fixtures" / "excellent.html").read_text(encoding="utf-8")

    res = await target.execute(
        {
            "improved_html": improved_html,
            "out_dir": str(tmp_path),
        }
    )

    assert res.success, f"execute() returned failure: {res.error}"

    B = Path(res.output["target_screenshot_path"])
    assert B.exists(), f"Screenshot B does not exist: {B}"
    assert B.stat().st_size > 0, f"Screenshot B is empty (0 bytes): {B}"
