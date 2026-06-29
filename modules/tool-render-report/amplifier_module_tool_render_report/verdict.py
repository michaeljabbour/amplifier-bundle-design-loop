"""Deterministic verdict parsing for design review reports.

Validates that an LLM-produced verdict has exactly the 8 CRITERIA scores,
each an int in 0..4. Recomputes total from scores (never trusts supplied total).
Strips JSON fences before parsing strings.
"""

from __future__ import annotations

import json
import re
from typing import Any

# The 8 canonical criteria for design quality scores.
CRITERIA: tuple[str, ...] = (
    "clarity",
    "elegance",
    "restraint",
    "empowerment",
    "agency",
    "ease",
    "character",
    "point",
)

# Regex to strip ```json ... ``` or ``` ... ``` fences (DOTALL).
_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _coerce_to_dict(obj: Any) -> dict | None:
    """Return *obj* as a dict, or None if it cannot be coerced.

    - dict   → returned as-is
    - str    → JSON-fence stripped, then json.loads; must produce dict
    - other  → None
    """
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        stripped = obj.strip()
        m = _FENCE.match(stripped)
        if m:
            stripped = m.group(1).strip()
        try:
            parsed = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            return None
        if isinstance(parsed, dict):
            return parsed
        return None
    return None


def parse_verdict(obj: Any) -> dict:
    """Parse and validate a verdict object from an LLM response.

    Returns one of two shapes:

    Success::

        {
            "valid": True,
            "verdict": {
                "scores": {"clarity": 3, ...},   # exactly CRITERIA keys, ints 0..4
                "total": int,                    # recomputed from scores
                "fixes": list,                   # defaulted to [] if not a list
            },
        }

    Failure::

        {
            "valid": False,
            "scores_unavailable": True,
            "raw": str(obj),
        }
    """
    _fail = {
        "valid": False,
        "scores_unavailable": True,
        "raw": str(obj),
    }

    data = _coerce_to_dict(obj)
    if data is None:
        return _fail

    # Validate scores section
    raw_scores = data.get("scores")
    if not isinstance(raw_scores, dict):
        return _fail

    # Ensure exactly the 8 required criteria are present with valid values.
    clean: dict[str, int] = {}
    for criterion in CRITERIA:
        value = raw_scores.get(criterion)
        # Must be int, not bool (bool is a subclass of int in Python).
        if not isinstance(value, int) or isinstance(value, bool):
            return _fail
        if not (0 <= value <= 4):
            return _fail
        clean[criterion] = value

    # Any extra keys are silently ignored (we only surface CRITERIA).

    # Fixes: default to [] if missing or wrong type.
    fixes = data.get("fixes")
    if not isinstance(fixes, list):
        fixes = []

    return {
        "valid": True,
        "verdict": {
            "scores": clean,
            "total": sum(clean.values()),
            "fixes": fixes,
        },
    }
