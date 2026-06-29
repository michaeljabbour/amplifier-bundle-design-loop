#!/usr/bin/env python3
"""design-loop transforms — pure, deterministic helpers for the recipe bash steps.

Centralises every multi-line Python transform the design-pass / design-converge
recipes need, so the recipe YAML bash steps stay one-liners (no embedded
multi-line Python, which would break YAML block-scalar indentation).

All commands read/write JSON files under a run/pass work dir `W` and print a
small JSON object to stdout for the recipe to capture via parse_json.

This file is the readable source of truth; the recipes also embed it (base64)
and materialise it at runtime so they remain self-contained and portable.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import sys

DIMS = [
    "clarity", "elegance", "restraint", "empowerment",
    "agency", "ease", "character", "point",
]


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _ledger_len(W):
    return len(_load(W + "/ledger.json", []) or [])


def extract(raw_file):
    """Pull the clean tool-result JSON out of `amplifier tool invoke --output json`.

    That CLI prints log lines then a pretty `{"status","tool","result"}` block
    whose `result` is a str(dict) Python repr (single quotes), not JSON.
    """
    try:
        raw = open(raw_file, encoding="utf-8").read()
    except Exception:
        print("null"); return
    m = re.search(r'\{\s*"status".*\}\s*\Z', raw, re.S)
    if not m:
        print("null"); return
    try:
        obj = json.loads(m.group(0))
    except Exception:
        print("null"); return
    res = obj.get("result")
    if isinstance(res, str):
        try:
            res = ast.literal_eval(res)
        except Exception:
            pass
    print(json.dumps(res))


def lintflags(lints_file):
    """Fail-closed lint summary: unreachable lints == hard_fail."""
    d = _load(lints_file)
    if not isinstance(d, dict):
        print(json.dumps({"hard_fail": "true", "reasons": ["lint_unavailable"]})); return
    hf = "true" if d.get("hard_fail") else "false"
    print(json.dumps({"hard_fail": hf, "reasons": d.get("hard_fail_reasons", [])}))


def baserec(W, run, tc, sig, rv):
    """Pass-0 baseline ledger record (the seed best). Real critic scores."""
    scores = _load(W + "/best_scores.json")
    lints = _load(W + "/pass0/lints.json", {}) or {}
    rec = {
        "run_id": run, "task_class": tc, "pass": 0, "signature": sig,
        "rubric_version": rv, "outcome": "accepted", "scores": scores,
        "fix_batch": [], "lint_results": lints,
        "artifact_ref": W + "/best.html", "decision": "NEW_BEST",
    }
    print(json.dumps(rec))


def lintrec(W, run, tc, sig, rv):
    """Lint-reject record: scores stay null (honest stopping), no judge spent."""
    lints = _load(W + "/lints.json", {}) or {}
    fb = _load(W + "/fix_batch.json", []) or []
    reasons = lints.get("hard_fail_reasons") or ["hard_fail"]
    rec = {
        "run_id": run, "task_class": tc, "pass": _ledger_len(W), "signature": sig,
        "rubric_version": rv, "outcome": "lint_reject", "scores": None,
        "reject_reason": "lint:" + ",".join(reasons),
        "fix_batch": fb, "lint_results": lints,
    }
    print(json.dumps(rec))


def passrec(W, run, tc, sig, rv, outcome, reason, dec):
    """Scored ledger record from a completed judge pass."""
    scores = _load(W + "/scores.json")
    lints = _load(W + "/lints.json", {}) or {}
    fb = _load(W + "/fix_batch.json", []) or []
    rec = {
        "run_id": run, "task_class": tc, "pass": _ledger_len(W), "signature": sig,
        "rubric_version": rv, "outcome": outcome, "scores": scores,
        "fix_batch": fb, "lint_results": lints, "decision": dec,
    }
    if outcome != "accepted":
        rec["reject_reason"] = reason or outcome
    print(json.dumps(rec))


def result(W, dec, bref):
    """design-pass return contract: {scores, decision, best_so_far_ref, candidate_html_path}."""
    scores = _load(W + "/scores.json")
    print(json.dumps({
        "scores": scores, "decision": dec,
        "best_so_far_ref": bref, "candidate_html_path": W + "/candidate.html",
    }))


def lintresult(W):
    """design-pass return contract for the lint-reject branch (scores null)."""
    print(json.dumps({
        "scores": None, "decision": "INVALID",
        "best_so_far_ref": None, "candidate_html_path": W + "/candidate.html",
    }))


def gateprep(W, prev_action):
    """Refresh best-so-far (a QUERY) + compute the plateau series for the gate.

    - best_record.json -> best_scores.json and best.html (rollback-for-free).
    - all_records.json -> improvements.json (worst-dim gain per pass; 0 on
      non-improving / lint-reject passes).
    - emits target_retried + last_decision for the controller gate.
    """
    best = _load(W + "/best_record.json")
    if isinstance(best, dict) and isinstance(best.get("scores"), dict):
        json.dump(best["scores"], open(W + "/best_scores.json", "w", encoding="utf-8"))
        ref = best.get("artifact_ref")
        if ref and ref != W + "/best.html" and os.path.exists(ref):
            try:
                shutil.copyfile(ref, W + "/best.html")
            except Exception:
                pass
    recs = sorted(_load(W + "/all_records.json", []) or [], key=lambda r: r.get("entry_id", 0))
    improvements = []
    prev_worst = None
    for r in recs:
        s = r.get("scores")
        if isinstance(s, dict):
            worst = min(s.get(d, 0) for d in DIMS)
            improvements.append(0.0 if prev_worst is None else float(max(0, worst - prev_worst)))
            prev_worst = worst if prev_worst is None else max(prev_worst, worst)
        else:
            improvements.append(0.0)
    json.dump(improvements, open(W + "/improvements.json", "w", encoding="utf-8"))
    res = _load(W + "/pass-live/result.json", {}) or {}
    print(json.dumps({
        "target_retried": "true" if prev_action == "ROLLBACK" else "false",
        "last_decision": res.get("decision", "NO_GAIN"),
    }))


def field(path, key, default=""):
    """Print {key: value} JSON for one field of a JSON file (for parse_json capture)."""
    print(json.dumps({key: (_load(path, {}) or {}).get(key, default)}))


def get(path, key, default=""):
    """Print the RAW scalar value of one field (for bash $(...) capture)."""
    v = (_load(path, {}) or {}).get(key, default)
    print(v if isinstance(v, str) else json.dumps(v))


def gateout(W, br):
    """Normalise the controller gate result; fail-closed action = ESCALATE."""
    g = _load(W + "/gate.json", {}) or {}
    print(json.dumps({
        "action": g.get("action", "ESCALATE"),
        "reason": g.get("reason", "gate_unavailable"),
        "budget_remaining": int(br),
    }))


def verdict(W):
    """Verdict object for render_report (scores + total)."""
    best = _load(W + "/best_record.json")
    scores = best.get("scores") if isinstance(best, dict) else None
    print(json.dumps({"scores": scores or {}, "total": sum((scores or {}).values()), "fixes": []}))


def summary(W, action):
    """Final run summary: {report_path, best_scores, passes, final_action, escalation}."""
    best = _load(W + "/best_record.json")
    best_scores = best.get("scores") if isinstance(best, dict) else None
    rep = _load(W + "/report.json", {}) or {}
    try:
        passes = int(open(W + "/passes.txt", encoding="utf-8").read().strip() or "0")
    except Exception:
        passes = 0
    escalation = None
    if action == "ESCALATE":
        g = _load(W + "/gate.json", {}) or {}
        escalation = {"reason": g.get("reason", "unknown")}
    print(json.dumps({
        "report_path": rep.get("report_html_path", W + "/report.html"),
        "best_scores": best_scores, "passes": passes,
        "final_action": action, "escalation": escalation,
    }))


_COMMANDS = {
    "extract": extract, "lintflags": lintflags, "baserec": baserec,
    "lintrec": lintrec, "passrec": passrec, "result": result,
    "lintresult": lintresult, "gateprep": gateprep, "verdict": verdict,
    "summary": summary, "field": field, "get": get, "gateout": gateout,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print("null"); return
    _COMMANDS[sys.argv[1]](*sys.argv[2:])


if __name__ == "__main__":
    main()
