"""Parser for Mastra agent framework tool and agent definitions.

Detects Mastra projects via ``mastra.config.ts``, ``package.json`` with
``@mastra/core``, or TS/JS files importing from ``@mastra/core``.
Extracts ``createTool()`` calls and ``new Agent()`` definitions plus
security metadata (URLs, env vars, shell calls, capabilities).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser

# ── Compiled regex patterns ───────────────────────────────────────────────

_MASTRA_IMPORT_PATTERN = re.compile(
    r"""(?:import\s+.*from\s+["']@mastra/core"""
    r"""|require\s*\(\s*["']@mastra/core)""",
)

_CREATE_TOOL_BLOCK = re.compile(
    r"createTool\s*\(\s*\{",
    re.MULTILINE,
)

_TOOL_ID_PATTERN = re.compile(
    r"""createTool\s*\(\s*\{[^}]*?id\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

_TOOL_DESC_PATTERN = re.compile(
    r"""createTool\s*\(\s*\{[^}]*?description\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

_AGENT_NAME_PATTERN = re.compile(
    r"""new\s+Agent\s*\(\s*\{[^}]*?name\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

_AGENT_INSTRUCTIONS_PATTERN = re.compile(
    r"""new\s+Agent\s*\(\s*\{[^}]*?instructions\s*:\s*["']([^"']+)["']""",
    re.DOTALL,
)

_URL_PATTERN = re.compile(r"https?://[^\s\"'`,)\]}>]+")

_ENV_VAR_PATTERN = re.compile(r"process\.env\.(\w+)")

_ENV_VAR_BRACKET = re.compile(r"""process\.env\[["'](\w+)["']\]""")

_SHELL_EXEC_PATTERNS = (
    re.compile(r"\bchild_process\b"), re.compile(r"\bexec\s*\("),
    re.compile(r"\bexecSync\s*\("), re.compile(r"\bspawn\s*\("),
    re.compile(r"\bspawnSync\s*\("),
)

_NET_PATTERNS = (re.compile(r"\bfetch\s*\("), re.compile(r"\baxios\b"),
                 re.compile(r"\bhttp\.\w+"))
_FS_PATTERN = re.compile(r"\bfs\.\w+")

_SENSITIVE_ENV = re.compile(
    r"(SECRET|KEY|TOKEN|PASSWORD|CREDENTIAL|PRIVATE)", re.IGNORECASE,
)

_MASTRA_CONFIG_FILES = ("mastra.config.ts", "mastra.config.js")

_TS_EXTENSIONS = (".ts", ".js", ".tsx", ".jsx")


# ── Extraction helpers ────────────────────────────────────────────────────

def _extract_env_vars(text: str) -> list[str]:
    """Extract unique environment variable names from TypeScript source."""
    found: set[str] = set()
    found.update(_ENV_VAR_PATTERN.findall(text))
    found.update(_ENV_VAR_BRACKET.findall(text))
    return sorted(found)


def _extract_urls(text: str) -> list[str]:
    """Extract all HTTP/HTTPS URLs from text."""
    return _URL_PATTERN.findall(text)


def _extract_shell_commands(text: str) -> list[str]:
    """Detect shell execution patterns in TypeScript source."""
    return [p.pattern for p in _SHELL_EXEC_PATTERNS if p.search(text)]


def _extract_capabilities(text: str, env_vars: list[str]) -> list[str]:
    """Infer declared capabilities from code patterns."""
    caps: set[str] = set()
    if env_vars:
        caps.add("env:read")
    if any(p.search(text) for p in _NET_PATTERNS):
        caps.update(("network:read", "network:write"))
    if _FS_PATTERN.search(text):
        caps.update(("filesystem:read", "filesystem:write"))
    if any(p.search(text) for p in _SHELL_EXEC_PATTERNS):
        caps.add("system:execute")
    if any(_SENSITIVE_ENV.search(v) for v in env_vars):
        caps.add("credentials:read")
    return sorted(caps)


def _extract_npm_deps(path: Path) -> list[str]:
    """Extract dependency names from package.json in the directory."""
    pkg_path = path / "package.json"
    if not pkg_path.is_file():
        return []
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = data.get(key, {})
        if isinstance(section, dict):
            deps.update(section.keys())
    return sorted(deps)


def _has_mastra_import(content: str) -> bool:
    """Check if content contains a Mastra SDK import or require."""
    return bool(_MASTRA_IMPORT_PATTERN.search(content))


def _read_safe(filepath: Path) -> str:
    """Read a file safely, returning empty string on failure."""
    try:
        return filepath.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _build_skill(
    name: str, description: str, source: str, filepath: Path,
    deps: list[str], instructions: str = "",
) -> ParsedSkill:
    """Build a ParsedSkill from extracted Mastra metadata."""
    env_vars = _extract_env_vars(source)
    return ParsedSkill(
        name=name, version="unknown", source_path=filepath,
        format="mastra", description=description,
        instructions=instructions,
        declared_capabilities=_extract_capabilities(source, env_vars),
        dependencies=deps, code_blocks=[source],
        urls=_extract_urls(source), env_vars_referenced=env_vars,
        shell_commands=_extract_shell_commands(source), raw_content=source,
    )


def _parse_ts_file(
    filepath: Path, deps: list[str],
) -> list[ParsedSkill]:
    """Parse a single TypeScript/JS file for Mastra tool and agent defs."""
    source = _read_safe(filepath)
    if not source:
        return []

    results: list[ParsedSkill] = []

    # Extract createTool() calls
    tool_ids = _TOOL_ID_PATTERN.findall(source)
    tool_descs = _TOOL_DESC_PATTERN.findall(source)
    desc_map = dict(zip(tool_ids, tool_descs)) if tool_descs else {}

    for tool_id in tool_ids:
        desc = desc_map.get(tool_id, "")
        results.append(_build_skill(tool_id, desc, source, filepath, deps))

    # Extract new Agent() definitions
    agent_names = _AGENT_NAME_PATTERN.findall(source)
    agent_instrs = _AGENT_INSTRUCTIONS_PATTERN.findall(source)
    instr_map = dict(zip(agent_names, agent_instrs)) if agent_instrs else {}

    for name in agent_names:
        instr = instr_map.get(name, "")
        desc = f"Mastra agent: {instr[:80]}" if instr else ""
        results.append(_build_skill(name, desc, source, filepath, deps, instr))

    return results


def _package_json_has_mastra(directory: Path) -> bool:
    """Check if package.json lists @mastra/core as a dependency."""
    pkg_path = directory / "package.json"
    if not pkg_path.is_file():
        return False
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    if not isinstance(data, dict):
        return False
    for dep_key in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(dep_key, {})
        if isinstance(deps, dict) and "@mastra/core" in deps:
            return True
    return False


# ── Main parser class ─────────────────────────────────────────────────────

class MastraParser(SkillParser):
    """Parser for Mastra AI agent framework tool and agent definitions.

    Detects Mastra projects via config files, package.json, or import
    statements. Extracts tools (``createTool``), agents (``new Agent``),
    and security-relevant metadata (URLs, env vars, shell calls).
    """

    def can_parse(self, path: Path) -> bool:
        """Detect Mastra project artifacts in a directory.

        Args:
            path: Root directory to probe.

        Returns:
            True if Mastra config, package.json deps, or imports found.
        """
        if not path.is_dir():
            return False
        for cfg_name in _MASTRA_CONFIG_FILES:
            if (path / cfg_name).is_file():
                return True
        if _package_json_has_mastra(path):
            return True
        return bool(self._find_mastra_files(path))

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Mastra tools and agents in the directory.

        Args:
            path: Root directory to scan.

        Returns:
            List of ParsedSkill instances with format ``"mastra"``.
        """
        if not path.is_dir():
            return []
        deps = _extract_npm_deps(path)
        results: list[ParsedSkill] = []

        for ts_file in self._find_mastra_files(path):
            results.extend(_parse_ts_file(ts_file, deps))

        # Also parse config files directly
        for cfg_name in _MASTRA_CONFIG_FILES:
            cfg_path = path / cfg_name
            if cfg_path.is_file() and cfg_path not in {
                r.source_path for r in results
            }:
                results.extend(_parse_ts_file(cfg_path, deps))

        return results

    def _find_mastra_files(self, path: Path) -> list[Path]:
        """Find TypeScript/JS files containing Mastra imports."""
        candidates: list[Path] = []
        search_dirs = [path]
        for sub_name in ("src", "tools", "agents", "mastra"):
            sub = path / sub_name
            if sub.is_dir():
                search_dirs.append(sub)

        for search_dir in search_dirs:
            for ts_file in sorted(search_dir.glob("*")):
                if ts_file.suffix not in _TS_EXTENSIONS:
                    continue
                head = _read_safe(ts_file)[:4096]
                if _has_mastra_import(head) or _CREATE_TOOL_BLOCK.search(head):
                    candidates.append(ts_file)
        return candidates
