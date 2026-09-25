"""Tests for root and behavior bundle composition (TDD RED -> GREEN)."""

import asyncio
import pathlib
from hashlib import sha256

import yaml

REPO = pathlib.Path(__file__).parents[1]
BUNDLE = REPO / "bundle.md"
BEHAVIOR = REPO / "behaviors" / "design-loop.yaml"
FULL_BEHAVIOR = REPO / "behaviors" / "design-loop-full.yaml"
RECIPE_TOOLS_BEHAVIOR = REPO / "behaviors" / "design-loop-recipe-tools.yaml"
FOUNDATION_SOURCE = "git+https://github.com/microsoft/amplifier-foundation@main"
DESIGN_INTELLIGENCE_SOURCE = (
    "git+https://github.com/microsoft/amplifier-bundle-design-intelligence"
    "@main#subdirectory=behaviors/design-intelligence.yaml"
)
RECIPES_SOURCE = (
    "git+https://github.com/microsoft/amplifier-bundle-recipes"
    "@main#subdirectory=behaviors/recipes.yaml"
)
ROOT_BODY_SHA256 = "27e734cb931429777dd3e8422319e62fa9c0abc47342dbd3172c68985fb8598e"
TOOL_NAMES = (
    "tool-render",
    "tool-target-state",
    "tool-render-report",
    "tool-design-lints",
    "tool-design-ledger",
    "tool-design-controller",
)
AGENT_NAMES = (
    "design-loop:design-judge",
    "design-loop:design-critic",
    "design-loop:design-maker",
    "design-loop:design-planner",
)


def _frontmatter(path: pathlib.Path) -> str:
    """Extract raw YAML frontmatter text from a markdown file."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{path} must start with '---'"
    _, fm, _ = text.split("---", 2)
    return fm


def _yaml(path: pathlib.Path) -> dict:
    """Read either a markdown bundle's frontmatter or a pure YAML behavior."""
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(_frontmatter(path) if text.startswith("---") else text)


def test_bundle_name_is_design_loop():
    fm = _frontmatter(BUNDLE)
    assert "name: design-loop" in fm, "bundle.name must be 'design-loop'"


def test_root_includes_only_foundation_and_its_behavior():
    document = _yaml(BUNDLE)
    assert document["includes"] == [
        {"bundle": FOUNDATION_SOURCE},
        {"bundle": "design-loop:behaviors/design-loop"},
    ]
    assert set(document) == {"bundle", "includes"}


def test_root_markdown_body_is_byte_exact_standalone_instruction():
    body = BUNDLE.read_bytes().split(b"---", 2)[2]
    assert sha256(body).hexdigest() == ROOT_BODY_SHA256


def test_root_division_of_labour_matches_composition():
    """bundle.md must not claim design-intelligence does the work: the slim
    behavior no longer includes it; the bundle's own agents do the design work."""
    body = BUNDLE.read_text(encoding="utf-8").split("---", 2)[2]
    section = body.split("## Division of labour", 1)[1].split("\n---", 1)[0]
    assert "`design-intelligence` agents do the design work" not in section
    for agent in ("design-critic", "design-maker", "design-planner"):
        assert agent in section
    assert "not** a dependency" in section
    assert "behaviors/design-loop-full.yaml" in section
    assert FULL_BEHAVIOR.exists()


def test_behavior_is_pure_yaml_and_owns_operational_configuration():
    text = BEHAVIOR.read_text(encoding="utf-8")
    document = _yaml(BEHAVIOR)
    assert not text.startswith("---"), (
        "behavior must be pure YAML, not markdown frontmatter"
    )
    assert document["bundle"]["name"] == "design-loop-behavior"
    assert document["bundle"]["version"] == "0.3.0"
    # design-intelligence is opt-in (behaviors/design-loop-full.yaml): nothing
    # here depends on it and its agent catalog costs tokens on every request.
    assert document["includes"] == [{"bundle": RECIPES_SOURCE}]


def test_behavior_mounts_no_tools():
    """The 6 deterministic tools no longer live on the composed behavior --
    they cost real per-request schema footprint. design-judge carries its own
    3 (agent-scoped, agents/design-judge.md); the recipe's bash steps resolve
    the rest via behaviors/design-loop-recipe-tools.yaml (bundle_ref)."""
    document = _yaml(BEHAVIOR)
    assert "tools" not in document


def test_recipe_tools_behavior_declares_all_local_tools():
    document = _yaml(RECIPE_TOOLS_BEHAVIOR)
    tools = document["tools"]
    assert tools == [
        {"module": name, "source": f"../modules/{name}"} for name in TOOL_NAMES
    ]
    assert "agents" not in document
    assert "context" not in document


def test_design_judge_declares_its_own_agent_scoped_tools():
    fm = yaml.safe_load(_frontmatter(REPO / "agents" / "design-judge.md"))
    judge_tools = {t["module"] for t in fm["tools"]}
    assert judge_tools == {"tool-render", "tool-target-state", "tool-render-report"}


def test_full_behavior_opts_into_design_intelligence():
    document = _yaml(FULL_BEHAVIOR)
    assert document["bundle"]["name"] == "design-loop-full-behavior"
    assert document["includes"] == [
        {"bundle": "design-loop:behaviors/design-loop"},
        {"bundle": DESIGN_INTELLIGENCE_SOURCE},
    ]
    assert not {"tools", "agents", "context"} & set(document)


def test_behavior_wires_all_design_loop_agents_and_awareness_context():
    document = _yaml(BEHAVIOR)
    assert document["agents"]["include"] == list(AGENT_NAMES)
    assert document["context"]["include"] == [
        "design-loop:context/design-loop-awareness.md"
    ]


def test_behavior_local_tool_dirs_exist():
    for tool_dir in TOOL_NAMES:
        pyproject = REPO / "modules" / tool_dir / "pyproject.toml"
        assert pyproject.exists(), f"modules/{tool_dir}/pyproject.toml must exist"


def _write_bundle_fixture(path: pathlib.Path, name: str, body: str = "") -> None:
    path.write_text(
        f"---\nbundle:\n  name: {name}\n  version: 0.2.0\n---{body}",
        encoding="utf-8",
    )


def test_public_foundation_load_composes_behavior_offline(tmp_path: pathlib.Path):
    """Public composition check using fixtures, not a certification of live dependencies."""
    from amplifier_foundation import BundleRegistry, load_bundle

    fixtures = {
        FOUNDATION_SOURCE: (tmp_path / "foundation.md", "fixture-foundation"),
        DESIGN_INTELLIGENCE_SOURCE: (
            tmp_path / "design-intelligence.md",
            "fixture-design-intelligence",
        ),
        RECIPES_SOURCE: (tmp_path / "recipes.md", "fixture-recipes"),
        "design-loop:behaviors/design-loop": (BEHAVIOR, "design-loop-behavior"),
    }
    for source, (path, name) in fixtures.items():
        if source == "design-loop:behaviors/design-loop":
            continue
        _write_bundle_fixture(path, name)

    def resolve_fixture(source: str) -> str:
        try:
            return str(fixtures[source][0])
        except KeyError as error:
            raise AssertionError(f"unexpected include source: {source}") from error

    registry = BundleRegistry(
        home=tmp_path / "amplifier-home",
        strict=True,
        include_source_resolver=resolve_fixture,
    )
    behavior = asyncio.run(load_bundle(str(BEHAVIOR), registry=registry))
    assert behavior.instruction is None

    bundle = asyncio.run(load_bundle(str(BUNDLE), registry=registry))
    root_instruction = BUNDLE.read_text(encoding="utf-8").split("---", 2)[2].strip()
    assert bundle.instruction == root_instruction
    # The composed behavior mounts no tools of its own (see
    # test_behavior_mounts_no_tools); design-judge carries its 3 agent-scoped
    # tools in its own frontmatter, mounted only in its own spawned session.
    assert not bundle.tools
    assert set(AGENT_NAMES) <= set(bundle.agents)
    for name in AGENT_NAMES:
        assert bundle.agents[name], f"{name} agent metadata did not resolve"
    # Namespaced context is deliberately deferred until every included bundle
    # has registered its namespace root during composition.
    bundle.resolve_pending_context()
    awareness = "design-loop:context/design-loop-awareness.md"
    assert (
        bundle.context[awareness]
        == (REPO / "context" / "design-loop-awareness.md").resolve()
    )


def test_nested_behavior_root_body_would_replace_a_bodyless_instruction(
    tmp_path: pathlib.Path,
):
    """A root include with a Markdown body is detectable as an instruction overlay."""
    from amplifier_foundation import BundleRegistry, load_bundle

    nested_root = tmp_path / "nested-root.md"
    behavior = tmp_path / "bodyless-behavior.yaml"
    _write_bundle_fixture(nested_root, "nested-root", "\nNested root instruction.\n")
    behavior.write_text(
        "bundle:\n  name: bodyless-behavior\n  version: 0.2.0\n"
        "includes:\n  - bundle: fixture:nested-root\n",
        encoding="utf-8",
    )

    def resolve_nested_root(source: str) -> str:
        if source != "fixture:nested-root":
            raise AssertionError(f"unexpected include source: {source}")
        return str(nested_root)

    registry = BundleRegistry(
        home=tmp_path / "amplifier-home",
        strict=True,
        include_source_resolver=resolve_nested_root,
    )
    loaded = asyncio.run(load_bundle(str(behavior), registry=registry))
    assert loaded.instruction == "Nested root instruction."


def test_full_behavior_composes_design_loop_plus_design_intelligence(
    tmp_path: pathlib.Path,
):
    """The opt-in behavior restores the pre-slimming composition."""
    from amplifier_foundation import BundleRegistry, load_bundle

    di = tmp_path / "design-intelligence.md"
    di.write_text(
        "---\nbundle:\n  name: fixture-design-intelligence\n  version: 1.0.0\n"
        "agents:\n  include:\n    - fixture-design-intelligence:art-director\n---\n",
        encoding="utf-8",
    )
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "art-director.md").write_text(
        "---\nmeta:\n  name: art-director\n  description: fixture\n---\nbody\n",
        encoding="utf-8",
    )
    recipes = tmp_path / "recipes.md"
    _write_bundle_fixture(recipes, "fixture-recipes")
    fixtures = {
        DESIGN_INTELLIGENCE_SOURCE: di,
        RECIPES_SOURCE: recipes,
        "design-loop:behaviors/design-loop": BEHAVIOR,
    }

    def resolve_fixture(source: str) -> str:
        try:
            return str(fixtures[source])
        except KeyError as error:
            raise AssertionError(f"unexpected include source: {source}") from error

    registry = BundleRegistry(
        home=tmp_path / "amplifier-home",
        strict=True,
        include_source_resolver=resolve_fixture,
    )
    full = asyncio.run(load_bundle(str(FULL_BEHAVIOR), registry=registry))
    assert set(AGENT_NAMES) <= set(full.agents)
    assert "fixture-design-intelligence:art-director" in full.agents
    # No tools composed here either -- design-judge's 3 are agent-scoped, and
    # the recipe's remaining 3 resolve via behaviors/design-loop-recipe-tools.yaml.
    assert not full.tools
