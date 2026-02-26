"""Data models for the Agent Skill Bill of Materials (ASBOM).

Contains ``SkillComponent`` (one entry in the ASBOM) and ``ASBOMMetadata``
(document-level metadata), plus the version-resolution helper used to stamp
the producing SkillFortify version into every generated document.

CycloneDX 1.6 Conformance
--------------------------
``SkillComponent.to_cyclonedx_component()`` produces a dict that satisfies
the CycloneDX 1.6 ``component`` schema, while
``to_cyclonedx_dependency()`` satisfies the ``dependency`` schema.  Component
``purl`` values use the ``pkg:agent-skill`` namespace.

References
----------
.. [CDX16] CycloneDX Specification v1.6 (2024). https://cyclonedx.org/specification/overview/
.. [PURL]  Package URL specification. https://github.com/package-url/purl-spec
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# SkillFortify version helpers
# ---------------------------------------------------------------------------

_SKILLFORTIFY_VERSION_DEFAULT = "0.1.0"


def _resolve_skillfortify_version() -> str:
    """Attempt to read the installed skillfortify version from package metadata."""
    try:
        from importlib.metadata import version

        return version("skillfortify")
    except Exception:
        return _SKILLFORTIFY_VERSION_DEFAULT


# ---------------------------------------------------------------------------
# SkillComponent: one entry in the ASBOM
# ---------------------------------------------------------------------------


@dataclass
class SkillComponent:
    """A skill component for the ASBOM.

    Represents a single agent skill in the bill of materials, carrying all
    security-relevant metadata produced by SkillFortify's analysis pipeline.

    Attributes:
        name: Human-readable skill identifier (e.g. ``"weather-api"``).
        version: Semantic version string.  ``"unknown"`` when the format
            does not declare a version.
        format: Parser format identifier (``"claude"``, ``"mcp"``,
            ``"openclaw"``).
        capabilities: Capability strings in ``"resource:LEVEL"`` form.
        is_safe: ``True`` if the analyzer produced zero findings.
        findings_count: Total number of security findings.
        trust_score: Numeric trust score in ``[0.0, 1.0]`` or ``None``.
        trust_level: Human-readable trust tier, e.g. ``"COMMUNITY_VERIFIED"``.
        dependencies: Names of skills this component depends on.
        source_path: File-system path to the skill source (informational).
    """

    name: str
    version: str
    format: str  # "claude", "mcp", "openclaw"
    capabilities: list[str] = field(default_factory=list)
    is_safe: bool = True
    findings_count: int = 0
    trust_score: float | None = None
    trust_level: str | None = None
    dependencies: list[str] = field(default_factory=list)
    source_path: str = ""

    @property
    def purl(self) -> str:
        """Package URL for this skill component.

        Uses the ``pkg:agent-skill`` namespace, a domain-specific extension
        of the PURL specification for agent skill packages.
        """
        return f"pkg:agent-skill/{self.name}@{self.version}"

    # -- CycloneDX serialisation helpers -----------------------------------

    def to_cyclonedx_component(self) -> dict[str, Any]:
        """Serialise to a CycloneDX 1.6 ``component`` dict."""
        props: list[dict[str, str]] = [
            {"name": "skillfortify:format", "value": self.format},
            {"name": "skillfortify:is-safe", "value": str(self.is_safe).lower()},
            {"name": "skillfortify:findings-count", "value": str(self.findings_count)},
        ]
        if self.capabilities:
            props.append(
                {"name": "skillfortify:capabilities", "value": ",".join(self.capabilities)}
            )
        if self.trust_score is not None:
            props.append(
                {"name": "skillfortify:trust-score", "value": f"{self.trust_score:.2f}"}
            )
        if self.trust_level is not None:
            props.append({"name": "skillfortify:trust-level", "value": self.trust_level})
        if self.source_path:
            props.append({"name": "skillfortify:source-path", "value": self.source_path})

        component: dict[str, Any] = {
            "type": "library",
            "name": self.name,
            "version": self.version,
            "purl": self.purl,
            "properties": props,
        }
        return component

    def to_cyclonedx_dependency(self) -> dict[str, Any]:
        """Serialise to a CycloneDX 1.6 ``dependency`` dict."""
        dep: dict[str, Any] = {"ref": self.purl}
        if self.dependencies:
            dep["dependsOn"] = [
                f"pkg:agent-skill/{d}@unknown" for d in self.dependencies
            ]
        return dep


# ---------------------------------------------------------------------------
# ASBOMMetadata: top-level metadata for the ASBOM document
# ---------------------------------------------------------------------------


@dataclass
class ASBOMMetadata:
    """Metadata for the ASBOM document.

    Attributes:
        project_name: Name of the agent project being inventoried.
        project_version: Version of the agent project.
        skillfortify_version: Version of SkillFortify that produced the ASBOM.
        timestamp: When the ASBOM was generated (UTC).  Defaults to *now*
            when ``generate()`` is called if left as ``None``.
    """

    project_name: str = "agent-project"
    project_version: str = "0.0.0"
    skillfortify_version: str = ""
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if not self.skillfortify_version:
            self.skillfortify_version = _resolve_skillfortify_version()
