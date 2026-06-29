"""Tests verifying the structure of agents/design-judge.md."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENT = REPO / "agents" / "design-judge.md"

CRITERIA = [
    "clarity",
    "elegance",
    "restraint",
    "empowerment",
    "agency",
    "ease",
    "character",
    "point",
]


def _frontmatter(text: str) -> str:
    assert text.startswith("---")
    return text.split("---", 2)[1]


def test_agent_exists_and_has_vision_role():
    assert AGENT.exists(), f"{AGENT} does not exist"
    text = AGENT.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "name: design-judge" in fm
    assert "model_role: vision" in fm


def test_agent_body_contains_full_rubric_and_contract():
    text = AGENT.read_text(encoding="utf-8")
    body = text.split("---", 2)[2].lower()
    for criterion in CRITERIA:
        assert criterion in body, f"Missing criterion in body: {criterion}"
    assert "verdict" in body, "Missing 'verdict' in body"
    assert "render_report" in body, "Missing 'render_report' in body"
    assert "target_state" in body, "Missing 'target_state' in body"
    assert "render" in body, "Missing 'render' in body"
    assert "n/a" in body or "never" in body, "Missing honesty rule ('n/a' or 'never') in body"
