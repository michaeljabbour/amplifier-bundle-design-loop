"""Tests for tool-design-lints mount() (Iron Law).

Verifies: mount() must call coordinator.mount('tools', tool, name=tool.name)
and return the mounted DesignLintsTool instance.
"""
import pytest
from amplifier_core.testing import create_test_coordinator

from amplifier_module_tool_design_lints import DesignLintsTool, mount


@pytest.mark.asyncio
async def test_mount_registers_design_lints_tool():
    """mount() constructs a DesignLintsTool, registers it under 'tools'/'design_lints', and returns it."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {})

    # The returned object must be a DesignLintsTool
    assert isinstance(returned, DesignLintsTool)

    # The coordinator must have the tool at mount_points['tools']['design_lints']
    assert coordinator.mount_points["tools"]["design_lints"] is returned
