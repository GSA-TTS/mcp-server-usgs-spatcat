"""Discover module IDs rather than hardcoding module availability."""

from fastmcp import FastMCP

from spatcat_mcp.api import request
from spatcat_mcp.models import ToolResult
from spatcat_mcp.tools.common import READ_ONLY


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_list_analysis_modules", annotations=READ_ONLY)
    async def list_analysis_modules() -> ToolResult:
        """List available analysis module IDs and API-supplied descriptions.

        Use returned module IDs with analyze_point. Availability is upstream
        controlled; examples such as soils/watershed are not an exhaustive enum.
        """
        return await request("analysis", "GET", "analysis/modules")
