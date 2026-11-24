"""Serve the single approved documentation skill, never agent-development skills."""

from pathlib import Path

from fastmcp import FastMCP, Skill
from fastmcp.skills.provider import SkillCatalogProvider

SKILL_NAME = "spatcat-data-preparation"


def load_skill() -> Skill:
    """Load a fixed source folder or the skill shipped in an installed wheel.

    Invalid source content fails closed; it does not fall back to another copy.
    The directory snapshot rejects symlinks and non-regular files.
    """
    module = Path(__file__).absolute()
    if module.parent.parent.name == "src":
        source = module.parents[2] / "skills" / SKILL_NAME
        skill = Skill.from_directory(source)
    else:
        skill = Skill.from_package("spatcat_mcp", f"_skills/{SKILL_NAME}")
    if skill.name != SKILL_NAME or set(skill.files) != {"SKILL.md"}:
        raise ValueError("Only the approved skill and its SKILL.md may be served")
    return skill


def register_skills(mcp: FastMCP) -> None:
    """Add resources and Skills-extension discovery without adding tools."""
    mcp.add_provider(SkillCatalogProvider([load_skill()]))
