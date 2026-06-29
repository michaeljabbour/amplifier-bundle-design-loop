"""Structural tests for the three harness agents: design-critic, design-maker,
design-planner; and the signature-vocabulary context file.

Mirrors the pattern of test_agent_structure.py (file exists, frontmatter parses,
meta.name matches filename, model_role declared) and adds contract-specific
assertions derived from HARNESS_DESIGN.md §1, §4, §5.
"""
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[1]
AGENTS = REPO / "agents"
CONTEXT = REPO / "context"

CRITERIA = [
    "clarity",
    "elegance",
    "restraint",
    "empowerment",
    "agency",
    "ease",
    "character",
    "point",
]


def _frontmatter(text: str) -> str:
    assert text.startswith("---"), "Agent file must begin with '---'"
    return text.split("---", 2)[1]


def _body(text: str) -> str:
    return text.split("---", 2)[2].lower()


# ─────────────────────────────────────────────────────────────────────────────
# design-critic
# ─────────────────────────────────────────────────────────────────────────────

CRITIC = AGENTS / "design-critic.md"


def test_critic_file_exists():
    assert CRITIC.exists(), f"{CRITIC} does not exist"


def test_critic_frontmatter_parses():
    text = CRITIC.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert fm.strip(), "design-critic frontmatter must not be empty"


def test_critic_meta_name_matches_filename():
    text = CRITIC.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "name: design-critic" in fm, (
        "design-critic frontmatter must contain 'name: design-critic'"
    )


def test_critic_declares_model_role():
    text = CRITIC.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "model_role: vision" in fm, (
        "design-critic must declare 'model_role: vision'"
    )


def test_critic_body_contains_full_rubric():
    """All 8 rubric criteria must appear in the body (context-sink contract)."""
    text = CRITIC.read_text(encoding="utf-8")
    body = _body(text)
    for criterion in CRITERIA:
        assert criterion in body, (
            f"design-critic body is missing rubric criterion: {criterion}"
        )


def test_critic_body_declares_json_output_fields():
    """Output schema fields must be documented in the body."""
    text = CRITIC.read_text(encoding="utf-8")
    body = _body(text)
    for field in ["scores", "reasons", "signatures", "total", "min_quality"]:
        assert field in body, (
            f"design-critic body missing JSON output field: {field}"
        )


def test_critic_body_states_firewall_never_clause():
    """Firewall: the body must state what the critic NEVER sees."""
    text = CRITIC.read_text(encoding="utf-8")
    body = _body(text)
    assert "never" in body, (
        "design-critic body must state 'never' to declare firewall constraints"
    )


def test_critic_body_references_signature_format():
    """Critic must reference the signature controlled-vocabulary contract."""
    text = CRITIC.read_text(encoding="utf-8")
    body = _body(text)
    assert "signature" in body, (
        "design-critic body must reference the signature vocabulary"
    )


# ─────────────────────────────────────────────────────────────────────────────
# design-maker
# ─────────────────────────────────────────────────────────────────────────────

MAKER = AGENTS / "design-maker.md"


def test_maker_file_exists():
    assert MAKER.exists(), f"{MAKER} does not exist"


def test_maker_frontmatter_parses():
    text = MAKER.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert fm.strip(), "design-maker frontmatter must not be empty"


def test_maker_meta_name_matches_filename():
    text = MAKER.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "name: design-maker" in fm, (
        "design-maker frontmatter must contain 'name: design-maker'"
    )


def test_maker_declares_model_role():
    text = MAKER.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "model_role: ui-coding" in fm, (
        "design-maker must declare 'model_role: ui-coding'"
    )


def test_maker_body_forbids_rubric():
    """Firewall: maker body must acknowledge rubric and forbid optimising for it."""
    text = MAKER.read_text(encoding="utf-8")
    body = _body(text)
    assert "rubric" in body, (
        "design-maker body must mention 'rubric' (to explicitly forbid it)"
    )


def test_maker_body_states_never_or_forbid():
    """Firewall: maker must contain a prohibition clause."""
    text = MAKER.read_text(encoding="utf-8")
    body = _body(text)
    assert "never" in body or "do not" in body or "forbidden" in body, (
        "design-maker body must contain a prohibition clause (never / do not / forbidden)"
    )


def test_maker_body_references_target_state_tool():
    text = MAKER.read_text(encoding="utf-8")
    body = _body(text)
    assert "target_state" in body, (
        "design-maker body must reference the target_state tool"
    )


def test_maker_body_references_render_tool():
    text = MAKER.read_text(encoding="utf-8")
    body = _body(text)
    assert "render" in body, (
        "design-maker body must reference the render tool"
    )


def test_maker_body_mentions_html_path_return():
    """Maker must state that it returns a path to the improved HTML."""
    text = MAKER.read_text(encoding="utf-8")
    body = _body(text)
    assert "html" in body, "design-maker body must mention HTML"
    assert "path" in body, "design-maker body must mention returning a path"


# ─────────────────────────────────────────────────────────────────────────────
# design-planner
# ─────────────────────────────────────────────────────────────────────────────

PLANNER = AGENTS / "design-planner.md"


def test_planner_file_exists():
    assert PLANNER.exists(), f"{PLANNER} does not exist"


def test_planner_frontmatter_parses():
    text = PLANNER.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert fm.strip(), "design-planner frontmatter must not be empty"


def test_planner_meta_name_matches_filename():
    text = PLANNER.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "name: design-planner" in fm, (
        "design-planner frontmatter must contain 'name: design-planner'"
    )


def test_planner_declares_model_role():
    text = PLANNER.read_text(encoding="utf-8")
    fm = _frontmatter(text)
    assert "model_role: reasoning" in fm, (
        "design-planner must declare 'model_role: reasoning'"
    )


def test_planner_body_references_design_ledger_tool():
    text = PLANNER.read_text(encoding="utf-8")
    body = _body(text)
    assert "design_ledger" in body, (
        "design-planner body must reference the design_ledger tool"
    )


def test_planner_body_declares_fix_batch_schema():
    """All fix_batch fields must be documented in the planner body."""
    text = PLANNER.read_text(encoding="utf-8")
    body = _body(text)
    for field in ["fix_id", "target_dims", "directive", "strategy_tag"]:
        assert field in body, (
            f"design-planner body missing fix_batch field: {field}"
        )


def test_planner_body_calls_dead_fixes():
    """Planner must use dead_fixes to skip failed strategies (firewall contract §5)."""
    text = PLANNER.read_text(encoding="utf-8")
    body = _body(text)
    assert "dead_fixes" in body, (
        "design-planner body must reference the dead_fixes ledger operation"
    )


def test_planner_body_states_directives_are_qualitative():
    """Directives must be qualitative — no rubric weights downstream."""
    text = PLANNER.read_text(encoding="utf-8")
    body = _body(text)
    assert "qualitative" in body, (
        "design-planner body must state that directives are qualitative"
    )


def test_planner_body_no_rubric_weights_in_directives():
    """Planner body must explicitly state NOT to pass numeric scores downstream."""
    text = PLANNER.read_text(encoding="utf-8")
    body = _body(text)
    # Body must contain a prohibition on passing numbers/weights to the Maker
    has_prohibition = (
        "never" in body
        or "must not" in body
        or "do not" in body
        or "forbidden" in body
    )
    assert has_prohibition, (
        "design-planner body must prohibit passing numeric scores/weights to the Maker"
    )


# ─────────────────────────────────────────────────────────────────────────────
# context/signature-vocabulary.md
# ─────────────────────────────────────────────────────────────────────────────

SIG_VOC = CONTEXT / "signature-vocabulary.md"


def test_signature_vocabulary_file_exists():
    assert SIG_VOC.exists(), f"{SIG_VOC} does not exist"


def test_signature_vocabulary_has_canonical_entries():
    """Must contain at least 10 entries in backtick-wrapped <problem>:<region> format."""
    text = SIG_VOC.read_text(encoding="utf-8")
    entries = re.findall(r"`[a-z][a-z0-9-]+:[a-z][a-z0-9-]+`", text)
    assert len(entries) >= 10, (
        f"signature-vocabulary.md must have ≥10 canonical entries, found {len(entries)}: {entries}"
    )


def test_signature_vocabulary_states_ratification_rule():
    """Must document that new signatures require ratification."""
    text = SIG_VOC.read_text(encoding="utf-8")
    body = text.lower()
    assert "ratif" in body, (
        "signature-vocabulary.md must state the ratification rule"
    )


def test_signature_vocabulary_mentions_unratified():
    """Must describe the unratified flag for proposed signatures."""
    text = SIG_VOC.read_text(encoding="utf-8")
    assert "unratified" in text, (
        "signature-vocabulary.md must describe the unratified flag"
    )
