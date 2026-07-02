"""WebSocket message handler: routes the client's {type:"start"} message to
either the DRY scripted runner or the REAL SDK-backed runner, streaming
stream_event / result / error messages back exactly like
amplifier-app-bundlewizard-web's ws_handler.py routes prompt/approval_response.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
from typing import Any

from starlette.websockets import WebSocketDisconnect

from .dry_runner import run_dry
from .protocols import WebStreamingHook

logger = logging.getLogger(__name__)


def _is_dry_mode() -> bool:
    """DRY is the default. Set DESIGN_LOOP_DRY=0 to opt into the real backend."""
    return os.environ.get("DESIGN_LOOP_DRY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _read_meta(run_dir: pathlib.Path) -> dict[str, Any]:
    """Read the run's meta.json (written by /api/upload or /api/source).

    Missing/corrupt meta is treated as an old-style image run (back-compat).
    """
    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        return {}
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        logger.warning("Failed to parse meta.json for %s", run_dir, exc_info=True)
        return {}


def _resolve_real_source(run_dir: pathlib.Path, kind: str, meta_source: str) -> str:
    """Resolve what the REAL runner should receive for `source`.

    image/html kinds resolve to an on-disk path (the recipe reads a file);
    url/prompt kinds forward the raw value captured in meta.json verbatim.
    """
    if kind == "image":
        candidates = sorted(run_dir.glob("input.*"))
        if not candidates:
            raise RuntimeError(f"no uploaded image found for run_id={run_dir.name!r}")
        return str(candidates[0])
    if kind == "html":
        html_path = run_dir / "input.html"
        if not html_path.exists():
            raise RuntimeError(f"no input.html found for run_id={run_dir.name!r}")
        return str(html_path)
    return meta_source


def _verdict_label(converged: bool, reason: str) -> str:
    """Short label describing the outcome -- the real gate `reason` when we
    have one (e.g. "bar_met", "plateau"), else a generic converged/escalated."""
    if reason:
        return reason
    return "converged" if converged else "escalated"


async def _run_start(
    websocket: Any,
    runs_dir: pathlib.Path,
    run_id: str,
    options: dict[str, Any] | None,
) -> None:
    hook = WebStreamingHook(websocket)
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    meta = _read_meta(run_dir)
    kind = meta.get("kind", "image")
    meta_source = meta.get("source", "")
    opts = options if isinstance(options, dict) else {}
    variant = opts.get("variant")
    focus = opts.get("focus")
    # Goal context: prefer the per-run option, fall back to what /api/source
    # captured on the run (so a re-run keeps the same goal).
    context = opts.get("context") or meta.get("context") or ""
    audience = opts.get("audience") or meta.get("audience") or ""
    compare_url = opts.get("compare_url") or ""
    # Optional design brief/goal captured at run-creation time (/api/upload or
    # /api/source), persisted in meta.json -- NOT a per-run option like
    # context/audience above. Empty by default; forwarded to the REAL runner
    # only (DRY mode ignores it, preserving existing DRY behavior exactly).
    goal = meta.get("goal", "") or ""

    try:
        if _is_dry_mode():
            result = await run_dry(
                run_id,
                run_dir,
                hook,
                kind=kind,
                source=meta_source,
                variant=variant,
                context=context,
                audience=audience,
                focus=focus,
                compare_url=compare_url,
            )
        else:
            from .real_runner import run_real

            real_source = _resolve_real_source(run_dir, kind, meta_source)
            result = await run_real(
                run_id,
                run_dir,
                hook,
                kind=kind,
                source=real_source,
                options=options,
                goal=goal,
            )

        total = result.get("total")
        converged = bool(result.get("converged", False))
        reason = result.get("reason") or ""

        await websocket.send_json(
            {
                "type": "result",
                "run_id": run_id,
                "report_url": f"/runs/{run_id}/report.html",
                "upgraded_url": f"/runs/{run_id}/upgraded.html",
                "baseline_url": f"/runs/{run_id}/baseline.html",
                "annotated_url": f"/runs/{run_id}/annotated.html",
                "total": total,
                "converged": converged,
                "verdict": _verdict_label(converged, reason),
                "variant": result.get("variant", ""),
                "payload": result.get("payload", {}),
            }
        )
    except asyncio.CancelledError:
        # Client asked to stop (or disconnected). Tell them the run was
        # cancelled -- best effort, the socket may already be gone -- then
        # re-raise so the awaiting task unwinds cleanly.
        logger.info("Run %s cancelled", run_id)
        try:
            await websocket.send_json({"type": "cancelled", "run_id": run_id})
        except Exception:
            pass
        raise
    except Exception as exc:
        logger.error("Run %s failed: %s", run_id, exc, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        hook.deactivate()


async def handle_websocket(websocket: Any, runs_dir: pathlib.Path) -> None:
    """Handle a single WebSocket connection lifecycle for one run.

    The run executes as its own asyncio task so this loop can keep receiving
    messages while it's in flight -- specifically a ``{"type": "cancel"}`` to
    stop a running analysis (rough edge #4). If the socket drops mid-run, the
    in-flight task is cancelled too, so a scripted transcript doesn't keep
    sleeping after the client is gone.
    """
    await websocket.accept()
    run_task: asyncio.Task | None = None
    try:
        while True:
            msg: dict[str, Any] = await websocket.receive_json()
            msg_type = msg.get("type")
            if msg_type == "start":
                run_id = msg.get("run_id", "")
                if not run_id:
                    await websocket.send_json(
                        {"type": "error", "message": "missing run_id"}
                    )
                    continue
                if run_task is not None and not run_task.done():
                    # A new run supersedes an in-flight one on the same socket.
                    run_task.cancel()
                    try:
                        await run_task
                    except (asyncio.CancelledError, Exception):
                        pass
                options = (
                    msg.get("options") if isinstance(msg.get("options"), dict) else None
                )
                run_task = asyncio.ensure_future(
                    _run_start(websocket, runs_dir, run_id, options)
                )
            elif msg_type == "cancel":
                if run_task is not None and not run_task.done():
                    run_task.cancel()
                    try:
                        await run_task
                    except (asyncio.CancelledError, Exception):
                        pass
                else:
                    # Nothing running -- acknowledge so the client can reset.
                    await websocket.send_json(
                        {"type": "cancelled", "run_id": msg.get("run_id", "")}
                    )
            else:
                logger.warning("Received unknown message type: %s", msg_type)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as exc:
        logger.warning("WebSocket handler error: %s", exc, exc_info=True)
    finally:
        if run_task is not None and not run_task.done():
            run_task.cancel()
            try:
                await run_task
            except (asyncio.CancelledError, Exception):
                pass
