"""Tests for bundle.md structure and correctness (TDD RED -> GREEN)."""
import pathlib


REPO = pathlib.Path(__file__).parents[1]
BUNDLE = REPO / "bundle.md"


def _frontmatter(path: pathlib.Path) -> str:
    """Extract raw YAML frontmatter text from a markdown file."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path} must start with '---'"
    _, fm, _ = text.split("---", 2)
    return fm


def test_bundle_name_is_design_loop():
    fm = _frontmatter(BUNDLE)
    assert "name: design-loop" in fm, "bundle.name must be 'design-loop'"


def test_bundle_includes_foundation_and_design_intelligence():
    fm = _frontmatter(BUNDLE)
    assert "amplifier-foundation" in fm, "bundle.md must include amplifier-foundation"
    assert "amplifier-bundle-design-intelligence" in fm, (
        "bundle.md must include amplifier-bundle-design-intelligence"
    )


def test_bundle_declares_three_local_tools():
    fm = _frontmatter(BUNDLE)
    assert "./modules/tool-render" in fm, "tool-render local source path must be in frontmatter"
    assert "./modules/tool-target-state" in fm, "tool-target-state local source path must be in frontmatter"
    assert "./modules/tool-render-report" in fm, "tool-render-report local source path must be in frontmatter"


def test_bundle_wires_design_judge_agent():
    fm = _frontmatter(BUNDLE)
    assert "design-loop:design-judge" in fm, (
        "agents.include must contain 'design-loop:design-judge'"
    )
    assert "@design-loop" not in fm, (
        "'@design-loop' must NOT appear in YAML frontmatter (@ prefix is markdown-only)"
    )


def test_local_tool_dirs_exist():
    tool_dirs = [
        "tool-render",
        "tool-target-state",
        "tool-render-report",
    ]
    for tool_dir in tool_dirs:
        pyproject = REPO / "modules" / tool_dir / "pyproject.toml"
        assert pyproject.exists(), f"modules/{tool_dir}/pyproject.toml must exist"
