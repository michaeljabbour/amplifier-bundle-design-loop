#!/usr/bin/env python3
"""Estimate the per-request prompt footprint of behaviors/design-loop.yaml.

What the model sees on EVERY request once the behavior is composed:
  * each always-on context file (context.include), verbatim;
  * one delegate-catalog line per agent: ``  - <name>: <meta.description>``
    (foundation's delegate tool strips <example>/<commentary> blocks at render
    time; both raw and stripped sizes are reported);
  * each mounted tool's name + description + JSON input schema.

Tokens are estimated as chars / 4 (a rough rule of thumb, not a tokenizer).
Tools are mounted against a minimal fake coordinator, which also times
import + mount() per module.

Usage:  python scripts/measure_footprint.py [--json]
Needs the modules importable (``pip install -e modules/tool-*``) and pyyaml.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import re
import sys
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
BEHAVIOR = REPO / "behaviors" / "design-loop.yaml"

_EXAMPLE = re.compile(
    r"(?:^[ \t]*)?<(example|commentary)\b[^>]*>.*?</\1\s*>(?:[ \t]*\n)?",
    re.DOTALL | re.IGNORECASE | re.MULTILINE,
)


def tok(chars: int) -> int:
    return round(chars / 4)


def _frontmatter(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1]) or {}


def agent_rows(behavior: dict) -> list[dict]:
    rows = []
    for ref in (behavior.get("agents") or {}).get("include", []):
        ns, name = ref.split(":", 1)
        meta = _frontmatter(REPO / "agents" / f"{name}.md").get("meta", {})
        desc = meta.get("description", "")
        raw = f"  - {ref}: {desc}"
        stripped = f"  - {ref}: {_EXAMPLE.sub('', desc)}"
        rows.append({"name": ref, "raw_chars": len(raw), "chars": len(stripped)})
    return rows


def context_rows(behavior: dict) -> list[dict]:
    rows = []
    for ref in (behavior.get("context") or {}).get("include", []):
        rel = ref.split(":", 1)[1]
        rows.append({"name": ref, "chars": len((REPO / rel).read_text(encoding="utf-8"))})
    return rows


class _FakeCoordinator:
    def __init__(self) -> None:
        self.mounted: dict = {}
        self.config: dict = {}

    async def mount(self, kind, obj, name=None):
        self.mounted[name or obj.name] = obj

    def get_capability(self, _name):
        return None

    def register_capability(self, *_a, **_k):
        pass


def tool_rows(behavior: dict) -> list[dict]:
    # amplifier_core is already loaded in any real session; exclude it from the
    # per-module import timing so the numbers show only what each module adds.
    import amplifier_core  # noqa: F401

    rows = []
    for spec in behavior.get("tools") or []:
        module = spec["module"]
        pkg = "amplifier_module_" + module.replace("-", "_")
        t0 = time.perf_counter()
        mod = importlib.import_module(pkg)
        t1 = time.perf_counter()
        coord = _FakeCoordinator()
        asyncio.run(mod.mount(coord, spec.get("config") or {}))
        t2 = time.perf_counter()
        for tool in coord.mounted.values():
            schema = json.dumps(tool.input_schema, separators=(",", ":"))
            rows.append(
                {
                    "name": tool.name,
                    "module": module,
                    "desc_chars": len(tool.description),
                    "schema_chars": len(schema),
                    "chars": len(tool.name) + len(tool.description) + len(schema),
                    "import_ms": round((t1 - t0) * 1000, 1),
                    "mount_ms": round((t2 - t1) * 1000, 1),
                }
            )
    return rows


def main() -> int:
    behavior = yaml.safe_load(BEHAVIOR.read_text(encoding="utf-8"))
    report = {
        "context": context_rows(behavior),
        "agents": agent_rows(behavior),
        "tools": tool_rows(behavior),
        "includes": [i.get("bundle") for i in behavior.get("includes") or []],
    }
    totals = {k: sum(r["chars"] for r in report[k]) for k in ("context", "agents", "tools")}
    totals["all"] = sum(totals.values())
    report["totals_chars"] = totals
    report["totals_tokens_est"] = {k: tok(v) for k, v in totals.items()}
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
        return 0
    for section in ("context", "agents", "tools"):
        print(f"[{section}]")
        for r in report[section]:
            extra = ""
            if section == "agents" and r["raw_chars"] != r["chars"]:
                extra = f"  (raw incl. <example>: ~{tok(r['raw_chars'])} tok)"
            if section == "tools":
                extra = f"  import {r['import_ms']} ms, mount {r['mount_ms']} ms"
            print(f"  {r['name']:<34} {r['chars']:>6} chars  ~{tok(r['chars']):>5} tok{extra}")
        print(f"  {'subtotal':<34} {totals[section]:>6} chars  ~{tok(totals[section]):>5} tok")
    print(f"TOTAL (own components) {totals['all']} chars ~{tok(totals['all'])} tok (chars/4)")
    if report["includes"]:
        print("includes (measured separately):", *report["includes"], sep="\n  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
