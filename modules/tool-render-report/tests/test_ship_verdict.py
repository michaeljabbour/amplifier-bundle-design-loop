"""Tests for ship_verdict() -- the ONE canonical ship/no-ship call.

ship_verdict() is the single source of truth imported by BOTH the app
(app/results.py) and this report renderer (template.py), so a run can never
show two different ship verdicts across the two surfaces.

Covers:
  1. Unit tests for ship_verdict() directly: blockers veto, converged+bar-met,
     below-bar.
  2. An integration test proving the report's rendered hero uses the exact
     same phrase ship_verdict() returns for a given (total, converged,
     blockers) combination -- i.e. the wiring, not just the function.
"""

from pathlib import Path

from amplifier_module_tool_render_report.template import SHIP_BAR, render, ship_verdict


class TestShipVerdictUnit:
    def test_blockers_veto_ship_regardless_of_score(self):
        """A ground-truth blocker vetoes shipping even at a high, converged score."""
        assert (
            ship_verdict(29, converged=True, blockers=2)
            == "Not ready \u2014 2 blockers"
        )

    def test_single_blocker_uses_singular_noun(self):
        assert (
            ship_verdict(29, converged=True, blockers=1)
            == "Not ready \u2014 1 blocker"
        )

    def test_converged_and_bar_met_ships(self):
        """Converged + total >= bar + no blockers -> Ready to ship."""
        assert ship_verdict(29, converged=True, blockers=0) == "Ready to ship"
        assert ship_verdict(SHIP_BAR, converged=True, blockers=0) == "Ready to ship"

    def test_below_bar_is_not_ready(self):
        """Below the bar (even if converged) is honestly 'Not ready yet'."""
        assert ship_verdict(18, converged=False, blockers=0) == "Not ready yet"
        assert ship_verdict(18, converged=True, blockers=0) == "Not ready yet"

    def test_converged_but_below_custom_bar(self):
        """A custom, stricter bar can withhold 'Ready to ship' even when converged."""
        assert ship_verdict(20, converged=True, blockers=0, bar=25) == "Not ready yet"
        assert ship_verdict(25, converged=True, blockers=0, bar=25) == "Ready to ship"

    def test_default_bar_is_ship_bar_constant(self):
        """Calling with no explicit bar uses the shared SHIP_BAR constant."""
        assert ship_verdict(SHIP_BAR - 1, converged=True, blockers=0) == "Not ready yet"
        assert ship_verdict(SHIP_BAR, converged=True, blockers=0) == "Ready to ship"


def _make_state(tmp_path: Path, *, total: int, converged: bool, blockers: int = 0) -> dict:
    """Minimal state dict for render() -- just enough to reach the hero."""
    champion_path = tmp_path / "champion.html"
    champion_path.write_text("<html><body>Champion</body></html>", encoding="utf-8")
    return {
        "records": [
            {
                "pass": 0,
                "task_class": "demo",
                "decision": "BASELINE",
                "scores": {"clarity": 0, "elegance": 0, "restraint": 0,
                           "empowerment": 0, "agency": 0, "ease": 0,
                           "character": 0, "point": 0},
                "artifact_ref": str(champion_path),
            }
        ],
        "gate": {"action": "DONE" if converged else "ESCALATE", "reason": "bar_met"},
        "champion": {
            "scores": {"clarity": 0, "elegance": 0, "restraint": 0,
                       "empowerment": 0, "agency": 0, "ease": 0,
                       "character": 0, "point": 0},
            "total": total,
            "artifact_ref": str(champion_path),
        },
        "converged": converged,
        "blockers": blockers,
    }


class TestShipVerdictReportWiring:
    """Prove the report's rendered hero uses ship_verdict(), not the old
    per-band 'ready' phrase (_pw_band_for no longer has a 'ready' key)."""

    def test_report_matches_ship_verdict_when_escalated_below_bar(self, tmp_path: Path) -> None:
        total, converged, blockers = 18, False, 0
        state = _make_state(tmp_path, total=total, converged=converged, blockers=blockers)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = render(state, out_dir=str(out_dir))
        report = Path(result["report_html"]).read_text(encoding="utf-8")

        expected = ship_verdict(total, converged=converged, blockers=blockers)
        assert expected == "Not ready yet"
        assert expected in report
        # The old, conflicting band phrase must be gone.
        assert "Ships, but forgettable" not in report

    def test_report_matches_ship_verdict_when_converged_bar_met(self, tmp_path: Path) -> None:
        total, converged, blockers = 29, True, 0
        state = _make_state(tmp_path, total=total, converged=converged, blockers=blockers)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = render(state, out_dir=str(out_dir))
        report = Path(result["report_html"]).read_text(encoding="utf-8")

        expected = ship_verdict(total, converged=converged, blockers=blockers)
        assert expected == "Ready to ship"
        assert expected in report

    def test_quality_tier_band_untouched_structurally(self) -> None:
        """_pw_band_for() still returns the quality-tier descriptor (name/line/
        color) -- that axis is untouched -- it just no longer carries a
        competing "ready" ship phrase (the old source of the bug)."""
        from amplifier_module_tool_render_report.template import _pw_band_for

        band = _pw_band_for(29)
        assert band["name"] == "Exemplary"
        assert band["line"] == "Ship it and learn in the open."
        assert "c" in band and "s" in band
        assert "ready" not in band, (
            "_pw_band_for() must no longer carry a 'ready' ship phrase -- "
            "ship_verdict() is now the only source of that decision"
        )

    def test_blocker_state_overrides_convergence(self, tmp_path: Path) -> None:
        """A run that converged and cleared the bar but has a ground-truth
        blocker must still show 'Not ready' in the report."""
        state = _make_state(tmp_path, total=29, converged=True, blockers=1)
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = render(state, out_dir=str(out_dir))
        report = Path(result["report_html"]).read_text(encoding="utf-8")

        expected = ship_verdict(29, converged=True, blockers=1)
        assert expected == "Not ready \u2014 1 blocker"
        assert expected in report

    def test_render_still_works_with_no_blockers_bar_in_state(self, tmp_path: Path) -> None:
        """Standalone render() (the real recipe path, no app payload in front
        of it) must keep working when state carries no 'blockers'/'bar' keys
        at all -- defaults (blockers=0, bar=SHIP_BAR) apply."""
        champion_path = tmp_path / "champion.html"
        champion_path.write_text("<html><body>X</body></html>", encoding="utf-8")
        state = {
            "records": [{"pass": 0, "scores": {c: 0 for c in
                         ("clarity", "elegance", "restraint", "empowerment",
                          "agency", "ease", "character", "point")},
                         "artifact_ref": str(champion_path)}],
            "gate": {"action": "DONE", "reason": "bar_met"},
            "champion": {"total": 29, "scores": {c: 0 for c in
                         ("clarity", "elegance", "restraint", "empowerment",
                          "agency", "ease", "character", "point")},
                         "artifact_ref": str(champion_path)},
            "converged": True,
            # deliberately no "blockers" / "bar" keys
        }
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = render(state, out_dir=str(out_dir))
        report = Path(result["report_html"]).read_text(encoding="utf-8")
        assert "Ready to ship" in report
