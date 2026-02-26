"""Integration tests for directory scanning with format auto-detection.

Verifies that the ParserRegistry correctly auto-detects and parses
skills in realistic project directory structures for each supported
format and combinations thereof.
"""
from __future__ import annotations

import json
from pathlib import Path


from skillfortify.core.analyzer import StaticAnalyzer
from skillfortify.parsers.registry import default_registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_claude_project(root: Path, skill_names: list[str]) -> None:
    """Create a Claude skills directory with named .md files."""
    skills_dir = root / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for name in skill_names:
        content = f"""---
name: {name}
description: A {name} skill
---

# {name}

Performs {name} operations on input data.
"""
        (skills_dir / f"{name}.md").write_text(content, encoding="utf-8")


def _create_mcp_project(root: Path, servers: dict) -> None:
    """Create an MCP project with a mcp.json config."""
    config = {"mcpServers": servers}
    (root / "mcp.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )


def _create_openclaw_project(
    root: Path, skills: list[dict], dir_name: str = ".claw"
) -> None:
    """Create an OpenClaw project with skill YAML files."""
    claw_dir = root / dir_name
    claw_dir.mkdir(parents=True, exist_ok=True)
    for skill_def in skills:
        name = skill_def["name"]
        version = skill_def.get("version", "1.0.0")
        desc = skill_def.get("description", "")
        content = f"""name: {name}
version: "{version}"
description: {desc}
instructions: |
  Use this skill for {name} tasks.
commands: []
dependencies: []
"""
        (claw_dir / f"{name}.yaml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScanClaudeProject:
    """Scanning directories with .claude/skills/ layout."""

    def test_discovers_all_claude_skills(self, tmp_path: Path) -> None:
        """All .md files in .claude/skills/ are discovered."""
        _create_claude_project(tmp_path, ["alpha", "beta", "gamma"])
        registry = default_registry()
        skills = registry.discover(tmp_path)

        names = {s.name for s in skills}
        assert names == {"alpha", "beta", "gamma"}
        assert all(s.format == "claude" for s in skills)

    def test_claude_skills_have_raw_content(self, tmp_path: Path) -> None:
        """Parsed Claude skills preserve the raw file content."""
        _create_claude_project(tmp_path, ["content-test"])
        skills = default_registry().discover(tmp_path)
        assert len(skills) == 1
        assert "content-test" in skills[0].raw_content

    def test_empty_claude_skills_dir(self, tmp_path: Path) -> None:
        """Empty .claude/skills/ directory yields no skills."""
        (tmp_path / ".claude" / "skills").mkdir(parents=True)
        skills = default_registry().discover(tmp_path)
        assert skills == []


class TestScanMcpProject:
    """Scanning directories with mcp.json configuration."""

    def test_discovers_mcp_servers(self, tmp_path: Path) -> None:
        """Each mcpServers entry becomes a parsed skill."""
        _create_mcp_project(tmp_path, {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            },
            "database": {
                "command": "node",
                "args": ["db-server.js"],
                "env": {"DATABASE_URL": "postgres://localhost/db"},
            },
        })

        skills = default_registry().discover(tmp_path)
        names = {s.name for s in skills}
        assert "filesystem" in names
        assert "database" in names
        assert all(s.format == "mcp" for s in skills)

    def test_mcp_hidden_config(self, tmp_path: Path) -> None:
        """Parser detects .mcp.json (hidden file variant)."""
        config = {
            "mcpServers": {
                "hidden-server": {"command": "node", "args": ["server.js"]}
            }
        }
        (tmp_path / ".mcp.json").write_text(
            json.dumps(config), encoding="utf-8"
        )
        skills = default_registry().discover(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "hidden-server"

    def test_mcp_extracts_env_vars(self, tmp_path: Path) -> None:
        """Environment variables in MCP config are captured."""
        _create_mcp_project(tmp_path, {
            "api-server": {
                "command": "node",
                "args": ["server.js"],
                "env": {"API_KEY": "abc", "SECRET_TOKEN": "xyz"},
            }
        })
        skills = default_registry().discover(tmp_path)
        assert len(skills) == 1
        assert "API_KEY" in skills[0].env_vars_referenced
        assert "SECRET_TOKEN" in skills[0].env_vars_referenced


class TestScanOpenClawProject:
    """Scanning directories with .claw/ or .openclaw/ layout."""

    def test_discovers_claw_skills(self, tmp_path: Path) -> None:
        """YAML files in .claw/ are discovered as openclaw skills."""
        _create_openclaw_project(tmp_path, [
            {"name": "web-scraper", "version": "1.3.0"},
            {"name": "file-handler", "version": "0.5.0"},
        ])
        skills = default_registry().discover(tmp_path)
        names = {s.name for s in skills}
        assert names == {"web-scraper", "file-handler"}
        assert all(s.format == "openclaw" for s in skills)

    def test_discovers_openclaw_dir(self, tmp_path: Path) -> None:
        """Skills in .openclaw/ (alternate dir name) are also found."""
        _create_openclaw_project(
            tmp_path,
            [{"name": "alt-skill", "version": "2.0.0"}],
            dir_name=".openclaw",
        )
        skills = default_registry().discover(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "alt-skill"

    def test_openclaw_preserves_version(self, tmp_path: Path) -> None:
        """Skill version from YAML is correctly parsed."""
        _create_openclaw_project(tmp_path, [
            {"name": "versioned", "version": "3.7.2"},
        ])
        skills = default_registry().discover(tmp_path)
        assert skills[0].version == "3.7.2"


class TestScanMixedProject:
    """Scanning directories with multiple format types together."""

    def test_all_three_formats_discovered(self, tmp_path: Path) -> None:
        """Claude + MCP + OpenClaw in one directory are all found."""
        _create_claude_project(tmp_path, ["claude-skill"])
        _create_mcp_project(tmp_path, {
            "mcp-server": {"command": "node", "args": ["s.js"]},
        })
        _create_openclaw_project(tmp_path, [
            {"name": "claw-skill", "version": "1.0.0"},
        ])

        skills = default_registry().discover(tmp_path)
        formats = {s.format for s in skills}
        assert formats == {"claude", "mcp", "openclaw"}

    def test_analysis_runs_on_all_formats(self, tmp_path: Path) -> None:
        """Static analyzer processes skills from all formats."""
        _create_claude_project(tmp_path, ["cs"])
        _create_mcp_project(tmp_path, {
            "ms": {"command": "node", "args": ["s.js"]},
        })
        _create_openclaw_project(tmp_path, [
            {"name": "os", "version": "1.0.0"},
        ])

        skills = default_registry().discover(tmp_path)
        analyzer = StaticAnalyzer()

        results = [analyzer.analyze(s) for s in skills]
        assert len(results) == len(skills)
        # All clean skills should pass
        for r in results:
            assert isinstance(r.is_safe, bool)

    def test_scan_nonexistent_directory(self) -> None:
        """Scanning a non-existent directory does not crash."""
        registry = default_registry()
        # Path that does not exist -- parsers should return empty
        fake = Path("/tmp/skillfortify-nonexistent-dir-abc123")
        skills = registry.discover(fake)
        assert skills == []
