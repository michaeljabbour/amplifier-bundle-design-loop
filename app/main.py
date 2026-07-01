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
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .landing import build_landing_html
from .ws_handler import handle_websocket

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Durable output root -- same location amplifier_module_tool_render_report's
# render_demo.py and the real design-converge.yaml recipe already write to,
# so runs created here interleave naturally with runs created by the CLI.
DURABLE_ROOT = Path.home() / "Downloads" / "design-loop"
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


def _write_meta(run_dir: Path, kind: str, source: str) -> None:
    """Every run directory gets a meta.json describing what kind of input it is.

    ws_handler reads this to decide how to drive the (dry or real) runner and
    what to show in the first log line, without re-guessing from disk layout.
    """
    (run_dir / "meta.json").write_text(
        json.dumps({"kind": kind, "source": source}), encoding="utf-8"
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
    a user opting into the real critique (DESIGN_LOOP_DRY=0) gets a clear signal
    up front instead of a mid-run import error.

    - dry_mode: scripted zero-cost transcript (still runs the REAL deterministic
      ground-truth audit on the actual page).
    - foundation_installed: whether `amplifier_foundation` can be imported (the
      real subjective critic path).
    """
    import importlib.util

    dry = _dry_mode()
    foundation = importlib.util.find_spec("amplifier_foundation") is not None
    if dry:
        message = "DRY mode: scripted transcript, zero cost. Ground-truth audit is real."
    elif foundation:
        message = "LIVE mode: real critique via amplifier_foundation (spends tokens)."
    else:
        message = (
            "LIVE mode requested but amplifier_foundation isn't installed -- runs "
            "will error. Install it (see app/real_runner.py) or set DESIGN_LOOP_DRY=1."
        )
    return JSONResponse(
        {
            "dry_mode": dry,
            "foundation_installed": foundation,
            "real_available": (not dry) and foundation,
            "mode": "dry" if dry else ("live" if foundation else "live-unavailable"),
            "message": message,
        }
    )


@app.get("/", response_class=HTMLResponse)
async def landing() -> HTMLResponse:
    return HTMLResponse(build_landing_html())


@app.post("/api/upload")
async def api_upload(file: UploadFile) -> JSONResponse:
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

    _write_meta(run_dir, kind, file.filename or dest.name)

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

    _write_meta(run_dir, kind, value)

    logger.info("Created run %s from %s source", run_id, kind)
    return JSONResponse({"run_id": run_id, "kind": kind})


@app.get("/api/history")
async def api_history() -> JSONResponse:
    """Return the last <=20 durable runs from history.jsonl, newest first.

    Each entry mirrors what amplifier_module_tool_render_report.template.render()
    appends: run_id, ts, task_class, total, converged, reason -- plus a
    report_url this app can link to directly (served via the /runs mount).
    """
    entries: list[dict[str, Any]] = []
    if _HISTORY_FILE.exists():
        lines = _HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        for line in lines[-20:]:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            run_id = obj.get("run_id", "")
            entries.append(
                {
                    "run_id": run_id,
                    "ts": obj.get("ts", ""),
                    "task_class": obj.get("task_class", ""),
                    "total": obj.get("total"),
                    "converged": bool(obj.get("converged", False)),
                    "reason": obj.get("reason", ""),
                    "report_url": f"/runs/{run_id}/report.html" if run_id else "",
                }
            )
    entries.reverse()  # newest first
    return JSONResponse({"entries": entries})


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await handle_websocket(websocket, RUNS_DIR)


# Serve generated report/upgraded/baseline HTML (and any run-local assets)
# directly from disk. Scoped to RUNS_DIR only -- mounted LAST so /, /api/*,
# and /ws all take priority over this catch-all.
RUNS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")
