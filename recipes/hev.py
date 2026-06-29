#!/usr/bin/env python3
"""harness-evolution transforms — pure, deterministic helpers for asset-8.

The promotion gate (HARNESS_DESIGN.md §6/§7) is the *slow clock*: a self-PR loop
that turns a recurring, expensive Judge catch into a cheap deterministic lint. This
file centralises every multi-line Python transform the `harness-evolution.yaml`
recipe needs, so the recipe YAML bash steps stay one-liners (no embedded multi-line
Python, which would break YAML block-scalar indentation).

It mirrors the `dlx.py` pattern used by design-pass / design-converge: each command
reads/writes JSON files under a work dir `W` and prints a small JSON object to stdout
for the recipe to capture via parse_json. The `extract` command is the SAME repr
unwrapper as dlx.py (the `amplifier tool invoke --output json` result is a str(dict)
Python repr, not JSON) — reused verbatim so the deterministic tool-call contract is
identical across the harness.

HONEST SCOPE: this helper MINES the ledger, GATES the top candidate against the five
§6 criteria (the deterministic parts), and DRAFTS a ratifiable promotion proposal. It
deliberately does NOT generate lint code, a regression test, or a rubric bump — those
are the human-ratified follow-up (the merged PR). No codegen is faked here.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone

DIMS = [
    "clarity", "elegance", "restraint", "empowerment",
    "agency", "ease", "character", "point",
]

# signatures that are not real join keys (never a promotion candidate)
_NULL_SIGS = {"", "unsigned", "unknown", "none", "null"}


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def extract(raw_file):
    """Pull the clean tool-result JSON out of `amplifier tool invoke --output json`.

    That CLI prints log lines then a pretty `{"status","tool","result"}` block whose
    `result` is a str(dict) Python repr (single quotes), not JSON. Identical to
    dlx.py:extract — reused so the deterministic tool-call contract stays uniform.
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


def _worst_dim(scores):
    if not isinstance(scores, dict):
        return None
    return min(float(scores.get(d, 0)) for d in DIMS)


def _low_dims(scores, thr):
    if not isinstance(scores, dict):
        return []
    return [d for d in DIMS if float(scores.get(d, 0)) <= thr]


def _ref(rec):
    """A nameable fixture reference for a ledger record.

    Prefer a concrete artifact_ref (a path/sha the builder can fetch); otherwise a
    durable ledger LOCATOR (records from scored passes may not co-locate the artifact
    bytes — see HARNESS_DESIGN.md §5). Either way the human/builder can find it.
    """
    art = rec.get("artifact_ref")
    if isinstance(art, str) and art:
        return art
    tc = rec.get("task_class", "?")
    eid = rec.get("entry_id", "?")
    return f"ledger:{tc}#entry{eid} (run={rec.get('run_id','?')} pass={rec.get('pass','?')})"


def mine(records_file, low_threshold, min_runs, out_file):
    """Scan the ledger for signatures the Judge repeatedly penalises across runs.

    A record is a 'judge penalty' for its signature when (deterministic):
      - signature is a real join key (not unsigned/unknown), AND
      - scores is a dict (the EXPENSIVE judge was actually spent), AND
      - worst_dim(scores) <= low_threshold (it assigned a low score to some quality).

    Recurrence = number of DISTINCT run_ids (not passes of one run, per §6.1).
    Candidates are ranked (distinct_runs desc, occurrences desc, signature asc).
    """
    thr = float(low_threshold)
    need = int(min_runs)
    recs = _load(records_file, []) or []
    if not isinstance(recs, list):
        recs = []

    groups: dict[str, dict] = {}
    for r in recs:
        if not isinstance(r, dict):
            continue
        sig = r.get("signature")
        if not isinstance(sig, str) or sig.strip().lower() in _NULL_SIGS:
            continue
        scores = r.get("scores")
        wd = _worst_dim(scores)
        if wd is None or wd > thr:
            continue
        g = groups.setdefault(sig, {"runs": set(), "occurrences": 0, "low": Counter(), "examples": []})
        g["runs"].add(r.get("run_id"))
        g["occurrences"] += 1
        g["low"].update(_low_dims(scores, thr))
        g["examples"].append({
            "run_id": r.get("run_id"),
            "pass": r.get("pass"),
            "entry_id": r.get("entry_id"),
            "worst_dim": wd,
            "rubric_version": r.get("rubric_version"),
            "reject_reason": r.get("reject_reason"),
            "ref": _ref(r),
            "scores": scores,
        })

    candidates = []
    for sig, g in groups.items():
        runs = sorted(x for x in g["runs"] if x is not None)
        examples = sorted(g["examples"], key=lambda e: (e["worst_dim"], e.get("pass") or 0))
        penalised_dim = g["low"].most_common(1)[0][0] if g["low"] else None
        candidates.append({
            "signature": sig,
            "recurrence_runs": len(runs),
            "occurrences": g["occurrences"],
            "run_ids": runs,
            "penalised_dim": penalised_dim,
            "meets_recurrence": len(runs) >= need,
            "worst_examples": examples[:3],
        })

    candidates.sort(key=lambda c: (-c["recurrence_runs"], -c["occurrences"], c["signature"]))
    _dump(candidates, out_file)

    top = candidates[0] if candidates else None
    print(json.dumps({
        "candidates_count": len(candidates),
        "has_candidate": "true" if top else "false",
        "top_signature": top["signature"] if top else "",
        "top_runs": top["recurrence_runs"] if top else 0,
        "low_threshold": thr,
        "min_runs": need,
    }))


def candidate(candidates_file, best_record_file, out_file):
    """Select the top candidate; bind known-bad (triggering) + known-good (best) refs.

    Exemplar-precision (§6.3) cannot be machine-verified here: that needs the predicate
    to EXIST as code to run against the bar-clearing exemplar bank, and this recipe does
    not generate lint code. So we instead NAME the fixture pair the builder/human will
    use to verify zero false positives.
    """
    cands = _load(candidates_file, []) or []
    best = _load(best_record_file)
    if not cands:
        out = {"signature": "", "has_candidate": "false"}
        _dump(out, out_file)
        print(json.dumps({
            "has_candidate": "false", "signature": "",
            "recurrence_runs": 0, "penalised_dim": "", "meets_recurrence": "false",
        }))
        return

    top = cands[0]
    bad = top["worst_examples"][0] if top.get("worst_examples") else {}
    good_ref = _ref(best) if isinstance(best, dict) else None
    good_scores = best.get("scores") if isinstance(best, dict) else None

    ctx = {
        "signature": top["signature"],
        "recurrence_runs": top["recurrence_runs"],
        "occurrences": top["occurrences"],
        "run_ids": top["run_ids"],
        "penalised_dim": top.get("penalised_dim"),
        "meets_recurrence": top["meets_recurrence"],
        "fixture_bad_ref": bad.get("ref"),
        "fixture_bad_run": bad.get("run_id"),
        "fixture_bad_scores": bad.get("scores"),
        "fixture_good_ref": good_ref,
        "fixture_good_scores": good_scores,
        "worst_examples": top.get("worst_examples", []),
    }
    _dump(ctx, out_file)
    print(json.dumps({
        "has_candidate": "true",
        "signature": top["signature"],
        "recurrence_runs": top["recurrence_runs"],
        "penalised_dim": top.get("penalised_dim") or "",
        "meets_recurrence": "true" if top["meets_recurrence"] else "false",
    }))


def _draft_markdown(p):
    """Render the promotion proposal as a human-ratifiable PR-draft body."""
    crit = p.get("criteria", {})
    def mark(ok):
        return {True: "PASS", False: "FAIL", None: "DEFERRED"}.get(ok, str(ok))
    lines = []
    lines.append(f"# Promotion proposal — `{p.get('signature','')}`")
    lines.append("")
    lines.append(f"**Status:** {p.get('status','')}  ")
    lines.append(f"**Ratified:** {p.get('ratified', False)}  ")
    lines.append(f"**Generated:** {p.get('ts','')}")
    lines.append("")
    lines.append("> Asset 8 — the ratchet (HARNESS_DESIGN.md §6). This is a PR-draft body:")
    lines.append("> a human merge ratifies it; a follow-up build turns a ratified proposal")
    lines.append("> into the actual lint predicate + regression test + rubric bump. This")
    lines.append("> recipe MINES, GATES, and DRAFTS only — it does not generate lint code.")
    lines.append("")
    lines.append("## The leftward graduation")
    lines.append("`subjective judgment → versioned rubric criterion → few-shot exemplar → deterministic lint`")
    lines.append("")
    lines.append("## The five-criteria gate (min-not-mean — a single FAIL blocks the lint)")
    lines.append("")
    lines.append("| # | Criterion | Verdict | Evidence |")
    lines.append("|---|-----------|---------|----------|")
    rc = crit.get("recurrence", {})
    lines.append(f"| 1 | Recurrence ≥ N distinct runs | {mark(rc.get('pass'))} | "
                 f"{rc.get('observed_runs','?')} runs (need {rc.get('required_runs','?')}): "
                 f"{', '.join(str(x) for x in rc.get('run_ids', []))} |")
    dt = crit.get("determinism", {})
    lines.append(f"| 2 | Determinism (measurable predicate) | {mark(dt.get('pass'))} | "
                 f"{dt.get('note','')} |")
    ep = crit.get("exemplar_precision", {})
    lines.append(f"| 3 | Precision on exemplar bank | {mark(ep.get('pass'))} | {ep.get('note','')} |")
    hr = crit.get("human_ratification", {})
    lines.append(f"| 4 | Human ratification (PR merge) | {mark(hr.get('pass'))} | {hr.get('note','')} |")
    rt = crit.get("regression_test", {})
    lines.append(f"| 5 | Bundled regression test (bad+good) | {mark(rt.get('pass'))} | {rt.get('note','')} |")
    lines.append("")
    lines.append("## Proposed deterministic lint")
    lines.append("")
    lines.append(f"- **Signature retired from rubric:** `{p.get('rubric_criterion_to_retire','')}`")
    lines.append(f"- **Predicate:** {p.get('proposed_predicate','(not-deterministic — stays a Judge criterion / exemplar)')}")
    lines.append(f"- **Threshold:** {p.get('threshold','')}")
    lines.append(f"- **Measurement:** {p.get('measurement','')}")
    lines.append(f"- **Rubric version bump:** {p.get('rubric_version_bump','')}")
    lines.append("")
    lines.append("## Regression fixture pair (the builder materialises these)")
    lines.append("")
    lines.append(f"- **Known-BAD (must catch)** — from triggering ledger record: `{p.get('fixture_bad_ref','')}`")
    lines.append(f"- **Known-GOOD (must pass)** — from best-so-far: `{p.get('fixture_good_ref','')}`")
    lines.append("")
    lines.append("## Ratified follow-up (NOT done by this recipe)")
    lines.append("")
    lines.append("1. Add the predicate to `tool-design-lints`.")
    lines.append("2. Drop the retired criterion from the `design-critic`/`design-judge` rubric; bump its version.")
    lines.append("3. Add the known-bad/known-good pair to `tests/` (CI must catch bad, pass good).")
    lines.append("4. Merge to `main` + refresh the bundle cache → the next run inherits the check for free.")
    lines.append("")
    return "\n".join(lines)


def gate(candidate_file, proposal_file, min_runs, out_file):
    """Apply the §6 five-criteria gate (deterministic parts) over candidate + PROPOSE.

    `proposal_file` is the agent PROPOSE step's JSON: it must carry `deterministic`
    (bool/"not-deterministic") and, when deterministic, `predicate` + `threshold`
    (+ optional measurement / rubric_criterion_to_retire / rubric_version_bump).

    Outcomes (each stops short honestly):
      no_candidate        — nothing recurred; nothing to promote.
      below_recurrence    — recurrence < N distinct runs (criterion 1 fails).
      exemplar_only       — not expressible as a predicate (criterion 2 fails): it can
                            only graduate to a few-shot EXEMPLAR, never a lint. Recorded.
      missing_fixtures    — no nameable bad/good pair (criterion 5 cannot ship).
      ready_for_ratification — criteria 1,2,5 hold deterministically; 3 deferred to the
                            builder (needs the predicate as code); 4 is the human merge.
    """
    need = int(min_runs)
    cand = _load(candidate_file, {}) or {}
    prop = _load(proposal_file, {}) or {}

    sig = cand.get("signature") or ""
    runs = int(cand.get("recurrence_runs") or 0)
    run_ids = cand.get("run_ids", [])
    bad_ref = cand.get("fixture_bad_ref")
    good_ref = cand.get("fixture_good_ref")

    det_raw = prop.get("deterministic")
    is_det = det_raw is True or (isinstance(det_raw, str) and det_raw.strip().lower() in {"true", "yes", "deterministic"})
    predicate = prop.get("predicate") or prop.get("proposed_predicate")
    threshold = prop.get("threshold")

    # ---- deterministic verdicts (min-not-mean) ----
    c1_pass = runs >= need
    c2_pass = bool(is_det and predicate)
    c5_pass = bool(bad_ref and good_ref)

    if not sig or str(cand.get("has_candidate")) == "false":
        status = "no_candidate"
    elif not c1_pass:
        status = "below_recurrence"
    elif not c2_pass:
        status = "exemplar_only"
    elif not c5_pass:
        status = "missing_fixtures"
    else:
        status = "ready_for_ratification"

    proposal = {
        "signature": sig,
        "recurrence_runs": runs,
        "run_ids": run_ids,
        "penalised_dim": cand.get("penalised_dim"),
        "proposed_predicate": predicate if is_det else None,
        "threshold": threshold if is_det else None,
        "measurement": prop.get("measurement") if is_det else None,
        "rubric_criterion_to_retire": prop.get("rubric_criterion_to_retire") or sig,
        "fixture_bad_ref": bad_ref,
        "fixture_good_ref": good_ref,
        "rubric_version_bump": prop.get("rubric_version_bump") or "minor (drop retired criterion)",
        "status": status,
        "ratified": False,
        "ts": datetime.now(timezone.utc).isoformat(),
        "criteria": {
            "recurrence": {
                "required_runs": need, "observed_runs": runs,
                "run_ids": run_ids, "pass": c1_pass,
            },
            "determinism": {
                "pass": c2_pass,
                "note": (f"predicate: {predicate}; threshold: {threshold}" if c2_pass
                         else "not expressible as a measurable predicate — promotes to an "
                              "EXEMPLAR only, stays a Judge criterion (§6.2)."),
            },
            "exemplar_precision": {
                "pass": None,
                "note": "DEFERRED: verifying zero false positives on the bar-clearing "
                        "exemplar bank requires the predicate to exist as code; this recipe "
                        "does not generate lint code. Fixture pair named for the builder.",
            },
            "human_ratification": {
                "pass": None,
                "note": "the staged approval gate = PR-merge analog (§6.4); pending until merged.",
            },
            "regression_test": {
                "pass": c5_pass,
                "note": (f"bad={bad_ref} ; good={good_ref}" if c5_pass
                         else "no nameable known-bad/known-good pair — cannot ship a "
                              "regression test (§6.5)."),
            },
        },
    }
    proposal["markdown"] = _draft_markdown(proposal)
    _dump(proposal, out_file)
    print(json.dumps({
        "status": status,
        "signature": sig,
        "recurrence_runs": runs,
        "ready": "true" if status == "ready_for_ratification" else "false",
    }))


def emit(gate_file, work_dir, ratified):
    """Write the (optionally ratified) promotion proposal as markdown + JSON.

    Always writes an artifact — even for below_recurrence / exemplar_only — because
    recording WHY nothing was promoted is part of the honest governance trail (§7).
    `ratified` reflects the human approval-gate decision (the PR-merge analog).
    """
    p = _load(gate_file, {}) or {}
    is_ratified = str(ratified).strip().lower() in {"true", "yes", "1", "merge", "approve", "approved"}
    promotable = p.get("status") == "ready_for_ratification"
    p["ratified"] = bool(is_ratified and promotable)
    p["ratified_ts"] = datetime.now(timezone.utc).isoformat() if p["ratified"] else None
    # human_ratification criterion now resolved
    crit = p.get("criteria", {})
    if "human_ratification" in crit:
        crit["human_ratification"]["pass"] = True if p["ratified"] else (False if promotable else None)
    md = _draft_markdown(p)
    p["markdown"] = md

    md_path = work_dir.rstrip("/") + "/promotion-proposal.md"
    json_path = work_dir.rstrip("/") + "/promotion-proposal.json"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    p_no_md = dict(p)
    p_no_md.pop("markdown", None)
    _dump(p_no_md, json_path)

    print(json.dumps({
        "status": p.get("status"),
        "ratified": p["ratified"],
        "signature": p.get("signature", ""),
        "recurrence_runs": p.get("recurrence_runs", 0),
        "proposed_predicate": p.get("proposed_predicate"),
        "fixture_bad_ref": p.get("fixture_bad_ref"),
        "fixture_good_ref": p.get("fixture_good_ref"),
        "proposal_md_path": md_path,
        "proposal_json_path": json_path,
    }))


def get(path, key, default=""):
    """Print the RAW scalar value of one field of a JSON file (for bash $(...) capture)."""
    v = (_load(path, {}) or {}).get(key, default)
    print(v if isinstance(v, str) else json.dumps(v))


_COMMANDS = {
    "extract": extract,
    "mine": mine,
    "candidate": candidate,
    "gate": gate,
    "emit": emit,
    "get": get,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print("null"); return
    _COMMANDS[sys.argv[1]](*sys.argv[2:])


if __name__ == "__main__":
    main()
