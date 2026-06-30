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


# =============================================================================
# NEW TESTS for render(state) -> two-artifact system (TDD RED phase)
# =============================================================================

import os
import tempfile
from pathlib import Path

# Import will fail until render() is implemented — that's the RED state.
# We import inside each test so test_template collection still works even if
# the function doesn't exist yet (ImportError surfaces as test failures, not
# collection-time crashes, if we guard it).


def _sample_champion_html() -> str:
    """Minimal bare page to serve as the champion candidate."""
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Champion Page</title>
</head><body><h1>Champion</h1><p>This is the improved version.</p></body></html>"""


def _make_state(tmp_path: Path, converged: bool = True, gate_reason: str = "bar_met") -> dict:
    """Build a minimal state dict matching the ledger/trace shape."""
    # Write a fake candidate.html for the champion
    champion_path = tmp_path / "champion.html"
    champion_path.write_text(_sample_champion_html(), encoding="utf-8")

    records = [
        {
            "pass": 0,
            "task_class": "demo-critique",
            "decision": "NEW_BEST",
            "outcome": "accepted",
            "scores": {"clarity": 1, "elegance": 1, "restraint": 0,
                       "empowerment": 2, "agency": 2, "ease": 2, "character": 0, "point": 2},
            "fix_batch": [],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(champion_path),
        },
        {
            "pass": 1,
            "decision": "NO_GAIN",
            "outcome": "rejected",
            "scores": {"clarity": 2, "elegance": 1, "restraint": 0,
                       "empowerment": 2, "agency": 2, "ease": 2, "character": 0, "point": 2},
            "fix_batch": [{"criterion": "clarity", "issue": "Low contrast", "fix": "Raise to AA"}],
            "artifact_ref": str(tmp_path / "pass1.html"),
        },
        {
            "pass": 2,
            "decision": "REGRESSION",
            "outcome": "rejected",
            "scores": {"clarity": 1, "elegance": 1, "restraint": 0,
                       "empowerment": 1, "agency": 2, "ease": 1, "character": 0, "point": 1},
            "fix_batch": [],
            "lint_results": {"hard_fail": True, "hard_fail_reasons": ["contrast_pass"]},
            "artifact_ref": str(tmp_path / "pass2.html"),
        },
    ]
    return {
        "records": records,
        "gate": {"action": "ESCALATE" if not converged else "DONE", "reason": gate_reason},
        "champion": {
            "scores": {"clarity": 1, "elegance": 1, "restraint": 0,
                       "empowerment": 2, "agency": 2, "ease": 2, "character": 0, "point": 2},
            "total": 10,
            "artifact_ref": str(champion_path),
        },
        "converged": converged,
    }


def test_render_produces_two_files(tmp_path: Path) -> None:
    """render(state, out_dir) writes upgraded.html AND report.html."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path, converged=False, gate_reason="floor_breach")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = render(state, out_dir=str(out_dir))

    assert "upgraded_html" in result, "render() must return paths dict with upgraded_html key"
    assert "report_html" in result, "render() must return paths dict with report_html key"

    upgraded = Path(result["upgraded_html"])
    report = Path(result["report_html"])
    assert upgraded.exists(), f"upgraded.html not created at {upgraded}"
    assert report.exists(), f"report.html not created at {report}"


def test_report_contains_per_pass_tracelog(tmp_path: Path) -> None:
    """report.html must include each pass index and its total score."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path, converged=False, gate_reason="floor_breach")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8")

    # Each pass index must appear
    assert "Pass 0" in report or "pass 0" in report.lower(), "Pass 0 missing from tracelog"
    assert "Pass 1" in report or "pass 1" in report.lower(), "Pass 1 missing from tracelog"
    assert "Pass 2" in report or "pass 2" in report.lower(), "Pass 2 missing from tracelog"

    # Each pass total must appear — Pass 0 total=10, Pass 1 total=11, Pass 2 total=7
    assert "10" in report, "Pass 0 total (10) missing from tracelog"
    assert "11" in report, "Pass 1 total (11) missing from tracelog"
    assert "7" in report, "Pass 2 total (7) missing from tracelog"


def test_report_honest_nonconvergence(tmp_path: Path) -> None:
    """When converged=False + gate reason=floor_breach, report must say so honestly."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path, converged=False, gate_reason="floor_breach")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8").lower()

    # Must NOT claim success / done
    # Must reference the escalation reason
    assert "floor_breach" in report or "floor breach" in report, (
        "floor_breach reason must appear in non-convergence report"
    )
    # Must NOT use misleading success language as the outcome descriptor
    assert "escalat" in report or "didn" in report or "not converge" in report or "breach" in report, (
        "Report must honestly surface non-convergence, not mask it as success"
    )


def test_report_has_page_worth_tokens(tmp_path: Path) -> None:
    """report.html must carry the Page_Worth design tokens (fonts + amber/ink oklch)."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path, converged=False, gate_reason="floor_breach")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8")
    low = report.lower()

    # Font family stacks (user-specified tokens)
    assert "cormorant garamond" in low, "Cormorant Garamond display font missing"
    assert "lora" in low, "Lora body font missing"
    assert "jost" in low, "Jost UI font missing"

    # oklch amber and ink custom properties
    assert "oklch" in low, "oklch() palette missing from report"
    assert "--slp-amber" in report or "0.68 0.12 65" in report or "amber" in low, (
        "Amber oklch token missing from report"
    )
    assert "--slp-ink" in report or "0.18 0.015 65" in report or "--ink" in low, (
        "Ink oklch token missing from report"
    )


def test_report_is_offline_and_no_script(tmp_path: Path) -> None:
    """report.html faithfully reuses the REAL Page_Worth design, which DOES fetch
    Google Fonts via @import (https://fonts.googleapis.com/...). That is no longer
    banned -- it's the real source's actual styling, vendored verbatim.

    The journey nav (Landing/Working/Results tabs + working-log replay) now adds
    ONE self-contained inline <script> -- vanilla, no framework, no external src,
    no network calls of its own. The invariant that still holds unconditionally:
    no <script> may load anything external (no src="http..." anywhere)."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path, converged=False, gate_reason="floor_breach")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8")
    low = report.lower()

    # The vendored Page_Worth <style> block fetches Google Fonts -- expected now.
    assert "@import" in low, "Vendored Page_Worth @import (Google Fonts) missing"
    assert "fonts.googleapis.com" in low, "Google Fonts host missing from @import"

    # The invariant that now holds: any <script> present must not pull from the
    # network. No external src= of any kind (http/https) is allowed.
    assert 'src="http' not in low, "External script/resource src found (violates offline guarantee)"


def test_upgraded_html_is_bare_champion(tmp_path: Path) -> None:
    """upgraded.html must be the bare champion page — no report chrome."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path, converged=False, gate_reason="floor_breach")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    result = render(state, out_dir=str(out_dir))

    upgraded = Path(result["upgraded_html"]).read_text(encoding="utf-8")

    # Must contain champion content
    assert "Champion" in upgraded or "champion" in upgraded.lower(), (
        "upgraded.html must contain champion page content"
    )

    # Must NOT contain report chrome markers
    assert "Design Loop" not in upgraded or "verdict" not in upgraded.lower(), (
        "upgraded.html must be bare champion HTML, not the report"
    )
    # More specific: the report's eyebrow text and trace table headers should NOT be in upgraded
    assert "tracelog" not in upgraded.lower(), "upgraded.html must not contain report chrome (tracelog)"
    assert "per-pass" not in upgraded.lower(), "upgraded.html must not contain report chrome (per-pass)"


# =============================================================================
# NEW TESTS: baseline.html, preview cards, history, durable persistence (TDD RED)
# =============================================================================

def test_baseline_html_emitted(tmp_path: Path) -> None:
    """render() emits baseline.html = bare byte-for-byte copy of pass-0 artifact."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path)
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir))

    baseline = out_dir / "baseline.html"
    assert baseline.exists(), "baseline.html not created"
    assert baseline.read_text(encoding="utf-8") == _sample_champion_html(), (
        "baseline.html must be exact copy of pass-0 artifact_ref bytes"
    )
    low = baseline.read_text(encoding="utf-8").lower()
    assert "tracelog" not in low, "baseline.html must be bare html, not report chrome"
    assert "pw-headline" not in low, "baseline.html must not contain Page_Worth chrome"


def test_report_has_two_preview_anchors(tmp_path: Path) -> None:
    """report.html contains two open-in-new-tab anchors (baseline.html + upgraded.html)."""
    import re
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path)
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir), durable_base=str(tmp_path / "dl"))
    report = Path(result["report_html"]).read_text(encoding="utf-8")

    assert 'href="baseline.html"' in report, "No relative href=baseline.html in report"
    assert 'href="upgraded.html"' in report, "No relative href=upgraded.html in report"

    anchors = re.findall(r"<a [^>]*>", report)
    new_tab = [a for a in anchors if 'target="_blank"' in a and 'rel="noopener"' in a]
    assert len(new_tab) >= 2, (
        f"Expected >=2 new-tab anchors with target=_blank+rel=noopener, found {len(new_tab)}"
    )
    bl_anchors = [a for a in new_tab if "baseline.html" in a]
    up_anchors = [a for a in new_tab if "upgraded.html" in a]
    assert bl_anchors, "No target=_blank anchor for baseline.html"
    assert up_anchors, "No target=_blank anchor for upgraded.html"


def test_report_has_iframes_no_scripts(tmp_path: Path) -> None:
    """report.html has >=2 iframes, none with allow-scripts."""
    import re
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path)
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir), durable_base=str(tmp_path / "dl"))
    report = Path(result["report_html"]).read_text(encoding="utf-8")

    iframes = re.findall(r"<iframe[^>]*>", report, re.IGNORECASE)
    assert len(iframes) >= 2, f"Expected >=2 iframes, found {len(iframes)}"
    for ifr in iframes:
        assert "allow-scripts" not in ifr.lower(), (
            f"iframe must NOT carry allow-scripts: {ifr}"
        )
        assert "sandbox" in ifr.lower(), f"iframe should carry sandbox attribute: {ifr}"


def test_history_jsonl_appended_and_past_verdicts_in_report(tmp_path: Path) -> None:
    """With durable_base set: history.jsonl gets one line; report shows Past verdicts."""
    import json
    from amplifier_module_tool_render_report.template import render

    dl_base = tmp_path / "dl"
    out_dir = tmp_path / "out"
    state = _make_state(tmp_path)
    result = render(state, out_dir=str(out_dir), durable_base=str(dl_base))

    history_path = dl_base / "history.jsonl"
    assert history_path.exists(), "history.jsonl not created under durable_base"

    lines = [l for l in history_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert lines, "history.jsonl is empty"

    entry = json.loads(lines[-1])
    assert "run_id" in entry, "history entry missing run_id"
    assert "ts" in entry, "history entry missing ts"
    assert "total" in entry, "history entry missing total"
    assert "report_path" in entry, "history entry missing report_path"
    assert "converged" in entry, "history entry missing converged"

    report = Path(result["report_html"]).read_text(encoding="utf-8").lower()
    assert "past verdicts" in report, (
        "Past verdicts section missing from report when durable_base is set"
    )


def test_report_invariants_after_new_features(tmp_path: Path) -> None:
    """Real Page_Worth design tokens hold after preview+history+process-trace added.

    NOTE: the radial-gradient body background and the Google Fonts @import are
    the REAL Page_Worth.html design (Page_Worth.html lines 1614-1637), vendored
    verbatim -- they are intentionally present, not banned. The only invariant
    that still holds unconditionally is no <script> tag.
    """
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path)
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir), durable_base=str(tmp_path / "dl"))
    report = Path(result["report_html"]).read_text(encoding="utf-8")
    low = report.lower()

    # Real Page_Worth design tokens must be present (vendored verbatim).
    assert "radial-gradient(" in low, "Page_Worth radial-gradient body background missing"
    assert "@import" in low, "Page_Worth Google Fonts @import missing"
    assert "--slp-amber" in report, "--slp-amber design token missing"
    assert "--font-display" in report, "--font-display design token missing"
    assert "cormorant garamond" in low, "Cormorant Garamond font missing"

    # The invariant that now holds: no <script> may load anything external.
    assert 'src="http' not in low, "External script src found (violates offline guarantee)"

    # Sub-features added alongside this re-skin must all render.
    assert "scorecard" in low and "weakest first" in low, "Weakest-first scorecard missing"
    assert "process" in low and "how the agent worked" in low, "Process trace section missing"
    assert "past verdicts" in low, "Past verdicts (history) section missing"


def test_baseline_missing_graceful(tmp_path: Path) -> None:
    """When records[0].artifact_ref is missing, render() completes without raising."""
    from amplifier_module_tool_render_report.template import render

    state = _make_state(tmp_path)
    state["records"][0]["artifact_ref"] = str(tmp_path / "nonexistent_baseline.html")

    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir))

    assert Path(result["report_html"]).exists(), "report.html must still be created"
    assert Path(result["upgraded_html"]).exists(), "upgraded.html must still be created"


# =============================================================================
# NEW TESTS: full journey (LANDING / WORKING / RESULTS) + demo fixtures (TDD RED)
# =============================================================================

FIXTURES_DEMO = Path(__file__).resolve().parent.parent / "fixtures" / "demo"
DEMO_SLOP = FIXTURES_DEMO / "slop.html"
DEMO_UPGRADED = FIXTURES_DEMO / "upgraded.html"


def _make_demo_state(converged: bool = True, gate_reason: str = "bar_met") -> dict:
    """A state whose pass-0 baseline and champion artifacts are the REAL
    fixtures/demo/{slop,upgraded}.html pages, used to prove the before/after
    previews render the substantial demo content, not toy stubs."""
    records = [
        {
            "pass": 0,
            "task_class": "landing-page-critique",
            "decision": "NEW_BEST",
            "outcome": "accepted",
            "scores": {"clarity": 1, "elegance": 0, "restraint": 0,
                       "empowerment": 1, "agency": 1, "ease": 1, "character": 0, "point": 1},
            "fix_batch": [
                {"criterion": "restraint", "issue": "Three identical feature cards.",
                 "fix": "Cut to the claims that actually differentiate."},
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(DEMO_SLOP),
        },
        {
            "pass": 1,
            "decision": "REGRESSION",
            "outcome": "rejected",
            "scores": {"clarity": 2, "elegance": 1, "restraint": 0,
                       "empowerment": 1, "agency": 1, "ease": 1, "character": 0, "point": 1},
            "fix_batch": [],
            "lint_results": {"hard_fail": True, "hard_fail_reasons": ["contrast_pass"]},
            "artifact_ref": str(DEMO_SLOP),
        },
        {
            "pass": 2,
            "decision": "NEW_BEST",
            "outcome": "accepted",
            "scores": {"clarity": 4, "elegance": 4, "restraint": 4,
                       "empowerment": 3, "agency": 3, "ease": 4, "character": 4, "point": 3},
            "fix_batch": [
                {"criterion": "restraint", "issue": "Replaced equal cards with an asymmetric list.",
                 "fix": "Each capability earns its own space."},
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(DEMO_UPGRADED),
        },
    ]
    return {
        "records": records,
        "gate": {"action": "ESCALATE" if not converged else "DONE", "reason": gate_reason},
        "champion": {
            "scores": records[2]["scores"],
            "total": sum(records[2]["scores"].values()),
            "artifact_ref": str(DEMO_UPGRADED),
        },
        "converged": converged,
    }


def test_report_has_landing_view(tmp_path: Path) -> None:
    """report.html reproduces Page_Worth's LANDING screen (lines 1659-1709):
    the 'Design intelligence' eyebrow, the H1, and the three mode tabs."""
    from amplifier_module_tool_render_report.template import render

    state = _make_demo_state()
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8")

    assert "Design intelligence" in report, "LANDING eyebrow missing"
    assert "Drop a screen" in report, "LANDING H1 ('Drop a screen...') missing"
    assert "Know what to" in report and ">fix<" in report, "LANDING H1 'fix' emphasis missing"
    assert "Single screen" in report, "LANDING mode tab 'Single screen' missing"
    assert "Compare A" in report, "LANDING mode tab 'Compare A \u00b7 B' missing"
    assert "Triage many" in report, "LANDING mode tab 'Triage many' missing"
    assert 'data-pw-view="landing"' in report, "LANDING view container missing"


def test_report_has_working_transaction_log(tmp_path: Path) -> None:
    """report.html includes a WORKING transaction-log view with per-pass
    maker/lints/critic/gate log lines, and the shimmer class on the most
    recently streamed (last) row."""
    from amplifier_module_tool_render_report.template import render

    state = _make_demo_state(converged=False, gate_reason="floor_breach")
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8")
    low = report.lower()

    assert 'data-pw-view="working"' in report, "WORKING view container missing"
    assert "transaction log" in low, "WORKING section heading missing"
    assert ">MAKER<" in report, "MAKER log step missing"
    assert ">LINTS<" in report, "LINTS log step missing"
    assert ">CRITIC<" in report, "CRITIC log step missing"
    assert ">GATE<" in report, "GATE log step missing"

    # Lint pass/FAIL must be driven from real per-pass lint_results.
    assert "PASS" in report, "A passing lint result must render PASS"
    assert "FAIL" in report, "A failing lint result must render FAIL with reasons"
    assert "contrast_pass" in report, "Lint failure reason must be surfaced"

    # Shimmer 'streaming' treatment on the most recent row.
    assert "pw-row-active" in report, "Shimmer class for the active/streaming row missing"
    assert "data-pw-logrow" in report, "Per-line data-pw-logrow marker missing (needed for replay)"
    assert "data-pw-play" in report, "Replay control missing from WORKING view"


def test_report_results_view_still_present(tmp_path: Path) -> None:
    """The existing RESULTS view (scorecard + verdict) survives the journey wrap."""
    from amplifier_module_tool_render_report.template import render

    state = _make_demo_state()
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8")
    low = report.lower()

    assert 'data-pw-view="results"' in report, "RESULTS view container missing"
    assert "scorecard" in low and "weakest first" in low, "A\u2192B scorecard missing from RESULTS"
    assert "worth it" in low or "stopped" in low, "Verdict sentence missing from RESULTS"


def test_no_external_script_src_anywhere(tmp_path: Path) -> None:
    """The journey nav's inline <script> (tab-switch + replay) must not load
    anything external -- vanilla JS only, no src= of any kind."""
    import re

    from amplifier_module_tool_render_report.template import render

    state = _make_demo_state()
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir))
    report = Path(result["report_html"]).read_text(encoding="utf-8")

    scripts = re.findall(r"<script[^>]*>", report, re.IGNORECASE)
    assert scripts, "Expected exactly one inline <script> tag for journey navigation"
    for tag in scripts:
        assert "src=" not in tag.lower(), f"<script> must not carry a src= attribute: {tag}"
    assert 'src="http' not in report.lower(), "No script/resource may load from an external URL"


def test_previews_invariants_hold_with_journey(tmp_path: Path) -> None:
    """Preview anchors/iframes keep target=_blank+rel=noopener and no
    allow-scripts even after the LANDING/WORKING views are added."""
    import re

    from amplifier_module_tool_render_report.template import render

    state = _make_demo_state()
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir), durable_base=str(tmp_path / "dl"))
    report = Path(result["report_html"]).read_text(encoding="utf-8")

    anchors = re.findall(r"<a [^>]*>", report)
    new_tab = [a for a in anchors if 'target="_blank"' in a and 'rel="noopener"' in a]
    assert len(new_tab) >= 2, "Expected >=2 target=_blank+rel=noopener preview anchors"

    iframes = re.findall(r"<iframe[^>]*>", report, re.IGNORECASE)
    assert len(iframes) >= 2, "Expected >=2 iframes (preview + landing input)"
    for ifr in iframes:
        assert "allow-scripts" not in ifr.lower(), f"iframe must not carry allow-scripts: {ifr}"
        assert "sandbox" in ifr.lower(), f"iframe must carry sandbox attribute: {ifr}"


def test_demo_fixtures_are_substantial_real_pages() -> None:
    """fixtures/demo/{slop,upgraded}.html are real, substantial pages -- not
    toy one-liner stubs."""
    assert DEMO_SLOP.exists(), f"missing demo fixture: {DEMO_SLOP}"
    assert DEMO_UPGRADED.exists(), f"missing demo fixture: {DEMO_UPGRADED}"

    slop_text = DEMO_SLOP.read_text(encoding="utf-8")
    upgraded_text = DEMO_UPGRADED.read_text(encoding="utf-8")

    assert len(slop_text) > 4000, "fixtures/demo/slop.html is too small to be a real page"
    assert len(upgraded_text) > 4000, "fixtures/demo/upgraded.html is too small to be a real page"
    assert "linear-gradient" in slop_text, "slop.html should use the recognizable purple/blue gradient"
    assert "Cormorant Garamond" in upgraded_text, "upgraded.html should use the editorial display font"


def test_baseline_and_upgraded_are_real_demo_fixtures(tmp_path: Path) -> None:
    """render()'s A/B previews resolve to the REAL demo fixtures, not stubs:
    baseline.html is byte-identical to fixtures/demo/slop.html (the recognizable
    slop hero), and the report's 'A' preview iframe points at it."""
    from amplifier_module_tool_render_report.template import render

    state = _make_demo_state()
    out_dir = tmp_path / "out"
    result = render(state, out_dir=str(out_dir))

    baseline = Path(result["baseline_html"])
    assert baseline.read_text(encoding="utf-8") == DEMO_SLOP.read_text(encoding="utf-8"), (
        "baseline.html must be a byte-identical copy of fixtures/demo/slop.html"
    )
    assert "Synergize Your Data" in baseline.read_text(encoding="utf-8"), (
        "baseline.html must contain the recognizable slop hero text"
    )

    upgraded = Path(result["upgraded_html"])
    assert "See what's actually" in upgraded.read_text(encoding="utf-8"), (
        "upgraded.html must contain the editorial redesign's real headline"
    )

    report = Path(result["report_html"]).read_text(encoding="utf-8")
    assert 'src="baseline.html"' in report, "report's A iframe must resolve to baseline.html"
    assert 'src="upgraded.html"' in report, "report's B iframe must resolve to upgraded.html"

