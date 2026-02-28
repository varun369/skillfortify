"""Static registry of known AI IDEs/tools and their configuration paths.

Each ``IDEProfile`` describes where a specific AI development tool stores
its MCP server configurations, skill directories, and dot-directories on
disk. The registry enables ``SystemScanner`` to check for the presence of
these tools without the user specifying paths manually.

Profiles cover 22+ AI coding tools as of March 2026, from major players
(Claude Code, Cursor, VS Code Copilot) to emerging tools (Kiro, Codex,
Trae). The list is intentionally generous -- checking for a non-existent
directory is cheap (one syscall), and discovering an unexpected tool is
high-value for the user.

Platform Notes:
    macOS stores VS Code configs under ``~/Library/Application Support/``.
    Linux uses ``~/.config/Code/``. Windows uses ``%APPDATA%``.
    Most AI tools use a dot-directory directly under ``$HOME``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# MCP config filename patterns used by the auto-discovery heuristic.
# When scanning unknown directories under ``~/.*``, these filenames
# indicate a potential AI tool configuration.
MCP_CONFIG_FILENAMES: list[str] = [
    "mcp.json",
    "mcp_config.json",
    "mcp_settings.json",
    "mcp_servers.json",
]


@dataclass(frozen=True)
class IDEProfile:
    """Describes where an AI IDE/tool stores its configurations.

    Attributes:
        name: Human-readable display name (e.g., "Claude Code").
        short_name: Machine identifier for CLI output (e.g., "claude").
        config_paths: Paths to MCP config files, relative to home directory.
        skill_paths: Paths to skill directories, relative to home directory.
        dot_dirs: Top-level dot-directories to probe (relative to home).
        platform: Target platform. "all" means cross-platform.
    """

    name: str
    short_name: str
    config_paths: list[str] = field(default_factory=list)
    skill_paths: list[str] = field(default_factory=list)
    dot_dirs: list[str] = field(default_factory=list)
    platform: str = "all"


def _build_profiles() -> list[IDEProfile]:
    """Build the complete list of known IDE profiles.

    Returns:
        Ordered list of IDE profiles covering 22+ AI tools.
    """
    return [
        # -- Tier 1: Major AI coding assistants --
        IDEProfile(
            name="Claude Code",
            short_name="claude",
            config_paths=[".claude/mcp_servers.json"],
            skill_paths=[".claude/skills"],
            dot_dirs=[".claude"],
        ),
        IDEProfile(
            name="Cursor",
            short_name="cursor",
            config_paths=[
                ".cursor/mcp.json",
                ".cursor/mcp_settings.json",
            ],
            skill_paths=[],
            dot_dirs=[".cursor"],
        ),
        IDEProfile(
            name="VS Code",
            short_name="vscode",
            config_paths=[
                "Library/Application Support/Code/User/mcp.json",
            ],
            skill_paths=[],
            dot_dirs=[".vscode"],
            platform="macos",
        ),
        IDEProfile(
            name="VS Code (Linux)",
            short_name="vscode-linux",
            config_paths=[
                ".config/Code/User/mcp.json",
            ],
            skill_paths=[],
            dot_dirs=[".vscode"],
            platform="linux",
        ),
        IDEProfile(
            name="Windsurf/Codeium",
            short_name="windsurf",
            config_paths=[".codeium/windsurf/mcp_config.json"],
            skill_paths=[],
            dot_dirs=[".codeium"],
        ),
        IDEProfile(
            name="Gemini CLI",
            short_name="gemini",
            config_paths=[".gemini/settings.json"],
            skill_paths=[],
            dot_dirs=[".gemini"],
        ),
        IDEProfile(
            name="OpenCode",
            short_name="opencode",
            config_paths=[".opencode/mcp.json"],
            skill_paths=[],
            dot_dirs=[".opencode"],
        ),
        # -- Tier 2: IDE extensions and agents --
        IDEProfile(
            name="Cline",
            short_name="cline",
            config_paths=[".cline/mcp_settings.json"],
            skill_paths=[],
            dot_dirs=[".cline"],
        ),
        IDEProfile(
            name="Continue",
            short_name="continue",
            config_paths=[".continue/config.json"],
            skill_paths=[],
            dot_dirs=[".continue"],
        ),
        IDEProfile(
            name="GitHub Copilot",
            short_name="copilot",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".copilot"],
        ),
        IDEProfile(
            name="n8n",
            short_name="n8n",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".n8n"],
        ),
        IDEProfile(
            name="Roo Code",
            short_name="roo",
            config_paths=[".roo/mcp.json"],
            skill_paths=[],
            dot_dirs=[".roo"],
        ),
        # -- Tier 3: Emerging AI tools --
        IDEProfile(
            name="Trae",
            short_name="trae",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".trae"],
        ),
        IDEProfile(
            name="Kiro",
            short_name="kiro",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".kiro"],
        ),
        IDEProfile(
            name="Kode",
            short_name="kode",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".kode"],
        ),
        IDEProfile(
            name="Jules",
            short_name="jules",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".jules"],
        ),
        IDEProfile(
            name="Junie",
            short_name="junie",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".junie"],
        ),
        IDEProfile(
            name="Codex CLI",
            short_name="codex",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".codex"],
        ),
        IDEProfile(
            name="SuperVS",
            short_name="supervs",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".supervs"],
        ),
        IDEProfile(
            name="Zencoder",
            short_name="zencoder",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".zencoder"],
        ),
        IDEProfile(
            name="CommandCode",
            short_name="commandcode",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".commandcode"],
        ),
        IDEProfile(
            name="Factory",
            short_name="factory",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".factory"],
        ),
        IDEProfile(
            name="Qoder",
            short_name="qoder",
            config_paths=[],
            skill_paths=[],
            dot_dirs=[".qoder"],
        ),
    ]


# Module-level constant: the canonical list of all known IDE profiles.
IDE_PROFILES: list[IDEProfile] = _build_profiles()
