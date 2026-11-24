"""Search the catalog without automatically fetching additional pages."""

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from spatcat_mcp.api import request
from spatcat_mcp.models import ToolResult
from spatcat_mcp.tools.common import READ_ONLY


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_search_layers", annotations=READ_ONLY)
    async def search_layers(
        query: Annotated[str | None, Field(max_length=500)] = None,
        service_type: Annotated[str | None, Field(pattern=r"^[A-Z_]{1,64}$")] = None,
        category: Annotated[str | None, Field(pattern=r"^[A-Z_]{1,64}$")] = None,
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        offset: Annotated[int, Field(ge=0, le=1000000)] = 0,
    ) -> ToolResult:
        """Search layer names, descriptions, and tags, or browse with no query.

        Use returned IDs with get_layer. Filters use API codes (e.g. WFS,
        FLOOD_HAZARD). Returns the upstream page, retaining pagination metadata
        when supplied; dataset freshness and total counts may be unknown.
        """
        params = {
            "query": query,
            "serviceType": service_type,
            "category": category,
            "limit": limit,
            "offset": offset,
        }
        return await request(
            "catalog",
            "GET",
            "layers",
            params={key: value for key, value in params.items() if value is not None},
        )
