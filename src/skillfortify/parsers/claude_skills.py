"""Parser for Claude Code skills (.claude/skills/*.md).

Claude Code stores user-defined skills as Markdown files in the
``.claude/skills/`` directory of a project. Each Markdown file may optionally
contain YAML frontmatter delimited by ``---`` lines, providing structured
metadata such as ``name`` and ``description``.

The parser extracts security-relevant signals from both the frontmatter and
the Markdown body:

- **URLs** -- Potential data exfiltration endpoints (DY-Skill attack surface:
  EXECUTE phase, DATA_EXFILTRATION class).
- **Environment variables** -- Credential exposure risk. Patterns matching
  SECRET, KEY, TOKEN, PASSWORD, CREDENTIAL are flagged as high-risk.
- **Shell commands** -- Code execution attack surface. Extracted from bash
  code blocks and inline backtick commands.
- **Code blocks** -- Raw code for deeper static analysis passes.

Frontmatter Parsing
-------------------
The parser uses a simple regex-based approach rather than a full YAML parser
for the frontmatter delimiter. The content between the ``---`` markers is
parsed as YAML to extract ``name`` and ``description``. If no frontmatter
is present, the filename stem is used as the skill name.

References:
    Claude Code documentation (2026): Skill files are Markdown with optional
    YAML frontmatter. The ``.claude/skills/`` convention is documented in
    the Claude Code CLI reference.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from skillfortify.parsers.base import ParsedSkill, SkillParser

# ---------------------------------------------------------------------------
# Regex patterns for security-relevant content extraction
# ---------------------------------------------------------------------------

# Match URLs: http:// or https:// followed by non-whitespace characters.
_URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")

# Match environment variable references. Captures identifiers that:
# - Are at least 2 characters long
# - Contain at least one underscore or are fully uppercase
# - Common patterns: DEPLOY_TOKEN, AWS_SECRET_ACCESS_KEY, API_KEY
# We avoid matching generic words by requiring an underscore or
# the pattern to appear after os.environ, $, or export.
_ENV_VAR_PATTERN = re.compile(
    r"""(?:"""
    r"""\$\{?([A-Z][A-Z0-9_]{1,})\}?"""  # $VAR or ${VAR}
    r"""|os\.environ\[["']([A-Z][A-Z0-9_]{1,})["']\]"""  # os.environ["VAR"]
    r"""|os\.getenv\(["']([A-Z][A-Z0-9_]{1,})["']\)"""  # os.getenv("VAR")
    r"""|export\s+([A-Z][A-Z0-9_]{1,})"""  # export VAR
    r"""|(?:^|[\s=:`])([A-Z][A-Z_]{1,}[A-Z0-9_]*)(?=[=\s"'`])"""  # Standalone ALL_CAPS with underscore
    r""")""",
    re.MULTILINE,
)

# Sensitive env var name fragments that warrant heightened scrutiny.
_SENSITIVE_FRAGMENTS = {"SECRET", "KEY", "TOKEN", "PASSWORD", "CREDENTIAL"}

# Match fenced code blocks: ```lang\n...\n```
_CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

# Match YAML frontmatter: ---\n...\n---
_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from text.

    Searches for multiple patterns: $VAR, ${VAR}, os.environ["VAR"],
    os.getenv("VAR"), export VAR, and standalone ALL_CAPS identifiers
    containing at least one underscore.

    Returns:
        Deduplicated list of env var names found in the text.
    """
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        # Each group corresponds to a different capture pattern.
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text."""
    return _URL_PATTERN.findall(text)


def _extract_code_blocks(text: str) -> list[str]:
    """Extract the content of all fenced code blocks."""
    return [match.group(2) for match in _CODE_BLOCK_PATTERN.finditer(text)]


def _extract_shell_commands(text: str) -> list[str]:
    """Extract shell commands from bash/shell code blocks.

    A code block is treated as shell if its language tag is one of:
    bash, sh, shell, zsh, or empty (untagged blocks are often shell).
    Each non-empty, non-comment line in such a block is a shell command.
    """
    shell_tags = {"bash", "sh", "shell", "zsh", ""}
    commands: list[str] = []
    for match in _CODE_BLOCK_PATTERN.finditer(text):
        lang = match.group(1).lower()
        if lang in shell_tags:
            block = match.group(2)
            for line in block.strip().splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    commands.append(stripped)
    return commands


class ClaudeSkillsParser(SkillParser):
    """Parser for Claude Code skills stored as Markdown in .claude/skills/.

    Discovery logic:
        1. Check for ``.claude/skills/`` subdirectory.
        2. Glob for ``*.md`` files within it.
        3. If at least one ``.md`` file exists, ``can_parse()`` returns True.

    Parse logic per file:
        1. Read raw content.
        2. Extract YAML frontmatter (if present) for name and description.
        3. Extract URLs, env vars, code blocks, and shell commands from body.
        4. Construct a ``ParsedSkill`` with format="claude".
    """

    def can_parse(self, path: Path) -> bool:
        """Check if the directory contains Claude Code skills.

        Args:
            path: Root directory to probe.

        Returns:
            True if ``.claude/skills/`` contains at least one ``.md`` file.
        """
        skills_dir = path / ".claude" / "skills"
        if not skills_dir.is_dir():
            return False
        return any(skills_dir.glob("*.md"))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Claude Code skill files in ``.claude/skills/``.

        Args:
            path: Root directory containing ``.claude/skills/``.

        Returns:
            List of ParsedSkill instances. Empty if no skills found.
        """
        skills_dir = path / ".claude" / "skills"
        if not skills_dir.is_dir():
            return []

        results: list[ParsedSkill] = []
        for md_file in sorted(skills_dir.glob("*.md")):
            skill = self._parse_file(md_file)
            if skill is not None:
                results.append(skill)
        return results

    def _parse_file(self, file_path: Path) -> ParsedSkill | None:
        """Parse a single Claude skill Markdown file.

        Args:
            file_path: Path to the .md file.

        Returns:
            A ParsedSkill, or None if the file cannot be read.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

        # Extract frontmatter.
        name = file_path.stem
        description = ""
        frontmatter_match = _FRONTMATTER_PATTERN.match(raw_content)
        if frontmatter_match:
            try:
                fm_data = yaml.safe_load(frontmatter_match.group(1))
                if isinstance(fm_data, dict):
                    name = fm_data.get("name", name)
                    description = fm_data.get("description", "")
            except yaml.YAMLError:
                pass  # Keep filename-based defaults.

        # Extract security-relevant metadata from the full content.
        urls = _extract_urls(raw_content)
        env_vars = _extract_env_vars(raw_content)
        code_blocks = _extract_code_blocks(raw_content)
        shell_commands = _extract_shell_commands(raw_content)

        return ParsedSkill(
            name=name,
            version="unknown",
            source_path=file_path,
            format="claude",
            description=description,
            instructions=raw_content,
            urls=urls,
            env_vars_referenced=env_vars,
            code_blocks=code_blocks,
            shell_commands=shell_commands,
            raw_content=raw_content,
        )
