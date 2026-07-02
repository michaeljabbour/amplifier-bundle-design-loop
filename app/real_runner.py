"""REAL design-loop backend: drives recipes/design-converge.yaml via the
`amplifier` CLI as a per-run OS SUBPROCESS (not the in-process SDK).

Why a subprocess, not the SDK (approach (a), replaced by this module)
----------------------------------------------------------------------
The filesystem write tool's `allowed_write_paths` defaults to
``[session.working_dir]``, and the kernel derives that from the OS
process's cwd at session start. When this app hosted the recipe's
maker/planner/critic sub-agents in-process (via load_bundle/create_session
inside the FastAPI worker), every one of those spawned sessions inherited
the *same* process-wide cwd -- wherever uvicorn happened to be launched
from -- so the maker's own write tool could never be scoped to this run's
own `work_dir`. Every candidate.html / fix_batch.json write from a spawned
agent was rejected as outside allowed_write_paths. That was the blocker.

The fix: run each `amplifier` CLI invocation as its own OS subprocess with
``cwd=work_dir``. Each subprocess gets its own top-level session whose
`session.working_dir` capability -- and therefore the write tool's
`allowed_write_paths` -- is exactly this run's `work_dir`. No SDK session,
no manual hook/spawn-capability wiring needed here anymore; the CLI does
all of that internally, correctly scoped, for free.

The recipe is a STAGED recipe with a single up-front approval gate. Driving
it is 3 CLI calls, ALL with cwd=work_dir and --bundle <this repo root>:

    1. execute  -- runs the up-front bash step, pauses at the APS gate.
    2. approve  -- auto-approves headlessly (this app has no human-in-the-
                   loop UI for that gate; the web app's whole design *is*
                   the human-authored APS, captured in the run's options).
    3. resume   -- runs the ENTIRE governed convergence loop (maker/critic/
                   planner sub-agents, real LLM calls, real cost). This is
                   the long call; its stdout/stderr is streamed live to the
                   WS log as it runs.

`execute`'s ``--output json`` envelope is
``{"status": "success"|"error", "tool": "recipes", "result": "<repr>"}``
where `result` is a **Python repr string** (single-quoted dict, True/False/
None) -- NOT JSON. Verified against the live CLI; see
``_parse_cli_json`` below, which uses ``ast.literal_eval`` (never
``json.loads``) on that field.

By the time `resume` returns without a further ``paused_for_approval``, the
recipe has ALREADY written report.html / upgraded.html / baseline.html
(via its own FINALIZE stage's `render_report` tool call + `dlx.py
render_two`, which calls the SAME render() this app's dry_runner also
calls) plus its ledger JSON files (gate.json, best_record.json,
all_records.json, verdict.json) directly into work_dir. This module reads
those back to build the app's result -- it never re-renders, and never
fabricates a result on failure.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import json
import logging
import os
import pathlib
import re
import shutil
import sys
from typing import Any

from .protocols import WebStreamingHook

logger = logging.getLogger(__name__)

# This app lives at <bundle-root>/app/real_runner.py.
_BUNDLE_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RECIPE_PATH = _BUNDLE_ROOT / "recipes" / "design-converge.yaml"

# Default APS (Acceptance/Production Spec) knobs for design-converge.yaml.
# `budget` defaults to 6 (a deliberately modest number of passes for the web
# app's real-money default -- higher than dry-mode's illustrative numbers,
# lower than the bundle's own CLI-usage-example default of 8..12, so a
# first real run doesn't burn an unbounded amount of budget by accident).
# Callers may override any of these via `options` (see `_apply_overrides`).
_DEFAULT_RECIPE_CONTEXT: dict[str, Any] = {
    "task_class": "landing-page-critique",
    "bar": 26,
    "floors": 2,
    "budget": 6,
    "epsilon": 1,
    "k": 3,
}
_NUMERIC_CONTEXT_KEYS = {"bar", "floors", "budget", "epsilon", "k"}
# Keys derived from THIS run's identity -- never overridable via `options`.
_PROTECTED_CONTEXT_KEYS = {"source", "kind", "work_dir", "bundle_ref", "run_id"}

# The `resume` call spawns maker/planner/critic agents across up to
# `budget` passes -- each a real LLM round-trip. Generous headroom; the
# recipe's own deterministic gate (design_controller op=gate) stops the
# loop on its own well before this fires in the normal case.
_RESUME_TIMEOUT_S = 1500.0
# execute/approve make no LLM calls (execute runs one bash step; approve
# just records a decision) -- short timeout is plenty.
_SHORT_TIMEOUT_S = 120.0
# Defensive cap on the approve/resume auto-approval loop (the recipe has
# exactly one gate; more than a handful of iterations means something is
# wrong, not that more gates exist).
_MAX_APPROVAL_ROUNDS = 12

# The trailing `{"status": ..., "tool": ..., "result": ...}` block the CLI
# prints as the LAST thing on stdout for `--output json` (human-readable
# log lines -- module installs, etc. -- precede it).
_ENVELOPE_RE = re.compile(r'\{\s*"status".*\}\s*\Z', re.S)


def _classify_fallback(source: str) -> str:
    """Best-effort classification via recipes/dlx.py's classify_input.

    Only used as a defensive fallback if a caller somehow invokes run_real
    without a resolved kind -- ws_handler always passes one (read from
    meta.json), so this should not normally execute.
    """
    try:
        import importlib
        import sys as _sys

        recipes_dir = _BUNDLE_ROOT / "recipes"
        if str(recipes_dir) not in _sys.path:
            _sys.path.insert(0, str(recipes_dir))
        dlx = importlib.import_module("dlx")
        return dlx.classify_input(source)
    except Exception:
        logger.warning(
            "classify_input fallback failed for source=%r", source, exc_info=True
        )
        return "prompt"


def _resolve_amplifier_bin() -> str:
    """Resolve the `amplifier` CLI executable to run as a subprocess.

    Prefers the console-script installed alongside the CURRENT interpreter
    (``sys.executable``) -- correct whenever this app itself was started as
    ``<venv>/bin/python -m uvicorn ...``, since `amplifier` lives in that
    same bin/ directory. Falls back to this repo's documented dev venv,
    then to whatever `amplifier` resolves to on PATH.
    """
    candidate = pathlib.Path(sys.executable).resolve().parent / "amplifier"
    if candidate.exists():
        return str(candidate)
    fallback = _BUNDLE_ROOT / ".venv" / "bin" / "amplifier"
    if fallback.exists():
        return str(fallback)
    found = shutil.which("amplifier")
    if found:
        return found
    raise RuntimeError(
        "Could not locate the `amplifier` CLI executable (checked next to "
        f"{sys.executable}, {fallback}, and $PATH). The real backend drives "
        "recipes/design-converge.yaml via this CLI as a subprocess -- "
        "install `amplifier` into this app's own venv."
    )


def _subprocess_env(amplifier_bin: str) -> dict[str, str]:
    """Environment for the `amplifier` subprocess.

    design-converge.yaml's OWN bash steps invoke a *bare* ``amplifier tool
    invoke ...`` (to call design_lints/design_ledger/design_controller/
    render) -- those NESTED invocations must resolve `amplifier` on PATH
    inside THIS subprocess's environment, not via the absolute path we used
    to launch the outer call. Prepend the resolved binary's directory so
    those nested calls succeed regardless of the parent process's own PATH.
    """
    env = os.environ.copy()
    bin_dir = str(pathlib.Path(amplifier_bin).resolve().parent)
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    return env


def _parse_cli_json(stdout: str) -> dict[str, Any]:
    """Extract the trailing ``--output json`` envelope and unwrap `result`.

    `result` is a Python repr string (single-quoted dict, True/False/None),
    NOT JSON -- confirmed against the live CLI:

        {"status": "success", "tool": "recipes",
         "result": "{'status': 'paused_for_approval', 'session_id': ..., "
                    "'stage_name': 'authorize-aps', ...}"}

    Parsed with ``ast.literal_eval``, never ``json.loads``, on that field.
    """
    match = _ENVELOPE_RE.search(stdout)
    if not match:
        raise RuntimeError(
            "no `--output json` envelope found in CLI stdout; tail:\n"
            + stdout[-1200:]
        )
    envelope = json.loads(match.group(0))
    if envelope.get("status") == "error":
        raise RuntimeError(
            f"amplifier tool invoke recipes failed: {envelope.get('result') or envelope}"
        )
    raw_result = envelope.get("result")
    if isinstance(raw_result, dict):
        return raw_result
    if isinstance(raw_result, str):
        try:
            parsed = ast.literal_eval(raw_result)
        except Exception as exc:
            raise RuntimeError(
                f"failed to ast.literal_eval CLI result repr: {exc}\n"
                f"raw: {raw_result[:1200]!r}"
            ) from exc
        return parsed if isinstance(parsed, dict) else {"_raw": parsed}
    return {"_raw": raw_result}


async def _run_cli(
    args: list[str],
    *,
    cwd: pathlib.Path,
    env: dict[str, str],
    hook: WebStreamingHook,
    timeout: float,
    stream_source: str | None = None,
) -> dict[str, Any]:
    """Run one ``amplifier tool invoke recipes <args>`` call; cwd=cwd.

    When `stream_source` is given, every stdout/stderr line is forwarded to
    the WS log live via ``hook.display`` as it arrives -- used for the long
    `resume` call so the user watches the real maker/critic/planner agents
    work (e.g. "[design-loop-design-maker] Thinking...") rather than a
    spinner. Always captures full stdout to parse the trailing JSON
    envelope once the process exits.

    Cancellable and time-bounded: on timeout or an external
    ``asyncio.CancelledError`` (a WS "cancel" message), the subprocess is
    killed rather than left running -- this is real, paid work; a
    cancelled WS request must not keep spending tokens in the background.
    """
    amplifier_bin = _resolve_amplifier_bin()
    cmd = [
        amplifier_bin,
        "tool",
        "invoke",
        "recipes",
        *args,
        "--bundle",
        str(_BUNDLE_ROOT),
        "--output",
        "json",
    ]
    logger.info(
        "real_runner subprocess: %s (cwd=%s, timeout=%.0fs)",
        " ".join(cmd),
        cwd,
        timeout,
    )

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_lines: list[str] = []

    async def _pump(
        stream: asyncio.StreamReader | None, *, capture: bool, label: str
    ) -> None:
        if stream is None:
            return
        while True:
            raw = await stream.readline()
            if not raw:
                break
            text = raw.decode("utf-8", errors="replace").rstrip("\n")
            if capture:
                stdout_lines.append(text)
            if stream_source and text.strip():
                await hook.display(text, source=label)

    try:
        await asyncio.wait_for(
            asyncio.gather(
                _pump(proc.stdout, capture=True, label=stream_source or "recipe"),
                _pump(
                    proc.stderr,
                    capture=False,
                    label=f"{stream_source or 'recipe'}-stderr",
                ),
                proc.wait(),
            ),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, asyncio.CancelledError):
        proc.kill()
        with contextlib.suppress(Exception):
            await proc.wait()
        raise

    stdout_text = "\n".join(stdout_lines)
    returncode = proc.returncode if proc.returncode is not None else -1
    if returncode != 0:
        raise RuntimeError(
            f"`amplifier tool invoke recipes {' '.join(args)}` exited "
            f"{returncode}.\nstdout tail:\n{stdout_text[-1200:]}"
        )
    return _parse_cli_json(stdout_text)


def _apply_context_overrides(
    recipe_context: dict[str, Any], options: dict[str, Any] | None
) -> None:
    """Apply `options` overrides onto `recipe_context`, in place.

    Only known APS knobs (task_class/bar/floors/budget/epsilon/k) are
    forwarded -- app-level UI options (variant/focus/context/audience/
    compare_url) are NOT recipe context and are handled separately by the
    caller when building the Results payload. Never lets an override touch
    the keys derived from this run's own identity.
    """
    if not options:
        return
    allowed = set(_DEFAULT_RECIPE_CONTEXT) | {"task_class"}
    for key, value in options.items():
        if key in _PROTECTED_CONTEXT_KEYS or key not in allowed:
            continue
        if key in _NUMERIC_CONTEXT_KEYS:
            try:
                value = int(value)
            except (TypeError, ValueError):
                logger.warning("Ignoring non-numeric override for %s: %r", key, value)
                continue
        recipe_context[key] = value


def _read_json(path: pathlib.Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _sanitize_records(records: Any) -> list[dict[str, Any]]:
    """Defensive normalisation of REAL ledger records before handing them to
    build_result_payload, which assumes the shape dry_runner's synthetic
    fixtures always have. Never fabricates data -- only drops entries whose
    shape build_result_payload can't safely interpret (e.g. a fix_batch
    item that's a bare string rather than a {criterion, issue, fix} dict),
    so slightly messier real agent-authored ledger data can't crash the
    Results screen.
    """
    if not isinstance(records, list):
        return []
    out: list[dict[str, Any]] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        rec = dict(rec)
        fb = rec.get("fix_batch")
        rec["fix_batch"] = (
            [f for f in fb if isinstance(f, dict) and f.get("criterion")]
            if isinstance(fb, list)
            else []
        )
        out.append(rec)
    return out


async def _build_result_from_work_dir(
    run_id: str,
    out_dir: pathlib.Path,
    *,
    kind: str,
    source: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Build the app result by READING the recipe's own outputs on disk.

    Never re-renders (the recipe's FINALIZE stage already wrote
    report.html/upgraded.html/baseline.html via the same render() dry_runner
    uses) and never fabricates a result -- a missing gate.json/report.html
    is treated as a failed run, matching the recipe's own fail-closed
    convention (dlx.py's own `gateout()` defaults action to "ESCALATE" and
    reason to "gate_unavailable" when the gate tool itself is unreachable).
    """
    gate = _read_json(out_dir / "gate.json") or {}
    best_record = _read_json(out_dir / "best_record.json") or {}
    all_records = _read_json(out_dir / "all_records.json") or []
    verdict = _read_json(out_dir / "verdict.json") or {}
    render_two_info = _read_json(out_dir / "render_two.json") or {}

    report_path = out_dir / "report.html"
    if not report_path.exists():
        raise RuntimeError(
            f"recipe finished but no report.html was written to {out_dir} "
            "-- treating as a failed run, not a fabricated result"
        )
    if not (out_dir / "gate.json").exists() or not (out_dir / "best_record.json").exists():
        raise RuntimeError(
            f"recipe finished but expected ledger files (gate.json / "
            f"best_record.json) are missing under {out_dir}"
        )
    if isinstance(render_two_info, dict) and render_two_info.get("warning"):
        logger.warning(
            "run %s: dlx.py render_two reported a warning: %s",
            run_id,
            render_two_info["warning"],
        )

    # Fail-closed defaults mirror dlx.py's own gateout(): action=ESCALATE,
    # reason=gate_unavailable, if the gate tool itself never ran.
    action = gate.get("action") or "ESCALATE"
    converged = action == "DONE"
    reason = gate.get("reason") or "gate_unavailable"

    champ_scores = best_record.get("scores") if isinstance(best_record, dict) else None
    total = verdict.get("total") if isinstance(verdict, dict) else None
    if not isinstance(total, int):
        flat = champ_scores if isinstance(champ_scores, dict) else {}
        if isinstance(flat.get("scores"), dict):
            flat = flat["scores"]
        total = sum(v for v in flat.values() if isinstance(v, int)) if flat else 0

    records_list = all_records if isinstance(all_records, list) and all_records else (
        [best_record] if best_record else []
    )
    state = {
        "records": _sanitize_records(records_list),
        "gate": gate,
        "champion": {
            "scores": champ_scores or {},
            "total": total,
            "artifact_ref": best_record.get("artifact_ref", str(out_dir / "best.html")),
        },
        "converged": converged,
    }

    from .audit import run_audit
    from .results import build_result_payload

    ctx = options.get("context", "") if options else ""
    aud = options.get("audience", "") if options else ""
    html_text = None
    if kind == "html" and pathlib.Path(source).exists():
        try:
            html_text = pathlib.Path(source).read_text(encoding="utf-8")
        except Exception:
            html_text = None
    audit = await run_audit(
        kind=kind, html=html_text, url=(source if kind == "url" else None)
    )
    payload = build_result_payload(state, context=ctx, audience=aud, audit=audit)

    cmp_url = options.get("compare_url", "") if options else ""
    if cmp_url:
        their = await run_audit(kind="url", url=cmp_url)
        payload["benchmark"] = {
            "url": cmp_url,
            "available": bool(their.get("available")),
            "you": audit.get("summary", {}) if audit.get("available") else {},
            "them": their.get("summary", {}),
            "you_findings": audit.get("findings", []) if audit.get("available") else [],
            "them_findings": their.get("findings", []),
            "note": "Objective ground-truth checks only -- subjective scoring needs the full critique.",
        }

    if html_text:
        try:
            from .annotate import annotate_html

            (out_dir / "annotated.html").write_text(
                annotate_html(html_text), encoding="utf-8"
            )
            payload["has_annotated"] = True
        except Exception:
            payload["has_annotated"] = False

    return {
        "total": total,
        "converged": converged,
        "reason": reason,
        "variant": "converged" if converged else "escalated",
        "payload": payload,
    }


async def run_real(
    run_id: str,
    out_dir: pathlib.Path,
    hook: WebStreamingHook,
    *,
    kind: str,
    source: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute recipes/design-converge.yaml as a real `amplifier` CLI
    subprocess, with cwd=out_dir for every call (see module docstring for
    why that's required). Returns a dict with the keys ws_handler.py's
    `_run_start` reads: total, converged, reason, variant, payload.

    `kind`/`source` (read by ws_handler from the run's meta.json) are
    forwarded into the recipe context -- `source` is a filesystem path for
    image/html inputs, or the raw URL/prompt text otherwise (the recipe's
    own INIT stage re-classifies from `source` itself; `kind` is passed
    through mainly for observability/debugging, not because the recipe
    templates it).
    """
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_kind = kind or _classify_fallback(source)
    options = options or {}

    recipe_context = dict(_DEFAULT_RECIPE_CONTEXT)
    recipe_context.update(
        {
            "source": source,
            "kind": resolved_kind,
            "work_dir": str(out_dir),
            "bundle_ref": str(_BUNDLE_ROOT),
            "run_id": run_id,
        }
    )
    _apply_context_overrides(recipe_context, options)

    amplifier_bin = _resolve_amplifier_bin()
    env = _subprocess_env(amplifier_bin)

    try:
        await hook.display(
            f"Loading design-converge recipe (work_dir={out_dir}) ...", source="loop"
        )
        await hook.tool_pre(
            "recipes", {"operation": "execute", "recipe": "design-converge.yaml"}
        )
        output = await _run_cli(
            [
                "operation=execute",
                f"recipe_path={_RECIPE_PATH}",
                f"context={json.dumps(recipe_context)}",
            ],
            cwd=out_dir,
            env=env,
            hook=hook,
            timeout=_SHORT_TIMEOUT_S,
        )
        await hook.tool_post(
            "recipes", success=True, summary=str(output.get("status", "started"))
        )

        guard = 0
        while (
            isinstance(output, dict)
            and output.get("status") == "paused_for_approval"
            and guard < _MAX_APPROVAL_ROUNDS
        ):
            guard += 1
            session_id = output.get("session_id")
            stage_name = output.get("stage_name")
            if not session_id or not stage_name:
                raise RuntimeError(
                    f"recipe paused for approval but response is missing "
                    f"session_id/stage_name: {output!r}"
                )

            await hook.display(
                f"Auto-approving APS gate '{stage_name}' (headless)", source="gate"
            )
            await hook.tool_pre(
                "recipes",
                {
                    "operation": "approve",
                    "session_id": session_id,
                    "stage_name": stage_name,
                },
            )
            await _run_cli(
                [
                    "operation=approve",
                    f"session_id={session_id}",
                    f"stage_name={stage_name}",
                    "message=auto-approved by design-loop web app",
                ],
                cwd=out_dir,
                env=env,
                hook=hook,
                timeout=_SHORT_TIMEOUT_S,
            )
            await hook.tool_post(
                "recipes", success=True, summary=f"approved '{stage_name}'"
            )

            await hook.display(
                "Resuming: running the governed convergence loop "
                "(maker / critic / planner agents)...",
                source="loop",
            )
            await hook.tool_pre("recipes", {"operation": "resume", "session_id": session_id})
            output = await _run_cli(
                ["operation=resume", f"session_id={session_id}"],
                cwd=out_dir,
                env=env,
                hook=hook,
                timeout=_RESUME_TIMEOUT_S,
                stream_source="agent",
            )
            await hook.tool_post(
                "recipes", success=True, summary=str(output.get("status", "resumed"))
            )

        if isinstance(output, dict) and output.get("status") == "paused_for_approval":
            raise RuntimeError(
                f"recipe still paused for approval after {guard} auto-approve "
                f"attempts: {output!r}"
            )

        await hook.display("Rendering report...", source="loop")
        result = await _build_result_from_work_dir(
            run_id, out_dir, kind=resolved_kind, source=source, options=options
        )
        await hook.display(
            f"Done: champion {result['total']}/32 ({result['reason']}).", source="gate"
        )
        return result
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        await hook.display(f"ERROR: {exc}", source="loop", level="error")
        raise
