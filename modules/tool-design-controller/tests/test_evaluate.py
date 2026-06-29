"""Tests for DesignControllerTool op='evaluate' — TDD red → green cycle.

Covers: NEW_BEST, NO_GAIN, REGRESSION, INVALID, and the critical maximin
anti-gaming guarantee (higher total + lower worst-dim → REGRESSION, not NEW_BEST).
"""
import pytest

from amplifier_module_tool_design_controller import DesignControllerTool

DIMS = [
    "clarity", "elegance", "restraint", "empowerment",
    "agency", "ease", "character", "point",
]


def make_scores(**overrides):
    """Return a valid 8-dim score dict, all 2s by default."""
    scores = {d: 2 for d in DIMS}
    scores.update(overrides)
    return scores


@pytest.fixture
def tool():
    return DesignControllerTool()


# ---------------------------------------------------------------------------
# NEW_BEST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_best_when_worst_improves(tool):
    """Candidate with higher worst-dim than best → NEW_BEST."""
    best = make_scores(clarity=1)   # worst=1
    candidate = make_scores()       # all 2s → worst=2 > 1
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": best,
    })
    assert result.success is True
    out = result.output
    assert out["decision"] == "NEW_BEST"
    assert out["worst"] == 2
    assert out["total"] == 16


@pytest.mark.asyncio
async def test_new_best_when_no_best(tool):
    """best_scores=None and hard_fail=False → always NEW_BEST."""
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": make_scores(),
        "candidate_hard_fail": False,
        "best_scores": None,
    })
    assert result.success is True
    assert result.output["decision"] == "NEW_BEST"


@pytest.mark.asyncio
async def test_new_best_tiebreak_by_total(tool):
    """Same worst, higher total → NEW_BEST via tiebreak."""
    best = make_scores()            # all 2s: worst=2, total=16
    candidate = make_scores(clarity=3)  # worst still=2, total=17
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": best,
    })
    assert result.success is True
    assert result.output["decision"] == "NEW_BEST"


# ---------------------------------------------------------------------------
# NO_GAIN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_gain_identical_scores(tool):
    """Identical candidate and best → NO_GAIN."""
    scores = make_scores()
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": scores,
        "candidate_hard_fail": False,
        "best_scores": scores,
    })
    assert result.success is True
    assert result.output["decision"] == "NO_GAIN"


@pytest.mark.asyncio
async def test_no_gain_when_worst_equal_total_lower(tool):
    """Same worst but candidate total < best total → NO_GAIN.

    no_regress_dims=[] disables regression protection so we can test the
    pure tiebreak rule in isolation: same worst, lower total → NO_GAIN.
    (With default all-8 protection, candidate clarity=2 < best clarity=3
     would fire REGRESSION before reaching the tiebreak check.)
    """
    best = make_scores(clarity=3)   # total=17, worst=2
    candidate = make_scores()       # total=16, worst=2; clarity dropped 3→2
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": best,
        "no_regress_dims": [],  # disable regression — pure tiebreak test
    })
    assert result.success is True
    assert result.output["decision"] == "NO_GAIN"


# ---------------------------------------------------------------------------
# REGRESSION
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regression_when_no_regress_dim_drops(tool):
    """candidate[dim] < best[dim] - tau on a no-regress dim → REGRESSION."""
    best = make_scores()                # all 2s
    candidate = make_scores(clarity=0)  # clarity dropped 2→0
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": best,
        "no_regress_dims": ["clarity"],
        "tau": 0,
    })
    assert result.success is True
    out = result.output
    assert out["decision"] == "REGRESSION"
    assert "clarity" in out["regression_flags"]


@pytest.mark.asyncio
async def test_regression_tau_allows_small_drop(tool):
    """candidate[dim] == best[dim] - tau is NOT a regression (strict <)."""
    best = make_scores()                # all 2s
    candidate = make_scores(clarity=1)  # dropped by 1; tau=1 → 1 < 2-1=1 is False
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": best,
        "no_regress_dims": ["clarity"],
        "tau": 1,
    })
    assert result.success is True
    assert result.output["decision"] != "REGRESSION"


@pytest.mark.asyncio
async def test_regression_default_all_dims_protected(tool):
    """Default no_regress_dims = all 8 dims."""
    best = make_scores()
    candidate = make_scores(point=1)    # point dropped below tau=0 threshold
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": best,
        # no_regress_dims not supplied → defaults to all 8
    })
    assert result.success is True
    assert result.output["decision"] == "REGRESSION"
    assert "point" in result.output["regression_flags"]


# ---------------------------------------------------------------------------
# INVALID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_on_hard_fail(tool):
    """candidate_hard_fail=True → INVALID regardless of scores."""
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": make_scores(),
        "candidate_hard_fail": True,
        "best_scores": None,
    })
    assert result.success is True
    assert result.output["decision"] == "INVALID"


@pytest.mark.asyncio
async def test_invalid_takes_priority_over_regression(tool):
    """hard_fail=True takes priority even when a regression would trigger."""
    best = make_scores()
    candidate = make_scores(clarity=0)
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": True,
        "best_scores": best,
        "no_regress_dims": DIMS,
    })
    assert result.success is True
    assert result.output["decision"] == "INVALID"


# ---------------------------------------------------------------------------
# THE MAXIMIN ANTI-GAMING TEST (critical correctness guarantee)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_maximin_anti_gaming_regression_not_new_best(tool):
    """CRITICAL: higher total + lower worst-dim on no-regress dim → REGRESSION, NEVER NEW_BEST.

    This is the core MACA guarantee: gaming by raising other dims while dropping
    a protected dim is structurally impossible — REGRESSION fires BEFORE NEW_BEST.
    """
    # best: all 3s → total=24, worst=3
    best = {d: 3 for d in DIMS}
    # candidate: drop clarity to 1 but raise all others to 4
    #   total = 7*4 + 1 = 29  (higher than 24)
    #   worst = 1              (lower than 3, so NOT a worst improvement)
    #   clarity regression: 1 < 3 - 0 = 3  → REGRESSION fires first
    candidate = {d: 4 for d in DIMS}
    candidate["clarity"] = 1

    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": best,
        "no_regress_dims": DIMS,
        "tau": 0,
    })

    assert result.success is True
    out = result.output

    # Verify the totals to prove anti-gaming is meaningful
    assert out["total"] == 29, f"Expected total=29, got {out['total']}"
    assert sum(best.values()) == 24

    # The key assertion: must be REGRESSION, not NEW_BEST
    assert out["decision"] == "REGRESSION", (
        f"ANTI-GAMING FAILURE: candidate total={out['total']} > best=24, "
        f"but clarity dropped 3→1; expected REGRESSION, got {out['decision']}"
    )
    assert "clarity" in out["regression_flags"]


# ---------------------------------------------------------------------------
# Output field correctness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_fields_worst_dim_and_total(tool):
    """worst_dim, worst, and total are computed correctly from candidate_scores."""
    candidate = make_scores(ease=0, clarity=1)  # worst=0 at ease
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": candidate,
        "candidate_hard_fail": False,
        "best_scores": None,
    })
    assert result.success is True
    out = result.output
    assert out["worst_dim"] == "ease"
    assert out["worst"] == 0
    assert out["total"] == sum(candidate.values())


@pytest.mark.asyncio
async def test_regression_flags_empty_when_no_regression(tool):
    """regression_flags is always present and empty on non-REGRESSION decisions."""
    result = await tool.execute({
        "op": "evaluate",
        "candidate_scores": make_scores(),
        "candidate_hard_fail": False,
        "best_scores": None,
    })
    assert result.success is True
    assert result.output["regression_flags"] == []


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bad_op_returns_failure(tool):
    """Unknown op → success=False with error dict."""
    result = await tool.execute({"op": "unknown_op"})
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_missing_op_returns_failure(tool):
    """Missing op field → success=False."""
    result = await tool.execute({})
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_evaluate_missing_required_field_returns_failure(tool):
    """evaluate op with missing candidate_scores → success=False."""
    result = await tool.execute({
        "op": "evaluate",
        "candidate_hard_fail": False,
        # candidate_scores missing
    })
    assert result.success is False
