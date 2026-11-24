"""Nearest-feature analysis with explicit vector-only semantics."""

from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from spatcat_mcp.api import request
from spatcat_mcp.models import Geometry, LayerIds, ToolResult
from spatcat_mcp.tools.common import READ_ONLY, unique_ids


def register(mcp: FastMCP) -> None:
    @mcp.tool(name="usgs_spatcat_distance_to_layers", annotations=READ_ONLY)
    async def distance_to_layers(
        layer_ids: LayerIds,
        geometry: Geometry,
        buffer_meters: Annotated[
            float, Field(gt=0, le=1000000, allow_inf_nan=False)
        ] = 10000,
    ) -> ToolResult:
        """Find nearest vector features to a WGS84 Point, Polygon, or MultiPolygon.

        Esri/WFS distance is closest approach in meters, zero for overlap,
        searching outward up to buffer_meters. S3 vectors use polygon centroids
        and ignore buffer_meters. Raster distance (COG/WCS/WMS raster) is NOT
        implemented. Discover supported layers first. No match does not prove
        absence beyond the search radius; preserve per-layer errors.
        """
        return await request(
            "analysis",
            "POST",
            "spatial/distance",
            body={
                "layerIds": unique_ids(layer_ids),
                "geometry": geometry.model_dump(),
                "bufferMeters": buffer_meters,
            },
            warnings=[
                "Vector only. S3 polygon distance uses the centroid "
                "and ignores bufferMeters."
            ],
        )
