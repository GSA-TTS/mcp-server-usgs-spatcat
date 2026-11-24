"""Tools submodule — one tool per file.

Each tool module (e.g. `example_tool.py`) exposes a `register(mcp)` function
that attaches its `@mcp.tool`-decorated function to the server. This file
aggregates them into a single `register_tools(mcp)` that `app.py` calls.

To add a tool:
  1. Create `tools/<your_tool>.py` with a `register(mcp)` function.
  2. Import it below and call `<your_tool>.register(mcp)` inside register_tools.
"""

from __future__ import annotations

from spatcat_mcp.tools import (
    analyze_point,
    distance_to_layers,
    get_layer,
    get_native_resolution,
    get_sublayers,
    intersect_layers,
    list_analysis_modules,
    list_spatial_layers,
    query_attributes,
    search_layers,
)


def register_tools(mcp) -> None:
    """Register all tools with the MCP server."""
    for module in (
        search_layers,
        get_layer,
        list_spatial_layers,
        get_sublayers,
        get_native_resolution,
        intersect_layers,
        distance_to_layers,
        query_attributes,
        list_analysis_modules,
        analyze_point,
    ):
        module.register(mcp)


__all__ = ["register_tools"]
