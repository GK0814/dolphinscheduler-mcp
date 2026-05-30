# __init__.py
"""Tools package for DolphinScheduler MCP."""

from mcp.server.fastmcp import FastMCP

# Import registration functions for default core tool modules.
from .dynamic_task_type_tools import register_dynamic_task_type_tools
from .worker_group_tools import register_worker_group_tools
from .project_tools import register_project_tools
from .datasource_tools import register_datasource_tools
from .project_preference_tools import register_project_preference_tools
from .process_definition_tools import register_process_definition_tools
from .process_runtime_tools import register_process_runtime_tools
from .schedule_tools import register_schedule_tools
from .tool_guidance_tools import register_tool_guidance_tools

# The all_tools list is no longer used since we now rely on registration functions
all_tools = []


def register_all_tools(mcp: FastMCP) -> None:
    """Register all available tools with the FastMCP instance.

    Args:
        mcp: The FastMCP instance to register tools with.
    """
    # Register Dynamic Task Type Tools
    register_dynamic_task_type_tools(mcp)

    # Register Worker Group Tools
    register_worker_group_tools(mcp)

    # Register Project Management Tools
    register_project_tools(mcp)

    # Register Datasource Management Tools
    register_datasource_tools(mcp)

    # Register Project Preference Tools
    register_project_preference_tools(mcp)

    # Register Workflow Definition Tools
    register_process_definition_tools(mcp)

    # Register Workflow Runtime Tools
    register_process_runtime_tools(mcp)

    # Register Schedule and Dependency Analysis Tools
    register_schedule_tools(mcp)

    # Register Tool Guidance Tools
    register_tool_guidance_tools(mcp)


__all__ = ["all_tools", "register_all_tools"]
