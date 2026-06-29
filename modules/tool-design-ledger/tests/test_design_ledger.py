"""Tests for tool-design-ledger — TDD red → green cycle.

All tests use tmp_path as ledger_dir; no global filesystem writes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from amplifier_module_tool_design_ledger import DesignLedgerTool, mount
from amplifier_core.testing import create_test_coordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tool(tmp_path: Path) -> DesignLedgerTool:
    return DesignLedgerTool(tmp_path)


def accepted_record(run_id: str, task_class: str, **kwargs) -> dict:
    return {
        "run_id": run_id,
        "task_class": task_class,
        "pass": True,
        "outcome": "accepted",
        **kwargs,
    }


def rejected_record(run_id: str, task_class: str, reject_reason: str = "too bland", **kwargs) -> dict:
    return {
        "run_id": run_id,
        "task_class": task_class,
        "pass": False,
        "outcome": "rejected",
        "reject_reason": reject_reason,
        **kwargs,
    }


def scores(**dims) -> dict:
    """Build a scores dict with all 8 dims, defaulting to 5."""
    base = {d: 5 for d in ("clarity", "elegance", "restraint", "empowerment",
                            "agency", "ease", "character", "point")}
    base.update(dims)
    return base


# ---------------------------------------------------------------------------
# append: entry_id monotonically increments, file line count matches
# ---------------------------------------------------------------------------

async def test_append_entry_id_increments_and_file_has_n_lines(tmp_path):
    tool = make_tool(tmp_path)
    task_class = "hero-section"

    for i in range(3):
        result = await tool.execute({"op": "append", "record": accepted_record(f"run-{i}", task_class)})
        assert result.success, f"append {i} failed: {result.error}"
        assert result.output["entry_id"] == i

    ledger_file = tmp_path / f"{task_class}.jsonl"
    lines = [l for l in ledger_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 3

    # Verify each line is valid JSON and entry_ids are 0, 1, 2
    parsed = [json.loads(l) for l in lines]
    assert [r["entry_id"] for r in parsed] == [0, 1, 2]


# ---------------------------------------------------------------------------
# append: ts is auto-filled when absent; caller-supplied entry_id is ignored
# ---------------------------------------------------------------------------

async def test_append_fills_ts_and_ignores_caller_entry_id(tmp_path):
    tool = make_tool(tmp_path)
    rec = accepted_record("run-0", "hero-section", entry_id=999)  # caller sets entry_id=999
    result = await tool.execute({"op": "append", "record": rec})
    assert result.success
    assert result.output["entry_id"] == 0  # tool ignores caller's 999

    line = (tmp_path / "hero-section.jsonl").read_text(encoding="utf-8").strip()
    stored = json.loads(line)
    assert stored["entry_id"] == 0
    assert "ts" in stored and stored["ts"]  # auto-filled


async def test_append_preserves_caller_ts_when_provided(tmp_path):
    tool = make_tool(tmp_path)
    rec = accepted_record("run-0", "hero-section", ts="2024-01-01T00:00:00+00:00")
    result = await tool.execute({"op": "append", "record": rec})
    assert result.success
    line = (tmp_path / "hero-section.jsonl").read_text(encoding="utf-8").strip()
    stored = json.loads(line)
    assert stored["ts"] == "2024-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# append: reject_reason required when outcome != "accepted"
# ---------------------------------------------------------------------------

async def test_append_non_accepted_without_reject_reason_fails(tmp_path):
    tool = make_tool(tmp_path)
    rec = {
        "run_id": "run-0",
        "task_class": "hero-section",
        "pass": False,
        "outcome": "rejected",
        # NO reject_reason
    }
    result = await tool.execute({"op": "append", "record": rec})
    assert not result.success
    assert "reject_reason" in result.error["message"].lower()

    # Nothing must have been written
    assert not (tmp_path / "hero-section.jsonl").exists()


async def test_append_non_accepted_with_reject_reason_succeeds(tmp_path):
    tool = make_tool(tmp_path)
    rec = rejected_record("run-0", "hero-section", reject_reason="too bland")
    result = await tool.execute({"op": "append", "record": rec})
    assert result.success


# ---------------------------------------------------------------------------
# append: missing required fields
# ---------------------------------------------------------------------------

async def test_append_missing_required_fields_fails(tmp_path):
    tool = make_tool(tmp_path)
    # Missing 'outcome' and 'pass'
    result = await tool.execute({
        "op": "append",
        "record": {"run_id": "run-0", "task_class": "hero-section"},
    })
    assert not result.success
    assert not (tmp_path / "hero-section.jsonl").exists()


# ---------------------------------------------------------------------------
# append: records for different task_classes go to separate files
# ---------------------------------------------------------------------------

async def test_append_separate_files_per_task_class(tmp_path):
    tool = make_tool(tmp_path)
    await tool.execute({"op": "append", "record": accepted_record("r0", "hero-section")})
    await tool.execute({"op": "append", "record": accepted_record("r1", "footer")})
    await tool.execute({"op": "append", "record": accepted_record("r2", "hero-section")})

    hero_lines = (tmp_path / "hero-section.jsonl").read_text(encoding="utf-8").splitlines()
    footer_lines = (tmp_path / "footer.jsonl").read_text(encoding="utf-8").splitlines()
    assert len([l for l in hero_lines if l.strip()]) == 2
    assert len([l for l in footer_lines if l.strip()]) == 1


# ---------------------------------------------------------------------------
# query: filters by task_class, signature, outcome
# ---------------------------------------------------------------------------

async def test_query_returns_records_for_task_class(tmp_path):
    tool = make_tool(tmp_path)
    await tool.execute({"op": "append", "record": accepted_record("r0", "hero-section")})
    await tool.execute({"op": "append", "record": accepted_record("r1", "footer")})
    await tool.execute({"op": "append", "record": accepted_record("r2", "hero-section")})

    result = await tool.execute({"op": "query", "task_class": "hero-section"})
    assert result.success
    assert len(result.output) == 2
    assert all(r["task_class"] == "hero-section" for r in result.output)


async def test_query_filters_by_signature(tmp_path):
    tool = make_tool(tmp_path)
    await tool.execute({"op": "append", "record": accepted_record("r0", "hero", signature="sig-a")})
    await tool.execute({"op": "append", "record": accepted_record("r1", "hero", signature="sig-b")})
    await tool.execute({"op": "append", "record": accepted_record("r2", "hero", signature="sig-a")})

    result = await tool.execute({"op": "query", "task_class": "hero", "signature": "sig-a"})
    assert result.success
    assert len(result.output) == 2
    assert all(r["signature"] == "sig-a" for r in result.output)


async def test_query_filters_by_outcome(tmp_path):
    tool = make_tool(tmp_path)
    await tool.execute({"op": "append", "record": accepted_record("r0", "hero")})
    await tool.execute({"op": "append", "record": rejected_record("r1", "hero")})
    await tool.execute({"op": "append", "record": rejected_record("r2", "hero")})

    result = await tool.execute({"op": "query", "task_class": "hero", "outcome": "accepted"})
    assert result.success
    assert len(result.output) == 1
    assert result.output[0]["outcome"] == "accepted"


async def test_query_filters_by_rubric_version(tmp_path):
    tool = make_tool(tmp_path)
    await tool.execute({"op": "append", "record": accepted_record("r0", "hero", rubric_version="v1")})
    await tool.execute({"op": "append", "record": accepted_record("r1", "hero", rubric_version="v2")})

    result = await tool.execute({"op": "query", "task_class": "hero", "rubric_version": "v1"})
    assert result.success
    assert len(result.output) == 1
    assert result.output[0]["rubric_version"] == "v1"


async def test_query_missing_task_class_fails(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "query"})
    assert not result.success


async def test_query_nonexistent_task_class_returns_empty(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "query", "task_class": "no-such-class"})
    assert result.success
    assert result.output == []


# ---------------------------------------------------------------------------
# best: returns ACCEPTED record with highest (worst_dim_score, total)
# ---------------------------------------------------------------------------

async def test_best_returns_maximin_accepted_record(tmp_path):
    tool = make_tool(tmp_path)
    # Record A: all dims = 5 → worst=5, total=40
    rec_a = accepted_record("r0", "hero", scores=scores())
    # Record B: one dim = 4, rest 5 → worst=4, total=39
    rec_b = accepted_record("r1", "hero", scores=scores(point=4))

    await tool.execute({"op": "append", "record": rec_a})
    await tool.execute({"op": "append", "record": rec_b})

    result = await tool.execute({"op": "best", "task_class": "hero"})
    assert result.success
    assert result.output is not None
    assert result.output["run_id"] == "r0"  # A has higher worst_dim_score (5 > 4)


async def test_best_tiebreaks_by_total(tmp_path):
    tool = make_tool(tmp_path)
    # A: worst=5, total=41 (one dim 6, rest 5)
    rec_a = accepted_record("r0", "hero", scores=scores(clarity=6))
    # B: worst=5, total=40 (all dims 5)
    rec_b = accepted_record("r1", "hero", scores=scores())

    await tool.execute({"op": "append", "record": rec_a})
    await tool.execute({"op": "append", "record": rec_b})

    result = await tool.execute({"op": "best", "task_class": "hero"})
    assert result.success
    assert result.output["run_id"] == "r0"  # higher total wins the tiebreak


async def test_best_ignores_rejected_records(tmp_path):
    tool = make_tool(tmp_path)
    # Rejected with perfect scores — must be ignored
    rec_rejected = rejected_record("r0", "hero", scores=scores(clarity=10))
    # Accepted with mediocre scores
    rec_accepted = accepted_record("r1", "hero", scores=scores())

    await tool.execute({"op": "append", "record": rec_rejected})
    await tool.execute({"op": "append", "record": rec_accepted})

    result = await tool.execute({"op": "best", "task_class": "hero"})
    assert result.success
    assert result.output["run_id"] == "r1"  # only accepted record


async def test_best_prefers_higher_worst_over_higher_total(tmp_path):
    """A record with worst_dim=5 beats one with worst_dim=1 even if the latter has higher total."""
    tool = make_tool(tmp_path)
    # D: worst=1, total = 1 + 7*10 = 71 — high total but terrible minimum
    rec_d = accepted_record("r0", "hero", scores=scores(point=1, clarity=10, elegance=10,
                                                         restraint=10, empowerment=10,
                                                         agency=10, ease=10, character=10))
    # E: worst=5, total=40 — balanced
    rec_e = accepted_record("r1", "hero", scores=scores())

    await tool.execute({"op": "append", "record": rec_d})
    await tool.execute({"op": "append", "record": rec_e})

    result = await tool.execute({"op": "best", "task_class": "hero"})
    assert result.success
    assert result.output["run_id"] == "r1"  # E wins: worst=5 > worst=1


async def test_best_returns_null_when_no_accepted_records(tmp_path):
    tool = make_tool(tmp_path)
    await tool.execute({"op": "append", "record": rejected_record("r0", "hero", scores=scores())})
    result = await tool.execute({"op": "best", "task_class": "hero"})
    assert result.success
    assert result.output is None


async def test_best_returns_null_for_empty_ledger(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "best", "task_class": "hero"})
    assert result.success
    assert result.output is None


async def test_best_filters_by_rubric_version(tmp_path):
    tool = make_tool(tmp_path)
    await tool.execute({"op": "append", "record": accepted_record("r0", "hero",
                                                                   rubric_version="v1",
                                                                   scores=scores(clarity=9))})
    await tool.execute({"op": "append", "record": accepted_record("r1", "hero",
                                                                   rubric_version="v2",
                                                                   scores=scores())})
    result = await tool.execute({"op": "best", "task_class": "hero", "rubric_version": "v2"})
    assert result.success
    assert result.output["run_id"] == "r1"  # v2 only, even though r0 has higher clarity


async def test_best_missing_task_class_fails(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "best"})
    assert not result.success


# ---------------------------------------------------------------------------
# dead_fixes: returns strategy_tags (and fix_ids) from non-accepted records
# ---------------------------------------------------------------------------

async def test_dead_fixes_returns_strategy_tags_of_non_accepted(tmp_path):
    tool = make_tool(tmp_path)
    sig = "sig-abc"

    fix_batch = [
        {"fix_id": "f1", "strategy_tag": "add-whitespace"},
        {"fix_id": "f2", "strategy_tag": "bolder-type"},
    ]
    rec = rejected_record("r0", "hero", signature=sig, fix_batch=fix_batch)
    await tool.execute({"op": "append", "record": rec})

    result = await tool.execute({"op": "dead_fixes", "task_class": "hero", "signature": sig})
    assert result.success
    assert "add-whitespace" in result.output
    assert "bolder-type" in result.output


async def test_dead_fixes_excludes_accepted_records(tmp_path):
    """Accepted records should NOT contribute to dead_fixes."""
    tool = make_tool(tmp_path)
    sig = "sig-abc"

    # This was accepted — should not appear in dead_fixes
    good_fix_batch = [{"strategy_tag": "reduce-padding"}]
    await tool.execute({"op": "append", "record": accepted_record("r0", "hero",
                                                                   signature=sig,
                                                                   fix_batch=good_fix_batch)})

    # This was rejected — should appear
    bad_fix_batch = [{"strategy_tag": "add-animation"}]
    await tool.execute({"op": "append", "record": rejected_record("r1", "hero",
                                                                   signature=sig,
                                                                   fix_batch=bad_fix_batch)})

    result = await tool.execute({"op": "dead_fixes", "task_class": "hero", "signature": sig})
    assert result.success
    assert "add-animation" in result.output
    assert "reduce-padding" not in result.output


async def test_dead_fixes_only_matches_given_signature(tmp_path):
    """Records with a different signature must not appear in dead_fixes."""
    tool = make_tool(tmp_path)

    await tool.execute({"op": "append", "record": rejected_record(
        "r0", "hero", signature="sig-x", fix_batch=[{"strategy_tag": "wrong-sig-tag"}])})
    await tool.execute({"op": "append", "record": rejected_record(
        "r1", "hero", signature="sig-y", fix_batch=[{"strategy_tag": "correct-sig-tag"}])})

    result = await tool.execute({"op": "dead_fixes", "task_class": "hero", "signature": "sig-y"})
    assert result.success
    assert "correct-sig-tag" in result.output
    assert "wrong-sig-tag" not in result.output


async def test_dead_fixes_deduplicates(tmp_path):
    """Same strategy_tag from multiple records appears only once."""
    tool = make_tool(tmp_path)
    sig = "sig-abc"

    for i in range(3):
        await tool.execute({"op": "append", "record": rejected_record(
            f"r{i}", "hero", signature=sig, fix_batch=[{"strategy_tag": "add-whitespace"}])})

    result = await tool.execute({"op": "dead_fixes", "task_class": "hero", "signature": sig})
    assert result.success
    assert result.output.count("add-whitespace") == 1


async def test_dead_fixes_returns_empty_for_no_failures(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "dead_fixes", "task_class": "hero", "signature": "sig-x"})
    assert result.success
    assert result.output == []


async def test_dead_fixes_missing_task_class_fails(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "dead_fixes", "signature": "sig-x"})
    assert not result.success


async def test_dead_fixes_missing_signature_fails(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "dead_fixes", "task_class": "hero"})
    assert not result.success


# ---------------------------------------------------------------------------
# unknown op
# ---------------------------------------------------------------------------

async def test_unknown_op_fails(tmp_path):
    tool = make_tool(tmp_path)
    result = await tool.execute({"op": "frobnicate"})
    assert not result.success


# ---------------------------------------------------------------------------
# mount() Iron Law
# ---------------------------------------------------------------------------

async def test_mount_registers_design_ledger_tool(tmp_path):
    """mount() must register the tool under tools/design_ledger and return it."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {"ledger_dir": str(tmp_path)})

    assert isinstance(returned, DesignLedgerTool)
    assert coordinator.mount_points["tools"]["design_ledger"] is returned


async def test_mount_uses_default_ledger_dir_when_config_empty(tmp_path):
    """mount() with config={} still mounts successfully (uses default path)."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {})
    assert isinstance(returned, DesignLedgerTool)
    assert coordinator.mount_points["tools"]["design_ledger"] is returned
