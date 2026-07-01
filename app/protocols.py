"""Protocol boundary: bridges the design-loop run to WebSocket JSON messages.

Mirrors amplifier-app-bundlewizard-web/src/app_bundlewizard_web/protocols.py's
WebStreamingHook: a thin wrapper around `websocket.send_json` that always emits
the same wire shape ({"type": "stream_event", "event_type": ..., "data": ...})
regardless of whether the event originated from a scripted dry-mode sequence
or a real kernel hook callback.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MSG_STREAM_EVENT = "stream_event"
MSG_RESULT = "result"
MSG_ERROR = "error"

# Kernel events we forward when running the REAL backend (approach a).
# Same vocabulary as amplifier-app-bundlewizard-web's STREAMING_EVENTS so the
# same frontend row-mapping logic (tool:pre / tool:post / display) applies
# whether the transcript came from a live kernel session or the dry script.
STREAMING_EVENTS = (
    "content_block:start",
    "content_block:end",
    "tool:pre",
    "tool:post",
    "llm:response",
    "display",
)


class WebStreamingHook:
    """Bridges event data to WebSocket JSON messages (dry or real source)."""

    def __init__(self, websocket: Any) -> None:
        self._websocket = websocket
        self._active = True

    async def on_event(self, event_type: str, data: Any) -> None:
        """Forward one streaming event over the WebSocket (no-op once deactivated)."""
        if not self._active:
            return
        try:
            await self._websocket.send_json(
                {
                    "type": MSG_STREAM_EVENT,
                    "event_type": event_type,
                    "data": self._make_serializable(data),
                }
            )
        except Exception:
            logger.debug("Failed to forward %s event over WebSocket", event_type)

    async def display(self, message: str, *, source: str = "loop", level: str = "info") -> None:
        """Convenience wrapper for a MAKER/LINTS/CRITIC/GATE narrative line."""
        await self.on_event(
            "display", {"message": message, "level": level, "metadata": {"source": source}}
        )

    async def tool_pre(self, tool_name: str, tool_input: dict[str, Any] | None = None) -> None:
        await self.on_event("tool:pre", {"tool_name": tool_name, "tool_input": tool_input or {}})

    async def tool_post(self, tool_name: str, *, success: bool = True, summary: str = "") -> None:
        await self.on_event(
            "tool:post",
            {"tool_name": tool_name, "tool_response": {"success": success, "summary": summary}},
        )

    def deactivate(self) -> None:
        """Stop forwarding events. Idempotent."""
        self._active = False

    @staticmethod
    def _make_serializable(data: Any) -> Any:
        """Best-effort conversion of event data to JSON-safe types (same as bundlewizard)."""
        if data is None or isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, dict):
            return {k: WebStreamingHook._make_serializable(v) for k, v in data.items()}
        if isinstance(data, (list, tuple)):
            return [WebStreamingHook._make_serializable(v) for v in data]
        if hasattr(data, "model_dump"):
            return data.model_dump()
        if hasattr(data, "__dict__"):
            return {
                k: WebStreamingHook._make_serializable(v)
                for k, v in data.__dict__.items()
                if not k.startswith("_")
            }
        return str(data)
