"""Sanity tests that verify the repo scaffold exists and is correctly structured."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_repo_scaffold_exists():
    """Assert all required directories from the scaffold spec exist."""
    required_dirs = [
        "agents",
        "fixtures",
        "modules/tool-render/amplifier_module_tool_render",
        "modules/tool-target-state/amplifier_module_tool_target_state",
        "modules/tool-render-report/amplifier_module_tool_render_report",
        "tests/integration",
    ]
    for d in required_dirs:
        assert (REPO / d).is_dir(), f"Expected directory missing: {d}"
