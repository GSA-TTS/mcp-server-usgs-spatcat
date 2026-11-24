# GSA MCP Hackathon — Server Template

## USGS Spatial Data Catalog tools

This repository now exposes ten read-only tools, prefixed `usgs_spatcat_`:
`search_layers`, `get_layer`, `list_spatial_layers`, `get_sublayers`,
`get_native_resolution`, `intersect_layers`, `distance_to_layers`,
`query_attributes`, `list_analysis_modules`, and `analyze_point`.

Set `SPATCAT_CATALOG_URL` and `SPATCAT_ANALYSIS_URL` in your local `.env` to
approved HTTPS API bases including `/spatcat-api` and `/spatcat-analysis`.
Optional `SPATCAT_CATALOG_TOKEN` and `SPATCAT_ANALYSIS_TOKEN` are independently
scoped bearer credentials. No live API hostname is assumed.

On Linux, keep the environment separate from a macOS environment:

```bash
UV_PROJECT_ENVIRONMENT=.venv-linux uv sync --frozen --group dev
.venv-linux/bin/python -m spatcat_mcp.app
.venv-linux/bin/pytest tests/ -q
.venv-linux/bin/ruff check .
```

`app.py` and its transport precedence are unchanged: a platform-injected port
selects HTTP, explicit `MCP_TRANSPORT=streamable-http` selects HTTP, otherwise
the server uses stdio. The template server display name is also unchanged.
The original example tool is no longer registered; example resources/prompts
remain template placeholders, not USGS data.

### Data preparation skill over MCP

The Python package is `spatcat_mcp`; the distribution and command remain
`example-server`. FastMCP is pinned to 4.2.5 for its documented skills API.
The server serves one AI-authored documentation skill from
[`skills/spatcat-data-preparation/SKILL.md`](skills/spatcat-data-preparation/SKILL.md):
format selection, GeoParquet/PMTiles/COG preparation and validation, permission-gated
S3 delivery planning, and registration preparation. All commands in it are
suggestions, not completed actions. No conversion, upload, or write tools were added.

Read it using MCP resources at `skill://spatcat-data-preparation/SKILL.md`, or
use FastMCP's Skills extension for discovery and verified whole-skill retrieval:

```python
from fastmcp import Client
from fastmcp.skills import SkillsClientExtension

# An in-process example; use your approved server connection in a real client.
from spatcat_mcp.app import mcp

async def read_preparation_skill():
    async with Client(mcp, extensions=[SkillsClientExtension()]) as client:
        entries = await client.list_skills()
        skill = await client.read_skill("skill://spatcat-data-preparation/SKILL.md")
        return entries, skill
```

Clients without the extension can list/read resources, or use FastMCP
`list_skill_resources()` and `read_skill()` through the manifest fallback.
Tool-only clients will not discover this skill: no resource-to-tools transform
is enabled, so the ten domain tools remain unchanged. Only this named skill and
its `SKILL.md` are allowed; `.agents/skills/` is never scanned. The file is included
in wheels and source distributions. Restart the server after editing it.
AI-generated code and documentation require human review before production use.

Verification: `.venv-linux/bin/pytest tests/ -q`,
`.venv-linux/bin/ruff check src tests`,
`.venv-linux/bin/ruff format --check src tests`, and
`uv build --python .venv-linux/bin/python` (build dependency downloads require approval).

### Query workflow and limitations

Search for layers, inspect metadata/capabilities and Esri sublayers, then run
spatial or attribute queries. Discover module IDs before point analysis.
GeoJSON is validated as two-dimensional WGS84 (longitude, latitude), with a
10,000-position budget; reprojection and topology repair are not performed.
Confirm this CRS assumption with the upstream operator before live use.

Results have `source`, `retrieved_at`, `data`, and `warnings`. `data` preserves
the upstream object/array, including per-layer errors and pagination metadata.
No undocumented response schemas, total counts, or dataset freshness dates are
invented. Catalog `limit` defaults to 20 and is capped at 100. Only the catalog
endpoint has documented pagination; other tools do not fabricate pagination.
Responses exceeding 5 MB fail explicitly rather than silently truncate.

Raster distance is not implemented by the API. S3 polygon distance uses the
centroid and ignores the buffer; Esri/WFS distance uses closest approach.
WMS and OGC support must be checked per layer. Capability metadata is returned
without guessing undocumented boolean field names or inferring support solely
from service type. Upstream unsupported-operation/partial-failure responses
remain visible; no-result queries are not determinations of site safety.

Attribute filters support field-to-literal comparisons, `IN`, `LIKE`,
`IS [NOT] NULL`, `AND`/`OR`, and bounded parentheses. Functions, comments,
subqueries, and SQL statements are rejected. `out_fields` accepts `*` or a
comma-separated identifier list. This is validation of an upstream Esri filter,
not permission to execute SQL against a database.

### Security and deployment boundary

Tool callers cannot choose HTTP origins. Origins are operator configuration;
HTTPS/443, disabled redirects/proxy inheritance, response limits, request
deadlines, and connection-time public-IP validation apply to every USGS API
request. DNS answers are validated and the TCP connection uses the validated
IP while TLS verifies the original hostname. The network adapter touches
httpx/httpcore internals and is tested against `uv.lock`; re-test on upgrades.
No request/response bodies, coordinates, or credentials are logged by these
tools. The API may perform costly backend analysis despite read-only intent.

Before remote deployment, configure MCP authentication, per-tool authorization,
rate limiting at the gateway, exact-origin egress allowlisting, and log access
controls. Existing template HTTP transport is not an authorization boundary.
These deployment changes are intentionally not part of this tool-only change.
Do not expose the template HTTP server publicly without those controls.
Live validation requires approved API URLs, credentials if needed, and explicit
network permission. AI-generated changes require human review before production.

---

A ready-to-run starter for building a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server in Python, plus deployment kits for **IBM Cloud (watsonx Orchestrate)** and **Databricks**.

Built with [FastMCP](https://github.com/jlowin/fastmcp) and [uv](https://docs.astral.sh/uv/). If you have never built an MCP server before, start with **[QUICKSTART.md](QUICKSTART.md)**.

---

## What is an MCP server?

An MCP server exposes **tools** (functions the model can call), **prompts** (reusable conversation starters), and **resources** (data the model can read) to an AI client such as Claude Desktop, Claude Code, or an agent platform like watsonx Orchestrate. You write the tools; the client's model decides when to call them.

This template gives you a working server with one example of each, so you can replace the examples with your own service and deploy.

---

## Repo structure

```
mcp-hackathon-template/
├── README.md                  # This file
├── QUICKSTART.md              # 5-minute clone → run → connect walkthrough
├── main.py                    # Local entry point (uv run python main.py)
├── pyproject.toml             # Package + dependencies (uv)
├── requirements.txt           # Mirror of runtime deps (for buildpack hosts)
├── Dockerfile                 # Container image (streamable-HTTP, port 8080)
├── manifest.yaml              # cloud.gov (Cloud Foundry) deploy
├── server.json                # MCP registry metadata
├── .env.example               # Copy to .env for local dev
├── .github/workflows/ci.yml   # Lint + test on push/PR
├── docs/                      # Vendor-contributed reference materials
├── src/
│   └── example_server/        # ← rename to your service
│       ├── app.py             # Thin entry point: builds FastMCP, picks transport
│       ├── config.py          # Settings from env vars / .env
│       ├── models.py          # Pydantic models & enums for tool params
│       ├── utils.py           # Shared helpers (HTTP client, pagination)
│       ├── routes.py          # HTTP-only routes (/health, /version)
│       ├── tools/             # ONE FILE PER TOOL
│       │   ├── __init__.py    #   register_tools(mcp) aggregator
│       │   └── example_tool.py
│       ├── prompts/
│       │   ├── __init__.py    #   register_prompts(mcp) aggregator
│       │   └── example.py
│       └── resources/
│           ├── __init__.py    #   register_resources(mcp) aggregator
│           └── example.py
├── tests/                     # Import + registration smoke tests
├── eval/                      # Stub → build a Phoenix eval harness (see mcp-eval skill)
└── deploy/
    ├── README.md              # Which deployment kit to use
    ├── ibm/                   # watsonx Orchestrate: 3 kits (see below)
    └── databricks/            # Databricks Apps kit
```

---

## Getting started

### Prerequisites
- [uv](https://docs.astral.sh/uv/) — `pip install uv` or `brew install uv`

### Install and run

```bash
cp .env.example .env
uv sync
uv run python main.py
```

The server starts in **stdio** mode — it talks JSON-RPC over stdin/stdout, which is how local clients (Claude Desktop, Claude Code) launch it. See [QUICKSTART.md](QUICKSTART.md) to connect a client.

### Verify

```bash
uv sync --group dev
uv run pytest tests/ -v      # tests
uv run ruff check .          # lint
```

---

## The one-tool-per-file pattern

Each tool lives in its own file under `src/example_server/tools/` and exposes a `register(mcp)` function. `tools/__init__.py` calls each one from a single `register_tools(mcp)`. This keeps the tool list scannable and lets you add or remove an integration by touching two files.

**Step 1 — create `src/example_server/tools/my_tool.py`:**

```python
from typing import Annotated
from urllib.parse import quote
from fastmcp import FastMCP

from example_server.utils import fetch_json


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="example_get_thing",
        annotations={
            "title": "Get a thing",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def get_thing(thing_id: Annotated[str, "The ID to fetch."]) -> dict:
        """One-line summary. Document the data source, its update cadence,
        and the return shape here — the model reads this docstring."""
        safe_id = quote(thing_id, safe="")
        return await fetch_json(f"things/{safe_id}")
```

**Step 2 — wire it up in `tools/__init__.py`:**

```python
from example_server.tools import example_tool, my_tool

def register_tools(mcp) -> None:
    example_tool.register(mcp)
    my_tool.register(mcp)  # ← add this line
```

**Step 3 — add any API key** as a typed field in `config.py` and document the env var in `.env.example`.

Prompts (`prompts/`) and resources (`resources/`) follow the exact same `register(mcp)` + aggregator pattern.

---

## Rename the package

Before publishing your server, rename `example_server` to your service (e.g. `census_mcp`):

1. Rename the folder `src/example_server/` → `src/<your_name>/`.
2. Update `pyproject.toml`: the `[project].name`, `[project.scripts]`, and `[tool.hatch.build.targets.wheel].packages`.
3. Find-and-replace `example_server` across `src/`, `tests/`, `main.py`, `Dockerfile`, and `manifest.yaml`.

---

## Tool design tips (federal data)

- **Return structured data, not prose.** Return dicts/lists with consistent keys and let the model narrate.
- **Document freshness.** Federal datasets lag; state the update frequency and "as-of" date in the docstring.
- **Expose pagination.** Use `PaginationParams` / `paginate()` from `utils.py`, and return `has_more` / `next_offset`.
- **Use explicit timeouts.** `utils.fetch_json` defaults to 30s.
- **Actionable errors.** Return an error dict with a `hint`, not a raw stack trace.
- **Constrain outbound requests.** Keep API origins in operator-controlled code or configuration, pass only validated relative paths to `fetch_json`, and encode path segments. Never pass a tool-supplied URL directly to an HTTP client.
- **Treat redirects and DNS as security boundaries.** Redirects are disabled by default. A server that must fetch caller-supplied URLs needs connection-time IP validation on every hop plus network egress controls; a one-time DNS check is not sufficient.
- **Keep sensitive data out of errors and logs.** Do not expose or log upstream bodies, headers, full URLs, query strings, credentials, stack traces, SSNs, dates of birth, or addresses.

---

## Deploying

Local development uses stdio. To share your server with an agent platform, deploy it and register it. See **[deploy/README.md](deploy/README.md)** for a chooser, then:

- **IBM watsonx Orchestrate** — [deploy/ibm/](deploy/ibm/) (three kits: local stdio toolkit, Code Engine build-from-Git, and prebuilt image).
- **Databricks Apps** — [deploy/databricks/](deploy/databricks/).

Both read the same server code; `app.py` automatically serves HTTP when the platform injects a port.

---

## Partner reference materials

The [`docs/`](docs/) directory contains educational reference materials that
IBM and Databricks may contribute for hackathon participants. Vendor-contributed
materials do not represent the views, positions, or policies of GSA or the
United States Government.

GSA does not endorse any commercial product, service, or enterprise referenced
in these materials. Reference to a commercial product, service, or enterprise
does not constitute or imply endorsement, recommendation, or favoring by GSA or
the United States Government. These materials are provided for educational
purposes only. See [`docs/README.md`](docs/README.md) for the complete notice and
contribution guidance.

---

## Evaluations

Measuring how well an LLM can use your tools is the real test of server quality. This template intentionally does **not** ship an eval harness — see [eval/README.md](eval/README.md) for how to build one with the `mcp-eval` skill.

---

## License

[MIT](LICENSE). See [SECURITY.md](SECURITY.md) for the vulnerability disclosure policy and hackathon security notes.
