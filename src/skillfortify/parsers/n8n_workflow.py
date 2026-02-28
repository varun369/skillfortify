"""Parser for n8n workflow automation definitions (JSON export format).

n8n is the largest open-source workflow automation platform (177K+ GitHub
stars as of March 2026). Workflows are exported as JSON files containing
a ``nodes`` array where each node represents an operation.

References:
    n8n documentation: https://docs.n8n.io/workflows/
"""

from __future__ import annotations

from pathlib import Path

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.n8n_extractors import (
    N8N_DIR,
    _SHELL_COMMAND_PATTERN,
    extract_node_capabilities,
    extract_node_code,
    extract_node_credentials,
    extract_node_shell_commands,
    extract_node_urls,
    is_n8n_workflow,
    safe_load_json,
)


class N8nWorkflowParser(SkillParser):
    """Parser for n8n workflow JSON exports.

    Discovery:
        1. Check for ``*.workflow.json`` files.
        2. Check for JSON files with n8n node type prefixes in ``nodes``.
        3. Check for ``.n8n/`` directory.
    """

    def can_parse(self, path: Path) -> bool:
        """Probe a directory for n8n workflow definitions."""
        if (path / N8N_DIR).is_dir():
            return True
        for json_file in path.glob("*.workflow.json"):
            if json_file.is_file():
                return True
        for json_file in path.glob("*.json"):
            data = safe_load_json(json_file)
            if data is not None and is_n8n_workflow(data):
                return True
        return False

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all n8n workflow files in a directory."""
        results: list[ParsedSkill] = []
        seen: set[Path] = set()
        for json_file in sorted(path.glob("*.workflow.json")):
            skill = self._parse_workflow_file(json_file)
            if skill is not None:
                results.append(skill)
                seen.add(json_file.resolve())
        for json_file in sorted(path.glob("*.json")):
            if json_file.resolve() in seen:
                continue
            data = safe_load_json(json_file)
            if data is not None and is_n8n_workflow(data):
                skill = self._parse_workflow_file(json_file)
                if skill is not None:
                    results.append(skill)
        return results

    def _parse_workflow_file(self, file_path: Path) -> ParsedSkill | None:
        """Parse a single n8n workflow JSON file."""
        data = safe_load_json(file_path)
        if data is None or not is_n8n_workflow(data):
            return None
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raw_content = ""

        workflow_name = str(data.get("name", file_path.stem))
        nodes = data.get("nodes", [])
        if not isinstance(nodes, list):
            nodes = []

        all_urls: list[str] = []
        all_code: list[str] = []
        all_shell: list[str] = []
        all_creds: list[str] = []
        all_caps: list[str] = []
        node_types: list[str] = []

        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("type", ""))
            if node_type:
                node_types.append(node_type)
            all_urls.extend(extract_node_urls(node))
            all_code.extend(extract_node_code(node))
            all_shell.extend(extract_node_shell_commands(node))
            all_creds.extend(extract_node_credentials(node))
            all_caps.extend(extract_node_capabilities(node))
            for code_block in extract_node_code(node):
                all_shell.extend(_SHELL_COMMAND_PATTERN.findall(code_block))

        seen_caps: set[str] = set()
        unique_caps: list[str] = []
        for cap in all_caps:
            if cap not in seen_caps:
                seen_caps.add(cap)
                unique_caps.append(cap)

        description_parts = [f"n8n workflow: {workflow_name}"]
        if node_types:
            description_parts.append(
                f"Nodes: {', '.join(sorted(set(node_types)))}"
            )

        return ParsedSkill(
            name=workflow_name,
            version=str(data.get("versionId", "unknown")),
            source_path=file_path,
            format="n8n",
            description="; ".join(description_parts),
            instructions="",
            declared_capabilities=unique_caps,
            dependencies=sorted(set(node_types)),
            code_blocks=all_code,
            urls=all_urls,
            env_vars_referenced=sorted(set(all_creds)),
            shell_commands=all_shell,
            raw_content=raw_content,
        )
