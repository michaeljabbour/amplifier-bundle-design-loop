"""Tests for tool-render mount() (Task 6).

Verifies the Iron Law: mount() must call coordinator.mount('tools', tool, name=tool.name)
and return the mounted RenderTool instance.
"""
import pytest
from amplifier_core.testing import create_test_coordinator

from amplifier_module_tool_render import RenderTool, mount


@pytest.mark.asyncio
async def test_mount_registers_render_tool():
    """mount() constructs a RenderTool, registers it under 'tools'/'render', and returns it."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {})

    # The returned object must be a RenderTool
    assert isinstance(returned, RenderTool)

    # The coordinator must have the tool at mount_points['tools']['render']
    assert coordinator.mount_points["tools"]["render"] is returned
