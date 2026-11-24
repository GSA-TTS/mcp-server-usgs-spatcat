"""Core tool invocation, geometry validation, and filter boundary tests."""

from __future__ import annotations

import importlib

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from spatcat_mcp.app import mcp
from spatcat_mcp.filters import validate_where
from spatcat_mcp.models import Geometry, ToolResult

POINT = {"type": "Point", "coordinates": [-105.15, 40.57]}
CASES = [
    (
        "search_layers",
        {},
        "catalog",
        "GET",
        "layers",
        {"params": {"limit": 20, "offset": 0}},
    ),
    (
        "search_layers",
        {
            "query": "flood",
            "category": "FLOOD_HAZARD",
            "service_type": "WFS",
            "limit": 5,
            "offset": 10,
        },
        "catalog",
        "GET",
        "layers",
        {
            "params": {
                "query": "flood",
                "category": "FLOOD_HAZARD",
                "serviceType": "WFS",
                "limit": 5,
                "offset": 10,
            }
        },
    ),
    ("get_layer", {"layer_id": "abc-123"}, "catalog", "GET", "layers/abc-123", {}),
    ("list_spatial_layers", {}, "analysis", "GET", "spatial/layers", {}),
    (
        "get_sublayers",
        {"layer_id": "abc", "include_fields": True},
        "analysis",
        "GET",
        "spatial/layers/abc/sublayers",
        {"params": {"fields": "true"}},
    ),
    (
        "get_native_resolution",
        {"layer_id": "abc"},
        "analysis",
        "GET",
        "spatial/layers/abc/native-resolution",
        {},
    ),
    (
        "intersect_layers",
        {
            "layer_ids": ["abc"],
            "geometry": POINT,
            "sublayers": [0, 2],
            "resolution": "native",
        },
        "analysis",
        "POST",
        "spatial/intersect",
        {
            "body": {
                "layerIds": ["abc"],
                "geometry": POINT,
                "sublayers": [0, 2],
                "resolution": "native",
            }
        },
    ),
    (
        "distance_to_layers",
        {"layer_ids": ["abc"], "geometry": POINT},
        "analysis",
        "POST",
        "spatial/distance",
        {"body": {"layerIds": ["abc"], "geometry": POINT, "bufferMeters": 10000}},
    ),
    (
        "query_attributes",
        {"layer_ids": ["abc"], "where": "ADMIN_ST = 'NM'"},
        "analysis",
        "POST",
        "spatial/attribute-query",
        {
            "body": {
                "layerIds": ["abc"],
                "where": "ADMIN_ST = 'NM'",
                "outFields": "*",
                "maxResults": 100,
            }
        },
    ),
    ("list_analysis_modules", {}, "analysis", "GET", "analysis/modules", {}),
    (
        "analyze_point",
        {"longitude": -105, "latitude": 39.7, "module_ids": ["soils"]},
        "analysis",
        "POST",
        "analysis/point",
        {"body": {"lng": -105, "lat": 39.7, "moduleIds": ["soils"]}},
    ),
    (
        "analyze_point",
        {"longitude": -105, "latitude": 39.7},
        "analysis",
        "POST",
        "analysis/point",
        {"body": {"lng": -105, "lat": 39.7}},
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("name,args,source,method,path,kwargs", CASES)
async def test_tool_endpoint_mapping(
    monkeypatch, name, args, source, method, path, kwargs
):
    calls = []

    async def fake_request(*positional, **keyword):
        calls.append((positional, keyword))
        return ToolResult(
            source=source,
            retrieved_at="2026-11-24T00:00:00+00:00",
            data={"results": [{"layerId": "abc", "error": "unavailable"}]},
        )

    module = importlib.import_module(f"spatcat_mcp.tools.{name}")
    monkeypatch.setattr(module, "request", fake_request)
    async with Client(mcp) as client:
        result = await client.call_tool(f"usgs_spatcat_{name}", args)
    assert not result.is_error
    assert result.structured_content["data"]["results"][0]["error"] == "unavailable"
    positional, keyword = calls[0]
    assert positional == (source, method, path)
    for key, value in kwargs.items():
        assert keyword[key] == value


@pytest.mark.parametrize(
    "geometry",
    [
        POINT,
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        {"type": "MultiPolygon", "coordinates": [[[[0, 0], [1, 0], [1, 1], [0, 0]]]]},
    ],
)
def test_valid_geometry(geometry):
    assert Geometry.model_validate(geometry).model_dump() == geometry


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Point", "coordinates": [181, 0]},
        {"type": "Point", "coordinates": [0, float("nan")]},
        {"type": "Point", "coordinates": [True, 0]},
        {"type": "Point", "coordinates": [0, 0, 1]},
        {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [2, 1]]]},
        {"type": "Polygon", "coordinates": [[[0, 0]] * 4]},
        {"type": "MultiPolygon", "coordinates": []},
        {"type": "Feature", "coordinates": [0, 0]},
    ],
)
def test_invalid_geometry(geometry):
    with pytest.raises(ValidationError):
        Geometry.model_validate(geometry)


def test_geometry_position_budget():
    with pytest.raises(ValidationError, match="10000"):
        Geometry(type="Polygon", coordinates=[[[0, 0]] * 10001])


@pytest.mark.parametrize(
    "where",
    [
        "ADMIN_ST = 'NM'",
        "AREA >= 10 AND (NAME LIKE 'A%' OR ID IN (1, 2))",
        "NAME = 'O''Brien'",
        "NAME IS NOT NULL",
        "ID NOT IN (1, 2)",
    ],
)
def test_allowed_filters(where):
    assert validate_where(where) == where


@pytest.mark.parametrize(
    "where",
    [
        "1=1",
        "NAME = 'x'; DROP TABLE layers",
        "ID=1 -- comment",
        "ID = 1 UNION SELECT secret FROM users",
        "LOWER(NAME) = 'x'",
        "ID IN ()",
        "ID = 1 OR",
        "",
        "(" * 30 + "ID=1" + ")" * 30,
    ],
)
def test_denied_filters(where):
    with pytest.raises(ToolError, match="invalid_filter"):
        validate_where(where)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,args",
    [
        ("get_layer", {"layer_id": "../admin"}),
        ("search_layers", {"limit": 101}),
        ("intersect_layers", {"layer_ids": [], "geometry": POINT}),
        ("intersect_layers", {"layer_ids": ["abc", "abc"], "geometry": POINT}),
        (
            "distance_to_layers",
            {"layer_ids": ["abc"], "geometry": POINT, "buffer_meters": -1},
        ),
        ("query_attributes", {"layer_ids": ["abc"], "where": "ID=1;DROP TABLE x"}),
        (
            "query_attributes",
            {"layer_ids": ["abc"], "where": "ID=1", "out_fields": "secret;--"},
        ),
        ("analyze_point", {"longitude": 181, "latitude": 0}),
    ],
)
async def test_invalid_tool_arguments_do_not_request(monkeypatch, name, args):
    async def unexpected_request(*args, **kwargs):
        raise AssertionError("Invalid input reached API client")

    module = importlib.import_module(f"spatcat_mcp.tools.{name}")
    monkeypatch.setattr(module, "request", unexpected_request)
    async with Client(mcp) as client:
        result = await client.call_tool(
            f"usgs_spatcat_{name}", args, raise_on_error=False
        )
    assert result.is_error
