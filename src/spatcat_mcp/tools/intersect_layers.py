"""Intersect registered vector or raster layers."""

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from spatcat_mcp.api import request
from spatcat_mcp.models import Geometry, LayerIds, Resolution, ToolResult
from spatcat_mcp.tools.common import READ_ONLY, unique_ids


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_intersect_layers", annotations=READ_ONLY)
    async def intersect_layers(
        layer_ids: LayerIds,
        geometry: Geometry,
        sublayers: Annotated[
            list[Annotated[int, Field(ge=0)]] | None, Field(min_length=1, max_length=50)
        ] = None,
        resolution: Resolution | None = None,
    ) -> ToolResult:
        """Intersect layers with a WGS84 Point, Polygon, or MultiPolygon.

        Vector results contain features; raster results contain summaries.
        Optional sublayers are Esri MapServer IDs; resolution is raster-only
        ('auto', 'native', or meters). WMS polygon queries require a sibling
        WFS/WCS endpoint. Preserve per-layer failures; absence is not a safe-site
        determination. Inspect layer capabilities first.
        """
        body = {"layerIds": unique_ids(layer_ids), "geometry": geometry.model_dump()}
        if sublayers is not None:
            body["sublayers"] = sublayers
        if resolution is not None:
            body["resolution"] = resolution
        return await request("analysis", "POST", "spatial/intersect", body=body)
