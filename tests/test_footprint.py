"""Per-request prompt footprint guards for behaviors/design-loop.yaml.

Every tool schema, agent description, and context file the behavior mounts is
sent to the model on every request of every session composing it, so these
tests pin (a) size budgets and (b) the tool input contracts, so trimming text
can never silently drop a parameter the recipes rely on.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "measure_footprint", REPO / "scripts" / "measure_footprint.py"
)
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)

BEHAVIOR = yaml.safe_load((REPO / "behaviors" / "design-loop.yaml").read_text())

# Budgets in characters (tokens ~= chars / 4). Before slimming the behavior's
# own components were ~11.5k chars (~2.9k tok); after, ~5.4k chars (~1.35k tok).
TOTAL_BUDGET_CHARS = 6500
AGENT_DESC_BUDGET_CHARS = 400
TOOL_DESC_BUDGET_CHARS = 400
CONTEXT_BUDGET_CHARS = 800

# Input contracts the recipes (via `amplifier tool invoke`) and agents use.
EXPECTED_CONTRACTS = {
    "render": ({"source", "kind", "out_path"}, ["source"]),
    "target_state": ({"original", "fixes", "improved_html", "out_dir"}, None),
    "render_report": (
        {"verdict", "verdict_text", "target_html_path", "target_screenshot_path", "out_path"},
        None,
    ),
    "design_lints": ({"html", "html_path", "url", "viewport"}, None),
    "design_ledger": (
        {"op", "record", "task_class", "signature", "rubric_version", "outcome"},
        ["op"],
    ),
    "design_controller": (
        {
            "op", "candidate_scores", "candidate_hard_fail", "best_scores",
            "no_regress_dims", "tau", "bar", "floors", "budget_remaining",
            "recent_improvements", "k", "epsilon", "last_decision", "target_retried",
        },
        ["op"],
    ),
}
EXPECTED_ENUMS = {
    ("render", "kind"): ["html", "url", "image"],
    ("design_ledger", "op"): ["append", "query", "best", "dead_fixes"],
    ("design_controller", "op"): ["evaluate", "gate"],
}


def test_total_per_request_footprint_within_budget():
    total = sum(
        r["chars"]
        for r in (
            measure.context_rows(BEHAVIOR)
            + measure.agent_rows(BEHAVIOR)
            + measure.tool_rows(BEHAVIOR)
        )
    )
    assert total <= TOTAL_BUDGET_CHARS, (
        f"design-loop per-request footprint grew to {total} chars "
        f"(~{total // 4} tok); budget {TOTAL_BUDGET_CHARS}"
    )


def test_agent_descriptions_are_short_and_example_free():
    for row in measure.agent_rows(BEHAVIOR):
        assert row["raw_chars"] == row["chars"], (
            f"{row['name']}: <example> blocks belong in the agent body, not meta.description"
        )
        assert row["chars"] <= AGENT_DESC_BUDGET_CHARS, row


def test_context_file_is_small():
    for row in measure.context_rows(BEHAVIOR):
        assert row["chars"] <= CONTEXT_BUDGET_CHARS, row


def test_tool_descriptions_are_short():
    for row in measure.tool_rows(BEHAVIOR):
        assert row["desc_chars"] <= TOOL_DESC_BUDGET_CHARS, row


def test_tool_input_contracts_preserved():
    import asyncio
    import importlib

    for spec in BEHAVIOR["tools"]:
        pkg = "amplifier_module_" + spec["module"].replace("-", "_")
        coord = measure._FakeCoordinator()
        asyncio.run(importlib.import_module(pkg).mount(coord, {}))
        for name, tool in coord.mounted.items():
            props, required = EXPECTED_CONTRACTS[name]
            schema = tool.input_schema
            assert set(schema["properties"]) == props, name
            assert schema.get("required") == required, name
            for (tname, prop), enum in EXPECTED_ENUMS.items():
                if tname == name:
                    assert schema["properties"][prop]["enum"] == enum


def test_mounting_tools_does_not_import_playwright():
    """playwright costs ~0.1-0.2 s to import; it must load on first use, not mount."""
    code = (
        "import asyncio, sys\n"
        "import amplifier_module_tool_render as r, amplifier_module_tool_design_lints as l\n"
        "class C:\n"
        "    async def mount(self, *a, **k): pass\n"
        "asyncio.run(r.mount(C())); asyncio.run(l.mount(C()))\n"
        "print('playwright' in sys.modules)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"
