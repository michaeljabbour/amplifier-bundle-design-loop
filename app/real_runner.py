"""REAL design-loop backend (approach a: SDK, not subprocess).

Mirrors amplifier-app-bundlewizard-web/src/app_bundlewizard_web/session_bridge.py:
    load_bundle(bundle_ref) -> bundle.prepare() -> prepared.create_session(...)
then registers a hook per STREAMING_EVENTS entry that forwards through the
same WebStreamingHook used by dry_runner, so the frontend's event handling
code does not need to know whether a run was real or scripted.

WIRED BUT NOT INVOKED DURING THIS BUILD: `amplifier_foundation` is not
installed in this repo's .venv (only `amplifier_core` is, as a dependency of
the already-mounted tool modules). Calling run_real() before installing it
raises a clear RuntimeError with the exact install command, rather than
silently falling back to dry mode. See README section "Real backend" for the
one-line `uv pip install` needed to make this path importable, and the
recipes-tool invocation this function drives once that's done.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

from .protocols import STREAMING_EVENTS, WebStreamingHook

logger = logging.getLogger(__name__)

# This app lives at <bundle-root>/app/real_runner.py, so the bundle root
# (which has bundle.md) is two parents up. Loading the bundle from its own
# local checkout means recipes/design-converge.yaml and the mounted
# tool-render-report/tool-design-lints/etc. modules resolve to THIS repo,
# with no network fetch for the bundle itself (its `includes:` still fetch
# foundation/design-intelligence/recipes from git on first prepare()).
_BUNDLE_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Default APS (Amplifier Product Spec) knobs for design-converge.yaml,
# matching the bundle.md usage example. Callers may override via `options`.
_DEFAULT_RECIPE_CONTEXT: dict[str, Any] = {
    "task_class": "landing-page-critique",
    "bar": 26,
    "floors": 2,
    "budget": 8,
    "epsilon": 1,
    "k": 3,
}


async def _register_streaming_hooks(coordinator: Any, hook: WebStreamingHook) -> None:
    """Register one kernel hook handler per STREAMING_EVENTS entry.

    Kernel calls handlers as handler(event_name: str, data: dict) and expects
    a HookResult back -- identical contract to amplifier-app-bundlewizard-web's
    session_bridge.register_web_hooks().
    """
    try:
        from amplifier_core.models import HookResult
    except ImportError:  # pragma: no cover -- amplifier_core is always present here
        from dataclasses import dataclass

        @dataclass
        class HookResult:  # type: ignore[no-redef]
            action: str = "continue"

    for event_name in STREAMING_EVENTS:

        async def _handler(event: str, data: Any, _evt: str = event_name) -> Any:
            try:
                await hook.on_event(_evt, data)
            except Exception:
                logger.warning("Failed to forward %s event", _evt, exc_info=True)
            return HookResult(action="continue")

        coordinator.hooks.register(event_name, _handler)

    logger.info("Registered %d real-backend streaming hooks", len(STREAMING_EVENTS))


def _classify_fallback(source: str) -> str:
    """Best-effort classification via recipes/dlx.py's classify_input.

    Only used as a defensive fallback if a caller somehow invokes run_real
    without a resolved kind -- ws_handler always passes one (read from
    meta.json), so this should not normally execute.
    """
    try:
        import importlib
        import sys as _sys

        recipes_dir = _BUNDLE_ROOT / "recipes"
        if str(recipes_dir) not in _sys.path:
            _sys.path.insert(0, str(recipes_dir))
        dlx = importlib.import_module("dlx")
        return dlx.classify_input(source)
    except Exception:
        logger.warning(
            "classify_input fallback failed for source=%r", source, exc_info=True
        )
        return "prompt"


async def run_real(
    run_id: str,
    out_dir: pathlib.Path,
    hook: WebStreamingHook,
    *,
    kind: str,
    source: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the real design-loop recipe against a classified input.

    Approach (a) from the task brief: load this bundle via the SDK, create a
    session, register WebStreamingHook on STREAMING_EVENTS, then invoke the
    `recipes` tool's execute operation directly (no LLM round-trip needed to
    decide to call it -- we call the mounted tool's execute() ourselves),
    driving recipes/design-converge.yaml. Kernel events for every agent spawn
    and tool call stream out through the hooks registered above during that
    execute() call.

    `kind`/`source` come from ws_handler (which reads meta.json written by
    /api/upload or /api/source) -- `source` is a filesystem path for
    image/html inputs, or the raw URL/prompt text otherwise. Both are
    forwarded into the recipe context so design-converge.yaml's own
    classify_input-driven front door can route the run (image -> tool-target-
    state screenshot path, html -> direct artifact, url -> fetch, prompt ->
    freeform brief).
    """
    try:
        from amplifier_foundation import load_bundle
    except ImportError as exc:
        raise RuntimeError(
            "amplifier_foundation is not installed in this .venv. Install it with:\n"
            "  cd ~/dev/amplifier-bundle-design-loop && "
            "uv pip install --python .venv/bin/python amplifier-foundation\n"
            "(amplifier-foundation is not yet published to PyPI in every environment; "
            "if that fails, install from source: "
            "uv pip install --python .venv/bin/python "
            "'git+https://github.com/microsoft/amplifier-foundation@main')"
        ) from exc

    resolved_kind = kind or _classify_fallback(source)

    await hook.display(f"Loading bundle from {_BUNDLE_ROOT} ...", source="loop")
    bundle = await load_bundle(str(_BUNDLE_ROOT))
    prepared = await bundle.prepare()

    session = await prepared.create_session()
    await _register_streaming_hooks(session.coordinator.hooks, hook)

    recipe_context = dict(_DEFAULT_RECIPE_CONTEXT)
    recipe_context["source"] = source
    recipe_context["kind"] = resolved_kind
    if options:
        recipe_context.update(options)

    tools = session.coordinator.get("tools") or {}
    recipes_tool = tools.get("recipes")
    if recipes_tool is None:
        raise RuntimeError(
            "'recipes' tool not mounted on this session -- check that the "
            "recipes bundle include resolved in bundle.md."
        )

    await hook.tool_pre(
        "recipes", {"operation": "execute", "recipe": "design-converge.yaml"}
    )
    tool_result = await recipes_tool.execute(
        {
            "operation": "execute",
            "recipe_path": "design-loop:recipes/design-converge.yaml",
            "context": recipe_context,
        }
    )
    await hook.tool_post("recipes", success=bool(getattr(tool_result, "success", True)))

    # design-converge.yaml's FINALIZE stage already calls render_report and
    # writes into a durable location; the summary/state it returns includes
    # the report path. We re-render into THIS run's out_dir for a stable,
    # app-owned URL regardless of where the recipe's own durable_base points.
    output = getattr(tool_result, "output", tool_result)
    state = output.get("state", output) if isinstance(output, dict) else {}

    from amplifier_module_tool_render_report import template as rr_template

    render_result = rr_template.render(state, out_dir=str(out_dir), durable_base=None)

    gate = state.get("gate") or {} if isinstance(state, dict) else {}
    champion = state.get("champion") or {} if isinstance(state, dict) else {}
    champ_scores = champion.get("scores") or {}
    if isinstance(champ_scores, dict) and isinstance(champ_scores.get("scores"), dict):
        champ_scores = champ_scores["scores"]
    total = champion.get("total")
    if total is None:
        total = sum(v for v in champ_scores.values() if isinstance(v, int))
    converged = (
        bool(state.get("converged", False)) if isinstance(state, dict) else False
    )
    reason = gate.get("reason") or ""

    render_result["total"] = total
    render_result["converged"] = converged
    render_result["reason"] = reason
    return render_result
