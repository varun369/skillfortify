"""Tests for the OpenClaw skills parser.

OpenClaw skills are defined in YAML files within ``.claw/`` or ``.openclaw/``
directories. Each YAML file declares a skill with metadata (name, description,
version), instructions, commands, and dependencies.

The parser must extract security-relevant metadata including URLs referenced
in instructions, environment variables, and shell commands -- all of which
feed into the capability lattice and threat model for static analysis.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from skillfortify.parsers.base import ParsedSkill
from skillfortify.parsers.openclaw import OpenClawParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser() -> OpenClawParser:
    return OpenClawParser()


@pytest.fixture
def openclaw_skill_dir(tmp_path: Path) -> Path:
    """Create a .claw/ directory with a sample skill YAML."""
    claw_dir = tmp_path / ".claw"
    claw_dir.mkdir()

    skill_yaml = """\
name: web-scraper
version: "1.3.0"
description: Scrapes web pages and extracts structured data
instructions: |
  Use this skill to scrape data from https://target-site.com/api.
  Requires SCRAPER_API_KEY to authenticate.
  Also connects to https://proxy.internal.net for rate limiting.
commands:
  - name: scrape
    description: Scrape a URL
    command: "curl -H 'Authorization: Bearer $SCRAPER_API_KEY' https://target-site.com"
  - name: export
    description: Export scraped data
    command: "python export.py --output /tmp/data.json"
dependencies:
  - beautifulsoup4>=4.12
  - httpx>=0.27
"""
    (claw_dir / "web-scraper.yaml").write_text(skill_yaml)
    return tmp_path


@pytest.fixture
def openclaw_alt_dir(tmp_path: Path) -> Path:
    """Create a .openclaw/ directory (alternative naming) with a .yml file."""
    openclaw_dir = tmp_path / ".openclaw"
    openclaw_dir.mkdir()

    skill_yml = """\
name: code-reviewer
version: "0.2.0"
description: Reviews code for common issues
instructions: |
  Analyze code quality. Set CODE_REVIEW_TOKEN for GitHub integration.
commands:
  - name: review
    command: "gh pr review --approve"
"""
    (openclaw_dir / "code-reviewer.yml").write_text(skill_yml)
    return tmp_path


@pytest.fixture
def empty_claw_dir(tmp_path: Path) -> Path:
    """Create an empty .claw/ directory."""
    (tmp_path / ".claw").mkdir()
    return tmp_path


@pytest.fixture
def malformed_claw_dir(tmp_path: Path) -> Path:
    """Create a .claw/ directory with an invalid YAML file."""
    claw_dir = tmp_path / ".claw"
    claw_dir.mkdir()
    (claw_dir / "broken.yaml").write_text("name: [invalid yaml\n  missing: {bracket")
    return tmp_path


# ---------------------------------------------------------------------------
# TestOpenClawParser
# ---------------------------------------------------------------------------


class TestOpenClawParser:
    """Validate the OpenClaw skills parser."""

    def test_can_parse_valid_dir(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Parser recognises a directory containing .claw/*.yaml files."""
        assert parser.can_parse(openclaw_skill_dir) is True

    def test_can_parse_alt_dir(self, parser: OpenClawParser, openclaw_alt_dir: Path) -> None:
        """Parser recognises .openclaw/ directory with .yml files."""
        assert parser.can_parse(openclaw_alt_dir) is True

    def test_cannot_parse_invalid_dir(self, parser: OpenClawParser, tmp_path: Path) -> None:
        """Parser rejects a directory without .claw/ or .openclaw/."""
        assert parser.can_parse(tmp_path) is False

    def test_cannot_parse_empty_claw_dir(
        self, parser: OpenClawParser, empty_claw_dir: Path
    ) -> None:
        """Parser rejects .claw/ when it contains no YAML files."""
        assert parser.can_parse(empty_claw_dir) is False

    def test_parses_skill_name(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts the skill name from the YAML top-level 'name' field."""
        skills = parser.parse(openclaw_skill_dir)
        assert len(skills) == 1
        assert skills[0].name == "web-scraper"

    def test_extracts_description(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts the description from the YAML top-level 'description' field."""
        skills = parser.parse(openclaw_skill_dir)
        assert "scrapes" in skills[0].description.lower()

    def test_extracts_version(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts the version string from the YAML."""
        skills = parser.parse(openclaw_skill_dir)
        assert skills[0].version == "1.3.0"

    def test_extracts_urls(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts all URLs from instructions and commands."""
        skills = parser.parse(openclaw_skill_dir)
        urls = skills[0].urls
        assert any("target-site.com" in u for u in urls)
        assert any("proxy.internal.net" in u for u in urls)

    def test_extracts_env_vars(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts environment variable references from instructions and commands."""
        skills = parser.parse(openclaw_skill_dir)
        env_vars = skills[0].env_vars_referenced
        assert "SCRAPER_API_KEY" in env_vars

    def test_extracts_shell_commands(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts shell commands from the commands list."""
        skills = parser.parse(openclaw_skill_dir)
        shell_cmds = skills[0].shell_commands
        assert any("curl" in cmd for cmd in shell_cmds)
        assert any("python" in cmd for cmd in shell_cmds)

    def test_extracts_dependencies(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts declared dependencies from the YAML."""
        skills = parser.parse(openclaw_skill_dir)
        deps = skills[0].dependencies
        assert any("beautifulsoup4" in d for d in deps)
        assert any("httpx" in d for d in deps)

    def test_extracts_instructions(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Extracts the instructions text."""
        skills = parser.parse(openclaw_skill_dir)
        assert "scrape" in skills[0].instructions.lower()

    def test_format_is_correct(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """Parsed skills must have format='openclaw'."""
        skills = parser.parse(openclaw_skill_dir)
        assert skills[0].format == "openclaw"

    def test_source_path_is_set(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """source_path points to the actual YAML file on disk."""
        skills = parser.parse(openclaw_skill_dir)
        assert skills[0].source_path.exists()
        assert skills[0].source_path.suffix == ".yaml"

    def test_handles_empty_dir(
        self, parser: OpenClawParser, empty_claw_dir: Path
    ) -> None:
        """Parsing an empty .claw/ directory returns an empty list."""
        skills = parser.parse(empty_claw_dir)
        assert skills == []

    def test_handles_malformed_content(
        self, parser: OpenClawParser, malformed_claw_dir: Path
    ) -> None:
        """Parsing invalid YAML returns an empty list rather than crashing."""
        skills = parser.parse(malformed_claw_dir)
        assert skills == []

    def test_returns_parsed_skill_instances(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """All returned items are ParsedSkill instances."""
        skills = parser.parse(openclaw_skill_dir)
        for skill in skills:
            assert isinstance(skill, ParsedSkill)

    def test_raw_content_preserved(
        self, parser: OpenClawParser, openclaw_skill_dir: Path
    ) -> None:
        """The full raw content of the YAML file is available."""
        skills = parser.parse(openclaw_skill_dir)
        assert "web-scraper" in skills[0].raw_content
