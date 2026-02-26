"""ASBOMGenerator — produce CycloneDX 1.6 Agent Skill Bill of Materials.

This module houses the main entry point for ASBOM generation.  It
accumulates ``SkillComponent`` instances (directly or via parsed-skill
integration) and then serialises a CycloneDX 1.6 compliant JSON document.

Design Decision — Pure Python Implementation
---------------------------------------------
The ASBOM is generated as a Python dict and serialised via ``json.dumps``.
This avoids a hard runtime dependency on ``cyclonedx-python-lib`` while still
producing output that validates against the CycloneDX 1.6 JSON schema.

References
----------
.. [CDX16] CycloneDX Specification v1.6 (2024). https://cyclonedx.org/specification/overview/
.. [EUAIA] EU AI Act, Article 17: Quality Management System.
.. [NIST]  NIST AI Risk Management Framework (AI RMF 1.0), MAP 3.4.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skillfortify.core.sbom.models import ASBOMMetadata, SkillComponent

if TYPE_CHECKING:
    from skillfortify.core.analyzer import AnalysisResult
    from skillfortify.parsers.base import ParsedSkill


class ASBOMGenerator:
    """Generate Agent Skill Bill of Materials in CycloneDX 1.6 format.

    The ASBOM provides a complete inventory of all agent skills in a project,
    along with their security analysis results, trust scores, capabilities,
    and dependency relationships.

    The generator accumulates ``SkillComponent`` instances (either directly
    or via ``add_from_parsed_skill``) and then produces a CycloneDX 1.6
    compliant JSON document.

    Usage::

        gen = ASBOMGenerator()
        gen.add_component(SkillComponent(name="weather", version="1.0", format="mcp"))
        print(gen.to_json())

    Output format: CycloneDX 1.6 JSON (pure Python, no external dependencies).
    """

    def __init__(self, metadata: ASBOMMetadata | None = None) -> None:
        self._metadata = metadata or ASBOMMetadata()
        self._components: list[SkillComponent] = []

    # -- Mutation -----------------------------------------------------------

    def add_component(self, component: SkillComponent) -> None:
        """Add a skill component to the ASBOM.

        Duplicate detection is *not* performed -- the caller is responsible
        for avoiding double-adds.  This mirrors how CycloneDX treats
        components: each entry is an independent declaration.
        """
        self._components.append(component)

    def add_from_parsed_skill(
        self,
        skill: ParsedSkill,
        analysis_result: AnalysisResult | None = None,
        trust_score: float | None = None,
        trust_level: str | None = None,
    ) -> None:
        """Create and add a component from SkillFortify pipeline outputs.

        This is the primary integration point.  It accepts the outputs of
        the parser, analyzer, and (optionally) trust engine, and assembles
        a ``SkillComponent`` with the union of all available metadata.

        Args:
            skill: A ``ParsedSkill`` instance from ``skillfortify.parsers.base``.
            analysis_result: Optional ``AnalysisResult`` from
                ``skillfortify.core.analyzer``.
            trust_score: Optional numeric trust score ``[0.0, 1.0]``.
            trust_level: Optional human-readable trust tier string.
        """
        is_safe = True
        findings_count = 0
        if analysis_result is not None:
            is_safe = analysis_result.is_safe
            findings_count = len(analysis_result.findings)

        component = SkillComponent(
            name=skill.name,
            version=skill.version,
            format=skill.format,
            capabilities=list(skill.declared_capabilities),
            is_safe=is_safe,
            findings_count=findings_count,
            trust_score=trust_score,
            trust_level=trust_level,
            dependencies=list(skill.dependencies),
            source_path=str(skill.source_path),
        )
        self._components.append(component)

    # -- Generation --------------------------------------------------------

    def generate(self) -> dict[str, Any]:
        """Generate the complete CycloneDX 1.6 ASBOM as a Python dict.

        Produces a dict whose structure validates against the CycloneDX 1.6
        JSON schema.  The ``serialNumber`` is a fresh UUID-4 on each call,
        and ``metadata.timestamp`` defaults to UTC *now* if not set.
        """
        ts = self._metadata.timestamp or datetime.now(timezone.utc)

        bom: dict[str, Any] = {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "version": 1,
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "metadata": {
                "timestamp": ts.isoformat(),
                "tools": {
                    "components": [
                        {
                            "type": "application",
                            "name": "skillfortify",
                            "version": self._metadata.skillfortify_version,
                            "properties": [
                                {"name": "skillfortify:provenance", "value": "sf-e94b3c8b10240fab"},
                            ],
                        }
                    ]
                },
                "component": {
                    "type": "application",
                    "name": self._metadata.project_name,
                    "version": self._metadata.project_version,
                },
            },
            "components": [c.to_cyclonedx_component() for c in self._components],
            "dependencies": [c.to_cyclonedx_dependency() for c in self._components],
        }
        return bom

    def to_json(self, indent: int = 2) -> str:
        """Generate CycloneDX 1.6 JSON string.

        Args:
            indent: JSON indentation level.  Use ``0`` or ``None`` for
                compact output.

        Returns:
            A JSON string conforming to CycloneDX 1.6 schema.
        """
        return json.dumps(self.generate(), indent=indent)

    def write_json(self, path: Path) -> None:
        """Write the ASBOM to a JSON file.

        Creates parent directories if they do not exist.

        Args:
            path: Destination file path (typically ``asbom.cdx.json``).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    # -- Queries -----------------------------------------------------------

    @property
    def component_count(self) -> int:
        """Number of components in the ASBOM."""
        return len(self._components)

    @property
    def components(self) -> list[SkillComponent]:
        """Read-only view of the accumulated components."""
        return list(self._components)

    def summary(self) -> dict[str, Any]:
        """Return a human-friendly summary of the ASBOM.

        Returns a dict with:
        - ``total``: total number of skill components
        - ``safe``: count with ``is_safe == True``
        - ``unsafe``: count with ``is_safe == False``
        - ``total_findings``: sum of all findings across components
        - ``formats``: mapping of format -> count
        - ``trust_distribution``: mapping of trust_level -> count
            (components without a trust level are grouped under ``"UNSCORED"``)
        """
        safe = sum(1 for c in self._components if c.is_safe)
        unsafe = sum(1 for c in self._components if not c.is_safe)
        total_findings = sum(c.findings_count for c in self._components)

        formats: dict[str, int] = {}
        for c in self._components:
            formats[c.format] = formats.get(c.format, 0) + 1

        trust_dist: dict[str, int] = {}
        for c in self._components:
            key = c.trust_level if c.trust_level is not None else "UNSCORED"
            trust_dist[key] = trust_dist.get(key, 0) + 1

        return {
            "total": len(self._components),
            "safe": safe,
            "unsafe": unsafe,
            "total_findings": total_findings,
            "formats": formats,
            "trust_distribution": trust_dist,
        }
