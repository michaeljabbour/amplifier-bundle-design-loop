#!/usr/bin/env python3
"""design-loop transforms — pure, deterministic helpers for the recipe bash steps.

Centralises every multi-line Python transform the design-pass / design-converge
recipes need, so the recipe YAML bash steps stay one-liners (no embedded
multi-line Python, which would break YAML block-scalar indentation).

All commands read/write JSON files under a run/pass work dir `W` and print a
small JSON object to stdout for the recipe to capture via parse_json.

This file is the readable source of truth; the recipes also embed it (base64)
and materialise it at runtime so they remain self-contained and portable.

LOOP PRIMITIVE — BRICK MAP (the reusable studs of this convergence loop)
------------------------------------------------------------------------
The harness is a generic *propose -> gate -> critique -> evaluate -> record
-> render* loop. Each brick is a separate tool invoked over a stable JSON
contract (`amplifier tool invoke <tool> --output json`); dlx.py is the
deterministic glue between them. To reuse the loop in another pipeline, swap
the domain bricks (maker/lints/critic) and keep the generic ones
(gate/ledger/render):

  front door  classify_input()/normalize  -> html | image | url | prompt
  maker       tool-target-state           -> a candidate artifact
  lints       tool-design-lints           -> hard pass/fail gates (offline,
                                             contrast, no-script, ...)
  critic      design-critic (agent)       -> 8-dim scorecard, ints 0..4
  gate        tool-design-controller      -> maximin action: PLAN | DONE |
                                             ESCALATE (bar/floor/plateau/
                                             regression/budget)
  evaluate    dlx normscores/extract      -> champion selection (fail-loud)
  ledger      tool-design-ledger          -> append-only run/pass records
  render      tool-render-report.render() -> {upgraded.html, report.html}

EXTRACTION SEAM: the studs are the JSON contracts, not Python imports. See
docs/PRIMITIVE.md for how to lift this loop into a non-design pipeline.
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

_ERROR_SENTINEL_EXTRACT = "extract_failed"
_ERROR_SENTINEL_SCORES  = "invalid_scores"


def _exit_error(err_type: str, detail: str) -> None:
    """Print fail-loud error sentinel to stdout, human message to stderr, exit 1.

    The sentinel is a dict parseable as JSON so callers can detect it, but its
    presence of __dlx_error__ key means it MUST NOT be treated as a valid result.
    Never returns — always raises SystemExit(1).
    """
    print(json.dumps({"__dlx_error__": err_type, "detail": str(detail)}))
    print(f"dlx error [{err_type}]: {detail}", file=sys.stderr)
    sys.exit(1)


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _loaddict(path):
    """Load a JSON file as a dict, fail-safe: any non-dict top-level value -> {}."""
    d = _load(path, {})
    return d if isinstance(d, dict) else {}


def _ledger_len(W):
    return len(_load(W + "/ledger.json", []) or [])


def extract(raw_file):
    """Pull the clean tool-result JSON out of `amplifier tool invoke --output json`.

    That CLI prints log lines then a pretty `{"status","tool","result"}` block
    whose `result` is a str(dict) Python repr (single quotes), not JSON.

    Fail-loud contract: any parse failure emits a structured error sentinel
    ({"__dlx_error__": "extract_failed", "detail": "..."}) to stdout, a human
    line to stderr, and exits nonzero.  Never emits a value that downstream
    can mistake for success.
    """
    try:
        raw = open(raw_file, encoding="utf-8").read()
    except Exception as exc:
        _exit_error(_ERROR_SENTINEL_EXTRACT, f"cannot read file: {exc}")
    m = re.search(r'\{\s*"status".*\}\s*\Z', raw, re.S)
    if not m:
        _exit_error(_ERROR_SENTINEL_EXTRACT, 'no {"status"...} block found in output')
    try:
        obj = json.loads(m.group(0))
    except Exception as exc:
        _exit_error(_ERROR_SENTINEL_EXTRACT, f"json.loads failed on status block: {exc}")
    res = obj.get("result")
    if isinstance(res, str):
        try:
            res = ast.literal_eval(res)
        except Exception as exc:
            _exit_error(_ERROR_SENTINEL_EXTRACT, f"ast.literal_eval failed on result repr: {exc}")
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
    lints = _loaddict(W + "/lints.json")
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
    - emits champion_is_baseline: "true" when no scored pass (pass>0 with
      non-null scores) has been run yet (the champion is still the untouched
      pass-0 baseline).  Used by _gate Rule 3 to suppress premature
      floor_breach escalation.
    - emits prior_lint_reasons: a directive string (non-empty only when the
      most recent pass was a lint-reject) to feed back to the maker so it
      fixes the deterministic failures first.
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
    res = _loaddict(W + "/pass-live/result.json")
    # champion_is_baseline: True iff no pass > 0 with real (non-null) scores exists
    scored_passes_gt0 = sum(
        1 for r in recs
        if isinstance(r.get("scores"), dict) and int(r.get("pass", 0)) > 0
    )
    champion_is_baseline = scored_passes_gt0 == 0
    # prior_lint_reasons: feed deterministic lint failures back to the maker
    lints_live = _loaddict(W + "/pass-live/lints.json")
    prior_lint_reasons = ""
    if lints_live.get("hard_fail"):
        reasons = lints_live.get("hard_fail_reasons") or ["hard_fail"]
        prior_lint_reasons = (
            "PRIOR DETERMINISTIC LINT FAILURES — fix these FIRST (no rubric): "
            + ", ".join(str(r) for r in reasons)
        )
    print(json.dumps({
        "target_retried": "true" if prev_action == "ROLLBACK" else "false",
        "last_decision": res.get("decision", "NO_GAIN"),
        "champion_is_baseline": "true" if champion_is_baseline else "false",
        "prior_lint_reasons": prior_lint_reasons,
    }))


def field(path, key, default=""):
    """Print {key: value} JSON for one field of a JSON file (for parse_json capture)."""
    print(json.dumps({key: _loaddict(path).get(key, default)}))


def get(path, key, default=""):
    """Print the RAW scalar value of one field (for bash $(...) capture)."""
    v = _loaddict(path).get(key, default)
    print(v if isinstance(v, str) else json.dumps(v))


def normscores(path):
    """Validate and normalise critic scores to the flat 8-dim {dim:int} contract.

    The blind critic agent may emit EITHER a flat {dim:int} object OR a full
    scorecard {scores:{...}, reasons:{...}, ...}.  Unwrap a nested `scores` dict
    if present, then VALIDATE all 8 dims strictly.

    Validation rules (matching tool-render-report/verdict.py):
      - ALL 8 known dims must be present (no defaults for missing dims)
      - Each value must be a plain int (bool rejected — bool is subclass of int)
      - Each value must be in 0..4 (inclusive)

    On any violation: emits {"__dlx_error__": "invalid_scores", "detail": "..."}
    to stdout, a human message to stderr, and exits nonzero.  Never emits a value
    downstream can mistake for valid scores.

    Valid path: writes the flat 8-dim dict back in-place AND prints it to stdout.
    Idempotent for already-valid flat dicts.
    """
    d = _load(path)
    if isinstance(d, dict) and isinstance(d.get("scores"), dict):
        d = d["scores"]
    if not isinstance(d, dict):
        _exit_error(_ERROR_SENTINEL_SCORES, f"top-level value is not a dict (got {type(d).__name__})")
    flat: dict = {}
    for dim in DIMS:
        if dim not in d:
            _exit_error(_ERROR_SENTINEL_SCORES, f"missing required dim: {dim!r}")
        v = d[dim]
        # bool is subclass of int in Python — reject explicitly before isinstance(int) check
        if isinstance(v, bool):
            _exit_error(_ERROR_SENTINEL_SCORES, f"dim {dim!r} is bool (True/False not allowed; use int 0-4)")
        if not isinstance(v, int):
            _exit_error(_ERROR_SENTINEL_SCORES, f"dim {dim!r} is not int: {v!r} (type {type(v).__name__})")
        if not (0 <= v <= 4):
            _exit_error(_ERROR_SENTINEL_SCORES, f"dim {dim!r} = {v} is out of range 0..4")
        flat[dim] = v
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flat, f)
    print(json.dumps(flat))


def gateout(W, br):
    """Normalise the controller gate result; fail-closed action = ESCALATE.

    Also threads prior_lint_reasons from gateprep.json so design-converge
    can carry it forward to the next pass's maker prompt.
    """
    g = _loaddict(W + "/gate.json")
    prep = _loaddict(W + "/gateprep.json")
    print(json.dumps({
        "action": g.get("action", "ESCALATE"),
        "reason": g.get("reason", "gate_unavailable"),
        "budget_remaining": int(br),
        "prior_lint_reasons": prep.get("prior_lint_reasons", ""),
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
    rep = _loaddict(W + "/report.json")
    try:
        passes = int(open(W + "/passes.txt", encoding="utf-8").read().strip() or "0")
    except Exception:
        passes = 0
    escalation = None
    if action == "ESCALATE":
        g = _loaddict(W + "/gate.json")
        escalation = {"reason": g.get("reason", "unknown")}
    print(json.dumps({
        "report_path": rep.get("report_html_path", W + "/report.html"),
        "best_scores": best_scores, "passes": passes,
        "final_action": action, "escalation": escalation,
    }))



def _default_durable_base() -> str:
    """OS-appropriate default location for persisted run history.

    Defaults to the user's Downloads folder: ``<home>/Downloads/design-loop``
    (resolves correctly on Windows, macOS, and Linux via ``Path.home()``).
    Override the base with the ``DESIGN_LOOP_HOME`` env var (a full path).
    """
    from pathlib import Path
    override = os.environ.get("DESIGN_LOOP_HOME", "").strip()
    if override:
        return str(Path(override).expanduser())
    return str(Path.home() / "Downloads" / "design-loop")


def render_two(W, action):
    """Two-artifact render: writes baseline.html + upgraded.html + report.html.

    Writes to W (work dir) AND copies to a durable run dir under
    <Downloads>/design-loop/runs/<run_id>/.  Returns durable paths.
    """
    import sys as _sys
    try:
        from amplifier_module_tool_render_report.template import render as _render
    except ImportError:
        import site
        for sp in (site.getusersitepackages(), *site.getsitepackages()):
            _sys.path.insert(0, sp)
        try:
            from amplifier_module_tool_render_report.template import render as _render
        except ImportError as exc:
            print(json.dumps({"upgraded_html": W + "/best.html",
                               "report_html": W + "/report.html",
                               "baseline_html": "",
                               "warning": f"render_two: import failed: {exc}"}))
            return

    import pathlib as _pl
    _durable_base = _default_durable_base()

    all_recs_path = W + "/all_records.json"
    recs = _load(all_recs_path, []) or []
    best_rec = _loaddict(W + "/best_record.json")
    gate = _loaddict(W + "/gate.json")

    champ_scores = best_rec.get("scores") or {}
    if isinstance(champ_scores, dict) and isinstance(champ_scores.get("scores"), dict):
        champ_scores = champ_scores["scores"]
    champ_total = sum(v for v in champ_scores.values() if isinstance(v, (int, float)))

    state = {
        "records": recs if recs else ([best_rec] if best_rec else []),
        "gate": gate,
        "champion": {
            "scores": champ_scores,
            "total": int(champ_total),
            "artifact_ref": best_rec.get("artifact_ref", W + "/best.html"),
        },
        "converged": gate.get("action", "ESCALATE") == "DONE",
    }

    try:
        result = _render(state, out_dir=W, durable_base=_durable_base)
        print(json.dumps({
            "upgraded_html": result.get("durable_upgraded_html") or result["upgraded_html"],
            "report_html":   result.get("durable_report_html")   or result["report_html"],
            "baseline_html": result.get("durable_baseline_html") or result.get("baseline_html", ""),
        }))
    except Exception as exc:
        print(json.dumps({"upgraded_html": W + "/best.html",
                           "report_html": W + "/report.html",
                           "baseline_html": "",
                           "warning": f"render_two: render failed: {exc}"}))


def classify_input(s: str) -> str:
    """Classify input string -> kind: url, html, image, or prompt.

    Rules (deterministic, no network):
      - starts with http:// or https://         -> "url"  (checked FIRST)
      - extension .html or .htm (any case)       -> "html"
      - extension .png/.jpg/.jpeg/.webp/.gif     -> "image"
      - everything else (free text, bare path)   -> "prompt"

    A URL that ends in .png is "url", not "image" — URL check wins.
    """
    import os as _os
    if s.startswith("http://") or s.startswith("https://"):
        return "url"
    ext = _os.path.splitext(s)[1].lower()
    if ext in (".html", ".htm"):
        return "html"
    if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return "image"
    return "prompt"


def classify(s: str) -> None:
    """Print {"kind": "..."} JSON for the given input string."""
    print(json.dumps({"kind": classify_input(s)}))


def designspec(W: str) -> None:
    """Deterministic text design-spec from run ledger.

    Reads all_records.json (or best_record.json fallback) from W, builds a
    text summary of champion scores + accepted fix decisions, writes
    design-spec.txt to W, and prints JSON {spec, spec_path} to stdout.
    Fully deterministic — no LLM.
    """
    best = _load(W + "/best_record.json") or {}
    recs = _load(W + "/all_records.json", []) or []

    # Champion scores (unwrap nested {scores:{...}} if needed)
    scores = best.get("scores") or {}
    if isinstance(scores, dict) and isinstance(scores.get("scores"), dict):
        scores = scores["scores"]
    total = int(sum(v for v in scores.values() if isinstance(v, (int, float))))

    lines = ["DESIGN SPECIFICATION", "=" * 40, ""]
    lines.append(f"Champion score: {total}/32")
    if scores:
        lines.append("Dimension scores:")
        for dim in DIMS:
            v = scores.get(dim)
            lines.append(f"  {dim}: {v}/4" if v is not None else f"  {dim}: -/4")
    lines.append("")

    # Accepted fixes from passes > 0 only (not baseline pass 0)
    accepted = [
        r for r in recs
        if r.get("outcome") == "accepted" and int(r.get("pass", 0)) > 0
    ]
    if accepted:
        lines.append("Design decisions (accepted fixes):")
        for rec in accepted:
            for fix in (rec.get("fix_batch") or []):
                if isinstance(fix, str):
                    lines.append(f"  - {fix}")
                elif isinstance(fix, dict):
                    label = (
                        fix.get("label") or fix.get("fix") or
                        fix.get("description") or fix.get("id") or str(fix)
                    )
                    lines.append(f"  - {label}")
    else:
        lines.append("No accepted improvements recorded.")

    spec = "\n".join(lines) + "\n"
    out_path = W + "/design-spec.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(spec)
    print(json.dumps({"spec": spec, "spec_path": out_path}))


_COMMANDS = {
    "extract": extract, "lintflags": lintflags, "baserec": baserec,
    "lintrec": lintrec, "passrec": passrec, "result": result,
    "lintresult": lintresult, "gateprep": gateprep, "verdict": verdict,
    "summary": summary, "field": field, "get": get, "gateout": gateout,
    "normscores": normscores,
    "render_two": render_two,
    "classify": classify,
    "designspec": designspec,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print("null"); return
    _COMMANDS[sys.argv[1]](*sys.argv[2:])


if __name__ == "__main__":
    main()
