"""Tests for TargetStateTool orchestration (write A, render B)."""

from __future__ import annotations

from pathlib import Path


from amplifier_module_tool_target_state import TargetStateTool


def _fake_render_factory(png_path: Path):
    """Return a fake render_fn that asserts the HTML file exists and returns a screenshot path."""

    async def _render(html_path: str) -> dict:
        assert Path(html_path).exists(), f"HTML file not found: {html_path}"
        return {"screenshot_path": str(png_path)}

    return _render


async def test_success_with_supplied_improved_html(tmp_path: Path):
    """TargetStateTool should write A from improved_html and render B via render_fn."""
    png_path = tmp_path / "screenshot.png"
    png_path.write_bytes(b"\x89PNG")  # create the fake screenshot file

    fake_render = _fake_render_factory(png_path)

    tool = TargetStateTool(render_fn=fake_render)

    out_dir = tmp_path / "output"
    result = await tool.execute(
        {
            "original": {"source": "x.html", "kind": "html"},
            "fixes": [{"selector": "h1", "change": "Update heading"}],
            "improved_html": "<!DOCTYPE html><h1>Better</h1>",
            "out_dir": str(out_dir),
        }
    )

    assert result.success, f"Expected success, got error: {result.error}"

    output = result.output
    # A path should exist and start with '<!DOCTYPE html'
    a_path = Path(output["target_html_path"])
    assert a_path.exists(), f"A path does not exist: {a_path}"
    content = a_path.read_text(encoding="utf-8")
    assert content.startswith("<!DOCTYPE html"), (
        f"A does not start with DOCTYPE: {content[:50]}"
    )

    # B should be the png path
    assert output["target_screenshot_path"] == str(png_path)


async def test_success_with_injected_generator(tmp_path: Path):
    """TargetStateTool should use injected generator when improved_html is not supplied."""
    png_path = tmp_path / "screenshot.png"
    png_path.write_bytes(b"\x89PNG")

    fake_render = _fake_render_factory(png_path)

    def fake_generator(original_html: str, fixes: list) -> str:
        return "<!DOCTYPE html><h1>Generated A</h1>"

    tool = TargetStateTool(render_fn=fake_render, generator=fake_generator)

    out_dir = tmp_path / "output2"
    result = await tool.execute(
        {
            "original": {"source": "nonexistent.html", "kind": "html"},
            "fixes": [],
            "out_dir": str(out_dir),
        }
    )

    assert result.success, f"Expected success, got error: {result.error}"

    output = result.output
    a_path = Path(output["target_html_path"])
    assert a_path.exists(), f"A path does not exist: {a_path}"
    content = a_path.read_text(encoding="utf-8")
    assert "Generated A" in content, (
        f"A does not contain 'Generated A': {content[:100]}"
    )
