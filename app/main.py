"""FastAPI entry point for the Design Loop web UI.

Mirrors amplifier-app-bundlewizard-web/src/app_bundlewizard_web/main.py's
shape: an @asynccontextmanager lifespan, a WebSocket endpoint, a StaticFiles
mount for generated artifacts, and a small REST surface -- scaled down to
this app's job (upload an image / paste a URL / paste or upload HTML, stream
a live transaction log, land in-app on the generated report.html).
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, UploadFile, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from amplifier_module_tool_render_report.history import filter_history, read_history

from .landing import build_landing_html
from .storage import ACTIVE_RUNS, DURABLE_ROOT, safe_run_dir
from .ws_handler import handle_websocket

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Durable output root -- same location amplifier_module_tool_render_report's
# render_demo.py and the real design-converge.yaml recipe already write to,
# so runs created here interleave naturally with runs created by the CLI.
RUNS_DIR = DURABLE_ROOT / "runs"
_HISTORY_FILE = DURABLE_ROOT / "history.jsonl"

_ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_ALLOWED_HTML_EXTS = {".html", ".htm"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB


@asynccontextmanager
async def lifespan(app: Any) -> AsyncGenerator[None, None]:
    """Ensure the runs directory exists before accepting connections."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Design Loop web app ready. Runs directory: %s", RUNS_DIR)
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Design Loop Web UI",
    description="Live-streaming UI for the design-loop convergence recipe",
    version="0.1.0",
    lifespan=lifespan,
)


class SourceRequest(BaseModel):
    """Body for POST /api/source: a non-file input (URL, raw HTML, or a text prompt)."""

    kind: str
    value: str
    goal: str = ""  # optional free-text design intent (e.g. "make a version for veterinary scientists")


def _write_meta(run_dir: Path, kind: str, source: str, goal: str = "") -> None:
    """Every run directory gets a meta.json describing what kind of input it is.

    ws_handler reads this to decide how to drive the (dry or real) runner and
    what to show in the first log line, without re-guessing from disk layout.

    `goal` is an OPTIONAL free-text design intent captured from the Landing
    page (e.g. "make a version for veterinary scientists"). Empty by default
    -- an empty goal must not change any existing behavior.
    """
    (run_dir / "meta.json").write_text(
        json.dumps({"kind": kind, "source": source, "goal": goal or ""}), encoding="utf-8"
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "runs_dir": str(RUNS_DIR)}


def _dry_mode() -> bool:
    import os

    return os.environ.get("DESIGN_LOOP_DRY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


@app.get("/api/preflight")
async def api_preflight() -> JSONResponse:
    """Report which backend a run will use, so the UI can label the mode and so
    a user opting into live critique (DESIGN_LOOP_DRY=0) can see whether the
    CLI used by the runner is present. This does not validate provider credentials.

    - dry_mode: scripted zero-cost transcript (still runs the REAL deterministic
      ground-truth audit on the actual page).
    - cli_available: whether the runner can locate the Amplifier executable.
    - foundation_installed: legacy informational field for the app interpreter.
    """
    import importlib.util

    dry = _dry_mode()
    foundation = importlib.util.find_spec("amplifier_foundation") is not None
    from .real_runner import _resolve_amplifier_bin

    try:
        _resolve_amplifier_bin()
        cli_available = True
    except RuntimeError:
        cli_available = False
    if dry:
        message = "DRY mode: scripted transcript, zero cost. Ground-truth audit is real."
    elif cli_available:
        message = "LIVE mode: Amplifier CLI found. Runs use its provider configuration and spend tokens."
    else:
        message = (
            "LIVE mode requested but the Amplifier CLI wasn't found. "
            "Install amplifier or set DESIGN_LOOP_DRY=1."
        )
    return JSONResponse(
        {
            "dry_mode": dry,
            "foundation_installed": foundation,
            "cli_available": cli_available,
            "real_available": (not dry) and cli_available,
            "mode": "dry" if dry else ("live" if cli_available else "live-unavailable"),
            "message": message,
        }
    )


@app.get("/", response_class=HTMLResponse)
async def landing() -> HTMLResponse:
    return HTMLResponse(build_landing_html())


@app.post("/api/upload")
async def api_upload(file: UploadFile, goal: str = Form("")) -> JSONResponse:
    """Save an uploaded screenshot -- or a pasted/dropped .html file -- to its
    own per-run directory.

    Returns {"run_id": ..., "kind": ...} which the client immediately uses to
    open the WebSocket and kick off the (dry or real) design loop for that
    input. Any extension we don't recognise is treated as an image and
    coerced to .png (the historical default for this endpoint); recognised
    .html/.htm uploads are saved as-is (never coerced to .png).
    """
    raw_suffix = Path(file.filename or "upload.png").suffix.lower()
    if raw_suffix in _ALLOWED_HTML_EXTS:
        kind = "html"
        suffix = ".html"
    elif raw_suffix in _ALLOWED_IMAGE_EXTS:
        kind = "image"
        suffix = raw_suffix
    else:
        kind = "image"
        suffix = ".png"

    run_id = uuid.uuid4().hex[:12]
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    dest = run_dir / f"input{suffix}"
    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > _MAX_UPLOAD_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                return JSONResponse({"error": "file too large"}, status_code=413)
            out.write(chunk)

    _write_meta(run_dir, kind, file.filename or dest.name, goal)

    logger.info(
        "Saved upload for run %s: %s (%d bytes, kind=%s)", run_id, dest, size, kind
    )
    return JSONResponse({"run_id": run_id, "kind": kind, "path": str(dest)})


@app.post("/api/source")
async def api_source(body: SourceRequest) -> JSONResponse:
    """Create a run from a non-file input: a URL to fetch, raw HTML pasted by
    the user, or a free-text design brief ("prompt").

    Writes the appropriate seed file for the (future) real recipe run plus
    meta.json, and returns {"run_id": ..., "kind": ...} -- same shape as
    /api/upload -- so the client can immediately open the WebSocket.
    """
    kind = (body.kind or "").strip().lower()
    value = body.value or ""
    if kind not in ("url", "html", "prompt"):
        return JSONResponse({"error": f"unsupported kind: {kind!r}"}, status_code=400)
    if not value.strip():
        return JSONResponse({"error": "value is required"}, status_code=400)

    run_id = uuid.uuid4().hex[:12]
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if kind == "url":
        (run_dir / "source.txt").write_text(value, encoding="utf-8")
    elif kind == "html":
        (run_dir / "input.html").write_text(value, encoding="utf-8")
    else:  # prompt
        (run_dir / "source_brief.txt").write_text(value, encoding="utf-8")

    _write_meta(run_dir, kind, value, body.goal)

    logger.info("Created run %s from %s source", run_id, kind)
    return JSONResponse({"run_id": run_id, "kind": kind})


def _safe_run_dir(run_id: str) -> Path | None:
    """Resolve run_id -> run dir, refusing anything that escapes RUNS_DIR
    (path-traversal guard) or isn't a plain run token."""
    return safe_run_dir(RUNS_DIR, run_id)


def _run_urls(run_id: str, run_dir: Path) -> dict[str, Any]:
    """Which artifacts actually exist on disk for this run."""
    def _u(name: str) -> str | None:
        artifact = run_dir / name
        return f"/runs/{run_id}/{name}" if artifact.is_file() and not artifact.is_symlink() else None

    return {
        "report_url": _u("report.html"),
        "upgraded_url": _u("upgraded.html"),
        "baseline_url": _u("baseline.html"),
        "annotated_url": _u("annotated.html"),
        "result_url": _u("result.json"),
    }


@app.get("/api/history")
async def api_history() -> JSONResponse:
    """Return the last <=50 durable runs from history.jsonl, newest first,
    enriched with input kind/goal and which artifacts exist so the client can
    reopen, link to, or delete each run."""
    entries: list[dict[str, Any]] = []
    if _HISTORY_FILE.exists():
        lines = read_history(_HISTORY_FILE)
        for line in lines[-50:]:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            run_id = obj.get("run_id", "")
            run_dir = _safe_run_dir(run_id)
            if run_dir is None:
                continue
            kind = goal = ""
            if run_dir and (run_dir / "meta.json").exists():
                try:
                    m = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
                    kind = m.get("kind", "")
                    goal = m.get("goal", "") or m.get("context", "")
                except Exception:
                    pass
            entry = {
                "run_id": run_id,
                "ts": obj.get("ts", ""),
                "task_class": obj.get("task_class", ""),
                "total": obj.get("total"),
                "converged": bool(obj.get("converged", False)),
                "reason": obj.get("reason", ""),
                "kind": kind,
                "goal": goal,
                "report_url": None,
            }
            if run_dir and run_dir.exists():
                entry.update(_run_urls(run_id, run_dir))
            entries.append(entry)
    entries.reverse()  # newest first
    return JSONResponse({"entries": entries})


@app.get("/api/run/{run_id}")
async def api_run(run_id: str) -> JSONResponse:
    """Return a past run's saved result snapshot so it can be reopened in-app.

    Falls back to a minimal payload (just the artifact links) for older runs
    that predate result.json.
    """
    run_dir = _safe_run_dir(run_id)
    if run_dir is None or not run_dir.is_dir():
        return JSONResponse({"error": "not found"}, status_code=404)
    result_path = run_dir / "result.json"
    if result_path.exists():
        try:
            msg = json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(msg, dict) and isinstance(msg.get("payload"), dict):
                msg.update(type="result", run_id=run_id)
                msg.update(_run_urls(run_id, run_dir))
                return JSONResponse(msg)
        except Exception:
            pass
    # Fallback: synthesize from whatever artifacts exist.
    msg: dict[str, Any] = {"type": "result", "run_id": run_id, "payload": {}}
    msg.update({k: v for k, v in _run_urls(run_id, run_dir).items() if v})
    return JSONResponse(msg)


@app.delete("/api/run/{run_id}")
async def api_run_delete(run_id: str) -> JSONResponse:
    """Delete one run: remove its directory (artifacts) and drop its
    history.jsonl line(s). Scoped to RUNS_DIR only."""
    run_dir = _safe_run_dir(run_id)
    if run_dir is None:
        return JSONResponse({"error": "bad run_id"}, status_code=400)
    if run_id in ACTIVE_RUNS:
        return JSONResponse({"error": "Stop the active run before deleting it."}, status_code=409)
    removed_dir = False
    if run_dir.exists():
        try:
            shutil.rmtree(run_dir)
        except OSError:
            logger.exception("Could not delete run %s", run_id)
            return JSONResponse({"error": "Could not remove run files."}, status_code=500)
        removed_dir = True
    def keep(line: str) -> bool:
        try:
            entry = json.loads(line)
            return not isinstance(entry, dict) or entry.get("run_id") != run_id
        except ValueError:
            return True

    dropped = filter_history(_HISTORY_FILE, keep)
    logger.info("Deleted run %s (dir=%s, history lines=%d)", run_id, removed_dir, dropped)
    return JSONResponse({"ok": True, "removed_dir": removed_dir, "dropped": dropped})


@app.post("/api/run/{run_id}/rerun")
async def api_run_rerun(run_id: str) -> JSONResponse:
    """Copy only the input into a fresh run; keep earlier verdicts intact."""
    previous = _safe_run_dir(run_id)
    if previous is None or not (previous / "meta.json").is_file():
        return JSONResponse({"error": "Original input is unavailable."}, status_code=404)
    new_id = uuid.uuid4().hex[:12]
    destination = RUNS_DIR / new_id
    destination.mkdir()
    try:
        for source in previous.iterdir():
            if source.name in {"meta.json", "source.txt", "source_brief.txt"} or source.name.startswith("input."):
                if source.is_file() and not source.is_symlink():
                    shutil.copy2(source, destination / source.name)
    except OSError:
        shutil.rmtree(destination)
        raise
    return JSONResponse({"run_id": new_id})


@app.post("/api/history/clear")
async def api_history_clear() -> JSONResponse:
    """Clear the Past-verdicts index (history.jsonl). Non-destructive to run
    directories/artifacts -- use DELETE /api/run/{id} to remove those."""
    n = filter_history(_HISTORY_FILE, lambda line: False)
    return JSONResponse({"ok": True, "cleared": n})


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await handle_websocket(websocket, RUNS_DIR)


# Serve generated report/upgraded/baseline HTML (and any run-local assets)
# directly from disk. Scoped to RUNS_DIR only -- mounted LAST so /, /api/*,
# and /ws all take priority over this catch-all.
RUNS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")
