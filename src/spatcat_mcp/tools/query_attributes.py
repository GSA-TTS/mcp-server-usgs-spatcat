"""Restricted read-only attribute filters for Esri layers."""

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from spatcat_mcp.api import request
from spatcat_mcp.filters import validate_where
from spatcat_mcp.models import LayerIds, ToolResult, validate_fields
from spatcat_mcp.tools.common import READ_ONLY, unique_ids


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_query_attributes", annotations=READ_ONLY)
    async def query_attributes(
        layer_ids: LayerIds,
        where: Annotated[str, Field(min_length=1, max_length=2000)],
        out_fields: Annotated[str, Field(min_length=1, max_length=2000)] = "*",
        max_results: Annotated[int, Field(ge=1, le=1000)] = 100,
    ) -> ToolResult:
        """Query Esri MapServer/FeatureServer layers by a read-only WHERE filter.

        Example: ADMIN_ST = 'NM'. Supports comparisons, IN, LIKE, IS NULL,
        AND/OR, and parentheses, not arbitrary SQL/functions. out_fields is '*'
        or comma-separated field names. max_results applies per layer, not
        globally. Discover field names before filtering; results may be capped.
        """
        try:
            fields = validate_fields(out_fields)
        except ValueError:
            raise ToolError(
                "invalid_fields: Use '*' or comma-separated field names."
            ) from None
        return await request(
            "analysis",
            "POST",
            "spatial/attribute-query",
            body={
                "layerIds": unique_ids(layer_ids),
                "where": validate_where(where),
                "outFields": fields,
                "maxResults": max_results,
            },
        )
