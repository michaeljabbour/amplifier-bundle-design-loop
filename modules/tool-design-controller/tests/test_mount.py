"""Tests for tool-design-controller mount() — Iron Law.

Verifies: mount() must call coordinator.mount('tools', tool, name=tool.name)
and return the mounted DesignControllerTool instance.
"""
import pytest
from amplifier_core.testing import create_test_coordinator

from amplifier_module_tool_design_controller import DesignControllerTool, mount


@pytest.mark.asyncio
async def test_mount_registers_design_controller_tool():
    """mount() constructs a DesignControllerTool, registers it under
    'tools'/'design_controller', and returns it."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {})

    # Returned object must be a DesignControllerTool
    assert isinstance(returned, DesignControllerTool)

    # Coordinator must have the tool at mount_points['tools']['design_controller']
    assert coordinator.mount_points["tools"]["design_controller"] is returned


@pytest.mark.asyncio
async def test_mount_tool_name_is_design_controller():
    """The mounted tool's .name property must return 'design_controller'."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, {})
    assert returned.name == "design_controller"


@pytest.mark.asyncio
async def test_mount_config_none_accepted():
    """mount() with config=None must not raise."""
    coordinator = create_test_coordinator()
    returned = await mount(coordinator, None)
    assert isinstance(returned, DesignControllerTool)
