#!/usr/bin/env python3
"""Regenerate the Pulseboard before/after DEMO report from fixtures/demo/.

This is the renderer's "sample/demo wiring": a synthetic-but-realistic
multi-pass `state` dict (matching the real ledger record shape produced by
recipes/dlx.py) whose pass-0 baseline artifact is fixtures/demo/slop.html and
whose champion artifact is fixtures/demo/upgraded.html. It exercises the full
LANDING -> WORKING -> RESULTS journey end to end and writes:

  - <durable_base>/runs/<run_id>/{baseline,upgraded,report}.html
  - <durable_base>/history.jsonl  (one line appended)
  - /tmp/design-loop/preview/{baseline,upgraded,report}.html  (mirror, no
    history side-effect; convenient `open` target during development)

Usage:
    python3 scripts/render_demo.py [--no-durable]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_MODULE_ROOT = _HERE.parent
sys.path.insert(0, str(_MODULE_ROOT))

from amplifier_module_tool_render_report.template import render  # noqa: E402

FIXTURES = _MODULE_ROOT / "fixtures" / "demo"
SLOP = FIXTURES / "slop.html"
UPGRADED = FIXTURES / "upgraded.html"

# A believable 3-pass run: slop baseline -> one rejected attempt (regression on
# restraint) -> the editorial redesign as the converged champion.
_BASELINE_SCORES = {
    "clarity": 1, "elegance": 0, "restraint": 0, "empowerment": 1,
    "agency": 1, "ease": 1, "character": 0, "point": 1,
}
_PASS1_SCORES = {
    "clarity": 2, "elegance": 1, "restraint": 0, "empowerment": 2,
    "agency": 1, "ease": 2, "character": 1, "point": 1,
}
_CHAMPION_SCORES = {
    "clarity": 4, "elegance": 4, "restraint": 4, "empowerment": 3,
    "agency": 3, "ease": 4, "character": 4, "point": 3,
}


def build_demo_state() -> dict:
    records = [
        {
            "pass": 0,
            "task_class": "landing-page-critique",
            "decision": "NEW_BEST",
            "outcome": "accepted",
            "scores": _BASELINE_SCORES,
            "fix_batch": [
                {
                    "criterion": "restraint",
                    "issue": "Three identical feature cards padded out with generic copy and emoji bullets.",
                    "fix": "Cut to the three claims that are actually true and differentiating.",
                },
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(SLOP),
        },
        {
            "pass": 1,
            "decision": "NO_GAIN",
            "outcome": "rejected",
            "scores": _PASS1_SCORES,
            "fix_batch": [
                {
                    "criterion": "character",
                    "issue": "Swapped the gradient for a flat color but kept the same generic layout.",
                    "fix": "Needs an actual point of view, not a palette swap.",
                },
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(SLOP),  # stand-in candidate; not promoted
        },
        {
            "pass": 2,
            "decision": "NEW_BEST",
            "outcome": "accepted",
            "scores": _CHAMPION_SCORES,
            "fix_batch": [
                {
                    "criterion": "restraint",
                    "issue": "Replaced the three equal feature cards with one asymmetric capability list.",
                    "fix": "Each capability earns its own space and makes one real claim.",
                },
            ],
            "lint_results": {"hard_fail": False, "hard_fail_reasons": []},
            "artifact_ref": str(UPGRADED),
        },
    ]
    return {
        "records": records,
        "gate": {"action": "DONE", "reason": "bar_met"},
        "champion": {
            "scores": _CHAMPION_SCORES,
            "total": sum(_CHAMPION_SCORES.values()),
            "artifact_ref": str(UPGRADED),
        },
        "converged": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-durable", action="store_true",
        help="Skip the Downloads/design-loop durable write + history.jsonl append.",
    )
    args = parser.parse_args()

    if not SLOP.exists() or not UPGRADED.exists():
        print(f"demo fixtures missing under {FIXTURES}", file=sys.stderr)
        return 1

    state = build_demo_state()

    durable_base = None if args.no_durable else str(Path.home() / "Downloads" / "design-loop")

    out_dir = Path("/tmp/design-loop/preview")
    out_dir.mkdir(parents=True, exist_ok=True)
    result = render(state, out_dir=str(out_dir), durable_base=durable_base)

    print("Wrote:")
    for key in ("baseline_html", "upgraded_html", "report_html"):
        print(f"  {key}: {result[key]}")
    if durable_base:
        print("Durable copies:")
        for key in ("durable_baseline_html", "durable_upgraded_html", "durable_report_html"):
            print(f"  {key}: {result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
