"""
Manual integration test: golden slop page.

This test exercises the full design-judge pipeline against a known-bad HTML
fixture (fixtures/slop.html) using a real provider.  It verifies:

1. **test_slop_scores_low_with_specific_fixes**: The slop page scores low
   (total <= 16) and the agent produces actionable top_fixes.  The generated
   report is also dogfood-clean — it must not embed the very slop patterns it
   criticises (purple→blue linear-gradient, Inter font quoted as "Inter").

2. **test_target_state_rejudges_higher**: The improved target-state HTML
   produced in the first run is re-judged and must score strictly higher than
   the original slop page.

HOW TO RUN
----------
    RUN_MANUAL=1 python -m pytest tests/integration/test_golden_slop.py -m manual -v -s

Prerequisites:
- A configured provider (e.g. ANTHROPIC_API_KEY set in the environment)
- amplifier_foundation installed (uv sync / uv pip install -e .)
- The design-loop bundle.md at the repo root and agents/design-judge.md present
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SLOP = REPO / "fixtures" / "slop.html"


async def _judge(source: str | Path, kind: str) -> dict:
    """
    Load the design-loop bundle, spawn the design-judge agent, and return the
    parsed RESULT dict.

    Uses the real provider — no mocks, no stubs.

    Parameters
    ----------
    source:
        Path or string passed as the ``source`` field to the agent.
    kind:
        One of ``html``, ``url``, or ``image``.

    Returns
    -------
    dict
        Parsed RESULT JSON returned by the agent.  Keys: ``report_html_path``,
        ``total``, ``top_fixes``, ``target_html_path``.
    """
    from amplifier_foundation import load_bundle  # noqa: PLC0415

    bundle = await load_bundle(REPO / "bundle.md")
    prepared = await bundle.prepare()
    agent = await load_bundle(REPO / "agents" / "design-judge.md")

    result = await prepared.spawn(
        child_bundle=agent,
        instruction=(
            f"Judge this artifact. source={source} kind={kind}. "
            "Return only the RESULT JSON: "
            '{"report_html_path", "total", "top_fixes", "target_html_path"}.'
        ),
    )

    output = result["output"]
    if isinstance(output, str):
        # Strip any markdown code fences before parsing
        cleaned = output.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # Drop first line (```json or ```) and last line (```)
            cleaned = "\n".join(lines[1:-1]).strip()
        return json.loads(cleaned)
    # Already a dict (some orchestrators return structured output directly)
    return output


@pytest.mark.manual
async def test_slop_scores_low_with_specific_fixes():
    """Slop page scores <= 16, has actionable fixes, and report is dogfood-clean."""
    result = await _judge(SLOP, "html")

    # 1. Total must be low — slop is genuinely bad
    total = result["total"]
    assert total <= 16, (
        f"Expected slop page to score <= 16 but got {total}. "
        "Check that the agent is using the 8-criteria rubric correctly."
    )

    # 2. At least one actionable fix must be present
    top_fixes = result.get("top_fixes", [])
    assert top_fixes, (
        "Expected the agent to surface at least one top_fix for the slop page. "
        f"Got: {top_fixes!r}"
    )

    # 3. The generated report must exist on disk
    report_path = Path(result["report_html_path"])
    assert report_path.exists(), (
        f"report_html_path {report_path} was returned but the file does not exist."
    )

    # 4. Dogfood check: the report itself must not use slop patterns
    report_html = report_path.read_text(encoding="utf-8").lower()
    assert "linear-gradient" not in report_html, (
        "The generated report contains 'linear-gradient' — the report is using the "
        "very slop pattern it criticises (dogfood violation)."
    )
    assert '"inter"' not in report_html, (
        "The generated report references 'Inter' as a quoted font — the report is "
        "using the default font slop pattern it criticises (dogfood violation)."
    )


@pytest.mark.manual
async def test_target_state_rejudges_higher():
    """The improved target-state HTML must score strictly higher than the original."""
    # First judge: original slop
    first = await _judge(SLOP, "html")

    # Sanity: target-state must be available
    assert "target-state unavailable" not in str(first.get("report_html_path", "")), (
        "The first judge run indicates target-state was unavailable. "
        "Cannot compare improvement without a target-state."
    )
    target_html_path = first.get("target_html_path")
    assert target_html_path, (
        "Expected the first judge run to produce a target_html_path. "
        f"Got: {first!r}"
    )
    assert Path(target_html_path).exists(), (
        f"target_html_path {target_html_path} was returned but the file does not exist."
    )

    # Second judge: improved target-state
    second = await _judge(target_html_path, "html")

    # The improved version must score strictly higher
    first_total = first["total"]
    second_total = second["total"]
    assert second_total > first_total, (
        f"Expected the target-state re-judge ({second_total}) to score strictly "
        f"higher than the original slop ({first_total}). "
        "This suggests the target-state did not meaningfully improve the design."
    )
