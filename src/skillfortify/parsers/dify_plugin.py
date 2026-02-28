"""Parser for Dify plugin definitions (manifest.yaml / manifest.json).

Dify is an open-source LLM app development platform (100K+ GitHub stars)
with an active plugin marketplace. Plugins are defined via manifest files
that declare tool identity, parameters, credential requirements, and
endpoint configurations.

Detection signals:
    - ``manifest.yaml`` / ``manifest.json`` with Dify plugin schema
      (top-level ``type`` in {tool, model, extension, bundle}).
    - ``.dify/`` directory presence.
    - Provider YAML files with ``credentials_for_provider`` blocks.

Security Relevance:
    Dify plugins can declare credentials, access external endpoints, and
    reference environment variables. The parser extracts all of these for
    downstream threat analysis via the capability lattice and DY-Skill
    threat model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from skillfortify.parsers.base import ParsedSkill, SkillParser
from skillfortify.parsers.dify_plugin_extractors import (
    DIFY_MANIFEST_FILENAMES,
    DIFY_PLUGIN_DIR,
    PROVIDER_CREDENTIAL_KEY,
    YAML_EXTENSIONS,
    extract_credentials,
    extract_dependencies,
    extract_env_vars,
    extract_shell_commands,
    extract_tool_descriptions,
    extract_urls,
    is_dify_manifest,
    parse_multi_tools,
    safe_load_json,
    safe_load_yaml,
)


class DifyPluginParser(SkillParser):
    """Parser for Dify plugin manifest files and provider configs.

    Discovery:
        1. Check for manifest.yaml / manifest.json with Dify schema.
        2. Check for .dify/ directory.
        3. Check for provider YAML files with credentials_for_provider.

    Parse logic:
        1. Load manifest and validate Dify schema.
        2. Extract plugin name, version, author, description.
        3. Extract tool definitions (single or multi-tool).
        4. Extract credentials, URLs, env vars, shell commands.
        5. Construct ParsedSkill instances with format="dify".
    """

    def can_parse(self, path: Path) -> bool:
        """Probe a directory for Dify plugin definitions.

        Args:
            path: Root directory to probe.

        Returns:
            True if Dify plugin files are detected.
        """
        for filename in DIFY_MANIFEST_FILENAMES:
            manifest_path = path / filename
            if manifest_path.is_file():
                data = self._load_manifest(manifest_path)
                if data is not None and is_dify_manifest(data):
                    return True
        if (path / DIFY_PLUGIN_DIR).is_dir():
            return True
        return False

    def parse(self, path: Path) -> list[ParsedSkill]:
        """Parse all Dify plugin definitions in a directory.

        Args:
            path: Root directory to scan.

        Returns:
            List of ParsedSkill instances. Empty if none found.
        """
        results: list[ParsedSkill] = []
        results.extend(self._parse_manifests(path))
        results.extend(self._parse_dify_dir(path))
        results.extend(self._parse_provider_files(path))
        return results

    def _load_manifest(self, file_path: Path) -> dict[str, Any] | None:
        """Load a manifest file (YAML or JSON).

        Args:
            file_path: Path to the manifest file.

        Returns:
            Parsed dict, or None on error.
        """
        if file_path.suffix == ".json":
            return safe_load_json(file_path)
        return safe_load_yaml(file_path)

    def _parse_manifests(self, path: Path) -> list[ParsedSkill]:
        """Parse manifest files in the directory root.

        Args:
            path: Root directory.

        Returns:
            List of ParsedSkill from manifest files.
        """
        results: list[ParsedSkill] = []
        for filename in DIFY_MANIFEST_FILENAMES:
            manifest_path = path / filename
            if not manifest_path.is_file():
                continue
            data = self._load_manifest(manifest_path)
            if data is None or not is_dify_manifest(data):
                continue
            results.extend(self._skills_from_manifest(data, manifest_path))
        return results

    def _skills_from_manifest(
        self, data: dict[str, Any], file_path: Path,
    ) -> list[ParsedSkill]:
        """Build ParsedSkill instances from a validated manifest.

        Args:
            data: Parsed manifest dict.
            file_path: Path to the manifest file.

        Returns:
            List of ParsedSkill instances.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raw_content = ""

        plugin_name = str(data.get("name", file_path.stem))
        plugin_version = str(data.get("version", "unknown"))
        plugin_description = extract_tool_descriptions(data)

        all_urls = extract_urls(raw_content)
        all_env_vars = extract_env_vars(raw_content)
        all_shell = extract_shell_commands(raw_content)
        all_deps = extract_dependencies(data)

        all_creds = extract_credentials(data)
        tool_block = data.get("tool", {})
        if isinstance(tool_block, dict):
            all_creds.extend(extract_credentials(tool_block))
        for tool_def in parse_multi_tools(data):
            all_creds.extend(extract_credentials(tool_def))

        combined_env = sorted(set(all_env_vars + all_creds))

        return [ParsedSkill(
            name=plugin_name,
            version=plugin_version,
            source_path=file_path,
            format="dify",
            description=plugin_description,
            instructions="",
            declared_capabilities=[str(data.get("type", "tool"))],
            dependencies=all_deps,
            code_blocks=[],
            urls=all_urls,
            env_vars_referenced=combined_env,
            shell_commands=all_shell,
            raw_content=raw_content,
        )]

    def _parse_dify_dir(self, path: Path) -> list[ParsedSkill]:
        """Parse YAML files inside a .dify/ directory.

        Args:
            path: Root directory.

        Returns:
            List of ParsedSkill from .dify/ contents.
        """
        dify_dir = path / DIFY_PLUGIN_DIR
        if not dify_dir.is_dir():
            return []
        results: list[ParsedSkill] = []
        for ext in YAML_EXTENSIONS:
            for yaml_file in sorted(dify_dir.glob(ext)):
                data = safe_load_yaml(yaml_file)
                if data is None:
                    continue
                results.extend(self._skills_from_manifest(data, yaml_file))
        return results

    def _parse_provider_files(self, path: Path) -> list[ParsedSkill]:
        """Parse provider YAML files that are not manifests.

        Args:
            path: Root directory.

        Returns:
            List of ParsedSkill from provider files.
        """
        results: list[ParsedSkill] = []
        manifest_names = set(DIFY_MANIFEST_FILENAMES)
        for ext in YAML_EXTENSIONS:
            for yaml_file in sorted(path.glob(ext)):
                if yaml_file.name in manifest_names:
                    continue
                data = safe_load_yaml(yaml_file)
                if data is None:
                    continue
                if PROVIDER_CREDENTIAL_KEY not in data:
                    continue
                skill = self._skill_from_provider(data, yaml_file)
                if skill is not None:
                    results.append(skill)
        return results

    def _skill_from_provider(
        self, data: dict[str, Any], file_path: Path,
    ) -> ParsedSkill | None:
        """Build a ParsedSkill from a provider config file.

        Args:
            data: Parsed provider YAML dict.
            file_path: Path to the provider file.

        Returns:
            ParsedSkill, or None if insufficient data.
        """
        try:
            raw_content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raw_content = ""

        identity = data.get("identity", {})
        if not isinstance(identity, dict):
            identity = {}

        name = str(identity.get("name", file_path.stem))
        description_raw = identity.get("description", "")
        if isinstance(description_raw, dict):
            description = str(
                description_raw.get(
                    "en_US", next(iter(description_raw.values()), "")
                )
            )
        elif isinstance(description_raw, str):
            description = description_raw
        else:
            description = ""

        creds = extract_credentials(data)
        all_env_vars = extract_env_vars(raw_content)
        combined_env = sorted(set(all_env_vars + creds))

        return ParsedSkill(
            name=name,
            version="unknown",
            source_path=file_path,
            format="dify",
            description=description,
            instructions="",
            declared_capabilities=["provider"],
            dependencies=[],
            code_blocks=[],
            urls=extract_urls(raw_content),
            env_vars_referenced=combined_env,
            shell_commands=[],
            raw_content=raw_content,
        )
