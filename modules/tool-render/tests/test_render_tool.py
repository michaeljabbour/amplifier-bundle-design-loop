"""Tests for RenderTool.execute (Task 5)."""
from pathlib import Path

import pytest

REPO = Path(__file__).parents[3]
SLOP = REPO / "fixtures" / "slop.html"


@pytest.mark.asyncio
async def test_html_input_renders(tmp_path):
    """execute with source+kind='html'+out_path returns success and screenshot_path exists nonempty."""
    from amplifier_module_tool_render import RenderTool

    tool = RenderTool()
    out = tmp_path / "output.png"
    result = await tool.execute(
        {
            "source": str(SLOP),
            "kind": "html",
            "out_path": str(out),
        }
    )

    assert result.success
    assert result.output is not None
    shot = Path(result.output["screenshot_path"])
    assert shot.exists()
    assert shot.stat().st_size > 0


@pytest.mark.asyncio
async def test_kind_autodetected_from_extension(tmp_path):
    """Omitting kind with a .html source auto-detects 'html' and renders successfully."""
    from amplifier_module_tool_render import RenderTool

    tool = RenderTool()
    out = tmp_path / "auto.png"
    result = await tool.execute(
        {
            "source": str(SLOP),
            "out_path": str(out),
        }
    )

    assert result.success
    assert result.output is not None
    shot = Path(result.output["screenshot_path"])
    assert shot.exists()
    assert shot.stat().st_size > 0


@pytest.mark.asyncio
async def test_image_input_passes_through(tmp_path):
    """execute with kind='image' returns screenshot_path equal to the source path unchanged."""
    from amplifier_module_tool_render import RenderTool

    tool = RenderTool()
    fake_img = tmp_path / "fake.png"
    fake_img.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_data")  # nonempty

    result = await tool.execute(
        {
            "source": str(fake_img),
            "kind": "image",
        }
    )

    assert result.success
    assert result.output["screenshot_path"] == str(fake_img)


@pytest.mark.asyncio
async def test_missing_source_is_error_not_crash(tmp_path):
    """execute({}) returns success=False with 'source' in the error message (no crash)."""
    from amplifier_module_tool_render import RenderTool

    tool = RenderTool()
    result = await tool.execute({})

    assert result.success is False
    assert result.error is not None
    assert "source" in result.error["message"].lower()


@pytest.mark.asyncio
async def test_image_passthrough_missing_file_is_error(tmp_path):
    """execute with kind='image' pointing to a nonexistent file returns success=False."""
    from amplifier_module_tool_render import RenderTool

    tool = RenderTool()
    result = await tool.execute(
        {
            "source": str(tmp_path / "nonexistent.png"),
            "kind": "image",
        }
    )

    assert result.success is False
    assert result.error is not None
