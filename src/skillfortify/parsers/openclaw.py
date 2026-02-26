"""Parser for OpenClaw skill definitions (.claw/ or .openclaw/).

OpenClaw is the largest open-source agent skill marketplace (228K+ GitHub
stars as of Feb 2026). Skills are defined in YAML files within ``.claw/``
or ``.openclaw/`` directories. Each YAML file declares a skill with
structured metadata:

.. code-block:: yaml

    name: web-scraper
    version: "1.3.0"
    description: Scrapes web pages and extracts structured data
    instructions: |
      Use this skill to scrape data from https://target-site.com/api.
      Requires SCRAPER_API_KEY to authenticate.
    commands:
      - name: scrape
        command: "curl -H 'Authorization: Bearer $SCRAPER_API_KEY' https://target-site.com"
    dependencies:
      - beautifulsoup4>=4.12

Security Relevance
------------------
OpenClaw was the target of the ClawHavoc campaign (Feb 2026) where 1,200+
malicious skills infiltrated the marketplace. The parser extracts:

- **URLs** from instructions and commands -- potential exfiltration endpoints.
- **Environment variables** from instructions and commands -- credential exposure.
- **Shell commands** from the commands list -- code execution surface.
- **Dependencies** -- transitive supply chain attack surface.

References:
    "SoK: Agentic Skills in the Wild" (arXiv:2602.20867, Feb 24, 2026).
    Documents ClawHavoc campaign and 7 skill design patterns.

    "MalTool: Benchmarking Malicious Tool Attacks Against LLM Agents"
    (arXiv:2602.12194, Feb 12, 2026). Catalogs 6,487 malicious tools.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from skillfortify.parsers.base import ParsedSkill, SkillParser

# Reuse URL and env-var extraction patterns.
_URL_PATTERN = re.compile(r"https?://[^\s\"'`)\]>]+")

_ENV_VAR_PATTERN = re.compile(
    r"""(?:"""
    r"""\$\{?([A-Z][A-Z0-9_]{1,})\}?"""
    r"""|(?:^|[\s=:])([A-Z][A-Z_]{1,}[A-Z0-9_]*)(?=[=\s"'`])"""
    r""")""",
    re.MULTILINE,
)

# Directories where OpenClaw skills are stored.
_CLAW_DIRS = (".claw", ".openclaw")

# YAML file extensions.
_YAML_EXTENSIONS = ("*.yaml", "*.yml")


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text."""
    return _URL_PATTERN.findall(text)


def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from text."""
    found: set[str] = set()
    for match in _ENV_VAR_PATTERN.finditer(text):
        for group in match.groups():
            if group:
                found.add(group)
    return sorted(found)


class OpenClawParser(SkillParser):
    """Parser for OpenClaw skill YAML files in .claw/ or .openclaw/.

    Discovery logic:
        1. Check for ``.claw/`` or ``.openclaw/`` subdirectory.
        2. Glob for ``*.yaml`` and ``*.yml`` files within it.
        3. If at least one YAML file exists, ``can_parse()`` returns True.

    Parse logic per file:
        1. Read and parse YAML.
        2. Extract top-level fields: name, version, description, instructions.
        3. Extract commands from the ``commands`` list.
        4. Extract URLs and env vars from instructions + command strings.
        5. Construct a ``ParsedSkill`` with format="openclaw".
    """

    def can_parse(self, path: Path) -> bool:
        """Check if the directory contains OpenClaw skill definitions.

        Args:
            path: Root directory to probe.

        Returns:
            True if .claw/ or .openclaw/ contains at least one YAML file.
        """
        for dir_name in _CLAW_DIRS:
            claw_dir = path / dir_name
            if claw_dir.is_dir():
                for ext in _YAML_EXTENSIONS:
                    if any(claw_dir.glob(ext)):
                        return True
        return False

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all OpenClaw skill YAML files.

        Scans both .claw/ and .openclaw/ directories.

        Args:
            path: Root directory to scan.

        Returns:
            List of ParsedSkill instances. Empty if no valid skills found.
        """
        results: list[ParsedSkill] = []
        for dir_name in _CLAW_DIRS:
            claw_dir = path / dir_name
            if not claw_dir.is_dir():
                continue
            for ext in _YAML_EXTENSIONS:
                for yaml_file in sorted(claw_dir.glob(ext)):
                    skill = self._parse_file(yaml_file)
                    if skill is not None:
                        results.append(skill)
        return results

    def _parse_file(self, file_path: Path) -> ParsedSkill | None:
        """Parse a single OpenClaw YAML skill file.

        Args:
            file_path: Path to the .yaml or .yml file.

        Returns:
            A ParsedSkill, or None if the file is malformed.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw_content)
        except (OSError, yaml.YAMLError):
            return None

        if not isinstance(data, dict):
            return None

        name = data.get("name", file_path.stem)
        version = str(data.get("version", "unknown"))
        description = data.get("description", "")
        instructions = data.get("instructions", "")

        # Extract commands from the commands list.
        commands_list = data.get("commands", [])
        shell_commands: list[str] = []
        command_text_parts: list[str] = []
        if isinstance(commands_list, list):
            for cmd_entry in commands_list:
                if isinstance(cmd_entry, dict):
                    cmd_str = cmd_entry.get("command", "")
                    if cmd_str:
                        shell_commands.append(cmd_str)
                        command_text_parts.append(cmd_str)

        # Extract dependencies.
        deps_raw = data.get("dependencies", [])
        dependencies: list[str] = []
        if isinstance(deps_raw, list):
            dependencies = [str(d) for d in deps_raw]

        # Combine all text sources for URL and env var extraction.
        all_text = "\n".join([
            instructions or "",
            *command_text_parts,
        ])
        urls = _extract_urls(all_text)
        env_vars = _extract_env_vars(all_text)

        return ParsedSkill(
            name=name,
            version=version,
            source_path=file_path,
            format="openclaw",
            description=description,
            instructions=instructions,
            shell_commands=shell_commands,
            dependencies=dependencies,
            urls=urls,
            env_vars_referenced=env_vars,
            raw_content=raw_content,
        )
