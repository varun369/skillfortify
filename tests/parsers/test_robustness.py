"""Tests for parser robustness edge cases.

Verifies parsers handle gracefully:
    - Malformed YAML frontmatter (missing closing ---).
    - Binary content in skill file.
    - Very large skill file (>1MB content).
    - Skill file with no name/description.
    - Duplicate server names in MCP config.
    - Empty .claude/skills/ directory.
    - Skill file with only whitespace.
    - Non-UTF8 encoding in skill file.
"""

from __future__ import annotations

from pathlib import Path


from skillfortify.parsers.claude_skills import ClaudeSkillsParser
from skillfortify.parsers.mcp_config import McpConfigParser


class TestMalformedYAMLFrontmatter:
    """Parser handles malformed YAML frontmatter without crashing."""

    def test_missing_closing_delimiter(self, tmp_path: Path) -> None:
        """Skill file with missing closing --- still parses."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "broken.md").write_text(
            "---\n"
            "name: broken-skill\n"
            "description: missing close\n"
            "\n"
            "This is the body text.\n"
        )
        parser = ClaudeSkillsParser()
        results = parser.parse(tmp_path)
        # Parser should return a result (using filename as fallback name).
        assert len(results) == 1
        # Name is derived from filename since frontmatter failed to parse.
        assert results[0].name == "broken"

    def test_invalid_yaml_content(self, tmp_path: Path) -> None:
        """Skill file with invalid YAML in frontmatter still parses."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "invalid.md").write_text(
            "---\n"
            "[this: is: not: valid: yaml: {{{\n"
            "---\n\n"
            "Body content here.\n"
        )
        parser = ClaudeSkillsParser()
        results = parser.parse(tmp_path)
        assert len(results) == 1
        # Falls back to filename stem as name.
        assert results[0].name == "invalid"


class TestBinaryContent:
    """Parser handles binary content in skill files."""

    def test_binary_skill_file_skipped(self, tmp_path: Path) -> None:
        """A file with binary (non-text) content is skipped or handled."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        binary_file = skills_dir / "binary.md"
        # Write random binary bytes.
        binary_file.write_bytes(bytes(range(256)) * 4)
        parser = ClaudeSkillsParser()
        # Should not raise; may return empty or skip the binary file.
        results = parser.parse(tmp_path)
        # If it returns results, the name should be the file stem.
        # If it skips, results may be empty. Both are acceptable.
        assert isinstance(results, list)


class TestVeryLargeSkillFile:
    """Parser handles very large skill files."""

    def test_large_file_over_1mb(self, tmp_path: Path) -> None:
        """A >1MB skill file is parsed without error."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        large_content = (
            "---\nname: large-skill\n---\n\n"
            + "This is a very long line. " * 50000  # ~1.3MB
        )
        (skills_dir / "large.md").write_text(large_content)
        parser = ClaudeSkillsParser()
        results = parser.parse(tmp_path)
        assert len(results) == 1
        assert results[0].name == "large-skill"
        assert len(results[0].raw_content) > 1_000_000


class TestNoNameDescription:
    """Parser handles skill files with no name or description."""

    def test_no_frontmatter_uses_filename(self, tmp_path: Path) -> None:
        """Skill with no frontmatter uses filename stem as name."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "unnamed.md").write_text(
            "Just some instructions.\n\nNo YAML frontmatter here.\n"
        )
        parser = ClaudeSkillsParser()
        results = parser.parse(tmp_path)
        assert len(results) == 1
        assert results[0].name == "unnamed"
        assert results[0].description == ""


class TestDuplicateMCPServerNames:
    """MCP parser handles duplicate server names (JSON key last-wins)."""

    def test_duplicate_server_names_last_wins(self, tmp_path: Path) -> None:
        """When JSON has duplicate keys, the last one wins per JSON spec."""
        # Standard JSON doesn't support duplicate keys, but Python's
        # json.loads takes the last value for duplicate keys.
        config_text = (
            '{"mcpServers": {'
            '"server-a": {"command": "first"},'
            '"server-a": {"command": "second"}'
            '}}'
        )
        (tmp_path / "mcp.json").write_text(config_text)
        parser = McpConfigParser()
        results = parser.parse(tmp_path)
        assert len(results) == 1
        assert results[0].name == "server-a"
        # The last command value should win.
        assert "second" in results[0].shell_commands[0]


class TestEmptyClaudeSkillsDir:
    """Parser handles empty .claude/skills/ directory."""

    def test_empty_skills_dir_returns_no_skills(self, tmp_path: Path) -> None:
        """An empty .claude/skills/ directory yields no parsed skills."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        parser = ClaudeSkillsParser()
        assert parser.can_parse(tmp_path) is False
        results = parser.parse(tmp_path)
        assert results == []


class TestWhitespaceOnlyFile:
    """Parser handles skill file with only whitespace."""

    def test_whitespace_only_file_parsed(self, tmp_path: Path) -> None:
        """A file containing only whitespace is parsed with filename as name."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "blank.md").write_text("   \n\n\t\n   ")
        parser = ClaudeSkillsParser()
        results = parser.parse(tmp_path)
        assert len(results) == 1
        assert results[0].name == "blank"
        # No URLs, no env vars, no commands.
        assert results[0].urls == []
        assert results[0].shell_commands == []


class TestNonUTF8Encoding:
    """Parser handles files with non-UTF8 encoding."""

    def test_latin1_encoded_file_handled(self, tmp_path: Path) -> None:
        """A Latin-1 encoded file is either parsed or gracefully skipped."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        latin1_file = skills_dir / "latin1.md"
        # Write Latin-1 encoded content that is NOT valid UTF-8.
        content_bytes = "---\nname: caf\xe9\n---\nR\xe9sum\xe9".encode("latin-1")
        latin1_file.write_bytes(content_bytes)
        parser = ClaudeSkillsParser()
        # Should not crash. May return empty list or parse with errors.
        results = parser.parse(tmp_path)
        assert isinstance(results, list)
