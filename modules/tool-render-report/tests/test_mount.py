"""Tests for RenderReportTool.execute + mount() (Task 9 — TDD).

Written BEFORE implementation (RED phase):
  - test_execute_writes_report_file: execute builds a real report with embedded base64 screenshot
  - test_execute_accepts_raw_verdict_text: execute with garbled text still returns success (honest stopping)
  - test_mount_registers_tool: mount() registers under 'tools'/'render_report' and returns the tool
"""
import base64
from pathlib import Path

import pytest
from amplifier_core.testing import create_test_coordinator

from amplifier_module_tool_render_report import RenderReportTool, mount
from amplifier_module_tool_render_report.verdict import CRITERIA


def _verdict() -> dict:
    """Build a valid verdict dict with all criteria scores set to 2 (total=16)."""
    return {"scores": {c: 2 for c in CRITERIA}, "total": 16, "fixes": []}


async def test_execute_writes_report_file(tmp_path: Path) -> None:
    """execute() reads A (HTML) and B (screenshot), embeds base64 PNG, writes report."""
    a_path = tmp_path / "A.html"
    b_path = tmp_path / "B.png"
    out_path = tmp_path / "report.html"

    a_path.write_text("<h1>Improved</h1>", encoding="utf-8")
    b_path.write_bytes(b"PNGDATA")

    tool = RenderReportTool()
    result = await tool.execute(
        {
            "verdict": _verdict(),
            "target_html_path": str(a_path),
            "target_screenshot_path": str(b_path),
            "out_path": str(out_path),
        }
    )

    assert result.success is True, f"Expected success, got error: {result.error}"
    assert out_path.exists(), "Report file was not written"

    content = out_path.read_text(encoding="utf-8")
    assert "data:image/png;base64," in content, "Report missing base64 image data URI"
    expected_b64 = base64.b64encode(b"PNGDATA").decode()
    assert expected_b64 in content, f"Report missing expected base64 string '{expected_b64}'"


async def test_execute_accepts_raw_verdict_text(tmp_path: Path) -> None:
    """execute() with unparseable verdict_text returns success=True (honest stopping).

    The raw text is preserved in the report so readers can inspect it.
    """
    out_path = tmp_path / "report.html"

    tool = RenderReportTool()
    result = await tool.execute(
        {
            "verdict_text": "garbled-not-json",
            "out_path": str(out_path),
        }
    )

    assert result.success is True, f"Expected success (honest stopping), got: {result.error}"
    content = out_path.read_text(encoding="utf-8")
    assert "garbled-not-json" in content, "Raw verdict text not preserved in report"


async def test_mount_registers_tool() -> None:
    """mount() constructs a RenderReportTool, registers it, and returns it."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator)

    assert isinstance(returned, RenderReportTool), (
        f"mount() should return a RenderReportTool, got {type(returned)}"
    )
    assert coordinator.mount_points["tools"]["render_report"] is returned, (
        "Tool not registered at mount_points['tools']['render_report']"
    )
