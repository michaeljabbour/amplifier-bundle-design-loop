"""Tests for DesignLintsTool.execute — TDD red → green cycle.

Good page:  high-contrast inline HTML, no external resources.
Bad page:   light-grey text on white (contrast ~1.6:1) + external <img> URL.

The bad-page fixture exercises TWO independent lint rules so that each
hard_fail_reason can be asserted independently.
"""
import pytest

from amplifier_module_tool_design_lints import DesignLintsTool

# ---------------------------------------------------------------------------
# Inline HTML fixtures
# ---------------------------------------------------------------------------

# Known-good: black / dark-grey text on white body, no external requests,
# modest DOM.  body { background: #fff } gives the body a non-transparent bg
# so getBg() can resolve the ancestor chain reliably.
GOOD_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Good Page</title>
  <style>body { margin: 20px; background: #ffffff; }</style>
</head>
<body>
  <h1 style="color: #000000;">Good Heading</h1>
  <p style="color: #333333;">
    Body text with sufficient contrast (dark grey on white ≈ 12:1).
  </p>
</body>
</html>"""

# Known-bad:
#   (a) low-contrast: #cccccc on #ffffff ≈ 1.6:1 — fails AA 4.5 threshold.
#   (b) external resource: absolute https:// img URL triggers a network request.
BAD_HTML = """<!DOCTYPE html>
<html>
<head><title>Bad Page</title></head>
<body style="background: #ffffff;">
  <p style="color: #cccccc; background-color: #ffffff;">
    Low-contrast text (grey on white, ratio ≈ 1.6:1).
  </p>
  <img src="https://example.com/external-image-lint-test.png" alt="ext">
</body>
</html>"""


# ---------------------------------------------------------------------------
# Good-page assertions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_good_html_hard_fail_is_false():
    """A self-contained high-contrast page must NOT trigger hard_fail."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": GOOD_HTML})

    assert result.success is True
    out = result.output
    assert out is not None, "output must be present"

    assert out["hard_fail"] is False, (
        f"Expected hard_fail=False but got reasons: {out.get('hard_fail_reasons')}"
    )


@pytest.mark.asyncio
async def test_good_html_contrast_pass_is_true():
    """Good page: contrast_pass must be True (all text meets AA threshold)."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": GOOD_HTML})

    out = result.output
    assert out["contrast_pass"] is True, (
        f"contrast_pass False; wcag_contrast_min={out.get('wcag_contrast_min')}"
    )


@pytest.mark.asyncio
async def test_good_html_dom_nodes_positive():
    """Good page: dom_nodes must be > 0 (the page has elements)."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": GOOD_HTML})

    out = result.output
    assert out["dom_nodes"] > 0


@pytest.mark.asyncio
async def test_good_html_no_network_request():
    """Good page: network_request must be False (fully self-contained)."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": GOOD_HTML})

    out = result.output
    assert out["network_request"] is False


@pytest.mark.asyncio
async def test_good_html_renders_ok():
    """Good page: renders_ok must be True (body non-empty, no JS errors)."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": GOOD_HTML})

    out = result.output
    assert out["renders_ok"] is True


# ---------------------------------------------------------------------------
# Bad-page assertions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bad_html_hard_fail_is_true():
    """Bad page (low contrast + external img) must trigger hard_fail=True."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": BAD_HTML})

    assert result.success is True
    out = result.output
    assert out is not None

    assert out["hard_fail"] is True, (
        "Expected hard_fail=True for bad page with low contrast + external img"
    )


@pytest.mark.asyncio
async def test_bad_html_contrast_fail_in_reasons():
    """Bad page: 'contrast_pass' must appear in hard_fail_reasons."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": BAD_HTML})

    out = result.output
    assert "contrast_pass" in out["hard_fail_reasons"], (
        f"Expected 'contrast_pass' in hard_fail_reasons; got {out['hard_fail_reasons']}"
    )
    # Sanity: the computed minimum contrast should reflect the ~1.6:1 ratio
    assert out["wcag_contrast_min"] is not None
    assert out["wcag_contrast_min"] < 3.0, (
        f"wcag_contrast_min should be ~1.6 for #ccc on #fff, got {out['wcag_contrast_min']}"
    )


@pytest.mark.asyncio
async def test_bad_html_network_request_in_reasons():
    """Bad page: 'network_request' must appear in hard_fail_reasons (external img)."""
    tool = DesignLintsTool()
    result = await tool.execute({"html": BAD_HTML})

    out = result.output
    assert out["network_request"] is True, "Expected network_request=True for page with external img"
    assert "network_request" in out["hard_fail_reasons"], (
        f"Expected 'network_request' in hard_fail_reasons; got {out['hard_fail_reasons']}"
    )


# ---------------------------------------------------------------------------
# html_path input variant
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_html_path_input(tmp_path):
    """execute with html_path reads the file and runs lints correctly."""
    page = tmp_path / "good.html"
    page.write_text(GOOD_HTML, encoding="utf-8")

    tool = DesignLintsTool()
    result = await tool.execute({"html_path": str(page)})

    assert result.success is True
    assert result.output["hard_fail"] is False


# ---------------------------------------------------------------------------
# Missing-input guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_source_returns_renders_ok_false():
    """execute({}) must return success=True with renders_ok=False (never crash)."""
    tool = DesignLintsTool()
    result = await tool.execute({})

    assert result.success is True
    assert result.output["renders_ok"] is False
    assert result.output["hard_fail"] is True


# ---------------------------------------------------------------------------
# Custom viewport is accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_viewport_accepted():
    """execute with a custom viewport dict must succeed without error."""
    tool = DesignLintsTool()
    result = await tool.execute(
        {"html": GOOD_HTML, "viewport": {"width": 375, "height": 667}}
    )
    assert result.success is True
    assert result.output["renders_ok"] is True
