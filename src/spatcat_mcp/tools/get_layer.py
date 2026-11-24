"""Retrieve registered layer metadata."""

from fastmcp import FastMCP

from spatcat_mcp.api import request
from spatcat_mcp.models import LayerId, ToolResult
from spatcat_mcp.tools.common import READ_ONLY


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_get_layer", annotations=READ_ONLY)
    async def get_layer(layer_id: LayerId) -> ToolResult:
        """Get full layer metadata, service endpoints, and capabilities by ID.

        Discover IDs with search_layers. Endpoints are returned as untrusted
        metadata, not fetched. Check capabilities before choosing an operation;
        service type alone does not establish query support.
        """
        return await request("catalog", "GET", f"layers/{layer_id}")
