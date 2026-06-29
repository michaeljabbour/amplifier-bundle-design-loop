"""Amplifier tool module: deterministic MACA decision core for the design harness.

This module is the stopping-rule and accept/reject engine used by the design
loop recipe.  It is intentionally stateless and dependency-free (stdlib only):
all decision functions are pure and synchronous; execute() is async only to
satisfy the Tool protocol.

Two operations are exposed via the single ``design_controller`` tool:

op="evaluate"
    MACA (Min-not-mean Accept/Reject) accept/reject decision.
    Compares a candidate design's 8-dim scores against the current best and
    returns one of: NEW_BEST | NO_GAIN | REGRESSION | INVALID.

op="gate"
    Stopping-rule gate.  Given budget, plateau, floor, and regression state,
    returns one of: DONE | ESCALATE | PLAN | ROLLBACK.
"""
from __future__ import annotations

import logging
from typing import Any

from amplifier_core import ModuleCoordinator, ToolResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIMS: list[str] = [
    "clarity",
    "elegance",
    "restraint",
    "empowerment",
    "agency",
    "ease",
    "character",
    "point",
]

_EVALUATE_DECISIONS = frozenset({"NEW_BEST", "NO_GAIN", "REGRESSION", "INVALID"})
_GATE_ACTIONS = frozenset({"DONE", "ESCALATE", "PLAN", "ROLLBACK"})


# ---------------------------------------------------------------------------
# Pure decision functions
# ---------------------------------------------------------------------------


def _evaluate(
    candidate_scores: dict[str, int],
    candidate_hard_fail: bool,
    best_scores: dict[str, int] | None,
    no_regress_dims: list[str] | None = None,
    tau: int = 0,
) -> dict[str, Any]:
    """MACA accept/reject: compare candidate against best using minmax ordering.

    Decision rules applied in order:
      1. INVALID  — hard lint fail
      2. REGRESSION — any protected dim dropped below best[dim] - tau
      3. NEW_BEST — best is None, OR worst(cand) > worst(best),
                    OR worst equal AND total(cand) > total(best)
      4. NO_GAIN  — everything else

    Parameters
    ----------
    candidate_scores:
        8-dim dict mapping dim name → score (0–4 int).
    candidate_hard_fail:
        Output of the lint gate; True forces INVALID regardless of scores.
    best_scores:
        Current champion scores, or None if no best exists yet.
    no_regress_dims:
        Dim names that must not regress below best[dim] - tau.
        Defaults to all 8 dims.
    tau:
        Tolerance: regression fires only if candidate < best - tau (strict <).

    Returns
    -------
    dict with keys: decision, worst_dim, worst, total, regression_flags
    """
    if no_regress_dims is None:
        no_regress_dims = DIMS[:]

    # Candidate statistics
    worst_dim: str = min(candidate_scores, key=lambda d: candidate_scores[d])
    worst: int = candidate_scores[worst_dim]
    total: int = sum(candidate_scores.values())

    # Rule 1: hard fail → INVALID
    if candidate_hard_fail:
        return {
            "decision": "INVALID",
            "worst_dim": worst_dim,
            "worst": worst,
            "total": total,
            "regression_flags": [],
        }

    # Rule 2: regression check (fires BEFORE NEW_BEST — the anti-gaming guarantee)
    if best_scores is not None:
        regression_flags = [
            dim
            for dim in no_regress_dims
            if candidate_scores.get(dim, 0) < best_scores.get(dim, 0) - tau
        ]
        if regression_flags:
            return {
                "decision": "REGRESSION",
                "worst_dim": worst_dim,
                "worst": worst,
                "total": total,
                "regression_flags": regression_flags,
            }

    # Rule 3: new best
    if best_scores is None:
        return {
            "decision": "NEW_BEST",
            "worst_dim": worst_dim,
            "worst": worst,
            "total": total,
            "regression_flags": [],
        }

    best_worst: int = min(best_scores.values())
    best_total: int = sum(best_scores.values())

    if worst > best_worst or (worst == best_worst and total > best_total):
        return {
            "decision": "NEW_BEST",
            "worst_dim": worst_dim,
            "worst": worst,
            "total": total,
            "regression_flags": [],
        }

    # Rule 4: no gain
    return {
        "decision": "NO_GAIN",
        "worst_dim": worst_dim,
        "worst": worst,
        "total": total,
        "regression_flags": [],
    }


def _gate(
    best_scores: dict[str, int] | None,
    bar: int,
    floors: int | dict[str, int],
    budget_remaining: int,
    recent_improvements: list[float],
    k: int,
    epsilon: float,
    last_decision: str,
    target_retried: bool,
) -> dict[str, str]:
    """Stopping-rule gate: decide what the recipe loop should do next.

    Rules applied in order:
      1. DONE      — total >= bar AND every dim >= floor         (bar_met)
      2. DONE      — budget_remaining <= 0                       (budget_exhausted)
      3. ESCALATE  — best exists AND some dim < floor            (floor_breach)
      4. ESCALATE  — last k improvements all < epsilon           (plateau)
      5. ROLLBACK  — last_decision == REGRESSION, not retried    (regression_retry)
         ESCALATE  — last_decision == REGRESSION, already retried (regression_stuck)
      6. PLAN      — none of the above                          (continue)

    Parameters
    ----------
    best_scores:
        Current champion scores or None.
    bar:
        Target total score threshold.
    floors:
        Per-dim minimum.  An int applies to every dim uniformly;
        a dict specifies per-dim overrides.
    budget_remaining:
        Number of design passes left.
    recent_improvements:
        Per-pass improvement in worst-dim over the most recent passes.
    k:
        Window size for plateau detection.
    epsilon:
        Improvement threshold below which a pass counts as "flat".
    last_decision:
        Most recent evaluate() decision string.
    target_retried:
        Whether a rollback has already been attempted for the current regression.

    Returns
    -------
    dict with keys: action, reason
    """
    # Normalize floors to per-dim dict
    if isinstance(floors, (int, float)):
        floor_dict: dict[str, int] = {d: int(floors) for d in DIMS}
    else:
        floor_dict = {d: int(floors.get(d, 0)) for d in DIMS}

    # Rule 1: bar met (total >= bar AND every dim >= its floor)
    if best_scores is not None:
        total = sum(best_scores.values())
        floors_met = all(
            best_scores.get(dim, 0) >= floor_dict.get(dim, 0) for dim in DIMS
        )
        if total >= bar and floors_met:
            return {"action": "DONE", "reason": "bar_met"}

    # Rule 2: budget exhausted
    if budget_remaining <= 0:
        return {"action": "DONE", "reason": "budget_exhausted"}

    # Rule 3: floor breach
    if best_scores is not None:
        breach = any(
            best_scores.get(dim, 0) < floor_dict.get(dim, 0) for dim in DIMS
        )
        if breach:
            return {"action": "ESCALATE", "reason": "floor_breach"}

    # Rule 4: plateau (last k improvements all below epsilon)
    if k > 0 and len(recent_improvements) >= k:
        last_k = recent_improvements[-k:]
        if all(imp < epsilon for imp in last_k):
            return {"action": "ESCALATE", "reason": "plateau"}

    # Rule 5: regression handling
    if last_decision == "REGRESSION":
        if target_retried:
            return {"action": "ESCALATE", "reason": "regression_stuck"}
        return {"action": "ROLLBACK", "reason": "regression_retry"}

    # Rule 6: default — keep going
    return {"action": "PLAN", "reason": "continue"}


# ---------------------------------------------------------------------------
# Tool class
# ---------------------------------------------------------------------------


class DesignControllerTool:
    """Deterministic decision core for the design harness.

    Exposes two operations via the ``op`` input field:

    * ``evaluate`` — MACA accept/reject (pure comparison, no LLM).
    * ``gate``     — Stopping-rule gate (budget / plateau / floor / regression).

    The tool holds NO state; callers supply all context on each invocation.
    Never raises: bad input always surfaces as ``ToolResult(success=False)``.
    """

    @property
    def name(self) -> str:
        return "design_controller"

    @property
    def description(self) -> str:
        return (
            "Deterministic MACA accept/reject and stopping-rule gate for the design harness. "
            "Stdlib only — no LLM, no I/O, no external deps. Stateless: call it once per "
            "design pass and act on the returned decision. "
            "\n\nop='evaluate': compare candidate_scores (8-dim int dict) against best_scores "
            "(8-dim dict or null). Returns decision ∈ {NEW_BEST, NO_GAIN, REGRESSION, INVALID} "
            "plus worst_dim, worst, total, regression_flags. "
            "Inputs: candidate_scores, candidate_hard_fail, best_scores, "
            "optional no_regress_dims (default=all 8), optional tau (default=0). "
            "\n\nop='gate': evaluate stopping rules. Returns action ∈ {DONE, ESCALATE, PLAN, "
            "ROLLBACK} plus reason. "
            "Inputs: best_scores, bar, floors (int or per-dim dict), budget_remaining, "
            "recent_improvements (list), k, epsilon, last_decision, target_retried."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["op"],
            "properties": {
                "op": {
                    "type": "string",
                    "enum": ["evaluate", "gate"],
                    "description": "Operation to perform: 'evaluate' (MACA) or 'gate' (stopping rules).",
                },
                # --- evaluate operands ---
                "candidate_scores": {
                    "type": "object",
                    "description": (
                        "8-dim score dict for the candidate design. "
                        "Keys: clarity, elegance, restraint, empowerment, agency, ease, character, point. "
                        "Values: int 0–4."
                    ),
                    "properties": {d: {"type": "integer", "minimum": 0, "maximum": 4} for d in DIMS},
                },
                "candidate_hard_fail": {
                    "type": "boolean",
                    "description": "Output of the lint gate; True forces INVALID decision.",
                },
                "best_scores": {
                    "description": "Current champion 8-dim score dict, or null if no best yet.",
                },
                "no_regress_dims": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Dim names protected against regression. Defaults to all 8.",
                },
                "tau": {
                    "type": "integer",
                    "default": 0,
                    "description": "Regression tolerance: fires only if candidate < best - tau.",
                },
                # --- gate operands ---
                "bar": {
                    "type": "integer",
                    "description": "Target total score threshold for DONE 'bar_met'.",
                },
                "floors": {
                    "description": (
                        "Per-dim minimum score. An int applies uniformly to all dims; "
                        "a dict specifies per-dim values."
                    ),
                },
                "budget_remaining": {
                    "type": "integer",
                    "description": "Remaining design passes. 0 or negative → budget_exhausted.",
                },
                "recent_improvements": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Per-pass worst-dim improvement over recent passes (plateau window).",
                },
                "k": {
                    "type": "integer",
                    "description": "Plateau detection window: look at the last k improvements.",
                },
                "epsilon": {
                    "type": "number",
                    "description": "Improvement threshold; < epsilon counts as a flat pass.",
                },
                "last_decision": {
                    "type": "string",
                    "description": "Most recent evaluate() decision (NEW_BEST / NO_GAIN / REGRESSION / INVALID).",
                },
                "target_retried": {
                    "type": "boolean",
                    "description": "True if a rollback for the current regression was already attempted.",
                },
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:  # noqa: A002
        """Dispatch to evaluate or gate based on 'op' field.

        Always returns a ToolResult; never raises.

        Parameters
        ----------
        input:
            Dict with 'op' plus operation-specific fields (see input_schema).

        Returns
        -------
        ToolResult
            success=True with output dict on valid input.
            success=False with error dict on invalid/missing input.
        """
        try:
            op = input.get("op")
            if op == "evaluate":
                return self._run_evaluate(input)
            elif op == "gate":
                return self._run_gate(input)
            elif op is None:
                return ToolResult(
                    success=False,
                    error={"message": "Missing required field: 'op'", "field": "op"},
                )
            else:
                return ToolResult(
                    success=False,
                    error={
                        "message": f"Unknown op '{op}'. Must be one of: evaluate, gate.",
                        "field": "op",
                        "received": op,
                    },
                )
        except Exception as exc:
            logger.exception("DesignControllerTool.execute: unexpected exception")
            return ToolResult(
                success=False,
                error={"message": f"Unexpected error: {exc}", "type": type(exc).__name__},
            )

    # ------------------------------------------------------------------
    # Internal dispatch helpers
    # ------------------------------------------------------------------

    def _run_evaluate(self, input: dict[str, Any]) -> ToolResult:  # noqa: A002
        """Validate inputs and invoke _evaluate()."""
        # Required fields
        if "candidate_scores" not in input:
            return ToolResult(
                success=False,
                error={"message": "evaluate: missing required field 'candidate_scores'"},
            )
        if "candidate_hard_fail" not in input:
            return ToolResult(
                success=False,
                error={"message": "evaluate: missing required field 'candidate_hard_fail'"},
            )

        candidate_scores: dict[str, int] = dict(input["candidate_scores"])
        candidate_hard_fail: bool = bool(input["candidate_hard_fail"])
        best_scores_raw = input.get("best_scores")
        best_scores: dict[str, int] | None = (
            dict(best_scores_raw) if best_scores_raw is not None else None
        )
        no_regress_dims = input.get("no_regress_dims", None)
        tau: int = int(input.get("tau", 0))

        result = _evaluate(
            candidate_scores=candidate_scores,
            candidate_hard_fail=candidate_hard_fail,
            best_scores=best_scores,
            no_regress_dims=no_regress_dims,
            tau=tau,
        )
        return ToolResult(success=True, output=result)

    def _run_gate(self, input: dict[str, Any]) -> ToolResult:  # noqa: A002
        """Validate inputs and invoke _gate()."""
        required = ["bar", "floors", "budget_remaining", "recent_improvements",
                    "k", "epsilon", "last_decision", "target_retried"]
        missing = [f for f in required if f not in input]
        if missing:
            return ToolResult(
                success=False,
                error={
                    "message": f"gate: missing required fields: {missing}",
                    "missing_fields": missing,
                },
            )

        best_scores_raw = input.get("best_scores")
        best_scores: dict[str, int] | None = (
            dict(best_scores_raw) if best_scores_raw is not None else None
        )

        result = _gate(
            best_scores=best_scores,
            bar=int(input["bar"]),
            floors=input["floors"],
            budget_remaining=int(input["budget_remaining"]),
            recent_improvements=list(input["recent_improvements"]),
            k=int(input["k"]),
            epsilon=float(input["epsilon"]),
            last_decision=str(input["last_decision"]),
            target_retried=bool(input["target_retried"]),
        )
        return ToolResult(success=True, output=result)


# ---------------------------------------------------------------------------
# Mount function (Iron Law: call coordinator.mount, return tool)
# ---------------------------------------------------------------------------


async def mount(
    coordinator: ModuleCoordinator,
    config: dict[str, Any] | None = None,
) -> DesignControllerTool:
    """Mount the design_controller tool into the session.

    Iron Law: calls ``coordinator.mount("tools", tool, name=tool.name)``
    and returns the tool instance.
    """
    tool = DesignControllerTool()
    await coordinator.mount("tools", tool, name=tool.name)
    logger.info("Mounted tool-design-controller")
    return tool
