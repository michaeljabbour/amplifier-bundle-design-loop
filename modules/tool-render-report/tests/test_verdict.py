"""Tests for parse_verdict() in verdict.py — written BEFORE implementation (TDD RED)."""

from amplifier_module_tool_render_report.verdict import CRITERIA, parse_verdict


def _good_scores() -> dict:
    """Build a valid scores dict cycling through 0..4."""
    return {criterion: i % 5 for i, criterion in enumerate(CRITERIA)}


class TestParseVerdictValid:
    def test_parse_valid_dict(self):
        """A well-formed dict passes, total equals sum of scores, keys match CRITERIA."""
        scores = _good_scores()
        out = parse_verdict({"scores": scores, "fixes": [], "total": 0})
        assert out["valid"] is True
        assert out["verdict"]["total"] == sum(scores.values())
        assert set(out["verdict"]["scores"].keys()) == set(CRITERIA)

    def test_total_is_repaired_when_wrong(self):
        """Supplied total 999 is ignored; total is always recomputed from scores."""
        scores = _good_scores()
        out = parse_verdict({"scores": scores, "fixes": [], "total": 999})
        assert out["valid"] is True
        assert out["verdict"]["total"] == sum(scores.values())
        assert out["verdict"]["total"] != 999

    def test_parse_valid_json_string_with_fences(self):
        """A JSON string wrapped in ```json fences is stripped and parsed."""
        import json
        scores = _good_scores()
        payload = {"scores": scores, "fixes": [], "total": 0}
        fenced = f"```json\n{json.dumps(payload)}\n```"
        out = parse_verdict(fenced)
        assert out["valid"] is True
        # fixes defaults to [] if not list
        assert out["verdict"]["fixes"] == []


class TestParseVerdictInvalid:
    def test_missing_criterion_flags_unavailable(self):
        """Removing 'clarity' from scores makes the result invalid with scores_unavailable."""
        scores = _good_scores()
        del scores["clarity"]
        out = parse_verdict({"scores": scores, "fixes": [], "total": 0})
        assert out["valid"] is False
        assert out["scores_unavailable"] is True

    def test_out_of_range_score_flags_unavailable(self):
        """A score of 7 for 'point' is outside 0..4, must flag unavailable."""
        scores = _good_scores()
        scores["point"] = 7
        out = parse_verdict({"scores": scores, "fixes": [], "total": 0})
        assert out["valid"] is False
        assert out["scores_unavailable"] is True

    def test_garbage_string_flags_unavailable(self):
        """Non-JSON string must flag valid=False, scores_unavailable=True, preserve raw text."""
        out = parse_verdict("not json")
        assert out["valid"] is False
        assert out["scores_unavailable"] is True
        assert "raw" in out
