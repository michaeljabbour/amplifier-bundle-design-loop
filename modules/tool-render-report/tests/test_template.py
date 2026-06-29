"""Tests for render_report() in template.py — TDD RED phase, written before implementation.

Four tests:
  1. test_report_is_self_contained_and_shows_scores  — full render, checks HTML structure
  2. test_report_handles_target_unavailable           — honest fallback when no target data
  3. test_dogfood_no_slop_markers                    — the report must not emit slop it penalises
  4. test_scores_unavailable_renders_honestly         — N/A path surfaces raw text
"""

from amplifier_module_tool_render_report.verdict import CRITERIA
from amplifier_module_tool_render_report.template import render_report

# A minimal 1x1 PNG encoded in base64 (valid image header, won't crash browsers)
_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+"
    "M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _verdict(total: int = 12) -> dict:
    """Build a valid parse_verdict-shaped dict with scores summing to *total* and 2 fixes."""
    # Distribute *total* evenly across 8 criteria (each 0-4).
    # E.g. total=12 -> 4 criteria at 2, 4 criteria at 1.
    base = total // len(CRITERIA)
    remainder = total % len(CRITERIA)
    scores = {
        c: base + (1 if i < remainder else 0)
        for i, c in enumerate(CRITERIA)
    }
    return {
        "valid": True,
        "verdict": {
            "scores": scores,
            "total": total,
            "fixes": [
                {
                    "criterion": "clarity",
                    "issue": "Text contrast too low",
                    "fix": "Raise contrast to AA+",
                },
                {
                    "criterion": "elegance",
                    "issue": "Too many competing weights",
                    "fix": "Limit to one typeface family",
                },
            ],
        },
    }


def test_report_is_self_contained_and_shows_scores():
    """Full render: DOCTYPE, all criteria, total/32, base64 screenshot, HTML-escaped A."""
    v = _verdict(total=12)
    output = render_report(
        v,
        target_html="<h1>A</h1>",
        target_screenshot_b64=_TINY_PNG_B64,
    )
    low = output.lstrip().lower()

    # Must be a full, self-contained HTML document
    assert low.startswith("<!doctype html"), "Output must begin with <!DOCTYPE html>"

    # Every criterion name must appear in the output (score table)
    for c in CRITERIA:
        assert c in low, f"Criterion {c!r} missing from rendered output"

    # Total score displayed as 'N / 32'
    assert "12 / 32" in output or "12/32" in output, "Total score 12/32 not found"

    # Screenshot embedded as a data URI (no external fetch)
    assert "data:image/png;base64," in output, "Base64 data URI missing"

    # target_html must be HTML-escaped, NOT executed as markup
    assert "&lt;h1&gt;A&lt;/h1&gt;" in output, "target_html must be HTML-escaped"


def test_report_handles_target_unavailable():
    """When target_html and b64 are both None, honest 'unavailable' message, no data URI."""
    v = _verdict()
    output = render_report(v, target_html=None, target_screenshot_b64=None)

    assert "target-state unavailable" in output.lower(), (
        "'target-state unavailable' message not found"
    )
    assert "data:image/png;base64," not in output, "Data URI should not appear when target absent"


def test_dogfood_no_slop_markers():
    """The report must not emit the same slop patterns it penalises in other UIs."""
    v = _verdict()
    output = render_report(v)
    low = output.lower()

    # No CSS gradient functions
    assert "linear-gradient" not in low, "No linear-gradient allowed"
    assert "radial-gradient" not in low, "No radial-gradient allowed"

    # Inter is the canonical slop font -- must not appear quoted as a CSS font name
    assert '"inter"' not in low, "Inter font (double-quoted) must not appear"
    assert "'inter'" not in low, "Inter font (single-quoted) must not appear"

    # Editorial heading font must be present
    assert "cormorant garamond" in low, "Cormorant Garamond heading font missing"

    # No external fetches
    assert "http://" not in output, "No http:// URLs allowed (external fetch)"
    assert "https://" not in output, "No https:// URLs allowed (external fetch)"

    # No script injection
    assert "<script" not in low, "No <script> tags allowed in self-contained report"


def test_scores_unavailable_renders_honestly():
    """When scores_unavailable, renders N/A and surfaces the raw text for debugging."""
    verdict = {"valid": False, "scores_unavailable": True, "raw": "garbled"}
    output = render_report(verdict)
    low = output.lower()

    # Must acknowledge the failure honestly
    assert "n/a" in low or "unavailable" in low, "Must say N/A or unavailable when scores missing"

    # Must surface the raw payload so the user can debug
    assert "garbled" in output, "Raw garbled text must appear in output"
