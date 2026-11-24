"""Deterministic outbound and redaction tests; no real network connections."""

from __future__ import annotations

import httpcore
import httpx
import pytest
from fastmcp.exceptions import ToolError

from spatcat_mcp import api


@pytest.fixture
def fake_api(monkeypatch):
    calls = []
    response = httpx.Response(200, json={"results": []})

    async def handler(request):
        calls.append(request)
        return response

    monkeypatch.setattr(api, "transport", lambda: httpx.MockTransport(handler))
    monkeypatch.setattr(
        api.settings, "spatcat_catalog_url", "https://catalog.usgs.gov/spatcat-api"
    )
    monkeypatch.setattr(
        api.settings,
        "spatcat_analysis_url",
        "https://analysis.usgs.gov/spatcat-analysis",
    )
    return calls, response


@pytest.mark.asyncio
async def test_api_get_and_post(fake_api):
    calls, _ = fake_api
    result = await api.request("catalog", "GET", "layers", params={"limit": 20})
    await api.request("analysis", "POST", "analysis/point", body={"lng": 0, "lat": 0})
    assert result.data == {"results": []}
    assert result.retrieved_at.endswith("+00:00")
    assert str(calls[0].url) == "https://catalog.usgs.gov/spatcat-api/layers?limit=20"
    assert calls[1].method == "POST"
    assert calls[1].url.host == "analysis.usgs.gov"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [301, 400, 401, 403, 404, 429, 500])
async def test_status_sanitization(fake_api, status, caplog):
    calls, response = fake_api
    response.status_code = status
    response.headers["location"] = "https://169.254.169.254/secret"
    sensitive = "SSN 123-45-6789 DOB 1940-01-01 token=secret"
    response._content = sensitive.encode()
    with pytest.raises(ToolError) as error:
        await api.request("catalog", "GET", "layers")
    assert sensitive not in str(error.value)
    assert sensitive not in caplog.text
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content,media_type",
    [
        (b"not-json token=secret", "application/json"),
        (b"null", "application/json"),
        (b"{}", "text/html"),
    ],
)
async def test_invalid_responses(fake_api, content, media_type):
    _, response = fake_api
    response._content = content
    response.headers["content-type"] = media_type
    with pytest.raises(ToolError, match="invalid_response"):
        await api.request("catalog", "GET", "layers")


@pytest.mark.asyncio
async def test_response_size_limit(fake_api, monkeypatch):
    monkeypatch.setattr(api, "MAX_RESPONSE_BYTES", 2)
    with pytest.raises(ToolError, match="response_too_large"):
        await api.request("catalog", "GET", "layers")


@pytest.mark.parametrize(
    "url",
    [
        "http://public.example",
        "https://user:secret@public.example",
        "https://public.example:8080",
        "https://public.example?token=x",
        "https://public.example/#x",
        "https://public.example/../admin",
        "https://public.example/%2e%2e/admin",
        "https://public.example:bad",
    ],
)
def test_invalid_configuration(url):
    with pytest.raises(ToolError, match="invalid_configuration"):
        api.validate_base_url(url, "catalog")


@pytest.mark.asyncio
async def test_missing_configuration(monkeypatch):
    monkeypatch.setattr(api.settings, "spatcat_catalog_url", "")
    with pytest.raises(ToolError, match="configuration_required"):
        await api.request("catalog", "GET", "layers")


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "0.0.0.0",
        "224.0.0.1",
        "240.0.0.1",
        "::1",
        "::",
        "fe80::1",
        "fc00::1",
        "ff02::1",
        "::ffff:127.0.0.1",
        "192.0.2.1",
    ],
)
def test_non_public_addresses_denied(address):
    assert not api.is_public_ip(address)


@pytest.mark.asyncio
async def test_dns_rebinding_connects_validated_ip(monkeypatch):
    calls = []

    async def resolve(*args, **kwargs):
        return [(2, 1, 6, "", ("8.8.8.8", 443))]

    class Backend:
        async def connect_tcp(self, host, *args):
            calls.append(host)
            return "stream"

    monkeypatch.setattr(api.anyio, "getaddrinfo", resolve)
    monkeypatch.setattr(api, "AnyIOBackend", Backend)
    assert (
        await api.PublicNetworkBackend().connect_tcp("approved.example", 443, 1)
        == "stream"
    )
    assert calls == ["8.8.8.8"]  # Never re-resolve the attacker-controlled hostname.


@pytest.mark.asyncio
async def test_mixed_dns_answers_fail_closed(monkeypatch):
    async def resolve(*args, **kwargs):
        return [(2, 1, 6, "", (ip, 443)) for ip in ["8.8.8.8", "127.0.0.1"]]

    monkeypatch.setattr(api.anyio, "getaddrinfo", resolve)
    with pytest.raises(httpcore.ConnectError):
        await api.PublicNetworkBackend().connect_tcp("approved.example", 443, 1)


def test_transport_backend_and_retry_policy():
    transport = api.transport()
    assert isinstance(transport._pool._network_backend, api.PublicNetworkBackend)
    assert transport._pool._retries == 0


@pytest.mark.asyncio
async def test_credentials_stay_scoped(fake_api, monkeypatch):
    from pydantic import SecretStr

    calls, _ = fake_api
    monkeypatch.setattr(
        api.settings, "spatcat_catalog_token", SecretStr("catalog-secret")
    )
    monkeypatch.setattr(
        api.settings, "spatcat_analysis_token", SecretStr("analysis-secret")
    )
    await api.request("catalog", "GET", "layers")
    await api.request("analysis", "GET", "analysis/modules")
    assert calls[0].headers["authorization"] == "Bearer catalog-secret"
    assert calls[1].headers["authorization"] == "Bearer analysis-secret"
