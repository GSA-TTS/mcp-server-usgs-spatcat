"""Exercise skills through MCP, including isolation and access boundaries."""

from pathlib import Path

import pytest
from fastmcp import Client, FastMCP
from fastmcp.skills import SkillsClientExtension
from mcp.shared.exceptions import MCPError

from spatcat_mcp import documentation
from spatcat_mcp.app import mcp

URI = "skill://spatcat-data-preparation/SKILL.md"
SOURCE = Path(__file__).parents[1] / "skills/spatcat-data-preparation/SKILL.md"


async def test_skill_extension_discovery_and_verified_retrieval():
    async with Client(mcp, extensions=[SkillsClientExtension()]) as client:
        entries = await client.list_skills()
        assert len(entries) == 1
        assert str(entries[0].uri) == URI
        assert entries[0].frontmatter.name == documentation.SKILL_NAME
        skill = await client.read_skill(URI)
        assert skill.files == {"SKILL.md": SOURCE.read_bytes()}
        assert "GeoParquet" in skill.description
        assert len(await client.list_tools()) == 10


async def test_resource_discovery_and_fallback_retrieval():
    async with Client(mcp) as client:
        resources = await client.list_resources()
        skills = {str(r.uri) for r in resources if str(r.uri).startswith("skill://")}
        assert skills == {URI, "skill://spatcat-data-preparation/_manifest"}
        content = await client.read_resource(URI)
        assert content[0].text == SOURCE.read_text()
        downloaded = await client.read_skill(URI)
        assert downloaded.files["SKILL.md"] == SOURCE.read_bytes()


@pytest.mark.parametrize(
    "uri",
    [
        "skill://mcp-builder/SKILL.md",
        "skill://spatcat-data-preparation/.env",
        "skill://spatcat-data-preparation/missing.md",
        "skill://spatcat-data-preparation/../.env",
        "skill://spatcat-data-preparation/%2e%2e/.env",
        "skill://spatcat-data-preparation/%2e%2e%2f.env",
        "skill://spatcat-data-preparation/../../.agents/skills/mcp-builder/SKILL.md",
    ],
)
async def test_unapproved_resource_paths_are_not_readable(uri):
    async with Client(mcp) as client:
        with pytest.raises(MCPError, match="Resource not found"):
            await client.read_resource(uri)


def source_fixture(tmp_path, monkeypatch):
    module = tmp_path / "src/spatcat_mcp/documentation.py"
    monkeypatch.setattr(documentation, "__file__", str(module))
    root = tmp_path / "skills" / documentation.SKILL_NAME
    root.mkdir(parents=True)
    (root / "SKILL.md").write_bytes(SOURCE.read_bytes())
    return root


def test_registration_is_explicit_and_rejects_extra_files(tmp_path, monkeypatch):
    root = source_fixture(tmp_path, monkeypatch)
    development = tmp_path / ".agents/skills/mcp-builder"
    development.mkdir(parents=True)
    (development / "SKILL.md").write_text("not a valid skill")
    documentation.register_skills(FastMCP("isolated"))
    (root / ".env").write_text("test-marker-not-a-secret")
    with pytest.raises(ValueError, match="Only the approved skill"):
        documentation.load_skill()


@pytest.mark.parametrize("root_link", [False, True])
def test_skill_symlinks_fail_closed(tmp_path, monkeypatch, root_link):
    root = source_fixture(tmp_path, monkeypatch)
    if root_link:
        target = root.with_name("outside")
        root.rename(target)
        root.symlink_to(target, target_is_directory=True)
    else:
        (root / "linked.md").symlink_to(SOURCE.absolute())
    with pytest.raises(ValueError, match="symlink"):
        documentation.load_skill()


def test_invalid_source_does_not_fall_back(tmp_path, monkeypatch):
    root = source_fixture(tmp_path, monkeypatch)
    (root / "SKILL.md").write_text("invalid frontmatter")
    with pytest.raises(ValueError, match="frontmatter"):
        documentation.load_skill()


async def test_hidden_skill_is_not_discoverable():
    server = FastMCP("hidden")
    documentation.register_skills(server)
    server.disable(keys={f"resource:{URI}@"})
    async with Client(server, extensions=[SkillsClientExtension()]) as client:
        assert await client.list_skills() == []
        with pytest.raises(MCPError, match="Resource not found"):
            await client.read_resource(URI)
