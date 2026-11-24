"""Inspect Esri MapServer sublayer metadata."""

from fastmcp import FastMCP

from spatcat_mcp.api import request
from spatcat_mcp.models import LayerId, ToolResult
from spatcat_mcp.tools.common import READ_ONLY


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_get_sublayers", annotations=READ_ONLY)
    async def get_sublayers(
        layer_id: LayerId, include_fields: bool = False
    ) -> ToolResult:
        """List Esri MapServer sublayer IDs, names, scales, and geometry types.

        Set include_fields for field definitions and available pagination info.
        Inspect fields before attribute queries and sublayers before intersects.
        """
        return await request(
            "analysis",
            "GET",
            f"spatial/layers/{layer_id}/sublayers",
            params={"fields": "true"} if include_fields else None,
        )
