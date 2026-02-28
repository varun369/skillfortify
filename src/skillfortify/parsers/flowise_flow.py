"""Parser for Flowise chatflow export files (JSON).

Flowise is a popular open-source no-code AI agent builder (49K+ GitHub
stars) that exports chatflow definitions as JSON files containing ``nodes``
and ``edges`` arrays.  Each node has a ``data`` field describing a component
such as a chat model, custom tool, vector store, memory, or agent.

Detection signals:
    - JSON files with a top-level ``nodes`` array whose elements contain
      ``data.type`` fields matching known Flowise component types.
    - Presence of a ``.flowise/`` directory.

Security relevance:
    Custom tool nodes embed arbitrary JavaScript code that may perform
    HTTP requests, reference credentials via ``process.env``, or invoke
    shell commands through ``child_process``.  Model and vector store
    nodes frequently contain hardcoded API keys in their ``inputs``
    blocks.  The parser extracts all of these signals for downstream
    threat analysis via the capability lattice and DY-Skill threat model.

References:
    Flowise GitHub repository: https://github.com/FlowiseAI/Flowise
    "Agent Skills in the Wild" (arXiv:2601.10338) -- vulnerability
    patterns relevant to no-code agent builders.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.flowise_extractors import (
    FLOWISE_DIR,
    extract_code_blocks,
    extract_credentials,
    extract_env_vars,
    extract_node_dependencies,
    extract_shell_commands,
    extract_urls,
    get_node_types,
    is_flowise_chatflow,
    safe_load_json,
)


class FlowiseParser(SkillParser):
    """Parser for Flowise chatflow export files (JSON).

    Discovery:
        1. Check for JSON files containing ``nodes`` array with Flowise
           component types.
        2. Check for ``.flowise/`` directory.

    Parse logic:
        1. Load JSON and validate Flowise chatflow structure.
        2. Extract custom tool JavaScript code blocks.
        3. Extract credential references from node inputs.
        4. Extract URLs, env vars, shell commands from code.
        5. Construct ParsedSkill instances with format="flowise".
    """

    def can_parse(self, path: Path) -> bool:
        """Probe a directory for Flowise chatflow exports.

        Args:
            path: Root directory to probe.

        Returns:
            True if Flowise chatflow files are detected.
        """
        if (path / FLOWISE_DIR).is_dir():
            return True
        for json_file in sorted(path.glob("*.json")):
            data = safe_load_json(json_file)
            if data is not None and is_flowise_chatflow(data):
                return True
        return False

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Flowise chatflow files in a directory.

        Args:
            path: Root directory to scan.

        Returns:
            List of ParsedSkill instances. Empty if none found.
        """
        results: list[ParsedSkill] = []
        search_dirs = [path]
        flowise_dir = path / FLOWISE_DIR
        if flowise_dir.is_dir():
            search_dirs.append(flowise_dir)
        for search_dir in search_dirs:
            for json_file in sorted(search_dir.glob("*.json")):
                results.extend(self._parse_chatflow_file(json_file))
        return results

    def _parse_chatflow_file(self, file_path: Path) -> list[ParsedSkill]:
        """Parse a single Flowise chatflow JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            List of ParsedSkill instances from this file.
        """
        data = safe_load_json(file_path)
        if data is None or not is_flowise_chatflow(data):
            return []
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raw_content = ""

        nodes = data.get("nodes", [])
        if not isinstance(nodes, list):
            return []

        code_blocks = extract_code_blocks(nodes)
        all_code = "\n".join(code_blocks)

        combined_env = sorted(set(
            extract_env_vars(all_code) + extract_credentials(nodes)
        ))

        return [ParsedSkill(
            name=file_path.stem,
            version="unknown",
            source_path=file_path,
            format="flowise",
            description=self._build_description(nodes),
            instructions="",
            declared_capabilities=get_node_types(nodes),
            dependencies=extract_node_dependencies(code_blocks),
            code_blocks=code_blocks,
            urls=extract_urls(raw_content),
            env_vars_referenced=combined_env,
            shell_commands=extract_shell_commands(all_code),
            raw_content=raw_content,
        )]

    @staticmethod
    def _build_description(nodes: list[dict[str, Any]]) -> str:
        """Build a human-readable description from node labels.

        Args:
            nodes: List of Flowise node dicts.

        Returns:
            Description string summarising the chatflow components.
        """
        labels: list[str] = []
        for node in nodes:
            data = node.get("data", {})
            if isinstance(data, dict):
                label = data.get("label", "")
                if label:
                    labels.append(str(label))
        if not labels:
            return "Flowise chatflow"
        return f"Flowise chatflow: {', '.join(labels)}"
