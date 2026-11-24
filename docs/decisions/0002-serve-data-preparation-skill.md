---
title: "Use FastMCP skills for data preparation documentation"
description: "AI-assisted proposed decision for a narrowly scoped MCP documentation interface"
status: proposed
tier: 2
date: "2026-11-24"
nist_controls: ["AC-6", "CM-3", "SA-11", "SI-10"]
risk_treatment: mitigate
related_files: ["skills/spatcat-data-preparation/SKILL.md", "src/spatcat_mcp/documentation.py", "tests/test_skills.py"]
---

# Use FastMCP skills for data preparation documentation

## Context and problem statement

Users need preparation, validation, upload-permission, and registration guidance
without adding execution or catalog-write tools. The operator approved the scoped
implementation plan and confirmed `spatcat_mcp` as the intentional Python package.
The distribution and CLI remain `example-server`. Decision-maker identity, FIPS
impact level, and ATO relevance are not asserted; human review is required.

## Decision drivers

- Serve one authoritative skill separate from development-agent instructions.
- Preserve ten domain tools and existing transport precedence.
- Load documentation in both source checkouts and installed distributions.
- Prevent incidental files, secrets, and path traversal from becoming resources.

## Considered options

1. One explicit `SkillCatalogProvider` with a validated skill snapshot.
2. A directory provider scanning a general development skills root.
3. New conversion/upload/registration tools or a resource-to-tools transform.

## Decision outcome

Choose option 1 using the documented FastMCP 4.2 API, pinned to the existing
locked 4.2.5 version. Keep the source at `skills/spatcat-data-preparation/SKILL.md`
and include that same file as wheel package data. The loader accepts only the
named skill with exactly `SKILL.md`; source symlinks and invalid content fail
closed. Installed packages use `Skill.from_package`. No caller controls paths.
Provider registration adds resources and Skills-extension discovery, not tools.
Do not add `ResourcesAsTools`: clients must support resources or the extension.

## Consequences

- Changes are loaded once; restarting the server publishes updated instructions.
- Tests exercise MCP discovery, verified retrieval, path/hiding boundaries, and
  transport behavior; installed-wheel checks cover package-data wiring.
- Extra reference files require an explicit allowlist/packaging change and review.
- Suggested commands are not executed by serving the skill. Uploads, overwrites,
  installations, and access changes require separate explicit authorization.
- Existing remote authentication/gateway deployment prerequisites remain unchanged;
  adding documentation is not production deployment approval.
