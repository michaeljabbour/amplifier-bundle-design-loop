"""
Integration test configuration for the design-loop bundle.

These tests hit a real LLM provider and require a configured environment.

HOW TO RUN MANUAL TESTS
========================

    RUN_MANUAL=1 python -m pytest tests/integration -m manual -v -s

Prerequisites:
- A configured provider API key (e.g. ANTHROPIC_API_KEY)
- A loadable design-loop bundle (bundle.md in the repo root)
- amplifier_foundation installed (uv sync)

These tests are excluded from CI. They are gated behind the RUN_MANUAL=1
environment variable so `pytest` and `pytest tests/` never run them by accident.
"""

import os

import pytest


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """Skip all 'manual' tests unless RUN_MANUAL=1 is set."""
    if os.environ.get("RUN_MANUAL") != "1":
        skip_manual = pytest.mark.skip(
            reason="manual integration test; set RUN_MANUAL=1 to run"
        )
        for item in items:
            if "manual" in item.keywords:
                item.add_marker(skip_manual)
