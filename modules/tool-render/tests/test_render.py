"""Tests for the render_to_png helper."""
from pathlib import Path

import pytest

REPO = Path(__file__).parents[3]
SLOP = REPO / "fixtures" / "slop.html"


@pytest.mark.asyncio
async def test_render_html_file_produces_nonempty_png(tmp_path):
    """Rendering the slop fixture produces a non-empty PNG at the requested path."""
    from amplifier_module_tool_render.render import render_to_png

    out = tmp_path / "output.png"
    result = await render_to_png(SLOP.resolve().as_uri(), out)

    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


@pytest.mark.asyncio
async def test_render_bad_url_raises(tmp_path):
    """Rendering a URL that does not exist raises an exception."""
    from amplifier_module_tool_render.render import render_to_png

    out = tmp_path / "output.png"
    with pytest.raises(Exception):
        await render_to_png("file:///definitely/not/here-12345.html", out)
