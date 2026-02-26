"""Tests for the Claude Code skills parser.

Claude Code stores user-defined skills as Markdown files in `.claude/skills/`.
Each file may contain YAML frontmatter (name, description) and Markdown body
with code blocks, shell commands, URLs, and environment variable references.

The parser must extract all security-relevant metadata from these files for
downstream static analysis by the capability lattice and threat model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.claude_skills import ClaudeSkillsParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> ClaudeSkillsParser:
    return ClaudeSkillsParser()


@pytest.fixture
def claude_skill_dir(tmp_path: Path) -> Path:
    """Create a .claude/skills/ directory with a sample skill."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    skill_content = """\
---
name: deploy-helper
description: Assists with deployment to production servers
---

# Deploy Helper

This skill helps deploy to https://deploy.example.com/api/v2 endpoints.

## Usage

Set your `DEPLOY_TOKEN` and `AWS_SECRET_ACCESS_KEY` before running:

```bash
export DEPLOY_TOKEN=your-token
kubectl apply -f manifests/
```

```python
import os
token = os.environ["API_KEY"]
requests.post("https://internal.corp.net/deploy", headers={"Authorization": token})
```

You can also use `curl https://webhook.site/abc123` to trigger a webhook.
"""
    (skills_dir / "deploy-helper.md").write_text(skill_content)
    return tmp_path


@pytest.fixture
def empty_claude_dir(tmp_path: Path) -> Path:
    """Create an empty .claude/skills/ directory."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def malformed_claude_dir(tmp_path: Path) -> Path:
    """Create a .claude/skills/ directory with a malformed skill file."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    # No frontmatter, just raw text
    (skills_dir / "broken.md").write_text("Just some text, no frontmatter.\n")
    return tmp_path


# ---------------------------------------------------------------------------
# TestClaudeSkillsParser
# ---------------------------------------------------------------------------


class TestClaudeSkillsParser:
    """Validate the Claude Code skills parser."""

    def test_can_parse_valid_dir(self, parser: ClaudeSkillsParser, claude_skill_dir: Path) -> None:
        """Parser recognises a directory containing .claude/skills/*.md files."""
        assert parser.can_parse(claude_skill_dir) is True

    def test_cannot_parse_invalid_dir(self, parser: ClaudeSkillsParser, tmp_path: Path) -> None:
        """Parser rejects a directory without .claude/skills/."""
        assert parser.can_parse(tmp_path) is False

    def test_cannot_parse_empty_skills_dir(
        self, parser: ClaudeSkillsParser, empty_claude_dir: Path
    ) -> None:
        """Parser rejects .claude/skills/ when it contains no .md files."""
        assert parser.can_parse(empty_claude_dir) is False

    def test_parses_skill_name(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """Extracts the skill name from YAML frontmatter."""
        skills = parser.parse(claude_skill_dir)
        assert len(skills) == 1
        assert skills[0].name == "deploy-helper"

    def test_extracts_description(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """Extracts the description from YAML frontmatter."""
        skills = parser.parse(claude_skill_dir)
        assert "deployment" in skills[0].description.lower()

    def test_extracts_urls(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """Extracts all URLs from the skill content."""
        skills = parser.parse(claude_skill_dir)
        urls = skills[0].urls
        assert any("deploy.example.com" in u for u in urls)
        assert any("internal.corp.net" in u for u in urls)
        assert any("webhook.site" in u for u in urls)

    def test_extracts_env_vars(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """Extracts environment variable references (ALL_CAPS patterns)."""
        skills = parser.parse(claude_skill_dir)
        env_vars = skills[0].env_vars_referenced
        assert "DEPLOY_TOKEN" in env_vars
        assert "AWS_SECRET_ACCESS_KEY" in env_vars
        assert "API_KEY" in env_vars

    def test_extracts_shell_commands(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """Extracts shell commands from bash code blocks."""
        skills = parser.parse(claude_skill_dir)
        shell_cmds = skills[0].shell_commands
        assert any("kubectl" in cmd for cmd in shell_cmds)
        assert any("export" in cmd for cmd in shell_cmds)

    def test_extracts_code_blocks(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """Extracts all fenced code blocks from the Markdown content."""
        skills = parser.parse(claude_skill_dir)
        code_blocks = skills[0].code_blocks
        assert len(code_blocks) >= 2  # bash block + python block

    def test_format_is_correct(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """Parsed skills must have format='claude'."""
        skills = parser.parse(claude_skill_dir)
        assert skills[0].format == "claude"

    def test_source_path_is_set(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """source_path points to the actual .md file on disk."""
        skills = parser.parse(claude_skill_dir)
        assert skills[0].source_path.exists()
        assert skills[0].source_path.suffix == ".md"

    def test_raw_content_preserved(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """The full raw content of the file is available."""
        skills = parser.parse(claude_skill_dir)
        assert "Deploy Helper" in skills[0].raw_content

    def test_handles_empty_dir(
        self, parser: ClaudeSkillsParser, empty_claude_dir: Path
    ) -> None:
        """Parsing an empty skills directory returns an empty list."""
        skills = parser.parse(empty_claude_dir)
        assert skills == []

    def test_handles_malformed_content(
        self, parser: ClaudeSkillsParser, malformed_claude_dir: Path
    ) -> None:
        """Parsing a skill file without frontmatter still succeeds gracefully."""
        skills = parser.parse(malformed_claude_dir)
        assert len(skills) == 1
        # Name falls back to filename stem
        assert skills[0].name == "broken"

    def test_returns_parsed_skill_instances(
        self, parser: ClaudeSkillsParser, claude_skill_dir: Path
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(claude_skill_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)

    def test_multiple_skills(self, parser: ClaudeSkillsParser, tmp_path: Path) -> None:
        """Parser discovers multiple .md files in the skills directory."""
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "skill-a.md").write_text("---\nname: alpha\n---\nContent A\n")
        (skills_dir / "skill-b.md").write_text("---\nname: beta\n---\nContent B\n")
        skills = parser.parse(tmp_path)
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"alpha", "beta"}
