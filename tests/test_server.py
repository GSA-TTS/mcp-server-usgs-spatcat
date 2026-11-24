"""Smoke tests for the example MCP server.

These verify the server imports and every submodule registers without error.
Add functional tests for your own tools as you build them.
"""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from spatcat_mcp.app import mcp
from spatcat_mcp.config import settings


def test_server_is_importable():
    assert mcp is not None


def test_server_has_name():
    assert mcp.name == "Example MCP Server"


def test_default_transport_is_stdio():
    """Guard against accidentally shipping with a non-stdio default."""
    assert settings.mcp_transport == "stdio"


def test_tools_register_without_error():
    from spatcat_mcp.tools import register_tools

    register_tools(FastMCP("test"))  # must not raise


def test_prompts_register_without_error():
    from spatcat_mcp.prompts import register_prompts

    register_prompts(FastMCP("test"))  # must not raise


def test_resources_register_without_error():
    from spatcat_mcp.resources import register_resources

    register_resources(FastMCP("test"))  # must not raise


def test_routes_register_without_error():
    from spatcat_mcp.routes import register_routes

    register_routes(FastMCP("test"))  # must not raise


@pytest.mark.asyncio
async def test_core_tools_are_discoverable():
    """Exactly the ten approved tools are registered."""
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert tool_names == {
        f"usgs_spatcat_{name}"
        for name in (
            "search_layers",
            "get_layer",
            "list_spatial_layers",
            "get_sublayers",
            "get_native_resolution",
            "intersect_layers",
            "distance_to_layers",
            "query_attributes",
            "list_analysis_modules",
            "analyze_point",
        )
    }


@pytest.mark.parametrize(
    "databricks,port,transport,expected",
    [
        (
            "9000",
            "9001",
            "stdio",
            {"transport": "http", "host": "0.0.0.0", "port": 9000},
        ),
        (
            None,
            "9001",
            "streamable-http",
            {"transport": "http", "host": "0.0.0.0", "port": 9001},
        ),
        (
            None,
            None,
            "streamable-http",
            {"transport": "streamable-http", "host": "127.0.0.1", "port": 8123},
        ),
        (None, None, "stdio", {"transport": "stdio"}),
    ],
)
def test_transport_precedence(monkeypatch, databricks, port, transport, expected):
    from unittest.mock import Mock

    from spatcat_mcp import app

    for name, value in (("DATABRICKS_APP_PORT", databricks), ("PORT", port)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    monkeypatch.setattr(settings, "mcp_transport", transport)
    monkeypatch.setattr(settings, "mcp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "mcp_port", 8123)
    run = Mock()
    monkeypatch.setattr(mcp, "run", run)
    app.main()
    run.assert_called_once_with(**expected)
