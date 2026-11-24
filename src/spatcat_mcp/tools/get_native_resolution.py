"""Probe native WCS pixel size."""

from fastmcp import FastMCP

from spatcat_mcp.api import request
from spatcat_mcp.models import LayerId, ToolResult
from spatcat_mcp.tools.common import READ_ONLY


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_get_native_resolution", annotations=READ_ONLY)
    async def get_native_resolution(layer_id: LayerId) -> ToolResult:
        """Probe a WCS raster layer's native resolution in meters.

        Use before selecting raster intersection resolution. This endpoint is
        not a general resolution probe for all service types.
        """
        return await request(
            "analysis", "GET", f"spatial/layers/{layer_id}/native-resolution"
        )
