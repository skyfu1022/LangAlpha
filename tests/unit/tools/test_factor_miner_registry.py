"""Tests for factor-miner skill registry entry and sandbox dependencies."""

from __future__ import annotations

from src.ptc_agent.agent.middleware.skills.registry import (
    SKILL_REGISTRY,
    get_command_to_skill_map,
    get_skill,
)
from src.ptc_agent.core.sandbox._defaults import DEFAULT_DEPENDENCIES


# ---------------------------------------------------------------------------
# Skill registry tests
# ---------------------------------------------------------------------------


def test_factor_miner_registered():
    """factor-miner is in the skill registry."""
    assert "factor-miner" in SKILL_REGISTRY
    skill = SKILL_REGISTRY["factor-miner"]
    assert skill.name == "factor-miner"
    assert skill.exposure == "ptc"
    assert skill.command == "factor-miner"
    assert len(skill.tools) == 4


def test_factor_miner_command_mapping():
    """factor-miner slash command maps correctly."""
    cmd_map = get_command_to_skill_map(mode="ptc")
    assert cmd_map.get("factor-miner") == "factor-miner"


def test_factor_miner_skill_md_path():
    """skill_md_path points to SKILL.md."""
    skill = get_skill("factor-miner", mode="ptc")
    assert skill is not None
    assert skill.skill_md_path == "skills/factor_miner/SKILL.md"


# ---------------------------------------------------------------------------
# Sandbox dependency smoke test
# ---------------------------------------------------------------------------


def test_phandas_in_default_dependencies():
    """phandas is included in sandbox default dependencies."""
    assert "phandas" in DEFAULT_DEPENDENCIES
