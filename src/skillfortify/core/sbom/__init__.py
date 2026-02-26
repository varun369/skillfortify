"""Agent Skill Bill of Materials (ASBOM) generator in CycloneDX 1.6 format.

This package produces a CycloneDX 1.6 compliant JSON document describing every
agent skill installed in a project, together with security metadata produced by
SkillFortify's analysis pipeline.  The output enables:

- **Compliance auditing**: EU AI Act Article 17 requires documentation of
  third-party AI components.  NIST AI RMF MAP 3.4 calls for inventories of
  software dependencies including AI plugins.
- **Supply chain visibility**: A complete, machine-readable inventory of every
  skill, its version, declared capabilities, trust level, and analysis verdict.
- **Vulnerability tracking**: When a skill is later found to be malicious (as
  happened with 1,200 skills during the ClawHavoc campaign), the ASBOM allows
  rapid identification of affected projects.
- **Reproducible configurations**: Pin exact skill versions so that an agent
  project can be rebuilt identically months later.
"""

from skillfortify.core.sbom.generator import ASBOMGenerator
from skillfortify.core.sbom.models import (
    ASBOMMetadata,
    SkillComponent,
    _SKILLFORTIFY_VERSION_DEFAULT,
    _resolve_skillfortify_version,
)

__all__ = [
    "ASBOMGenerator",
    "ASBOMMetadata",
    "SkillComponent",
    "_SKILLFORTIFY_VERSION_DEFAULT",
    "_resolve_skillfortify_version",
]
