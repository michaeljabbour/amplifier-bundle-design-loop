"""
Manual integration test: already-excellent page.

This test exercises the full design-judge pipeline against a known-good HTML
fixture (fixtures/excellent.html) using a real provider.  It verifies:

1. **test_excellent_page_scores_high_and_stops_honestly**: The excellent page
   scores high (total >= 24), the agent surfaces no top_fixes, the generated
   report exists on disk, and the report states 'no changes warranted' --
   demonstrating honest stopping on an already-excellent artifact.

HOW TO RUN
----------
    RUN_MANUAL=1 python -m pytest tests/integration/test_excellent_page.py -m manual -v -s

Prerequisites:
- A configured provider (e.g. ANTHROPIC_API_KEY set in the environment)
- amplifier_foundation installed (uv sync / uv pip install -e .)
- The design-loop bundle.md at the repo root and agents/design-judge.md present
"""

from pathlib import Path

import pytest

from tests.integration.test_golden_slop import _judge  # single implementation; do not duplicate

REPO = Path(__file__).resolve().parents[2]
EXCELLENT = REPO / "fixtures" / "excellent.html"


@pytest.mark.manual
async def test_excellent_page_scores_high_and_stops_honestly():
    """Already-excellent page scores >= 24, has no fixes, and report says 'no changes warranted'."""
    result = await _judge(str(EXCELLENT), "html")

    # 1. Total must be high -- the page is genuinely good
    total = result["total"]
    assert total >= 24, (
        f"Expected excellent page to score >= 24 but got {total}. "
        "Check that the agent is using the 8-criteria rubric correctly and that the "
        "fixture HTML is a valid high-quality design."
    )

    # 2. No top_fixes should be surfaced for an excellent page
    top_fixes = result.get("top_fixes", [])
    assert not top_fixes, (
        "Expected no top_fixes for the excellent page (honest stopping), "
        f"but the agent returned: {top_fixes!r}"
    )

    # 3. The generated report must exist on disk
    report_path = Path(result["report_html_path"])
    assert report_path.exists(), (
        f"report_html_path {report_path} was returned but the file does not exist."
    )

    # 4. The report must state that no changes are warranted (honest stopping signal)
    report_html = report_path.read_text(encoding="utf-8").lower()
    assert "no changes warranted" in report_html, (
        "Expected the report to state 'no changes warranted' for an excellent page, "
        "but the phrase was not found in the report. "
        "The agent should honestly stop and not invent fixes for already-excellent work."
    )
