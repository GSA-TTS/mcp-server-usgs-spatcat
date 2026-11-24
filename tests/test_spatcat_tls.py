"""Exercise the real httpx/httpcore adapter with a fake TLS-capable stream."""

import logging

import httpcore
import httpx
import pytest

from spatcat_mcp import api


@pytest.mark.asyncio
async def test_pinned_connection_preserves_tls_hostname(monkeypatch, caplog):
    events = []

    class Stream(httpcore.AsyncNetworkStream):
        async def read(self, max_bytes, timeout=None):
            return (
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                b"Content-Length: 2\r\n\r\n{}"
            )

        async def write(self, buffer, timeout=None):
            events.append(("write", buffer))

        async def aclose(self):
            pass

        async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            events.append(("tls", server_hostname, ssl_context.check_hostname))
            return self

        def get_extra_info(self, info):
            return None

    class Backend:
        async def connect_tcp(self, host, *args):
            events.append(("tcp", host))
            return Stream()

    async def resolve(*args, **kwargs):
        return [(2, 1, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(api.anyio, "getaddrinfo", resolve)
    monkeypatch.setattr(api, "AnyIOBackend", Backend)
    caplog.set_level(logging.DEBUG, logger="httpcore")
    caplog.set_level(logging.INFO, logger="httpx")
    async with httpx.AsyncClient(transport=api.transport(), trust_env=False) as client:
        response = await client.get(
            "https://approved.example/layers?query=private-search"
        )
    assert response.json() == {}
    assert ("tcp", "8.8.8.8") in events
    assert ("tls", "approved.example", True) in events
    assert any(
        b"Host: approved.example" in item[1] for item in events if item[0] == "write"
    )
    assert "private-search" not in caplog.text
    assert "approved.example" not in caplog.text
