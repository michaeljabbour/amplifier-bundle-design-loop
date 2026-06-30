"""Tests for DesignControllerTool op='gate' — TDD red → green cycle.

Covers all 6 stopping-rule branches in order:
  1. DONE  – bar_met
  2. DONE  – budget_exhausted
  3. ESCALATE – floor_breach
  4. ESCALATE – plateau
  5. ROLLBACK – regression_retry  /  ESCALATE – regression_stuck
  6. PLAN  – continue (default)
"""
import pytest

from amplifier_module_tool_design_controller import DesignControllerTool

DIMS = [
    "clarity", "elegance", "restraint", "empowerment",
    "agency", "ease", "character", "point",
]


def make_scores(**overrides):
    scores = {d: 2 for d in DIMS}
    scores.update(overrides)
    return scores


@pytest.fixture
def tool():
    return DesignControllerTool()


# Shared baseline gate kwargs that do NOT trigger any stopping rule by themselves.
# Tests override individual fields as needed.
_BASE = dict(
    bar=24,           # total threshold (all-2s → total=16, won't meet bar=24)
    floors=1,         # each dim must be >= 1 (all-2s → no breach)
    budget_remaining=5,
    recent_improvements=[0.5, 0.5],  # 2 samples, k=3 → plateau won't fire
    k=3,
    epsilon=0.1,
    last_decision="NEW_BEST",
    target_retried=False,
)


def gate_kwargs(**overrides):
    """Return a complete gate op payload, merging _BASE with overrides."""
    kw = dict(_BASE)
    kw.update(overrides)
    return {"op": "gate", **kw}


# ---------------------------------------------------------------------------
# DONE – bar_met
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_done_bar_and_floors_met(tool):
    """best total >= bar AND every dim >= floor → DONE 'bar_met'."""
    best = {d: 3 for d in DIMS}   # total=24, every dim=3
    result = await tool.execute(gate_kwargs(
        best_scores=best, bar=24, floors=3, budget_remaining=5,
    ))
    assert result.success is True
    assert result.output["action"] == "DONE"
    assert result.output["reason"] == "bar_met"


@pytest.mark.asyncio
async def test_not_done_when_total_below_bar(tool):
    """Total < bar even if floors met → should NOT return bar_met."""
    best = {d: 2 for d in DIMS}   # total=16 < bar=24
    result = await tool.execute(gate_kwargs(
        best_scores=best, bar=24, floors=1,
    ))
    assert result.success is True
    assert not (result.output["action"] == "DONE" and result.output["reason"] == "bar_met")


@pytest.mark.asyncio
async def test_not_done_when_floor_not_met_despite_bar(tool):
    """total >= bar but a dim is still below floor, run is improving, budget remains.

    F2 behaviour: when total >= bar but one dim < floor AND the run is NOT
    plateaued AND budget remains, floor_breach must NOT escalate — the loop
    should keep climbing to lift the sub-floor dim.  Returns PLAN.
    """
    best = {d: 3 for d in DIMS}
    best["clarity"] = 2   # below floor=3; total = 7*3+2 = 23 >= bar=22
    result = await tool.execute(gate_kwargs(
        best_scores=best, bar=22, floors=3, budget_remaining=5,
    ))
    # total=23 >= bar=22, clarity=2 < floor=3, NOT plateaued (len=2 < k=3),
    # budget remaining → F2: keep climbing, do NOT escalate
    assert result.success is True
    assert result.output["action"] == "PLAN", (
        f"F2: expected PLAN but got action={result.output['action']!r}, "
        f"reason={result.output.get('reason')!r}"
    )


# ---------------------------------------------------------------------------
# DONE – budget_exhausted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_done_budget_zero(tool):
    """budget_remaining == 0 → DONE 'budget_exhausted'."""
    best = make_scores()   # total=16 < bar=24; rule 1 won't fire
    result = await tool.execute(gate_kwargs(best_scores=best, budget_remaining=0))
    assert result.success is True
    assert result.output["action"] == "DONE"
    assert result.output["reason"] == "budget_exhausted"


@pytest.mark.asyncio
async def test_done_budget_negative(tool):
    """budget_remaining < 0 → DONE 'budget_exhausted'."""
    best = make_scores()
    result = await tool.execute(gate_kwargs(best_scores=best, budget_remaining=-3))
    assert result.success is True
    assert result.output["action"] == "DONE"
    assert result.output["reason"] == "budget_exhausted"


# ---------------------------------------------------------------------------
# ESCALATE – floor_breach
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalate_floor_breach_uniform(tool):
    """Uniform floor=3, all dims=2 (below floor) → ESCALATE 'floor_breach'."""
    best = make_scores()   # all 2s, total=16 < bar=24
    result = await tool.execute(gate_kwargs(best_scores=best, floors=3))
    assert result.success is True
    assert result.output["action"] == "ESCALATE"
    assert result.output["reason"] == "floor_breach"


@pytest.mark.asyncio
async def test_escalate_floor_breach_per_dim(tool):
    """Per-dim floors dict: only one dim breaches floor → ESCALATE 'floor_breach'."""
    best = make_scores()   # all 2s
    per_dim = {d: 1 for d in DIMS}
    per_dim["clarity"] = 3   # clarity=2 < 3 → breach
    result = await tool.execute(gate_kwargs(
        best_scores=best, floors=per_dim, bar=100,
    ))
    assert result.success is True
    assert result.output["action"] == "ESCALATE"
    assert result.output["reason"] == "floor_breach"


# ---------------------------------------------------------------------------
# ESCALATE – plateau
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalate_plateau_exactly_k(tool):
    """Exactly k recent improvements all < epsilon → ESCALATE 'plateau'."""
    best = make_scores()   # floor=1 → no breach; total < bar
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=1,
        recent_improvements=[0.05, 0.02, 0.03],  # k=3 items, all < epsilon=0.1
        k=3,
        epsilon=0.1,
    ))
    assert result.success is True
    assert result.output["action"] == "ESCALATE"
    assert result.output["reason"] == "plateau"


@pytest.mark.asyncio
async def test_escalate_plateau_more_than_k(tool):
    """len > k but last k all < epsilon → ESCALATE 'plateau'."""
    best = make_scores()
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=1,
        recent_improvements=[1.0, 0.05, 0.02, 0.03],  # last 3 < 0.1
        k=3,
        epsilon=0.1,
    ))
    assert result.success is True
    assert result.output["action"] == "ESCALATE"
    assert result.output["reason"] == "plateau"


@pytest.mark.asyncio
async def test_no_plateau_when_fewer_than_k(tool):
    """len(recent_improvements) < k → plateau rule does NOT fire → falls to PLAN."""
    best = make_scores()
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=1,
        recent_improvements=[0.05, 0.05],   # only 2 samples < k=3
        k=3,
        epsilon=0.1,
        last_decision="NEW_BEST",
    ))
    assert result.success is True
    assert result.output["action"] == "PLAN"


@pytest.mark.asyncio
async def test_no_plateau_when_one_improvement_above_epsilon(tool):
    """Last k has one item >= epsilon → plateau does NOT fire."""
    best = make_scores()
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=1,
        recent_improvements=[0.05, 0.5, 0.05],  # 0.5 >= epsilon=0.1
        k=3,
        epsilon=0.1,
        last_decision="NEW_BEST",
    ))
    assert result.success is True
    assert result.output["action"] == "PLAN"


# ---------------------------------------------------------------------------
# ROLLBACK / ESCALATE – regression handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rollback_regression_not_retried(tool):
    """last_decision == 'REGRESSION', target_retried=False → ROLLBACK 'regression_retry'."""
    best = make_scores()
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=1,
        last_decision="REGRESSION",
        target_retried=False,
    ))
    assert result.success is True
    assert result.output["action"] == "ROLLBACK"
    assert result.output["reason"] == "regression_retry"


@pytest.mark.asyncio
async def test_escalate_regression_stuck(tool):
    """last_decision == 'REGRESSION', target_retried=True → ESCALATE 'regression_stuck'."""
    best = make_scores()
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=1,
        last_decision="REGRESSION",
        target_retried=True,
    ))
    assert result.success is True
    assert result.output["action"] == "ESCALATE"
    assert result.output["reason"] == "regression_stuck"


# ---------------------------------------------------------------------------
# PLAN – default
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_is_default(tool):
    """No stopping rule fires → PLAN 'continue'."""
    best = make_scores()   # total=16 < bar=24, all dims=2 >= floor=1
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=1,
        recent_improvements=[1.0, 1.0, 1.0],  # all above epsilon → no plateau
        last_decision="NEW_BEST",
        target_retried=False,
    ))
    assert result.success is True
    assert result.output["action"] == "PLAN"
    assert result.output["reason"] == "continue"


@pytest.mark.asyncio
async def test_plan_when_best_is_none(tool):
    """best_scores=None with budget remaining → should PLAN (no bar/floor checks)."""
    result = await tool.execute(gate_kwargs(
        best_scores=None,
        floors=1,
        recent_improvements=[1.0],
        k=3,
        last_decision="NEW_BEST",
    ))
    assert result.success is True
    assert result.output["action"] == "PLAN"


# ---------------------------------------------------------------------------
# Priority ordering (rules must fire in order)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_budget_exhausted_beats_floor_breach(tool):
    """Rule 2 (budget) fires before rule 3 (floor_breach) — budget_remaining=0."""
    best = make_scores()   # floor=3 would breach, but budget=0 fires first
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=3,
        budget_remaining=0,
    ))
    assert result.success is True
    assert result.output["action"] == "DONE"
    assert result.output["reason"] == "budget_exhausted"


@pytest.mark.asyncio
async def test_floor_breach_beats_plateau(tool):
    """Rule 3 (floor_breach) fires before rule 4 (plateau)."""
    best = make_scores()
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=3,                              # breach: dims=2 < floor=3
        recent_improvements=[0.01, 0.01, 0.01],  # plateau would fire too
        k=3,
        epsilon=0.1,
    ))
    assert result.success is True
    assert result.output["action"] == "ESCALATE"
    assert result.output["reason"] == "floor_breach"  # floor breach, not plateau


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_missing_required_field(tool):
    """gate op with missing required field → success=False."""
    result = await tool.execute({"op": "gate"})  # missing everything
    assert result.success is False
    assert result.error is not None


# ---------------------------------------------------------------------------
# champion_is_baseline guard (floor_breach suppression)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_floor_breach_not_escalated_while_champion_is_baseline(tool):
    """floor breach + budget remaining + champion_is_baseline=True
    -> loop has NOT yet scored a real candidate; must NOT escalate.
    The gate should return the normal continue action (PLAN), not ESCALATE floor_breach.
    """
    best = make_scores()  # all 2s — below floor=3, total=16 < bar=24
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=3,           # every dim breaches floor (2 < 3)
        budget_remaining=5,
        champion_is_baseline=True,
    ))
    assert result.success is True
    # floor_breach must NOT fire while the champion is still the pass-0 baseline
    assert not (
        result.output["action"] == "ESCALATE"
        and result.output["reason"] == "floor_breach"
    ), (
        f"floor_breach fired on a baseline champion (action={result.output['action']!r}, "
        f"reason={result.output.get('reason')!r}); expected PLAN/continue"
    )
    # The gate has budget left and no other rule fires, so it should PLAN
    assert result.output["action"] == "PLAN"


@pytest.mark.asyncio
async def test_floor_breach_escalates_when_scored_champion_below_floor(tool):
    """floor breach + budget remaining + champion_is_baseline=False
    -> a real scored pass has become champion and it is still below floor.
    Must ESCALATE floor_breach (we genuinely tried and are stuck).
    """
    best = make_scores()  # all 2s — below floor=3
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        floors=3,
        budget_remaining=5,
        champion_is_baseline=False,
    ))
    assert result.success is True
    assert result.output["action"] == "ESCALATE"
    assert result.output["reason"] == "floor_breach"


# ---------------------------------------------------------------------------
# F2: floor_breach ordering — keep climbing vs escalate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f2_floor_breach_plan_when_total_meets_bar_and_improving(tool):
    """F2 Case 1: total >= bar, one dim < floor, budget remaining, NOT plateaued,
    champion_is_baseline=False  →  PLAN (keep lifting the stuck dim), NOT ESCALATE.

    The run has already hit the bar in total but one dimension is still sub-floor.
    While budget remains and the run is still improving (not plateaued), floor_breach
    should NOT escalate — it should spend the remaining budget trying to lift the dim.
    """
    best = {d: 3 for d in DIMS}
    best["clarity"] = 2          # clarity=2 < floor=3; total = 7*3+2 = 23 >= bar=22
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        bar=22,                  # total=23 meets bar
        floors=3,                # floor breach on clarity
        budget_remaining=5,
        recent_improvements=[0.5, 0.5],  # len=2 < k=3 → NOT plateaued
        k=3,
        epsilon=0.1,
        champion_is_baseline=False,
        last_decision="NEW_BEST",
        target_retried=False,
    ))
    assert result.success is True
    assert result.output["action"] == "PLAN", (
        f"F2: expected PLAN (keep climbing) but got "
        f"action={result.output['action']!r}, reason={result.output.get('reason')!r}. "
        f"When total>=bar but one dim is sub-floor and the run is still improving, "
        f"floor_breach must NOT escalate — use remaining budget to lift the dim."
    )


@pytest.mark.asyncio
async def test_f2_floor_breach_escalates_when_total_meets_bar_and_plateaued(tool):
    """F2 Case 2: total >= bar, one dim < floor, AND plateaued  →  ESCALATE floor_breach.

    Once the run has plateaued (k consecutive flat improvements), spending more budget
    will not lift the sub-floor dim.  Escalation is appropriate.
    """
    best = {d: 3 for d in DIMS}
    best["clarity"] = 2          # total=23 >= bar=22, clarity=2 < floor=3
    result = await tool.execute(gate_kwargs(
        best_scores=best,
        bar=22,
        floors=3,
        budget_remaining=5,
        recent_improvements=[0.01, 0.01, 0.01],  # all < epsilon → plateaued
        k=3,
        epsilon=0.1,
        champion_is_baseline=False,
        last_decision="NEW_BEST",
        target_retried=False,
    ))
    assert result.success is True
    assert result.output["action"] == "ESCALATE", (
        f"F2: expected ESCALATE floor_breach but got "
        f"action={result.output['action']!r}, reason={result.output.get('reason')!r}. "
        f"When total>=bar, floor breach persists, AND the run is plateaued, escalation is correct."
    )
    assert result.output["reason"] == "floor_breach", (
        f"reason should be 'floor_breach', got {result.output.get('reason')!r}"
    )
