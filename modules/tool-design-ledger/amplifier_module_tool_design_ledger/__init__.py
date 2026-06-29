"""Amplifier tool module: durable append-only cross-run design ledger.

Persists one JSONL file per task_class at a configurable ledger_dir.
Deterministic, no LLM, stdlib-only (json, pathlib, datetime).
amplifier_core (ToolResult) is a peer dep — not listed in pyproject.toml.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from amplifier_core import ToolResult

logger = logging.getLogger(__name__)

_SCORE_DIMS: tuple[str, ...] = (
    "clarity", "elegance", "restraint", "empowerment",
    "agency", "ease", "character", "point",
)
_REQUIRED_FIELDS: tuple[str, ...] = ("run_id", "task_class", "pass", "outcome")


class DesignLedgerTool:
    """Durable, append-only, cross-run capital account for the design harness.

    One JSONL file per task_class, stored at ledger_dir.
    Monotonic entry_id per file; ts auto-filled (ISO-8601 UTC) when absent.
    Never crashes: bad input surfaces as ToolResult(success=False, error={...}).

    Operations
    ----------
    append
        Append a scored design record.  Required record fields: run_id,
        task_class, pass, outcome.  reject_reason is required whenever
        outcome != "accepted".  scores may be null.
        Returns {entry_id, path}.

    query
        Return records matching task_class (required) plus optional filters
        signature, rubric_version, outcome.

    best
        Return the ACCEPTED record for task_class with the highest
        (worst_dim_score, total) key — maximin over the 8 score dimensions,
        tiebroken by sum.  Returns null when no accepted+scored records exist.

    dead_fixes
        Return the deduplicated list of strategy_tag / fix_id values drawn
        from the fix_batch of non-accepted records for task_class + signature.
    """

    def __init__(self, ledger_dir: Path) -> None:
        self._ledger_dir = ledger_dir
        self._ledger_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ protocol

    @property
    def name(self) -> str:
        return "design_ledger"

    @property
    def description(self) -> str:
        return (
            "Durable append-only cross-run design ledger persisted as JSONL. "
            "op=append: persist a record (required: run_id, task_class, pass, outcome; "
            "reject_reason required when outcome != 'accepted'; scores may be null). "
            "op=query: filter records by task_class + optional signature/rubric_version/outcome. "
            "op=best: return the accepted record with highest (worst_dim_score, total) for task_class. "
            "op=dead_fixes: return strategy_tags/fix_ids of non-accepted records for task_class+signature. "
            "Never raises; all failures surface as success=False with error dict."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "op": {
                    "type": "string",
                    "enum": ["append", "query", "best", "dead_fixes"],
                    "description": "Operation to perform.",
                },
                "record": {
                    "type": "object",
                    "description": (
                        "Record to append (op=append). "
                        "Required fields: run_id, task_class, pass, outcome. "
                        "reject_reason required when outcome != 'accepted'. "
                        "scores may be null."
                    ),
                },
                "task_class": {
                    "type": "string",
                    "description": "Task class identifier (required for query, best, dead_fixes).",
                },
                "signature": {
                    "type": "string",
                    "description": (
                        "Design signature filter "
                        "(optional for query; required for dead_fixes)."
                    ),
                },
                "rubric_version": {
                    "type": "string",
                    "description": "Rubric version filter (optional for query and best).",
                },
                "outcome": {
                    "type": "string",
                    "description": "Outcome filter (optional for query).",
                },
            },
            "required": ["op"],
        }

    # ------------------------------------------------------------------ internal helpers

    def _ledger_path(self, task_class: str) -> Path:
        return self._ledger_dir / f"{task_class}.jsonl"

    def _read_records(self, task_class: str) -> list[dict]:
        """Return all stored records for task_class; empty list if file absent."""
        path = self._ledger_path(task_class)
        if not path.exists():
            return []
        records: list[dict] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _count_lines(self, path: Path) -> int:
        """Count non-empty lines in a JSONL file; 0 if absent."""
        if not path.exists():
            return 0
        count = 0
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    count += 1
        return count

    # ------------------------------------------------------------------ operations

    def _op_append(self, record: dict | None) -> ToolResult:
        """Validate and append one record; assign monotonic entry_id."""
        if record is None:
            return ToolResult(
                success=False,
                error={"message": "op=append requires a 'record' object"},
            )

        # Validate required fields
        missing = [f for f in _REQUIRED_FIELDS if f not in record]
        if missing:
            return ToolResult(
                success=False,
                error={"message": f"record is missing required fields: {missing}"},
            )

        task_class = record.get("task_class")
        if not isinstance(task_class, str) or not task_class:
            return ToolResult(
                success=False,
                error={"message": "'task_class' must be a non-empty string"},
            )

        outcome = record.get("outcome")
        if outcome != "accepted" and "reject_reason" not in record:
            return ToolResult(
                success=False,
                error={
                    "message": (
                        f"'reject_reason' is required when outcome={outcome!r}. "
                        "Nothing was written."
                    )
                },
            )

        path = self._ledger_path(task_class)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Monotonic entry_id = number of existing valid lines
        entry_id = self._count_lines(path)

        # Build stored record (shallow copy; never mutate caller's dict)
        stored = dict(record)
        stored.pop("entry_id", None)   # discard any caller-supplied entry_id
        stored["entry_id"] = entry_id
        if "ts" not in stored:
            stored["ts"] = datetime.now(timezone.utc).isoformat()

        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(stored, ensure_ascii=False) + "\n")

        return ToolResult(success=True, output={"entry_id": entry_id, "path": str(path)})

    def _op_query(
        self,
        task_class: str | None,
        signature: str | None,
        rubric_version: str | None,
        outcome: str | None,
    ) -> ToolResult:
        """Return records matching task_class plus optional filters."""
        if not task_class:
            return ToolResult(
                success=False,
                error={"message": "op=query requires 'task_class'"},
            )

        records = self._read_records(task_class)

        if signature is not None:
            records = [r for r in records if r.get("signature") == signature]
        if rubric_version is not None:
            records = [r for r in records if r.get("rubric_version") == rubric_version]
        if outcome is not None:
            records = [r for r in records if r.get("outcome") == outcome]

        return ToolResult(success=True, output=records)

    def _op_best(self, task_class: str | None, rubric_version: str | None) -> ToolResult:
        """Return the accepted record with the highest (worst_dim_score, total)."""
        if not task_class:
            return ToolResult(
                success=False,
                error={"message": "op=best requires 'task_class'"},
            )

        records = self._read_records(task_class)

        # Filter: accepted only
        accepted = [r for r in records if r.get("outcome") == "accepted"]

        if rubric_version is not None:
            accepted = [r for r in accepted if r.get("rubric_version") == rubric_version]

        # Filter: must have non-null scores dict
        scored = [r for r in accepted if isinstance(r.get("scores"), dict)]

        if not scored:
            return ToolResult(success=True, output=None)

        def _score_key(r: dict) -> tuple[float, float]:
            s = r["scores"]
            vals = [float(s.get(dim, 0)) for dim in _SCORE_DIMS]
            return (min(vals), sum(vals))

        best = max(scored, key=_score_key)
        return ToolResult(success=True, output=best)

    def _op_dead_fixes(self, task_class: str | None, signature: str | None) -> ToolResult:
        """Return deduplicated strategy_tags / fix_ids of non-accepted records."""
        if not task_class:
            return ToolResult(
                success=False,
                error={"message": "op=dead_fixes requires 'task_class'"},
            )
        if signature is None:
            return ToolResult(
                success=False,
                error={"message": "op=dead_fixes requires 'signature'"},
            )

        records = self._read_records(task_class)
        failed = [
            r for r in records
            if r.get("outcome") != "accepted" and r.get("signature") == signature
        ]

        dead: list[str] = []
        for r in failed:
            for fix in r.get("fix_batch") or []:
                if "strategy_tag" in fix:
                    dead.append(fix["strategy_tag"])
                if "fix_id" in fix:
                    dead.append(fix["fix_id"])

        # Deduplicate while preserving insertion order
        seen: set[str] = set()
        unique: list[str] = []
        for tag in dead:
            if tag not in seen:
                seen.add(tag)
                unique.append(tag)

        return ToolResult(success=True, output=unique)

    # ------------------------------------------------------------------ execute

    async def execute(self, input: dict[str, Any]) -> ToolResult:  # noqa: A002
        """Dispatch an op to the appropriate handler.

        Parameters
        ----------
        input:
            Dict with key ``op`` plus op-specific operands.

        Returns
        -------
        ToolResult
            success=True on success; success=False + error dict on bad input.
            Never raises.
        """
        try:
            op = input.get("op")
            if op == "append":
                return self._op_append(input.get("record"))
            if op == "query":
                return self._op_query(
                    task_class=input.get("task_class"),
                    signature=input.get("signature"),
                    rubric_version=input.get("rubric_version"),
                    outcome=input.get("outcome"),
                )
            if op == "best":
                return self._op_best(
                    task_class=input.get("task_class"),
                    rubric_version=input.get("rubric_version"),
                )
            if op == "dead_fixes":
                return self._op_dead_fixes(
                    task_class=input.get("task_class"),
                    signature=input.get("signature"),
                )
            return ToolResult(
                success=False,
                error={
                    "message": (
                        f"Unknown op={op!r}. "
                        "Must be one of: append, query, best, dead_fixes"
                    )
                },
            )
        except Exception as exc:
            logger.exception("DesignLedgerTool.execute: unexpected exception")
            return ToolResult(
                success=False,
                error={"message": f"Unexpected error: {exc}"},
            )


# ── mount (Iron Law) ─────────────────────────────────────────────────────────

async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> DesignLedgerTool:
    """Mount the design_ledger tool.

    Config
    ------
    ledger_dir : str
        Directory for JSONL ledger files.
        Defaults to ``~/.amplifier/design-ledger``.
        Always expanded with Path.expanduser().
    """
    cfg = config or {}
    ledger_dir_str: str = cfg.get("ledger_dir", "~/.amplifier/design-ledger")
    ledger_dir = Path(ledger_dir_str).expanduser()
    ledger_dir.mkdir(parents=True, exist_ok=True)

    tool = DesignLedgerTool(ledger_dir)
    await coordinator.mount("tools", tool, name=tool.name)   # Iron Law
    logger.info("Mounted tool-design-ledger at %s", ledger_dir)
    return tool
