"""Discover queryable layers and upstream capability metadata."""

from fastmcp import FastMCP

from spatcat_mcp.api import request
from spatcat_mcp.models import ToolResult
from spatcat_mcp.tools.common import READ_ONLY


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_list_spatial_layers", annotations=READ_ONLY)
    async def list_spatial_layers() -> ToolResult:
        """List layers supporting spatial queries with their API capabilities.

        No undocumented filtering or pagination parameters are forwarded.
        Raster distance is not implemented, even if metadata suggests support.
        WMS support depends on sibling endpoints and geometry type.
        """
        return await request(
            "analysis",
            "GET",
            "spatial/layers",
            warnings=[
                "Raster distance is not implemented. Confirm per-layer capabilities."
            ],
        )
