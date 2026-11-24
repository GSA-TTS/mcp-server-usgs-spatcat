"""Run discovered analysis modules at one WGS84 point."""

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from spatcat_mcp.api import request
from spatcat_mcp.models import ModuleIds, ToolResult
from spatcat_mcp.tools.common import READ_ONLY, unique_ids


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_analyze_point", annotations=READ_ONLY)
    async def analyze_point(
        longitude: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)],
        latitude: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)],
        module_ids: ModuleIds | None = None,
    ) -> ToolResult:
        """Analyze a WGS84 longitude/latitude using selected modules or all modules.

        Discover module IDs with list_analysis_modules. Omit module_ids to run
        all modules; specify a subset to reduce latency. Returns point metadata
        and module-specific results without inventing missing values.
        """
        body = {"lng": longitude, "lat": latitude}
        if module_ids is not None:
            body["moduleIds"] = unique_ids(module_ids)
        return await request("analysis", "POST", "analysis/point", body=body)
