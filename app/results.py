"""Turn a loop-run `state` into the payload the Results screen actually needs.

The old Results pane led with a score. A paying user (see
docs/persona-and-user-stories.md) leads with the FIX: the top few problems with
their page, ranked by impact, each paired with a specific change. This module
derives that punch list -- plus a compact A->B scorecard, what-changed, and a
ship/no-ship call -- from the same `state` dict both the dry and real runners
already produce. It reuses the render-report module's dimension vocabulary so
labels/order match the full report exactly.
"""

from __future__ import annotations

from typing import Any

from amplifier_module_tool_render_report import template as t
from amplifier_module_tool_render_report.template import SHIP_BAR, ship_verdict

# Ordered dimension ids + human labels, straight from the report module so the
# punch list and the full report never disagree.
_ORDER: list[str] = [d["id"] for d in t.PW_DIMS]
_LABEL: dict[str, str] = {d["id"]: d["label"] for d in t.PW_DIMS}

# The bar a candidate must clear to "ship" -- imported from the report
# renderer (SHIP_BAR) so the app and the report can never disagree.

# Fallback issue/fix per dimension, in a smart-friend voice, used when a run's
# own fix_batch doesn't already carry a line for a weak dimension. Keeps the
# punch list specific even on edge cases / escalated runs.
_DIM_FIX: dict[str, tuple[str, str]] = {
    "clarity": (
        "A visitor can't tell what to do at a glance.",
        "Lead with one plain headline and one primary action; remove competing CTAs.",
    ),
    "elegance": (
        "It reads as merely functional, not refined.",
        "Fix the type scale and spacing rhythm; strip decorative noise (gradients, emoji bullets).",
    ),
    "restraint": (
        "Too many equal-weight elements fight for attention.",
        "Cut anything not earning its place. Fewer, truer claims beat three padded cards.",
    ),
    "empowerment": (
        "Users leave with a pitch, not something usable.",
        "Give one concrete next step or takeaway they can act on immediately.",
    ),
    "agency": (
        "Users can only scroll, not decide.",
        "Add a real choice or entry point -- a path they pick, not just a wall of copy.",
    ),
    "ease": (
        "It's heavy on the mind -- too much at once.",
        "One idea per section. Shorten the copy and simplify the layout.",
    ),
    "character": (
        "It looks like a templated default with no point of view.",
        "Commit to a specific voice and visual stance instead of generic SaaS.",
    ),
    "point": (
        "It's not obvious why any of this matters.",
        "State the stakes plainly: what the reader gains, or loses by not acting.",
    ),
}


# Rough fix-effort per dimension (a senior lead ranks by impact x effort, not
# just severity). "low" = a copy/layout trim; "high" = needs real design work.
_EFFORT: dict[str, str] = {
    "clarity": "medium",
    "elegance": "high",
    "restraint": "low",
    "empowerment": "medium",
    "agency": "medium",
    "ease": "low",
    "character": "high",
    "point": "low",
}

# One-line "what's already working" note per dimension, used when a dimension
# scores competent+ on the baseline.
_STRENGTH_NOTE: dict[str, str] = {
    "clarity": "the purpose reads at a glance",
    "elegance": "the visual language feels considered",
    "restraint": "it resists the obvious slop defaults",
    "empowerment": "users are given something they can act on",
    "agency": "the affordances are legible",
    "ease": "the primary path is low-effort to follow",
    "character": "it has a recognisable point of view",
    "point": "it knows what it's for",
}

# The "through-line" a lead would name when a given dimension is the weakest.
_ROOT_CAUSE: dict[str, str] = {
    "clarity": "there's no clear focal point or hierarchy, so everything competes at once",
    "elegance": "the page leans on defaults instead of a deliberate type-and-spacing system",
    "restraint": "too much is on the page -- slop defaults (gradients, equal card grids) instead of a few true claims",
    "empowerment": "it pitches at the user instead of handing them something usable",
    "agency": "there's no obvious thing to do -- the user can only scroll",
    "ease": "the cognitive load is high; the primary path isn't obvious",
    "character": "it reads as a templated default with no distinct voice",
    "point": "it never makes the stakes clear -- why any of this matters",
}

_EFFORT_RANK = {"low": 0, "medium": 1, "high": 2}

# Objective audit fails -> first-class punch-list problems. A senior lead leads
# with "your text is unreadable (1.9:1)" over subjective taste, because it's
# factual. `blocker=True` means a page shouldn't ship until it's fixed, no
# matter how high the design score is. `dim` maps the finding to the closest of
# the 8 critic dimensions for continuity with the scorecard.
_AUDIT_PROBLEM = {
    #  id          label                  fix                                                                 impact   effort  blocker  dim
    "contrast":  ("Color contrast",     "Raise text/background contrast to at least 4.5:1 (WCAG AA).",        "high",  "low",  True,   "ease"),
    "overflow":  ("Horizontal overflow", "Constrain content to the viewport width -- no sideways scroll.",     "high",  "low",  True,   "ease"),
    "viewport":  ("Mobile viewport",    "Add <meta name=viewport content=\"width=device-width, initial-scale=1\">.", "high", "low", True, "clarity"),
    "renders":   ("Renders cleanly",    "Fix the markup/JS errors preventing a clean render.",               "high",  "low",  True,   "clarity"),
    "alt":       ("Image alt text",     "Add descriptive alt text to every meaningful image.",               "medium","low",  False,  "empowerment"),
    "headings":  ("Heading structure",  "Use a single h1 and don't skip heading levels.",                    "medium","low",  False,  "clarity"),
    "labels":    ("Form labels",        "Associate a <label> with every input.",                             "medium","low",  False,  "agency"),
}


def _audit_problems(audit: dict | None) -> tuple[list[dict], int]:
    """Turn objective audit FAILs into punch-list problems + count blockers."""
    if not audit or not audit.get("available"):
        return [], 0
    probs: list[dict] = []
    blockers = 0
    for f in audit.get("findings", []):
        if f.get("status") != "fail":
            continue
        spec = _AUDIT_PROBLEM.get(f.get("id"))
        if not spec:
            continue
        label, fix, impact, effort, blocker, dim = spec
        if blocker:
            blockers += 1
        probs.append(
            {
                "criterion": dim,
                "label": label,
                "a": 0,
                "b": 0,
                "issue": f.get("detail", ""),
                "fix": fix,
                "severity": "critical" if blocker else "high",
                "impact": impact,
                "effort": effort,
                "source": "ground-truth",
                "blocker": blocker,
            }
        )
    return probs, blockers


def _flat(scores: Any) -> dict[str, int]:
    """Normalise possibly-nested scores to a flat {dim: int}."""
    if not isinstance(scores, dict):
        return {}
    if "clarity" not in scores and isinstance(scores.get("scores"), dict):
        scores = scores["scores"]
    return {k: v for k, v in scores.items() if isinstance(v, int)}


def _severity(a: int) -> str:
    if a <= 0:
        return "critical"
    if a == 1:
        return "high"
    return "medium"


def build_result_payload(
    state: dict, context: str = "", audience: str = "", audit: dict | None = None
) -> dict[str, Any]:
    """Derive the Results payload (punch list, verdict, strengths, root cause)
    from `state`, folding in the objective ground-truth `audit` when present.

    Safe on partial/empty state -- every field has a sensible default so the
    Results screen always has something actionable to show, including on an
    escalated run.
    """
    records = state.get("records") or []
    champion = state.get("champion") or {}
    gate = state.get("gate") or {}
    converged = bool(state.get("converged", False))

    a_rec = records[0] if records else {}
    a_scores = _flat(a_rec.get("scores"))
    b_scores = _flat(champion.get("scores"))

    # Prefer a run's own words: first fix_batch line seen per criterion wins.
    fix_lookup: dict[str, tuple[str, str]] = {}
    for rec in records:
        for fb in rec.get("fix_batch") or []:
            crit = fb.get("criterion")
            if crit and crit not in fix_lookup:
                fix_lookup[crit] = (fb.get("issue", ""), fb.get("fix", ""))

    scores = []
    for c in _ORDER:
        a = int(a_scores.get(c, 0))
        b = int(b_scores.get(c, 0))
        scores.append({"id": c, "label": _LABEL[c], "a": a, "b": b, "delta": b - a})

    # The weakest three dimensions are the candidate problems...
    weakest = sorted(_ORDER, key=lambda c: (a_scores.get(c, 0), _ORDER.index(c)))[:3]
    problems = []
    for c in weakest:
        a = int(a_scores.get(c, 0))
        issue, fix = fix_lookup.get(c) or _DIM_FIX[c]
        impact = "high" if a <= 1 else "medium"
        effort = _EFFORT.get(c, "medium")
        problems.append(
            {
                "criterion": c,
                "label": _LABEL[c],
                "a": a,
                "b": int(b_scores.get(c, 0)),
                "issue": issue,
                "fix": fix,
                "severity": _severity(a),
                "impact": impact,
                "effort": effort,
            }
        )
    # Fold in OBJECTIVE audit fails as first-class problems. They lead the list:
    # a factual "text is unreadable at 1.9:1" outranks subjective taste.
    audit_probs, blockers = _audit_problems(audit)
    # Drop subjective problems that duplicate a dimension an audit problem
    # already covers, so the list stays tight.
    covered = {ap["criterion"] for ap in audit_probs}
    problems = [p for p in problems if p["criterion"] not in covered]

    # ...order by impact x effort (do the high-impact, low-effort fix first),
    # not merely by how bad the score is. Objective/blocker items sort ahead.
    def _rank(p: dict) -> tuple:
        return (
            0 if p.get("source") == "ground-truth" else 1,
            0 if p.get("blocker") else 1,
            0 if p["impact"] == "high" else 1,
            _EFFORT_RANK.get(p["effort"], 1),
            p["a"],
        )

    problems = sorted(audit_probs + problems, key=_rank)[:4]
    for i, p in enumerate(problems):
        p["first"] = i == 0

    improved = [_LABEL[c] for c in _ORDER if b_scores.get(c, 0) > a_scores.get(c, 0)]
    regressed = [_LABEL[c] for c in _ORDER if b_scores.get(c, 0) < a_scores.get(c, 0)]

    # What's already working: the input's strongest competent+ dimensions.
    strongest = sorted(_ORDER, key=lambda c: (-a_scores.get(c, 0), _ORDER.index(c)))
    strengths = [
        {"label": _LABEL[c], "a": int(a_scores.get(c, 0)), "note": _STRENGTH_NOTE[c]}
        for c in strongest
        if a_scores.get(c, 0) >= 2
    ][:2]
    # A lead still says something honest when nothing clears "competent".
    strengths_note = (
        "" if strengths else "Nothing clears 'competent' yet — which means every fix below is pure upside."
    )

    # Root cause: the through-line a lead would name -- anchored on the single
    # weakest dimension, tying the rest together.
    worst = weakest[0] if weakest else None
    root_cause = _ROOT_CAUSE.get(worst, "") if worst else ""

    total = champion.get("total")
    if total is None:
        total = sum(s["b"] for s in scores)
    total = int(total)

    # A senior lead won't sign off on a page with blocking accessibility fails,
    # no matter how high the taste score is. Blockers veto "ship". ship_label
    # comes from the SAME canonical function the report renderer uses, so this
    # payload and the embedded report can never show two different verdicts
    # for the same run.
    ship_label = ship_verdict(total, converged=converged, blockers=blockers, bar=SHIP_BAR)
    ship = ship_label == "Ready to ship"
    if blockers > 0:
        blocker_note = (
            f"{blockers} blocking ground-truth issue"
            + ("s" if blockers != 1 else "")
            + " must be fixed before this ships, regardless of the design score."
        )
    else:
        blocker_note = ""

    goal_note = ""
    if context and problems:
        goal_note = (
            f'For a {context.strip()}, the highest-impact fix is {problems[0]["label"].lower()}.'
        )

    return {
        "problems": problems,
        "scores": scores,
        "improved": improved,
        "regressed": regressed,
        "strengths": strengths,
        "strengths_note": strengths_note,
        "root_cause": root_cause,
        "total": total,
        "bar": _BAR,
        "ship": ship,
        "ship_label": ship_label,
        "blockers": blockers,
        "blocker_note": blocker_note,
        "context": context or "",
        "audience": audience or "",
        "goal_note": goal_note,
        "reason": gate.get("reason", "") or "",
        "ground_truth": audit or {"available": False, "findings": [], "summary": {}, "note": ""},
    }
