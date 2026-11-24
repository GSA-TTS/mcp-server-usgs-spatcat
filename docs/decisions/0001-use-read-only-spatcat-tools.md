---
title: "Use read-only tools for the Spatial Data Catalog"
description: "AI-assisted draft documenting the initial API integration boundary"
status: proposed
tier: 2
date: "2026-11-24"
nist_controls: ["AC-6", "SC-7", "SC-8", "SI-10", "SA-11"]
risk_treatment: mitigate
---

# Use read-only tools for the Spatial Data Catalog

## Context and problem statement

The user approved ten core tools built on the existing Python/FastMCP template
and explicitly requested that `app.py` retain its current transport selection.
API documentation was supplied, but origins, credentials, detailed capability
schemas, and deployed authentication controls have not been supplied.

## Decision drivers

- Retain the existing stack and one-tool-per-file registration pattern.
- Enable discovery before analysis, with visible per-layer failures.
- Keep catalog mutation, direct S3 access, and shapefile uploads out of scope.
- Prevent caller-controlled destinations and credential leakage.

## Considered options

1. Ten focused tools wrapping the documented read-only endpoints.
2. A combined parcel-analysis workflow hiding discovery and layer selection.
3. Full endpoint coverage including writes and direct S3 operations.

## Decision outcome

Implement option 1 in `src/example_server/`, leaving `app.py` unchanged.
Typed request parameters map to upstream names; a typed result envelope preserves
upstream objects/arrays rather than inventing undocumented schemas. CRS validation
provisionally assumes two-dimensional WGS84 and requires upstream confirmation.
Each API base and bearer credential is operator-configured and independently
scoped. HTTP redirects and inherited proxies are disabled. DNS answers must be
public and TCP uses the validated IP; TLS retains the original hostname.
The isolated network adapter uses httpx/httpcore internals because httpx does not
expose backend injection publicly; upgrades require regression testing.

## Consequences

- Agents can compose search, metadata inspection, intersection, distance,
  attribute filtering, and module-based point analysis.
- Read-only analysis can still incur backend compute cost; gateway authorization,
  rate limiting, and exact-origin egress controls are deployment prerequisites.
- Raster distance is explicitly unsupported. WMS/OGC support remains per-layer.
- No live API validation or production readiness is claimed.
- Template server name, prompts, resources, and HTTP transport remain unchanged.
- Decision makers, FIPS impact level, and ATO applicability require human review;
  this AI-authored record is proposed, not an approval or compliance certification.
