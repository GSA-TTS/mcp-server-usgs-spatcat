"""Bounded API calls to operator-configured origins; sanitized MCP failures."""

from __future__ import annotations

import ipaddress
import json
import logging
import socket
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlsplit

import anyio
import httpcore
import httpx
from fastmcp.exceptions import ToolError
from httpcore._backends.anyio import AnyIOBackend

from spatcat_mcp.config import settings
from spatcat_mcp.models import ToolResult
from spatcat_mcp.utils import MAX_RESPONSE_BYTES, _validate_relative_path


class SafeHTTPLogFilter(logging.Filter):
    """Prevent library diagnostics from exposing URLs, headers, or payloads."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = "HTTP client diagnostic (details redacted)."
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


# Library diagnostics can include caller-selected query values even though the
# tools themselves never log bodies. Preserve events, redact message contents.
for logger_name in (
    "httpx",
    "httpcore.connection",
    "httpcore.http11",
    "httpcore.http2",
    "httpcore.proxy",
    "httpcore.socks",
):
    logging.getLogger(logger_name).addFilter(SafeHTTPLogFilter())


class PublicNetworkBackend(httpcore.AsyncNetworkBackend):
    """Connect to validated IPs, preserving httpcore's original-host TLS/SNI.

    All DNS answers must be public. No hostname is resolved again at connection
    time, closing the DNS preflight/connection gap. No Unix sockets are allowed.
    """

    async def connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        with anyio.fail_after(timeout):
            answers = await anyio.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            addresses = list(dict.fromkeys(answer[4][0] for answer in answers))
            if not addresses or any(not is_public_ip(ip) for ip in addresses):
                raise httpcore.ConnectError("Destination denied by network policy.")
            return await AnyIOBackend().connect_tcp(
                addresses[0], port, timeout, local_address, socket_options
            )

    async def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("Unix sockets are not permitted.")

    async def sleep(self, seconds):
        await anyio.sleep(seconds)


def is_public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast and not address.is_reserved


def validate_base_url(value: str, source: str) -> str:
    if not value:
        raise ToolError(
            f"configuration_required: Set SPATCAT_{source.upper()}_URL "
            "to the approved HTTPS API base."
        )
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError:
        port = -1
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.query
        or parsed.fragment
        or "\\" in value
        or "%" in value
        or any(segment in {".", ".."} for segment in parsed.path.split("/"))
    ):
        raise ToolError("invalid_configuration: Use an HTTPS API base on port 443.")
    return value.rstrip("/") + "/"


def transport() -> httpx.AsyncHTTPTransport:
    # httpx has no public network-backend injection API. Keep this adapter
    # isolated and regression-tested against the repository's locked versions.
    result = httpx.AsyncHTTPTransport(retries=0)
    result._pool._network_backend = PublicNetworkBackend()
    return result


async def request(
    source: Literal["catalog", "analysis"],
    method: Literal["GET", "POST"],
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> ToolResult:
    safe_path = _validate_relative_path(path)
    base = validate_base_url(getattr(settings, f"spatcat_{source}_url"), source)
    token = getattr(settings, f"spatcat_{source}_token").get_secret_value()
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with anyio.fail_after(settings.spatcat_timeout_seconds):
            async with httpx.AsyncClient(
                base_url=base,
                headers=headers,
                transport=transport(),
                follow_redirects=False,
                trust_env=False,
                timeout=settings.spatcat_timeout_seconds,
            ) as client:
                async with client.stream(
                    method, safe_path, params=params, json=body
                ) as response:
                    if response.status_code >= 300:
                        raise status_error(response.status_code)
                    media_type = response.headers.get("content-type", "").split(";")[0]
                    if media_type != "application/json" and not media_type.endswith(
                        "+json"
                    ):
                        raise ToolError("invalid_response: API did not return JSON.")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise ToolError(
                                "response_too_large: Narrow the layer selection, "
                                "geometry, fields, or result limit."
                            )
                        content.extend(chunk)
                    data = json.loads(content)
                    if not isinstance(data, (dict, list)):
                        raise ToolError(
                            "invalid_response: Expected an object or array."
                        )
                    return ToolResult(
                        source=source,
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        data=data,
                        warnings=warnings or [],
                    )
    except ToolError:
        raise
    except (TimeoutError, httpx.TimeoutException):
        raise ToolError("upstream_timeout: Narrow the query and retry later.") from None
    except (ValueError, UnicodeError, httpx.DecodingError):
        raise ToolError("invalid_response: API returned malformed data.") from None
    except (httpx.RequestError, httpcore.NetworkError, OSError):
        raise ToolError(
            "upstream_unavailable: Check the approved API configuration "
            "and egress policy."
        ) from None


def status_error(status: int) -> ToolError:
    hints = {
        400: "invalid_request: Check layer capabilities and query parameters.",
        401: "authentication_required: Check the API-specific credential.",
        403: "access_denied: Request access from the API operator.",
        404: "not_found: Rediscover the layer or check the API base path.",
        429: "rate_limited: Wait before retrying; reduce request frequency.",
    }
    return ToolError(
        hints.get(status, f"upstream_error: API returned status {status}.")
    )
